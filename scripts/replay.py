"""
Data replay script for OikosNomos

Simulates IoT device readings by replaying historical data as MQTT messages.
Can run in real-time or accelerated mode.
"""

import paho.mqtt.client as mqtt
import pandas as pd
import time
import json
import argparse
from datetime import datetime, timedelta
import sys
from pathlib import Path

class DataReplayer:
    def __init__(self, broker_host="localhost", broker_port=1883, home_id="home_001"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.home_id = home_id
        self.client = None
        
    def connect(self):
        """Connect to MQTT broker"""
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="data_replayer")
        self.connected = False
        
        def on_connect(client, userdata, flags, reason_code, properties):
            self.connected = True
            if reason_code == 0:
                print(f"✓ Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            else:
                print(f"✗ Connection failed with code {reason_code}")
                sys.exit(1)
        
        self.client.on_connect = on_connect
        self.client.connect(self.broker_host, self.broker_port, 60)
        self.client.loop_start()
        
        # Wait for connection to be established
        timeout = 5
        start = time.time()
        while not self.connected and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        if not self.connected:
            print("✗ Connection timeout")
            sys.exit(1)
        
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            time.sleep(0.5)  # Allow time for final messages to be sent
            self.client.loop_stop()
            self.client.disconnect()
            print("✓ Disconnected from MQTT broker")
    
    def publish_reading(self, device_category, power_w, energy_wh, timestamp=None):
        """Publish a power reading to MQTT"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Ensure timestamp has timezone info for proper ISO format
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=None)
            timestamp_str = timestamp.isoformat() + "Z"
        else:
            timestamp_str = timestamp.isoformat()
        
        payload = {
            "timestamp": timestamp_str,
            "device_category": device_category,
            "power_w": power_w,
            "energy_wh": energy_wh
        }
        
        topic = f"home/{self.home_id}/device/{device_category}/power"
        result = self.client.publish(topic, json.dumps(payload), qos=1)
        rc = result.wait_for_publish()
        if result.rc != 0:
            print(f"✗ Publish failed: {result.rc}")
    
    def replay_from_csv(self, csv_path, speed_multiplier=1.0, start_date=None, duration_hours=None):
        """
        Replay historical data from CSV file
        
        Args:
            csv_path: Path to CSV file with columns: timestamp, consumption_kwh, temperature_c, etc.
            speed_multiplier: Speed multiplier (1.0 = real-time, 60.0 = 1 hour in 1 minute)
            start_date: Optional start date to begin replay from
            duration_hours: Optional duration in hours to replay
        """
        print(f"Loading data from {csv_path}...")
        df = pd.read_csv(csv_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Filter by start date if specified
        if start_date:
            start_dt = pd.to_datetime(start_date)
            df = df[df['timestamp'] >= start_dt]
        
        # Limit duration if specified
        if duration_hours:
            end_dt = df['timestamp'].iloc[0] + timedelta(hours=duration_hours)
            df = df[df['timestamp'] <= end_dt]
        
        if df.empty:
            print("✗ No data to replay")
            return
        
        print(f"✓ Loaded {len(df)} records")
        print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Speed: {speed_multiplier}x")
        print(f"  Duration: {(df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600:.1f} hours")
        print()
        
        # Device category distribution (simplified model)
        device_mix = {
            'base_load': 0.15,
            'office': 0.10,
            'hvac': 0.50,
            'garden_pump': 0.05,
            'ev_charger': 0.20
        }
        
        start_time = time.time()
        last_timestamp = None
        
        for idx, row in df.iterrows():
            current_timestamp = row['timestamp']
            
            # Calculate sleep time based on time difference and speed multiplier
            if last_timestamp is not None:
                time_diff = (current_timestamp - last_timestamp).total_seconds()
                sleep_time = time_diff / speed_multiplier
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # Split consumption into device categories
            total_power_w = row['consumption_kwh'] * 1000  # Convert kWh to W (assuming hourly data)
            
            for category, fraction in device_mix.items():
                power_w = total_power_w * fraction
                energy_wh = power_w * (1.0 if 'consumption_kwh' in row.name else 1.0)
                
                self.publish_reading(category, power_w, energy_wh, current_timestamp)
            
            # Progress update every 100 records
            if idx % 100 == 0:
                elapsed = time.time() - start_time
                progress = (idx + 1) / len(df) * 100
                simulated_time = (current_timestamp - df['timestamp'].iloc[0]).total_seconds() / 3600
                print(f"\rProgress: {progress:5.1f}% | Simulated: {simulated_time:6.1f}h | Elapsed: {elapsed:6.1f}s", end="")
            
            last_timestamp = current_timestamp
        
        print(f"\n✓ Replay complete")
    
    def generate_synthetic_data(self, duration_hours=24, interval_seconds=60):
        """
        Generate and publish synthetic data
        
        Args:
            duration_hours: How many hours of data to generate
            interval_seconds: Interval between readings
        """
        import random
        
        print(f"Generating synthetic data for {duration_hours} hours...")
        
        start_time = datetime.now()
        current_time = start_time
        end_time = start_time + timedelta(hours=duration_hours)
        
        device_profiles = {
            'base_load': {'base': 150, 'variance': 20},
            'office': {'base': 100, 'variance': 50, 'active_hours': (8, 18)},
            'hvac': {'base': 1500, 'variance': 500, 'seasonal': True},
            'garden_pump': {'base': 200, 'variance': 50, 'active_hours': (6, 8)},
            'ev_charger': {'base': 7000, 'variance': 1000, 'active_hours': (18, 24)}
        }
        
        iteration = 0
        while current_time < end_time:
            hour = current_time.hour
            
            for category, profile in device_profiles.items():
                # Check if device is active during this hour
                if 'active_hours' in profile:
                    active_start, active_end = profile['active_hours']
                    if not (active_start <= hour < active_end):
                        power_w = profile['base'] * 0.1  # Standby
                    else:
                        power_w = profile['base'] + random.gauss(0, profile['variance'])
                else:
                    power_w = profile['base'] + random.gauss(0, profile['variance'])
                
                power_w = max(0, power_w)
                energy_wh = power_w * (interval_seconds / 3600)
                
                self.publish_reading(category, power_w, energy_wh, current_time)
            
            if iteration % 60 == 0:
                elapsed = (current_time - start_time).total_seconds() / 3600
                print(f"\rSimulated: {elapsed:.1f}h / {duration_hours}h", end="")
            
            current_time += timedelta(seconds=interval_seconds)
            time.sleep(0.1)  # Small delay to avoid overwhelming MQTT
            iteration += 1
        
        print(f"\n✓ Synthetic data generation complete")

def main():
    parser = argparse.ArgumentParser(description="Replay or generate IoT data for OikosNomos")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--home-id", default="home_001", help="Home ID")
    parser.add_argument("--mode", choices=["replay", "synthetic"], default="synthetic",
                        help="Mode: replay CSV or generate synthetic data")
    parser.add_argument("--file", help="CSV file to replay (for replay mode)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Speed multiplier (e.g., 60 = 1 hour in 1 minute)")
    parser.add_argument("--duration", type=float, default=24,
                        help="Duration in hours")
    parser.add_argument("--start-date", help="Start date for replay (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("OikosNomos Data Replayer")
    print("=" * 60)
    
    replayer = DataReplayer(
        broker_host=args.broker,
        broker_port=args.port,
        home_id=args.home_id
    )
    
    try:
        replayer.connect()
        
        if args.mode == "replay":
            if not args.file:
                print("✗ Error: --file required for replay mode")
                sys.exit(1)
            
            if not Path(args.file).exists():
                print(f"✗ Error: File not found: {args.file}")
                sys.exit(1)
            
            replayer.replay_from_csv(
                csv_path=args.file,
                speed_multiplier=args.speed,
                start_date=args.start_date,
                duration_hours=args.duration if args.start_date else None
            )
        else:
            replayer.generate_synthetic_data(
                duration_hours=args.duration,
                interval_seconds=60
            )
    
    except KeyboardInterrupt:
        print("\n\n✓ Stopped by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        replayer.disconnect()

if __name__ == "__main__":
    main()

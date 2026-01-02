"""
Load historical data into TimescaleDB

This script loads historical consumption data from CSV into the database
for model training and analysis.
"""

import psycopg2
import pandas as pd
import argparse
from datetime import datetime
import sys

def load_historical_data(csv_path, db_config, home_id="home_001"):
    """
    Load historical data from CSV into database
    
    Expected CSV columns:
    - timestamp: ISO format datetime
    - consumption_kwh: Energy consumption in kWh
    - temperature_c: Outdoor temperature (optional)
    - humidity: Humidity percentage (optional)
    - device_phase: Device phase label (optional)
    """
    print(f"Loading data from {csv_path}...")
    
    # Read CSV
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} records from CSV")
    
    # Validate required columns
    if 'timestamp' not in df.columns or 'consumption_kwh' not in df.columns:
        print("✗ Error: CSV must have 'timestamp' and 'consumption_kwh' columns")
        sys.exit(1)
    
    # Parse timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Total consumption: {df['consumption_kwh'].sum():.1f} kWh")
    
    # Connect to database
    print("\nConnecting to database...")
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    print("✓ Connected")
    
    # Insert data
    print("\nInserting data into raw_readings table...")
    
    # Simple device distribution for historical data
    device_mix = {
        'base_load': 0.15,
        'office': 0.10,
        'hvac': 0.50,
        'garden_pump': 0.05,
        'ev_charger': 0.20
    }
    
    inserted = 0
    batch_size = 1000
    batch = []
    
    for idx, row in df.iterrows():
        timestamp = row['timestamp']
        total_kwh = row['consumption_kwh']
        total_w = total_kwh * 1000  # Convert to watts (assuming hourly data)
        
        # Split across device categories
        for category, fraction in device_mix.items():
            power_w = total_w * fraction
            energy_wh = power_w  # For 1-hour intervals
            
            batch.append((
                timestamp,
                home_id,
                category,
                power_w,
                energy_wh,
                None  # metadata
            ))
            
            if len(batch) >= batch_size:
                cur.executemany(
                    """
                    INSERT INTO raw_readings (timestamp, home_id, device_category, power_w, energy_wh, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    batch
                )
                conn.commit()
                inserted += len(batch)
                print(f"\r  Inserted: {inserted:,} records", end="")
                batch = []
    
    # Insert remaining batch
    if batch:
        cur.executemany(
            """
            INSERT INTO raw_readings (timestamp, home_id, device_category, power_w, energy_wh, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            batch
        )
        conn.commit()
        inserted += len(batch)
        print(f"\r  Inserted: {inserted:,} records")
    
    # Insert weather data if available
    if 'temperature_c' in df.columns:
        print("\nInserting weather data...")
        weather_inserted = 0
        
        for idx, row in df.iterrows():
            if pd.notna(row.get('temperature_c')):
                cur.execute(
                    """
                    INSERT INTO weather (timestamp, location_id, temp_c, humidity, source)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        row['timestamp'],
                        'location_001',
                        row['temperature_c'],
                        row.get('humidity'),
                        'historical_data'
                    )
                )
                weather_inserted += 1
        
        conn.commit()
        print(f"✓ Inserted {weather_inserted} weather records")
    
    # Refresh continuous aggregates
    print("\nRefreshing continuous aggregates...")
    cur.execute("CALL refresh_continuous_aggregate('hourly_consumption', NULL, NULL);")
    cur.execute("CALL refresh_continuous_aggregate('daily_consumption', NULL, NULL);")
    conn.commit()
    print("✓ Aggregates refreshed")
    
    # Close connection
    cur.close()
    conn.close()
    
    print(f"\n✓ Data load complete!")
    print(f"  Total records inserted: {inserted:,}")

def main():
    parser = argparse.ArgumentParser(description="Load historical data into OikosNomos database")
    parser.add_argument("--file", required=True, help="CSV file to load")
    parser.add_argument("--host", default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=5432, help="Database port")
    parser.add_argument("--user", default="postgres", help="Database user")
    parser.add_argument("--password", default="oikosnomo_dev", help="Database password")
    parser.add_argument("--database", default="oikosnomo", help="Database name")
    parser.add_argument("--home-id", default="home_001", help="Home ID")
    
    args = parser.parse_args()
    
    db_config = {
        'host': args.host,
        'port': args.port,
        'user': args.user,
        'password': args.password,
        'database': args.database
    }
    
    print("=" * 60)
    print("OikosNomos Historical Data Loader")
    print("=" * 60)
    
    try:
        load_historical_data(args.file, db_config, args.home_id)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

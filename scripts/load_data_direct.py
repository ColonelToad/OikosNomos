"""
Direct database loader for OikosNomos - bypasses MQTT for initial data loading
"""

import psycopg2
from datetime import datetime, timedelta
import random

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="oikosnomo",
    user="postgres",
    password="oikosnomo_dev"
)
cursor = conn.cursor()

print("Generating and inserting synthetic data directly to database...")

# Generate 30 days of historical data
start_date = datetime.now() - timedelta(days=30)
home_id = "home_001"

device_profiles = {
    'base_load': {'base': 150, 'variance': 20},
    'office': {'base': 100, 'variance': 50, 'active_hours': (8, 18)},
    'hvac': {'base': 1500, 'variance': 500},
    'garden_pump': {'base': 200, 'variance': 50, 'active_hours': (6, 8)},
    'ev_charger': {'base': 7000, 'variance': 1000, 'active_hours': (18, 24)}
}

# Insert readings every 5 minutes for 30 days
interval_minutes = 5
total_intervals = 30 * 24 * (60 // interval_minutes)

current_time = start_date
records_inserted = 0

for i in range(total_intervals):
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
        energy_wh = power_w * (interval_minutes / 60)
        
        # Insert into database
        cursor.execute(
            """
            INSERT INTO raw_readings (timestamp, home_id, device_category, power_w, energy_wh)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (current_time, home_id, category, power_w, energy_wh)
        )
        records_inserted += 1
    
    current_time += timedelta(minutes=interval_minutes)
    
    if i % 1000 == 0:
        conn.commit()
        print(f"Progress: {i}/{total_intervals} intervals ({records_inserted} records)")

conn.commit()
cursor.close()
conn.close()

print(f"✓ Inserted {records_inserted} readings for {len(device_profiles)} devices over 30 days")
print(f"  Date range: {start_date} to {current_time}")
print(f"\nYou can now train the forecast model with: Invoke-RestMethod -Method POST -Uri 'http://localhost:8001/train'")

"""
Script: generate_and_load_synthetic_data.py
Purpose: Generate and load 10 years of realistic, home-profile-based synthetic data directly into the OikosNomos database.
"""
import psycopg2
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from psycopg2.extras import execute_values

# Database connection settings (update if needed)
DB_SETTINGS = dict(
    host='localhost',
    port=5432,
    user='postgres',
    password='oikosnomo_dev',
    database='oikosnomo'
)

# Home profiles
HOMES = [
    {
        'id': 'home_001', 'name': 'Main House', 'beds': 4, 'baths': 3, 'floors': 2, 'sqft': 2500,
        'appliance_upgrade_year': 2020, 'smart_devices': ['thermostat', 'lighting', 'EV charger', 'solar'],
        'device_mix': ['base_load', 'office', 'hvac', 'garden_pump', 'ev_charger', 'entertainment', 'kitchen'],
        'location_id': 'suburbs'
    },
    {
        'id': 'home_002', 'name': 'Guest House', 'beds': 2, 'baths': 1, 'floors': 1, 'sqft': 900,
        'appliance_upgrade_year': None, 'smart_devices': [],
        'device_mix': ['base_load', 'hvac', 'kitchen', 'entertainment'],
        'location_id': 'rural'
    },
    {
        'id': 'home_003', 'name': 'Apartment', 'beds': 1, 'baths': 1, 'floors': 1, 'sqft': 600,
        'appliance_upgrade_year': 2023, 'smart_devices': ['plugs'],
        'device_mix': ['base_load', 'hvac', 'kitchen', 'entertainment'],
        'location_id': 'downtown'
    },
    {
        'id': 'home_005', 'name': 'Cottage', 'beds': 3, 'baths': 2, 'floors': 1, 'sqft': 1200,
        'appliance_upgrade_year': 2022, 'smart_devices': ['lighting'],
        'device_mix': ['base_load', 'hvac', 'kitchen', 'garden_pump'],
        'location_id': 'lakefront'
    },
    {
        'id': 'home_006', 'name': 'Studio', 'beds': 0, 'baths': 1, 'floors': 1, 'sqft': 400,
        'appliance_upgrade_year': None, 'smart_devices': [],
        'device_mix': ['base_load', 'kitchen', 'entertainment'],
        'location_id': 'city'
    },
]

# Device category base loads (kWh per hour, can be randomized)
DEVICE_LOADS = {
    'base_load': (0.2, 0.3),
    'office': (0.05, 0.15),
    'hvac': (0.2, 2.0),
    'garden_pump': (0.1, 0.5),
    'ev_charger': (0.0, 7.0),
    'entertainment': (0.02, 0.2),
    'kitchen': (0.05, 1.5)
}

# Generate weather data (simple sinusoidal temp/humidity)
def generate_weather(start, end, location_id):
    hours = int((end - start).total_seconds() // 3600)
    timestamps = [start + timedelta(hours=i) for i in range(hours)]
    # Slightly different weather patterns for each location type
    base_temp = {
        'suburbs': 15,
        'rural': 13,
        'downtown': 18,
        'lakefront': 12,
        'city': 17
    }.get(location_id, 15)
    temp_c = base_temp + 10 * np.sin(np.linspace(0, 2 * np.pi, hours))
    humidity = 50 + 20 * np.cos(np.linspace(0, 2 * np.pi, hours))
    location_ids = [location_id] * hours
    return pd.DataFrame({'timestamp': timestamps, 'location_id': location_ids, 'temp_c': temp_c, 'humidity': humidity})

def main():
    conn = psycopg2.connect(**DB_SETTINGS)
    cur = conn.cursor()
    start = datetime(datetime.now().year - 2, 1, 1)
    end = datetime(datetime.now().year, 1, 1)
    print(f"Generating data from {start} to {end}")

    # Insert homes if not present
    for home in HOMES:
        metadata = json.dumps({k: home[k] for k in home if k not in ['id', 'name', 'device_mix', 'location_id']})
        cur.execute("""
            INSERT INTO homes (id, name, location_id, metadata)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (home['id'], home['name'], home['location_id'], metadata))
    conn.commit()

    # Generate and insert weather data for each location type
    location_types = set(home['location_id'] for home in HOMES)
    for loc in location_types:
        weather = generate_weather(start, end, loc)
        # Batch insert in chunks of 1000 rows
        rows = list(weather.itertuples(index=False, name=None))
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            execute_values(cur, """
                INSERT INTO weather (timestamp, location_id, temp_c, humidity)
                VALUES %s
            """, rows[i:i+batch_size])
            conn.commit()

    # Generate and insert readings
    for home in HOMES:
        print(f"Generating readings for {home['id']}")
        readings = []
        for device in home['device_mix']:
            # Simulate device usage pattern
            device_min, device_max = DEVICE_LOADS[device]
            hours = int((end - start).total_seconds() // 3600)
            for i in range(hours):
                ts = start + timedelta(hours=i)
                # Simulate seasonal and daily variation
                hour = ts.hour
                month = ts.month
                # HVAC more in summer/winter, less in spring/fall
                if device == 'hvac':
                    seasonal = 1.5 if month in [1,2,12,6,7,8] else 0.5
                    base = np.random.uniform(device_min, device_max) * seasonal
                # EV charger: only at night, only if home has it
                elif device == 'ev_charger':
                    base = np.random.uniform(0, device_max) if hour in [22,23,0,1,2,3,4,5] else 0
                # Kitchen: more in morning/evening
                elif device == 'kitchen':
                    base = np.random.uniform(device_min, device_max) * (1.5 if hour in [6,7,8,17,18,19] else 0.7)
                else:
                    base = np.random.uniform(device_min, device_max)
                readings.append((ts, home['id'], device, base*1000, base*1000, '{}'))
        execute_values(cur, """
            INSERT INTO raw_readings (timestamp, home_id, device_category, power_w, energy_wh, metadata)
            VALUES %s
        """, readings)
        conn.commit()
        print(f"Inserted {len(readings)} readings for {home['id']}")

    print("Done.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()

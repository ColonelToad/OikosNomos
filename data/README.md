rm# Data Directory

This directory contains historical and example datasets for OikosNomos.

## Required Data Files

### 1. Historical Consumption Data

**File**: `historical_load.csv`

**Columns**:
- `timestamp`: ISO 8601 format (e.g., "2023-01-01T00:00:00Z")
- `consumption_kwh`: Energy consumption in kWh (float)
- `temperature_c`: Outdoor temperature in Celsius (optional)
- `humidity`: Relative humidity percentage (optional)
- `device_phase`: Phase label - "regular", "hybrid", "smart", "de-smart" (optional)

**Resolution**: Hourly (15-minute preferred if available)

**Span**: 10 years recommended (2015-2025) for robust model training

**Sources**:
- [Pecan Street Dataport](https://dataport.pecanstreet.org/) - Austin, TX household data
- [UK DALE](https://jack-kelly.com/data/) - UK household electricity data
- [REFIT](https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements) - UK homes
- [OpenEI Building Data](https://openei.org/datasets/dataset) - Commercial buildings

### 2. Weather Data

**File**: `weather_hourly.csv`

**Columns**:
- `timestamp`: ISO 8601 format
- `location_id`: Location identifier (e.g., "location_001")
- `temp_c`: Temperature in Celsius
- `humidity`: Relative humidity percentage
- `wind_speed_mps`: Wind speed in meters per second (optional)
- `pm25_ugm3`: PM2.5 air quality in µg/m³ (optional)
- `source`: Data source name

**Sources**:
- [NOAA ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) - Historical weather
- [OpenWeatherMap API](https://openweathermap.org/api) - Current and forecast weather

## Example Data

The file `example_historical.csv` contains a minimal 24-hour example. **This is not sufficient for training** - it's only for testing the data loading pipeline.

## Data Preparation

1. **Download real datasets** from sources above
2. **Preprocess** to match the expected schema:
   ```python
   import pandas as pd
   
   # Example preprocessing
   df = pd.read_csv('raw_data.csv')
   df['timestamp'] = pd.to_datetime(df['timestamp'])
   df = df.rename(columns={'kwh': 'consumption_kwh'})
   df = df[['timestamp', 'consumption_kwh', 'temperature_c', 'humidity']]
   df = df.sort_values('timestamp')
   df.to_csv('historical_load.csv', index=False)
   ```

3. **Validate** data quality:
   - No missing timestamps
   - No negative consumption values
   - Reasonable ranges (0.1 - 20 kWh per hour for residential)
   - Temperature in reasonable range (-20°C to 50°C)

4. **Load** into database:
   ```bash
   python scripts/load_historical.py --file data/historical_load.csv
   ```

## Data Privacy

- Do not commit large CSV files to Git (see `.gitignore`)
- Store sensitive data files locally or in secure cloud storage
- Use example/synthetic data for public repositories

## Synthetic Data Generation

If you cannot obtain real data, the replay script can generate synthetic data:

```bash
python scripts/replay.py --mode synthetic --duration 720  # 30 days
```

This generates realistic-looking data but **is not suitable for production model training**.

# Forecast Service

Python FastAPI service for ML-based energy consumption and cost forecasting.

## Features

- LightGBM-based forecasting model
- 1-3 hour ahead predictions
- Time-series feature engineering
- Weather integration
- Model training endpoint
- PostgreSQL/TimescaleDB integration

## API Endpoints

### `GET /health`
Health check.

**Response**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "db_connected": true
}
```

### `POST /predict`
Forecast energy consumption.

**Request**:
```json
{
  "home_id": "home_001",
  "horizon_hours": 3
}
```

**Response**:
```json
{
  "home_id": "home_001",
  "timestamp": "2026-01-02T14:30:00",
  "forecast_kwh": [1.2, 1.3, 1.1],
  "forecast_cost": [0.36, 0.39, 0.33],
  "model_version": "v1.0"
}
```

### `POST /train`
Train or retrain the model.

**Response**:
```json
{
  "status": "success",
  "metrics": {
    "rmse": 0.45,
    "mae": 0.32,
    "mape": 12.5
  },
  "model_version": "v1.0",
  "trained_at": "2026-01-02T14:00:00"
}
```

### `GET /model/info`
Get model information.

## Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload

# Train model
curl -X POST http://localhost:8000/train
```

## Model Details

- **Algorithm**: LightGBM (Gradient Boosting)
- **Features**: Hour, day, month, weather, lags (1h, 24h, 168h), rolling statistics
- **Training data**: 2015-2023 (validation: 2024)
- **Update frequency**: Weekly (or on-demand)

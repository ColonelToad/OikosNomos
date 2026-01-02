# Scenario Service

Python FastAPI service for evaluating device configuration scenarios and cost projections.

## Features

- Device mix configuration evaluation
- Monthly cost and energy projections
- CO2 emissions calculation
- Scenario comparison
- Savings analysis vs current usage
- PostgreSQL storage for scenario history

## API Endpoints

### `POST /scenario/evaluate`
Evaluate a device configuration.

**Request**:
```json
{
  "home_id": "home_001",
  "name": "No EV scenario",
  "device_mix": {
    "base_load": true,
    "office": true,
    "hvac": true,
    "garden_pump": false,
    "ev_charger": false,
    "entertainment": true,
    "kitchen": true
  }
}
```

**Response**:
```json
{
  "scenario_id": 1,
  "home_id": "home_001",
  "name": "No EV scenario",
  "monthly_cost": 85.50,
  "monthly_kwh": 285.0,
  "co2_kg": 119.7,
  "daily_cost": 2.85,
  "savings_vs_current": 34.50,
  "devices_active": {...},
  "created_at": "2026-01-02T14:30:00"
}
```

### `GET /scenario/{scenario_id}`
Get a saved scenario.

### `GET /scenario/home/{home_id}?limit=10`
List recent scenarios for a home.

### `POST /scenario/compare`
Compare multiple scenarios.

**Request**:
```json
[1, 2, 3]
```

**Response**:
```json
{
  "scenarios": [...],
  "comparison": {
    "best_cost": {"scenario_id": 2, "cost": 60.0},
    "worst_cost": {"scenario_id": 1, "cost": 120.0},
    "cost_range": 60.0,
    "avg_cost": 85.0
  }
}
```

### `GET /devices`
List all device categories and profiles.

## Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload
```

## Device Categories

- **base_load**: Always-on devices (3.5 kWh/day)
- **office**: Computer, monitors (2.1 kWh/day)
- **hvac**: Heating/cooling (18.0 kWh/day)
- **garden_pump**: Irrigation (1.2 kWh/day)
- **ev_charger**: Electric vehicle (25.0 kWh/day)
- **entertainment**: TV, streaming (1.8 kWh/day)
- **kitchen**: Appliances (2.5 kWh/day)

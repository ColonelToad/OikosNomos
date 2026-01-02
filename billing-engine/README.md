# Billing Engine

Go-based service for real-time energy billing and cost calculation.

## Features

- MQTT subscriber for device power readings
- Real-time cost calculation with utility tariffs
- 5-minute billing snapshots
- HTTP API for current billing status and history
- PostgreSQL/TimescaleDB storage

## API Endpoints

### `GET /health`
Health check endpoint.

**Response**:
```json
{"status": "healthy"}
```

### `GET /billing/current`
Get current billing information.

**Response**:
```json
{
  "home_id": "home_001",
  "cost_today": 3.45,
  "energy_today_kwh": 12.3,
  "projected_month": 120.50,
  "tariff": "pge_e6_2025"
}
```

### `GET /billing/history`
Get historical billing data (TODO).

## Development

```bash
# Install dependencies
go mod download

# Run locally
export MQTT_BROKER=localhost:1883
export DB_HOST=localhost
go run .

# Build
go build -o billing-engine

# Run tests
go test ./...
```

## MQTT Topics

**Subscribes to**:
- `home/{home_id}/device/+/power`

**Publishes to**:
- `home/{home_id}/billing/today_cost`
- `home/{home_id}/billing/month_projected`
- `home/{home_id}/billing/co2_today`

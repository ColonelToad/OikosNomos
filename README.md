# OikosNomos – Smart Home, Rational Bill

A realistic end-to-end system for modeling the cost and environmental impact of a home as it becomes more "smart" and then "de-smarted."

## Overview

OikosNomos combines:
- **MQTT (Mosquitto)** for IoT telemetry
- **Real utility tariffs** and price data
- **Real-time and historical ML models** for cost forecasting
- **Billing engine** and scenario system
- **LLM + RAG layer** for explaining outputs and exploring scenarios

## Architecture

```
[Simulated Devices] 
     ↓ MQTT publish
[Mosquitto Broker] ←→ [Billing Engine (Go)]
     ↓                      ↓ HTTP API
[TimescaleDB] ←─── [Data Ingestion]
     ↓ read historical
[Forecast Service (Python)] → [RAG Service (Python)]
     ↑ config                     ↑
[Scenario Service (Python)] ─────┘
```

### Services

1. **Mosquitto**: MQTT broker for all IoT telemetry
2. **TimescaleDB**: Time-series database for historical and real-time data
3. **Billing Engine** (Go): Real-time cost computation and tariff application
4. **Forecast Service** (Python/FastAPI): ML-based consumption and cost prediction
5. **Scenario Service** (Python/FastAPI): Device configuration impact estimation
6. **RAG Service** (Python/FastAPI): LLM-powered query interface

## Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) Go 1.21+ for local development
- (Optional) Python 3.10+ for local development
- OpenAI API key (for RAG service)

### Setup

1. **Clone and navigate to the project**:
   ```bash
   cd OikosNomos
   ```

2. **Set environment variables**:
   ```bash
   # Create .env file
   echo "OPENAI_API_KEY=your_key_here" > .env
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Verify services are running**:
   ```bash
   docker-compose ps
   ```

5. **Check logs**:
   ```bash
   docker-compose logs -f
   ```

### Load Initial Data

1. **Initialize database schemas** (runs automatically on first start)

2. **Load historical data**:
   ```bash
   python scripts/load_historical.py --file data/historical_load.csv
   ```

3. **Index RAG documents**:
   ```bash
   python scripts/index_docs.py --docs-dir docs/
   ```

### Run Simulation

Start the data replay simulation:
```bash
python scripts/replay.py --speed 60x  # 1 hour in 1 minute
```

### Query the System

**Forecast API**:
```bash
curl http://localhost:8001/predict
```

**Scenario API**:
```bash
curl -X POST http://localhost:8002/scenario/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "home_id": "home_001",
    "device_mix": {
      "base_load": true,
      "office": true,
      "hvac": true,
      "garden_pump": false,
      "ev_charger": false
    }
  }'
```

**RAG Query**:
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Why is my bill $120?"}'
```

## MQTT Topics

Subscribe to topics to monitor system activity:

```bash
# Install MQTT client
# Windows: Download from https://mosquitto.org/download/
# Linux: apt-get install mosquitto-clients
# Mac: brew install mosquitto

# Monitor all topics
mosquitto_sub -h localhost -t "home/#" -v

# Monitor billing only
mosquitto_sub -h localhost -t "home/+/billing/#" -v
```

### Topic Structure

- `home/{home_id}/device/{category}/power` - Power in Watts
- `home/{home_id}/device/{category}/energy` - Energy in Wh (cumulative)
- `home/{home_id}/environment/indoor/temperature` - Indoor temp (°C)
- `home/{home_id}/environment/indoor/humidity` - Humidity (%)
- `home/{home_id}/billing/current_rate` - Current rate ($/kWh)
- `home/{home_id}/billing/today_cost` - Today's cost ($)
- `home/{home_id}/billing/month_projected` - Projected monthly ($)
- `home/{home_id}/billing/co2_today` - CO₂ today (kg)

## Development

### Project Structure

```
OikosNomos/
├── billing-engine/      # Go service for real-time billing
├── forecast-service/    # Python ML forecasting service
├── scenario-service/    # Python scenario evaluation service
├── rag-service/         # Python LLM+RAG query service
├── database/            # SQL schemas and migrations
├── mosquitto/           # MQTT broker configuration
├── scripts/             # Data loading and simulation scripts
├── docs/                # Documentation for RAG indexing
├── data/                # Historical datasets (not in git)
└── docker-compose.yml   # Service orchestration
```

### Local Development

**Go services**:
```bash
cd billing-engine
go mod download
go run main.go
```

**Python services**:
```bash
cd forecast-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Testing

```bash
# Run billing engine tests
cd billing-engine && go test ./...

# Run Python service tests
cd forecast-service && pytest

# Integration test
python scripts/integration_test.py
```

## Data Sources

The system expects the following data:

1. **Historical load data**: `data/historical_load.csv`
   - Columns: `timestamp`, `consumption_kwh`, `temperature_c`, `humidity`, `device_phase`
   - Resolution: Hourly (15-min preferred)
   - Span: 2015–2025

2. **Tariff definitions**: `database/tariffs/pge_e6_2025.json`

3. **Device profiles**: `database/device_profiles.csv`

4. **Weather data**: `data/weather_hourly.csv`

See `docs/data_requirements.md` for detailed specifications.

## Configuration

### Tariffs

Edit or add tariffs in `database/tariffs/`. Format:

```json
{
  "tariff_id": "example_tariff",
  "utility": "Example Utility",
  "rate_structure": {
    "fixed_charge_monthly": 10.0,
    "energy_charges": [...]
  }
}
```

### Device Profiles

Edit `database/device_profiles.csv` to add or modify device categories.

## Roadmap

- [x] MVP architecture design
- [ ] Milestone 1: Infrastructure setup
- [ ] Milestone 2: Data ingestion
- [ ] Milestone 3: Billing engine
- [ ] Milestone 4: ML forecast service
- [ ] Milestone 5: Scenario engine
- [ ] Milestone 6: RAG document store
- [ ] Milestone 7: RAG query service
- [ ] Milestone 8: End-to-end integration
- [ ] Milestone 9: Monitoring
- [ ] Milestone 10: Documentation

## License

MIT (or specify your license)

## Contributing

See `CONTRIBUTING.md` (TBD)

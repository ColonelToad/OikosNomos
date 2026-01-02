# OikosNomos Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key (or Anthropic API key for Claude)
- 8GB+ RAM recommended
- Git for version control (optional)

## Step 1: Initial Setup

```powershell
# Navigate to project directory
cd C:\Users\legot\OikosNomos

# Create environment file
Copy-Item .env.example .env

# Edit .env and add your API key
notepad .env
# Set: OPENAI_API_KEY=sk-your-key-here
```

## Step 2: Start Services

```powershell
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

Wait about 30 seconds for all services to start and the database to initialize.

## Step 3: Verify Services

```powershell
# Check health endpoints
curl http://localhost:8001/health  # Forecast service
curl http://localhost:8002/health  # Scenario service
curl http://localhost:8003/health  # RAG service
```

## Step 4: Index Documentation

```powershell
# Install Python dependencies for scripts
cd scripts
pip install -r requirements.txt
cd ..

# Index documentation for RAG
python scripts/index_docs.py
```

## Step 5: Start Data Simulation

Open a new terminal and run:

```powershell
# Generate synthetic data (runs for 24 hours of simulation)
python scripts/replay.py --mode synthetic --duration 24
```

This will publish simulated IoT readings to MQTT. Leave this running in the background.

## Step 6: Test the System

### Query the RAG Service

```powershell
curl -X POST http://localhost:8003/query `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"What devices use the most energy?\", \"home_id\": \"home_001\"}'
```

### Check Current Billing

```powershell
# Wait a few minutes for data to accumulate, then:
curl http://localhost:8080/billing/current
```

### Evaluate a Scenario

```powershell
curl -X POST http://localhost:8002/scenario/evaluate `
  -H "Content-Type: application/json" `
  -d '{
    \"home_id\": \"home_001\",
    \"name\": \"No EV Scenario\",
    \"device_mix\": {
      \"base_load\": true,
      \"office\": true,
      \"hvac\": true,
      \"garden_pump\": true,
      \"ev_charger\": false,
      \"entertainment\": true,
      \"kitchen\": true
    }
  }'
```

### Get a Forecast

```powershell
curl -X POST http://localhost:8001/predict `
  -H "Content-Type: application/json" `
  -d '{\"home_id\": \"home_001\", \"horizon_hours\": 3}'
```

## Step 7: Monitor MQTT Messages (Optional)

If you have mosquitto_sub installed:

```powershell
# Install mosquitto clients (one-time)
# Download from https://mosquitto.org/download/

# Monitor all messages
mosquitto_sub -h localhost -t "home/#" -v
```

## Stopping the System

```powershell
# Stop data simulation (Ctrl+C in that terminal)

# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: deletes all data)
docker-compose down -v
```

## Troubleshooting

### Services won't start

```powershell
# Check logs
docker-compose logs <service-name>

# Common issues:
# - Port conflicts: Change ports in docker-compose.yml
# - Memory: Increase Docker memory limit to 4GB+
# - API key: Check .env file
```

### Database connection errors

```powershell
# Database may still be initializing
# Wait 30 seconds and try again

# Force restart database
docker-compose restart timescaledb
```

### RAG service errors

```powershell
# Rebuild index
curl -X POST http://localhost:8003/index/rebuild

# Check if documents exist
ls docs/*.md
```

### No data appearing

```powershell
# Verify replay script is running
# Check MQTT connectivity:
docker-compose logs mosquitto

# Check if billing engine is subscribed:
docker-compose logs billing-engine
```

## Next Steps

1. **Get Real Data**: Download historical consumption data from Pecan Street or UK-DALE
2. **Load Historical Data**: `python scripts/load_historical.py --file data/your_data.csv`
3. **Train Forecast Model**: `curl -X POST http://localhost:8001/train`
4. **Explore Scenarios**: Create and compare different device configurations
5. **Ask Questions**: Use the RAG service to explore your energy usage

## Architecture Overview

```
Port 1883  - MQTT Broker (Mosquitto)
Port 5432  - PostgreSQL/TimescaleDB
Port 8080  - Billing Engine (Go)
Port 8001  - Forecast Service (Python)
Port 8002  - Scenario Service (Python)
Port 8003  - RAG Service (Python)
```

## Development

### Edit Go code (billing-engine)

```powershell
cd billing-engine
go mod download
go run main.go
```

### Edit Python services

```powershell
cd forecast-service
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Rebuild after changes

```powershell
docker-compose build <service-name>
docker-compose up -d <service-name>
```

## Resources

- [Project README](README.md) - Full documentation
- [Architecture Design](docs/project_overview.md) - System overview
- [Device Profiles](docs/device_profiles.md) - Energy consumption reference
- [FAQ](docs/faq.md) - Common questions

## Getting Help

- Check service logs: `docker-compose logs -f <service>`
- Check health endpoints: `curl http://localhost:<port>/health`
- Read service READMEs in each service directory
- Open an issue on GitHub

---

**Congratulations!** Your OikosNomos system is now running. Start exploring your energy usage and scenarios.

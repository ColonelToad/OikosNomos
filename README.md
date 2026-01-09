# OikosNomos – Smart Home, Rational Bill

A realistic end-to-end system for modeling the cost and environmental impact of a home as it becomes more "smart" and then "de-smarted" over time.

## Try the App Online

[Check it out here](https://share.streamlit.io/your-org/oikosnomos/main/ui/app.py)

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
- Python 3.10+ for local development (optional, for scripts)
- Groq API key (for RAG service)

### Setup

1. **Clone and navigate to the project**:
   ```bash
   cd OikosNomos
   ```


2. **Set environment variables**:
   - Copy .env.example to .env and fill in your Groq API key.
   - Set LLM_PROVIDER=groq in .env.


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

1. **Load historical data**:
   ```bash
   python scripts/load_historical.py --file data/historical_load.csv
   ```


### Run Simulation (optional)

To simulate device data:
```bash
python scripts/replay.py --speed 60x
```

**Streamlit Cloud Demo Mode**

If you deploy the UI to Streamlit Cloud but don't host the backend services, enable the demo mode so the app uses bundled sample data:

- In Streamlit Cloud, open your app, go to *Settings → Secrets* and add:

   - `DEMO_MODE=true`

- Alternatively, set the environment variable locally or in your hosting environment:

   - Linux/macOS: `export DEMO_MODE=true`
   - Windows PowerShell: `$env:DEMO_MODE = "true"`

- The demo UI reads sample CSVs from `data/processed/` and does not require the backend services. It still needs the Python dependencies in `requirements.txt`.

When `DEMO_MODE` is enabled the UI will display canned forecasts, billing and scenario results so others can explore the app without a running backend.
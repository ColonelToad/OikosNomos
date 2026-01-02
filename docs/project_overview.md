# OikosNomos Project Overview

## What is OikosNomos?

OikosNomos (Greek: οἶκος "home" + νόμος "law/management") is a smart home billing and scenario analysis system. It helps homeowners understand their energy costs and explore "what-if" scenarios as their homes become more automated and then potentially "de-smarted."

## Core Concept

The system models a home's energy journey through different phases:

1. **Regular** (2015-2018): Traditional appliances, minimal smart devices
2. **Hybrid** (2019-2021): Mix of traditional and smart devices
3. **Smart** (2022-2024): Highly automated with many IoT devices, EV charging
4. **De-smart** (2025+): Selectively removing devices to reduce costs

## Key Questions Answered

- What is my current energy cost and CO₂ footprint?
- How much will I spend this month given current usage?
- Can I ever get back to my 2015 electricity bill?
- Which devices contribute most to my bill?
- What would happen if I removed my EV charger?
- How can I reduce costs while maintaining comfort?

## System Components

### 1. Billing Engine
Real-time cost calculation based on:
- Device-level power consumption
- Utility tariff structures (time-of-use, tiers, demand charges)
- Current and projected monthly costs
- CO₂ emissions tracking

### 2. Forecasting Model
Machine learning predictions for:
- Next 1-3 hours of consumption
- Cost projections
- Anomaly detection (future)

### 3. Scenario Engine
"What-if" analysis:
- Configure device mixes (which devices are active)
- Estimate monthly costs and savings
- Compare scenarios side-by-side

### 4. Intelligent Assistant
Natural language interface:
- Ask questions about your bill
- Explore scenarios conversationally
- Get explanations with citations
- Receive actionable recommendations

## Data Flow

```
IoT Devices → MQTT → Billing Engine → Database
                           ↓
                    Cost Calculation
                           ↓
                      Time-Series DB
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
         Forecast Model          Scenario Engine
              ↓                         ↓
              └────────────┬────────────┘
                           ↓
                      RAG Assistant
                           ↓
                      User Queries
```

## Technology Stack

- **MQTT (Mosquitto)**: IoT message broker
- **TimescaleDB**: Time-series database for consumption data
- **Go**: High-performance billing engine
- **Python**: ML models and API services
- **LightGBM**: Gradient boosting for forecasting
- **ChromaDB**: Vector store for documentation
- **OpenAI/Claude**: LLM for natural language interface

## Getting Started

1. Set up the system with Docker Compose
2. Load historical consumption data
3. Start data simulation or connect real devices
4. Query the system through the RAG interface

## Example Queries

- "Why is my projected bill $120 this month?"
- "Can I save money by removing my garden pump?"
- "What's the difference between peak and off-peak pricing?"
- "Show me a scenario without EV charging"
- "Which device uses the most energy?"

## Future Enhancements

- Real device integrations (smart plugs, panels)
- Multiple utility tariff support
- Comfort scoring and optimization
- Weather-based recommendations
- Community comparisons
- Mobile app interface

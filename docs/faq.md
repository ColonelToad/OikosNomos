# Frequently Asked Questions

## General

### What is OikosNomos?
OikosNomos is a smart home energy billing and scenario analysis system. It helps you understand your energy costs, forecast future bills, and explore "what-if" scenarios to reduce expenses while maintaining comfort.

### How does it work?
The system monitors your home's energy consumption through IoT devices or simulated data, applies your utility tariff to calculate real-time costs, and uses machine learning to forecast future consumption. You can ask questions in plain English and get explanations with actionable recommendations.

### Do I need special hardware?
For the MVP, you can use simulated data or connect smart plugs and energy monitors that publish to MQTT. In the future, we'll support direct integrations with popular smart home platforms.

---

## Billing and Costs

### What is a tariff?
A tariff is the rate structure your utility company uses to charge for electricity. It includes:
- Fixed monthly charges
- Energy rates (per kWh)
- Time-of-use (TOU) periods with different rates
- Tiered pricing (rates increase with usage)
- Demand charges (commercial/industrial)

### What is time-of-use (TOU) pricing?
TOU pricing charges different rates depending on the time of day and season. Electricity costs more during "peak" hours (typically 4pm-9pm) when demand is high, and less during "off-peak" hours (overnight and midday) when demand is low.

**Example**: 
- Peak: $0.45/kWh
- Off-peak: $0.25/kWh
- Shifting 10 kWh from peak to off-peak saves $2.00/day or $60/month

### How is my projected monthly bill calculated?
Your projected bill is calculated by:
1. Taking your consumption so far this month
2. Dividing by the number of days elapsed
3. Multiplying by the number of days in the month
4. Applying your tariff's rate structure

This assumes your usage pattern stays consistent for the rest of the month.

### Why is my bill higher than last month?
Common reasons:
- **Seasonal changes**: More HVAC usage in hot/cold weather
- **New devices**: EV charging, new appliances
- **Usage patterns**: More time at home, guests
- **Tariff tier**: Crossed into a higher tier (e.g., >400 kWh)
- **Rate changes**: Utility increased rates

Ask the system "Why is my bill higher?" with your specific numbers for a detailed analysis.

### How accurate are the forecasts?
The ML forecast model typically achieves 85-90% accuracy (within 15% error) for 1-3 hour predictions. Accuracy decreases for longer horizons and during unusual events (heat waves, vacations).

---

## Scenarios and Optimization

### What is a scenario?
A scenario is a "what-if" analysis where you configure which devices are active in your home and the system estimates your monthly cost and energy consumption. This helps you understand the impact of adding or removing devices.

### How do I create a scenario?
Use the scenario API or ask the assistant:
- "What would my bill be without the EV charger?"
- "Show me a scenario with only base load and HVAC"
- "Compare my current setup to a minimal configuration"

### Can I really get back to my 2015 bill?
Maybe, but probably not exactly. Your 2015 bill reflected:
- Lower consumption (fewer devices)
- Older electricity rates (often 10-20% lower)
- Different tariff structure

You can get close by:
1. Removing optional devices (EV, garden pump)
2. Reducing HVAC usage
3. Shifting remaining usage to off-peak hours

The system will calculate realistic scenarios and tell you if your target is achievable.

### What's the comfort trade-off?
Some optimizations reduce comfort:
- **HVAC reduction**: Higher/lower temperatures
- **No irrigation**: Brown lawn in summer
- **No EV charging**: Limits driving range

The system rates comfort impact as "none", "low", "medium", or "high" for each device category. You can decide which trade-offs are acceptable.

---

## Technical

### What is MQTT?
MQTT is a lightweight messaging protocol commonly used for IoT devices. Devices publish messages (e.g., power readings) to "topics", and the billing engine subscribes to these topics to receive data.

**Example topic**: `home/home_001/device/hvac/power`

### What is a hypertable?
A hypertable is TimescaleDB's way of storing time-series data efficiently. It automatically partitions data into chunks (e.g., by day or week) and provides fast queries for recent data while compressing older data.

### How is CO₂ calculated?
CO₂ emissions are calculated by multiplying your energy consumption (kWh) by the grid's emissions factor:

**CO₂ (kg) = kWh × 0.42**

The factor varies by region and time of day (cleaner during high renewable generation). OikosNomos uses a simplified average of 0.42 kg CO₂ per kWh for PG&E's service area.

### Can I add my own devices?
Yes! Device profiles are stored in the database. You can add custom categories with your own consumption patterns. Use the admin API or directly edit the `device_profiles` table.

### What machine learning model is used?
The forecast service uses **LightGBM** (Light Gradient Boosting Machine), which is:
- Fast to train and predict
- Accurate for time-series with multiple features
- Interpretable (shows feature importance)

Features include: hour of day, day of week, recent consumption lags, temperature, and rolling statistics.

---

## Privacy and Data

### What data is stored?
- **Time-series**: Power readings, timestamps, device categories
- **Tariffs**: Rate structures, effective dates
- **Scenarios**: Your saved "what-if" configurations
- **Billing snapshots**: Daily cost summaries

No personally identifiable information (PII) is required. Home IDs are arbitrary strings.

### Is my data shared?
No. This is a self-hosted system. All data stays in your PostgreSQL database. The only external service is the LLM (OpenAI/Anthropic) for natural language queries, which receives:
- Your question
- Retrieved documentation (not raw data)
- Current billing summary (no historical details)

### Can I export my data?
Yes. All data is in PostgreSQL and can be exported as CSV/JSON using standard tools or the API.

---

## Getting Help

### The system isn't answering my question correctly
The RAG assistant can only answer questions based on:
1. Indexed documentation
2. Current system state (billing, forecast)

If your question is outside this scope, the assistant will say so. You can improve results by:
- Adding more documentation
- Being more specific in your questions
- Checking if services are running (`/health` endpoints)

### A service isn't starting
Check logs:
```bash
docker-compose logs <service-name>
```

Common issues:
- Database not ready → Wait 10-20 seconds
- API key not set → Check `.env` file
- Port conflict → Change port in `docker-compose.yml`

### How do I report a bug?
Open an issue on GitHub with:
- Description of the problem
- Steps to reproduce
- Logs from affected service
- Expected vs. actual behavior

---

## Future Features

### Roadmap
- Mobile app interface
- Real-time alerts (approaching budget, anomaly detection)
- Community comparisons (how do I compare to similar homes?)
- Integration with Nest, Ecobee, Tesla, etc.
- Multi-home support
- Advanced optimization (genetic algorithms for cost minimization)

### Can I contribute?
Yes! This is an open-source project. Contributions welcome for:
- New device integrations
- Additional tariff definitions
- ML model improvements
- Documentation
- Bug fixes

See `CONTRIBUTING.md` for guidelines.

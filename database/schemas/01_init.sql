-- OikosNomos Database Schema
-- PostgreSQL + TimescaleDB

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- TIME-SERIES TABLES (Hypertables)
-- ============================================================================

-- Raw IoT readings from devices
CREATE TABLE raw_readings (
    timestamp TIMESTAMPTZ NOT NULL,
    home_id TEXT NOT NULL,
    device_category TEXT NOT NULL,
    power_w REAL,
    energy_wh REAL,
    metadata JSONB
);

-- Convert to hypertable (1-day chunks)
SELECT create_hypertable('raw_readings', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for common queries
CREATE INDEX idx_readings_home_device ON raw_readings(home_id, device_category, timestamp DESC);
CREATE INDEX idx_readings_timestamp ON raw_readings(timestamp DESC);

-- Enable compression after 7 days
ALTER TABLE raw_readings SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'home_id,device_category',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('raw_readings', INTERVAL '7 days');

-- Weather data
CREATE TABLE weather (
    timestamp TIMESTAMPTZ NOT NULL,
    location_id TEXT NOT NULL,
    temp_c REAL,
    humidity REAL,
    wind_speed_mps REAL,
    pm25_ugm3 REAL,
    source TEXT,
    metadata JSONB
);

SELECT create_hypertable('weather', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_weather_location ON weather(location_id, timestamp DESC);

-- Enable compression
ALTER TABLE weather SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'location_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('weather', INTERVAL '7 days');

-- Billing snapshots (5-minute rollups)
CREATE TABLE billing_snapshots (
    timestamp TIMESTAMPTZ NOT NULL,
    home_id TEXT NOT NULL,
    cost_today REAL NOT NULL,
    energy_today_kwh REAL NOT NULL,
    projected_month REAL,
    co2_today_kg REAL,
    current_rate REAL,
    tariff_id INTEGER,
    metadata JSONB
);

SELECT create_hypertable('billing_snapshots', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_billing_home ON billing_snapshots(home_id, timestamp DESC);

-- ============================================================================
-- REGULAR TABLES (Configuration and Reference Data)
-- ============================================================================

-- Utility tariffs
CREATE TABLE tariffs (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    utility TEXT NOT NULL,
    structure JSONB NOT NULL,
    effective_date DATE NOT NULL,
    end_date DATE,
    co2_factor_kg_per_kwh REAL DEFAULT 0.42,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add a comment explaining structure format
COMMENT ON COLUMN tariffs.structure IS 'JSON structure: {fixed_charge_monthly, energy_charges: [{tier, limit_kwh, rate_per_kwh, tou_periods}], demand_charge_per_kw, seasons}';

-- Device profiles (categories and consumption patterns)
CREATE TABLE device_profiles (
    category TEXT PRIMARY KEY,
    avg_daily_kwh REAL NOT NULL,
    standby_w REAL NOT NULL DEFAULT 0,
    co2_factor REAL NOT NULL DEFAULT 0.42,
    acquisition_cost REAL,
    comfort_impact TEXT CHECK (comfort_impact IN ('none', 'low', 'medium', 'high')),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Homes/buildings being monitored
CREATE TABLE homes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location_id TEXT,
    timezone TEXT DEFAULT 'UTC',
    active_tariff_id INTEGER REFERENCES tariffs(id),
    device_phase TEXT CHECK (device_phase IN ('regular', 'hybrid', 'smart', 'de-smart')),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scenario runs
CREATE TABLE scenarios (
    id SERIAL PRIMARY KEY,
    home_id TEXT NOT NULL REFERENCES homes(id),
    name TEXT,
    device_config JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scenarios_home ON scenarios(home_id, created_at DESC);

-- ML model metadata
CREATE TABLE ml_models (
    id SERIAL PRIMARY KEY,
    model_type TEXT NOT NULL, -- 'forecast', 'scenario', etc.
    version TEXT NOT NULL,
    trained_at TIMESTAMPTZ NOT NULL,
    training_data_start TIMESTAMPTZ,
    training_data_end TIMESTAMPTZ,
    metrics JSONB, -- {rmse, mae, r2, etc.}
    hyperparameters JSONB,
    file_path TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_models_active ON ml_models(model_type, active, trained_at DESC);

-- ============================================================================
-- CONTINUOUS AGGREGATES (Pre-computed rollups for fast queries)
-- ============================================================================

-- Hourly consumption rollup
CREATE MATERIALIZED VIEW hourly_consumption
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS hour,
    home_id,
    device_category,
    AVG(power_w) AS avg_power_w,
    MAX(power_w) AS max_power_w,
    SUM(energy_wh) / 1000.0 AS total_kwh,
    COUNT(*) AS reading_count
FROM raw_readings
GROUP BY hour, home_id, device_category
WITH NO DATA;

-- Add refresh policy (refresh last 3 hours every 30 minutes)
SELECT add_continuous_aggregate_policy('hourly_consumption',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes');

-- Daily consumption rollup
CREATE MATERIALIZED VIEW daily_consumption
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', timestamp) AS day,
    home_id,
    device_category,
    AVG(power_w) AS avg_power_w,
    MAX(power_w) AS max_power_w,
    SUM(energy_wh) / 1000.0 AS total_kwh,
    COUNT(*) AS reading_count
FROM raw_readings
GROUP BY day, home_id, device_category
WITH NO DATA;

SELECT add_continuous_aggregate_policy('daily_consumption',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- ============================================================================
-- INITIAL DATA INSERTS
-- ============================================================================

-- Insert default home
INSERT INTO homes (id, name, location_id, timezone, device_phase) 
VALUES ('home_001', 'Default Home', 'location_001', 'America/Los_Angeles', 'hybrid')
ON CONFLICT (id) DO NOTHING;

-- Insert device profiles
INSERT INTO device_profiles (category, avg_daily_kwh, standby_w, co2_factor, acquisition_cost, comfort_impact, description) VALUES
('base_load', 3.5, 150, 0.42, 0, 'none', 'Always-on devices: fridge, router, clocks'),
('office', 2.1, 8, 0.42, 800, 'low', 'Computer, monitors, desk equipment'),
('hvac', 18.0, 50, 0.42, 5000, 'high', 'Heating, ventilation, and air conditioning'),
('garden_pump', 1.2, 0, 0.42, 200, 'low', 'Irrigation and garden watering system'),
('ev_charger', 25.0, 5, 0.42, 1200, 'medium', 'Electric vehicle Level 2 charger'),
('entertainment', 1.8, 12, 0.42, 600, 'low', 'TV, streaming devices, game consoles'),
('kitchen', 2.5, 30, 0.42, 0, 'medium', 'Microwave, dishwasher, small appliances')
ON CONFLICT (category) DO NOTHING;

-- Insert example tariff (PG&E E-6 TOU style)
INSERT INTO tariffs (name, utility, structure, effective_date, co2_factor_kg_per_kwh) VALUES
('pge_e6_2025', 'PG&E', '{
  "fixed_charge_monthly": 10.0,
  "energy_charges": [
    {
      "tier": 1,
      "limit_kwh": 400,
      "summer": {
        "off_peak": 0.25,
        "partial_peak": 0.30,
        "peak": 0.45
      },
      "winter": {
        "off_peak": 0.23,
        "partial_peak": 0.27,
        "peak": 0.35
      }
    },
    {
      "tier": 2,
      "limit_kwh": null,
      "summer": {
        "off_peak": 0.35,
        "partial_peak": 0.40,
        "peak": 0.55
      },
      "winter": {
        "off_peak": 0.33,
        "partial_peak": 0.37,
        "peak": 0.45
      }
    }
  ],
  "tou_schedule": {
    "summer_months": [6, 7, 8, 9],
    "peak_hours": [16, 17, 18, 19, 20],
    "partial_peak_hours": [7, 8, 9, 10, 11, 12, 13, 14, 15, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5, 6, 23]
  }
}', '2025-01-01', 0.42)
ON CONFLICT (name) DO NOTHING;

-- Update home to use this tariff
UPDATE homes SET active_tariff_id = (SELECT id FROM tariffs WHERE name = 'pge_e6_2025') WHERE id = 'home_001';

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- Latest reading per device category
CREATE VIEW latest_readings AS
SELECT DISTINCT ON (home_id, device_category)
    home_id,
    device_category,
    timestamp,
    power_w,
    energy_wh
FROM raw_readings
ORDER BY home_id, device_category, timestamp DESC;

-- Active tariffs
CREATE VIEW active_tariffs AS
SELECT * FROM tariffs
WHERE (end_date IS NULL OR end_date > CURRENT_DATE)
ORDER BY effective_date DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for tariffs
CREATE TRIGGER update_tariffs_updated_at
    BEFORE UPDATE ON tariffs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to get current TOU period
CREATE OR REPLACE FUNCTION get_tou_period(
    check_time TIMESTAMPTZ,
    tariff_structure JSONB
) RETURNS TEXT AS $$
DECLARE
    hour_of_day INTEGER;
    month_of_year INTEGER;
    is_summer BOOLEAN;
    tou_schedule JSONB;
BEGIN
    hour_of_day := EXTRACT(HOUR FROM check_time);
    month_of_year := EXTRACT(MONTH FROM check_time);
    tou_schedule := tariff_structure->'tou_schedule';
    
    -- Check if summer
    is_summer := month_of_year = ANY(
        ARRAY(SELECT jsonb_array_elements_text(tou_schedule->'summer_months')::INTEGER)
    );
    
    -- Determine period
    IF hour_of_day = ANY(
        ARRAY(SELECT jsonb_array_elements_text(tou_schedule->'peak_hours')::INTEGER)
    ) THEN
        RETURN 'peak';
    ELSIF hour_of_day = ANY(
        ARRAY(SELECT jsonb_array_elements_text(tou_schedule->'partial_peak_hours')::INTEGER)
    ) THEN
        RETURN 'partial_peak';
    ELSE
        RETURN 'off_peak';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO oikosnomo_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO oikosnomo_user;

COMMENT ON DATABASE oikosnomo IS 'OikosNomos Smart Home Billing and Forecasting System';

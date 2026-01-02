package main

import (
	"database/sql"
	"fmt"
	"time"

	_ "github.com/lib/pq"
)

type Database struct {
	conn *sql.DB
}

type Tariff struct {
	ID        int
	Name      string
	BaseRate  float64
	CO2Factor float64
}

func NewDatabase(config Config) (*Database, error) {
	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		config.DBHost, config.DBPort, config.DBUser, config.DBPassword, config.DBName)

	conn, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, err
	}

	if err := conn.Ping(); err != nil {
		return nil, err
	}

	return &Database{conn: conn}, nil
}

func (db *Database) Close() error {
	return db.conn.Close()
}

func (db *Database) GetActiveTariff(homeID string) (*Tariff, error) {
	query := `
		SELECT t.id, t.name, t.co2_factor_kg_per_kwh
		FROM homes h
		JOIN tariffs t ON h.active_tariff_id = t.id
		WHERE h.id = $1
	`

	var tariff Tariff
	err := db.conn.QueryRow(query, homeID).Scan(&tariff.ID, &tariff.Name, &tariff.CO2Factor)
	if err != nil {
		return nil, err
	}

	// Simplified: use a base rate of $0.30/kWh
	// In real implementation, calculate based on TOU and tier
	tariff.BaseRate = 0.30

	return &tariff, nil
}

func (db *Database) SaveBillingSnapshot(homeID string, data map[string]interface{}) error {
	query := `
		INSERT INTO billing_snapshots (
			timestamp, home_id, cost_today, energy_today_kwh, 
			projected_month, co2_today_kg, current_rate
		) VALUES ($1, $2, $3, $4, $5, $6, $7)
	`

	_, err := db.conn.Exec(query,
		time.Now(),
		homeID,
		data["cost_today"],
		data["energy_today_kwh"],
		data["projected_month"],
		data["co2_today_kg"],
		data["current_rate"],
	)

	return err
}

func (db *Database) SaveReading(homeID string, reading PowerReading) error {
	query := `
		INSERT INTO raw_readings (timestamp, home_id, device_category, power_w, energy_wh)
		VALUES ($1, $2, $3, $4, $5)
	`

	_, err := db.conn.Exec(query,
		reading.Timestamp,
		homeID,
		reading.DeviceCategory,
		reading.PowerW,
		reading.EnergyWh,
	)

	return err
}

type PowerReading struct {
	Timestamp      time.Time `json:"timestamp"`
	DeviceCategory string    `json:"device_category"`
	PowerW         float64   `json:"power_w"`
	EnergyWh       float64   `json:"energy_wh"`
}

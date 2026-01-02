package main

import (
	"sync"
	"time"
)

type EnergyAccumulator struct {
	homeID   string
	db       *Database
	mu       sync.RWMutex
	readings map[string][]PowerReading // device_category -> readings
}

func NewEnergyAccumulator(homeID string, db *Database) *EnergyAccumulator {
	return &EnergyAccumulator{
		homeID:   homeID,
		db:       db,
		readings: make(map[string][]PowerReading),
	}
}

func (a *EnergyAccumulator) AddReading(reading PowerReading) {
	a.mu.Lock()
	defer a.mu.Unlock()

	// Store reading
	a.readings[reading.DeviceCategory] = append(
		a.readings[reading.DeviceCategory],
		reading,
	)

	// Save to database (async in production)
	go a.db.SaveReading(a.homeID, reading)

	// Clean old readings (keep last 24 hours)
	a.cleanOldReadings()
}

func (a *EnergyAccumulator) GetTodayTotal() float64 {
	a.mu.RLock()
	defer a.mu.RUnlock()

	startOfDay := time.Now().Truncate(24 * time.Hour)
	totalKWh := 0.0

	for _, readings := range a.readings {
		for _, reading := range readings {
			if reading.Timestamp.After(startOfDay) {
				// Simplified: assume readings are every 5 seconds, convert W to kWh
				// In production, use actual energy_wh field
				totalKWh += reading.PowerW * (5.0 / 3600.0) / 1000.0
			}
		}
	}

	return totalKWh
}

func (a *EnergyAccumulator) cleanOldReadings() {
	cutoff := time.Now().Add(-24 * time.Hour)

	for category, readings := range a.readings {
		filtered := []PowerReading{}
		for _, reading := range readings {
			if reading.Timestamp.After(cutoff) {
				filtered = append(filtered, reading)
			}
		}
		a.readings[category] = filtered
	}
}

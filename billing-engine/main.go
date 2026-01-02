package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"net/http"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	"github.com/gorilla/mux"
)

type Config struct {
	MQTTBroker string
	DBHost     string
	DBPort     string
	DBUser     string
	DBPassword string
	DBName     string
	HomeID     string
}

type BillingEngine struct {
	config      Config
	mqttClient  mqtt.Client
	db          *Database
	accumulator *EnergyAccumulator
	httpServer  *http.Server
}

func loadConfig() Config {
	return Config{
		MQTTBroker: getEnv("MQTT_BROKER", "localhost:1883"),
		DBHost:     getEnv("DB_HOST", "localhost"),
		DBPort:     getEnv("DB_PORT", "5432"),
		DBUser:     getEnv("DB_USER", "postgres"),
		DBPassword: getEnv("DB_PASSWORD", "oikosnomo_dev"),
		DBName:     getEnv("DB_NAME", "oikosnomo"),
		HomeID:     getEnv("HOME_ID", "home_001"),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
	log.Println("Starting OikosNomos Billing Engine...")

	config := loadConfig()
	engine := &BillingEngine{config: config}

	// Initialize database
	var err error
	engine.db, err = NewDatabase(config)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer engine.db.Close()
	log.Println("Database connected")

	// Initialize energy accumulator
	engine.accumulator = NewEnergyAccumulator(config.HomeID, engine.db)

	// Setup MQTT
	if err := engine.setupMQTT(); err != nil {
		log.Fatalf("Failed to setup MQTT: %v", err)
	}
	defer engine.mqttClient.Disconnect(250)
	log.Println("MQTT connected")

	// Setup HTTP API
	engine.setupHTTP()
	log.Printf("HTTP API listening on :8080")

	// Start billing calculation loop
	go engine.billingLoop()

	// Wait for interrupt
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	<-sigChan

	log.Println("Shutting down...")
	engine.httpServer.Shutdown(nil)
}

func (e *BillingEngine) setupMQTT() error {
	opts := mqtt.NewClientOptions()
	opts.AddBroker(fmt.Sprintf("tcp://%s", e.config.MQTTBroker))
	opts.SetClientID("billing-engine")
	opts.SetDefaultPublishHandler(e.messageHandler)
	opts.SetOnConnectHandler(func(c mqtt.Client) {
		log.Println("MQTT connected, subscribing to topics...")
		// Subscribe to all device power topics
		topic := fmt.Sprintf("home/%s/device/+/power", e.config.HomeID)
		if token := c.Subscribe(topic, 0, nil); token.Wait() && token.Error() != nil {
			log.Printf("Failed to subscribe to %s: %v", topic, token.Error())
		} else {
			log.Printf("Subscribed to %s", topic)
		}
	})

	e.mqttClient = mqtt.NewClient(opts)
	if token := e.mqttClient.Connect(); token.Wait() && token.Error() != nil {
		return token.Error()
	}

	return nil
}

func (e *BillingEngine) messageHandler(client mqtt.Client, msg mqtt.Message) {
	// Parse power reading
	var reading PowerReading
	if err := json.Unmarshal(msg.Payload(), &reading); err != nil {
		log.Printf("Failed to parse message: %v", err)
		return
	}

	// Add to accumulator
	e.accumulator.AddReading(reading)
}

func (e *BillingEngine) billingLoop() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		if err := e.calculateAndPublishBilling(); err != nil {
			log.Printf("Error in billing calculation: %v", err)
		}
	}
}

func (e *BillingEngine) calculateAndPublishBilling() error {
	log.Println("Calculating billing...")

	// Get accumulated energy for today
	todayEnergy := e.accumulator.GetTodayTotal()

	// Get tariff
	tariff, err := e.db.GetActiveTariff(e.config.HomeID)
	if err != nil {
		return fmt.Errorf("failed to get tariff: %w", err)
	}

	// Calculate cost (simplified - in real implementation, apply TOU logic)
	costToday := todayEnergy * tariff.BaseRate

	// Project monthly
	daysInMonth := 30.0
	dayOfMonth := float64(time.Now().Day())
	projectedMonth := (costToday / dayOfMonth) * daysInMonth

	// Calculate CO2
	co2Today := todayEnergy * tariff.CO2Factor

	// Publish to MQTT
	billingData := map[string]interface{}{
		"timestamp":        time.Now().Format(time.RFC3339),
		"cost_today":       costToday,
		"energy_today_kwh": todayEnergy,
		"projected_month":  projectedMonth,
		"co2_today_kg":     co2Today,
		"current_rate":     tariff.BaseRate,
	}

	payload, _ := json.Marshal(billingData)
	topic := fmt.Sprintf("home/%s/billing/today_cost", e.config.HomeID)
	e.mqttClient.Publish(topic, 0, false, payload)

	// Save to database
	if err := e.db.SaveBillingSnapshot(e.config.HomeID, billingData); err != nil {
		log.Printf("Failed to save billing snapshot: %v", err)
	}

	log.Printf("Billing calculated: Today=$%.2f, Projected=$%.2f, Energy=%.2fkWh",
		costToday, projectedMonth, todayEnergy)

	return nil
}

func (e *BillingEngine) setupHTTP() {
	router := mux.NewRouter()

	router.HandleFunc("/health", e.healthHandler).Methods("GET")
	router.HandleFunc("/billing/current", e.currentBillingHandler).Methods("GET")
	router.HandleFunc("/billing/history", e.billingHistoryHandler).Methods("GET")

	e.httpServer = &http.Server{
		Addr:    ":8080",
		Handler: router,
	}

	go func() {
		if err := e.httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("HTTP server error: %v", err)
		}
	}()
}

func (e *BillingEngine) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func (e *BillingEngine) currentBillingHandler(w http.ResponseWriter, r *http.Request) {
	todayEnergy := e.accumulator.GetTodayTotal()
	tariff, _ := e.db.GetActiveTariff(e.config.HomeID)

	costToday := todayEnergy * tariff.BaseRate
	projectedMonth := (costToday / float64(time.Now().Day())) * 30.0

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"home_id":          e.config.HomeID,
		"cost_today":       costToday,
		"energy_today_kwh": todayEnergy,
		"projected_month":  projectedMonth,
		"tariff":           tariff.Name,
	})
}

func (e *BillingEngine) billingHistoryHandler(w http.ResponseWriter, r *http.Request) {
	// TODO: Implement history query from database
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode([]interface{}{})
}

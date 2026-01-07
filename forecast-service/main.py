from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from database import Database
from model import ForecastModel
from config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OikosNomos Forecast Service", version="1.0.0")

# Global instances
db = Database(settings)
model = ForecastModel()

# --- Billing endpoint ---
from fastapi import Query

@app.get("/billing/current")
async def billing_current(home_id: str = Query(..., description="Home ID")):
    """Return current bill and summary for a home."""
    try:
        # Get all consumption for this month
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query = """
            SELECT SUM(total_kwh) as kwh
            FROM hourly_consumption
            WHERE home_id = %s AND hour >= %s AND hour < %s
        """
        with db.conn.cursor() as cur:
            cur.execute(query, (home_id, month_start, now))
            row = cur.fetchone()
            kwh = row["kwh"] if row and row["kwh"] is not None else 0.0
        tariff = db.get_active_tariff(home_id)
        current_bill = kwh * tariff["base_rate"]
        return {
            "home_id": home_id,
            "current_bill": round(current_bill, 2),
            "kwh": round(kwh, 2),
            "tariff_name": tariff["name"],
            "rate": tariff["base_rate"],
            "period_start": month_start.isoformat(),
            "period_end": now.isoformat()
        }
    except Exception as e:
        logger.error(f"Billing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize database and load model on startup"""
    try:
        db.connect()
        logger.info("Database connected")
        
        # Load model if available, but don't train on startup
        if not model.load():
            logger.warning("No trained model found. Use POST /train to train a model.")
        else:
            logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    db.close()
    logger.info("Database connection closed")

class PredictRequest(BaseModel):
    home_id: str = "home_001"
    horizon_hours: int = 3

class PredictResponse(BaseModel):
    home_id: str
    timestamp: datetime
    forecast_kwh: List[float]
    forecast_cost: List[float]
    model_version: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OikosNomos Forecast Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model.is_loaded(),
        "db_connected": db.is_connected()
    }

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Predict energy consumption and cost for next N hours
    
    Args:
        request: PredictRequest with home_id and horizon_hours
        
    Returns:
        PredictResponse with forecasted kWh and cost
    """
    try:
        if not model.is_loaded():
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Get recent historical data for features
        recent_data = db.get_recent_readings(
            home_id=request.home_id,
            hours=168  # Last week
        )
        
        if recent_data.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"No recent data found for home {request.home_id}"
            )
        
        # Get weather data
        weather = db.get_recent_weather(hours=24)
        
        # Make predictions
        forecast_kwh = model.predict(
            recent_data=recent_data,
            weather=weather,
            horizon_hours=request.horizon_hours
        )
        
        # Get tariff and calculate costs
        tariff = db.get_active_tariff(request.home_id)
        forecast_cost = [kwh * tariff["base_rate"] for kwh in forecast_kwh]
        
        return PredictResponse(
            home_id=request.home_id,
            timestamp=datetime.now(),
            forecast_kwh=forecast_kwh,
            forecast_cost=forecast_cost,
            model_version=model.version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train")
async def train_model():
    """
    Train or retrain the forecasting model
    
    This endpoint triggers model training on historical data.
    Should be called periodically (e.g., weekly) or when data drift is detected.
    """
    try:
        logger.info("Starting model training...")
        
        # Get the most recent data available (not hardcoded to last 90 days)
        # First check what data we have
        check_query = "SELECT MIN(timestamp) as min_ts, MAX(timestamp) as max_ts FROM raw_readings"
        date_range = pd.read_sql_query(check_query, db.engine)
        
        if date_range.empty or pd.isna(date_range['max_ts'].iloc[0]):
            raise HTTPException(
                status_code=404,
                detail="No training data available in database"
            )
        
        # Use the most recent year of data for training, or all if less than a year
        end_date = pd.to_datetime(date_range['max_ts'].iloc[0])
        start_date = max(pd.to_datetime(date_range['min_ts'].iloc[0]), end_date - timedelta(days=365))
        
        logger.info(f"Training on data from {start_date} to {end_date}")
        
        train_data = db.get_historical_data(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        if train_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No training data available between {start_date} and {end_date}"
            )
        
        # Get weather data
        weather_data = db.get_weather_data(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        # Train model
        metrics = model.train(train_data, weather_data)
        
        # Save model
        model.save()
        
        logger.info(f"Model training complete: {metrics}")
        
        return {
            "status": "success",
            "metrics": metrics,
            "model_version": model.version,
            "trained_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Training error: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")

@app.get("/model/info")
async def model_info():
    """Get information about the current model"""
    if not model.is_loaded():
        return {"status": "no_model_loaded"}
    
    return {
        "model_version": model.version,
        "model_type": "LightGBM",
        "features": model.get_feature_names(),
        "trained_at": model.trained_at,
        "metrics": model.metrics
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

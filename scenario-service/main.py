from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import logging
from datetime import datetime

from database import Database
from config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OikosNomos Scenario Service", version="1.0.0")

# Global database instance
db = Database(settings)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        db.connect()
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    db.close()
    logger.info("Database connection closed")

class DeviceMix(BaseModel):
    base_load: bool = True
    office: bool = True
    hvac: bool = True
    garden_pump: bool = True
    ev_charger: bool = True
    entertainment: bool = True
    kitchen: bool = True

class ScenarioRequest(BaseModel):
    home_id: str = "home_001"
    name: Optional[str] = None
    device_mix: DeviceMix
    
class ScenarioResponse(BaseModel):
    scenario_id: int
    home_id: str
    name: Optional[str]
    monthly_cost: float
    monthly_kwh: float
    co2_kg: float
    daily_cost: float
    savings_vs_current: Optional[float]
    devices_active: Dict[str, bool]
    created_at: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OikosNomos Scenario Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "db_connected": db.is_connected()
    }

@app.post("/scenario/evaluate", response_model=ScenarioResponse)
async def evaluate_scenario(request: ScenarioRequest):
    """
    Evaluate a device configuration scenario
    
    Calculates projected monthly cost, energy consumption, and CO2 emissions
    based on which devices are active in the home.
    
    Args:
        request: ScenarioRequest with device mix configuration
        
    Returns:
        ScenarioResponse with cost projections and comparisons
    """
    try:
        # Get device profiles from database
        device_profiles = db.get_device_profiles()
        
        if not device_profiles:
            raise HTTPException(
                status_code=500,
                detail="No device profiles found in database"
            )
        
        # Get active tariff for cost calculation
        tariff = db.get_active_tariff(request.home_id)
        
        # Calculate total consumption
        daily_kwh = 0.0
        device_mix_dict = request.device_mix.dict()
        
        for category, is_active in device_mix_dict.items():
            if is_active and category in device_profiles:
                profile = device_profiles[category]
                daily_kwh += profile['avg_daily_kwh']
        
        # Monthly projections
        monthly_kwh = daily_kwh * 30
        monthly_cost = monthly_kwh * tariff['base_rate']
        daily_cost = daily_kwh * tariff['base_rate']
        co2_kg = monthly_kwh * tariff['co2_factor']
        
        # Calculate savings vs current (if available)
        current_projection = db.get_current_projection(request.home_id)
        savings = None
        if current_projection:
            savings = current_projection - monthly_cost
        
        # Save scenario to database
        scenario_id = db.save_scenario(
            home_id=request.home_id,
            name=request.name or f"Scenario {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            device_config=device_mix_dict,
            result={
                'monthly_cost': monthly_cost,
                'monthly_kwh': monthly_kwh,
                'co2_kg': co2_kg,
                'daily_cost': daily_cost
            }
        )
        
        logger.info(f"Scenario {scenario_id} evaluated: ${monthly_cost:.2f}/month, {monthly_kwh:.1f}kWh")
        
        return ScenarioResponse(
            scenario_id=scenario_id,
            home_id=request.home_id,
            name=request.name,
            monthly_cost=round(monthly_cost, 2),
            monthly_kwh=round(monthly_kwh, 2),
            co2_kg=round(co2_kg, 2),
            daily_cost=round(daily_cost, 2),
            savings_vs_current=round(savings, 2) if savings else None,
            devices_active=device_mix_dict,
            created_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scenario evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scenario/{scenario_id}")
async def get_scenario(scenario_id: int):
    """Get details of a previously saved scenario"""
    try:
        scenario = db.get_scenario(scenario_id)
        
        if not scenario:
            raise HTTPException(
                status_code=404,
                detail=f"Scenario {scenario_id} not found"
            )
        
        return scenario
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scenario/home/{home_id}")
async def list_scenarios(home_id: str, limit: int = 10):
    """List recent scenarios for a home"""
    try:
        scenarios = db.list_scenarios(home_id, limit)
        return {
            "home_id": home_id,
            "count": len(scenarios),
            "scenarios": scenarios
        }
    except Exception as e:
        logger.error(f"Error listing scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/devices")
async def list_devices():
    """Get list of all available device categories and their profiles"""
    try:
        devices = db.get_device_profiles()
        return {
            "devices": devices
        }
    except Exception as e:
        logger.error(f"Error retrieving device profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scenario/compare")
async def compare_scenarios(scenario_ids: list[int]):
    """
    Compare multiple scenarios side by side
    
    Args:
        scenario_ids: List of scenario IDs to compare
        
    Returns:
        Comparison of costs, energy, and device configurations
    """
    try:
        if len(scenario_ids) > 5:
            raise HTTPException(
                status_code=400,
                detail="Maximum 5 scenarios can be compared at once"
            )
        
        scenarios = []
        for sid in scenario_ids:
            scenario = db.get_scenario(sid)
            if scenario:
                scenarios.append(scenario)
        
        if not scenarios:
            raise HTTPException(
                status_code=404,
                detail="No valid scenarios found"
            )
        
        # Find best and worst
        costs = [s['result']['monthly_cost'] for s in scenarios]
        best_idx = costs.index(min(costs))
        worst_idx = costs.index(max(costs))
        
        return {
            "scenarios": scenarios,
            "comparison": {
                "best_cost": {
                    "scenario_id": scenarios[best_idx]['id'],
                    "cost": costs[best_idx]
                },
                "worst_cost": {
                    "scenario_id": scenarios[worst_idx]['id'],
                    "cost": costs[worst_idx]
                },
                "cost_range": max(costs) - min(costs),
                "avg_cost": sum(costs) / len(costs)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

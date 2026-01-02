import psycopg2
from psycopg2.extras import RealDictCursor, Json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, settings):
        self.settings = settings
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.settings.db_host,
                port=self.settings.db_port,
                user=self.settings.db_user,
                password=self.settings.db_password,
                database=self.settings.db_name,
                cursor_factory=RealDictCursor
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        try:
            if self.conn:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return True
        except:
            return False
        return False
    
    def get_device_profiles(self) -> Dict[str, dict]:
        """
        Get all device profiles
        
        Returns:
            Dictionary mapping category name to profile data
        """
        query = """
            SELECT 
                category,
                avg_daily_kwh,
                standby_w,
                co2_factor,
                acquisition_cost,
                comfort_impact,
                description
            FROM device_profiles
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                
                profiles = {}
                for row in rows:
                    profiles[row['category']] = {
                        'avg_daily_kwh': float(row['avg_daily_kwh']),
                        'standby_w': float(row['standby_w']),
                        'co2_factor': float(row['co2_factor']),
                        'acquisition_cost': float(row['acquisition_cost']) if row['acquisition_cost'] else 0,
                        'comfort_impact': row['comfort_impact'],
                        'description': row['description']
                    }
                
                return profiles
                
        except Exception as e:
            logger.error(f"Error fetching device profiles: {e}")
            return {}
    
    def get_active_tariff(self, home_id: str) -> dict:
        """Get active tariff for a home"""
        query = """
            SELECT t.name, t.structure, t.co2_factor_kg_per_kwh
            FROM homes h
            JOIN tariffs t ON h.active_tariff_id = t.id
            WHERE h.id = %s
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (home_id,))
                result = cur.fetchone()
                
                if result:
                    return {
                        "name": result["name"],
                        "structure": result["structure"],
                        "co2_factor": float(result["co2_factor_kg_per_kwh"]),
                        "base_rate": 0.30  # Simplified for MVP
                    }
        except Exception as e:
            logger.error(f"Error fetching tariff: {e}")
        
        # Default tariff
        return {
            "name": "default",
            "base_rate": 0.30,
            "co2_factor": 0.42
        }
    
    def get_current_projection(self, home_id: str) -> Optional[float]:
        """Get current monthly cost projection for a home"""
        query = """
            SELECT projected_month
            FROM billing_snapshots
            WHERE home_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (home_id,))
                result = cur.fetchone()
                
                if result and result['projected_month']:
                    return float(result['projected_month'])
        except Exception as e:
            logger.error(f"Error fetching current projection: {e}")
        
        return None
    
    def save_scenario(
        self,
        home_id: str,
        name: str,
        device_config: dict,
        result: dict
    ) -> int:
        """
        Save a scenario to the database
        
        Returns:
            Scenario ID
        """
        query = """
            INSERT INTO scenarios (home_id, name, device_config, result)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    query,
                    (home_id, name, Json(device_config), Json(result))
                )
                scenario_id = cur.fetchone()['id']
                self.conn.commit()
                logger.info(f"Scenario {scenario_id} saved")
                return scenario_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving scenario: {e}")
            raise
    
    def get_scenario(self, scenario_id: int) -> Optional[dict]:
        """Get a specific scenario by ID"""
        query = """
            SELECT 
                id,
                home_id,
                name,
                device_config,
                result,
                created_at
            FROM scenarios
            WHERE id = %s
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (scenario_id,))
                result = cur.fetchone()
                
                if result:
                    return dict(result)
        except Exception as e:
            logger.error(f"Error fetching scenario {scenario_id}: {e}")
        
        return None
    
    def list_scenarios(self, home_id: str, limit: int = 10) -> List[dict]:
        """List recent scenarios for a home"""
        query = """
            SELECT 
                id,
                home_id,
                name,
                device_config,
                result,
                created_at
            FROM scenarios
            WHERE home_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (home_id, limit))
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing scenarios: {e}")
            return []

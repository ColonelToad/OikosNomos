import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, settings):
        self.settings = settings
        self.conn = None
        self.engine = None
        
    def connect(self):
        """Establish database connection"""
        try:
            # Create SQLAlchemy engine for pandas
            connection_string = f"postgresql+psycopg2://{self.settings.db_user}:{self.settings.db_password}@{self.settings.db_host}:{self.settings.db_port}/{self.settings.db_name}"
            self.engine = create_engine(connection_string)
            
            # Also keep psycopg2 connection for potential direct use
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
    
    def get_recent_readings(self, home_id: str, hours: int = 168) -> pd.DataFrame:
        """
        Get recent power readings for a home
        
        Args:
            home_id: Home identifier
            hours: Number of hours to look back
            
        Returns:
            DataFrame with columns: timestamp, device_category, power_w, energy_wh
        """
        query = """
            SELECT 
                timestamp,
                device_category,
                power_w,
                energy_wh
            FROM raw_readings
            WHERE home_id = %s
                AND timestamp > NOW() - INTERVAL '%s hours'
            ORDER BY timestamp ASC
        """
        
        try:
            df = pd.read_sql_query(
                query,
                self.conn,
                params=(home_id, hours)
            )
            return df
        except Exception as e:
            logger.error(f"Error fetching recent readings: {e}")
            return pd.DataFrame()
    
    def get_historical_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get historical aggregated consumption data
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with hourly consumption
        """
        query = """
            SELECT 
                hour as timestamp,
                SUM(total_kwh) as total_kwh,
                AVG(avg_power_w) as avg_power_w
            FROM hourly_consumption
            WHERE hour >= %s AND hour < %s
            GROUP BY hour
            ORDER BY hour
        """
        
        try:
            df = pd.read_sql_query(
                query,
                self.engine,
                params=(start_date, end_date)
            )
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def get_weather_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get weather data for date range"""
        query = """
            SELECT 
                timestamp,
                temp_c,
                humidity,
                wind_speed_mps
            FROM weather
            WHERE timestamp >= %s AND timestamp < %s
            ORDER BY timestamp
        """
        
        try:
            df = pd.read_sql_query(
                query,
                self.engine,
                params=(start_date, end_date)
            )
            return df
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            return pd.DataFrame()
    
    def get_recent_weather(self, hours: int = 24) -> pd.DataFrame:
        """Get recent weather data"""
        query = """
            SELECT 
                timestamp,
                temp_c,
                humidity
            FROM weather
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC
            LIMIT 1
        """
        
        try:
            df = pd.read_sql_query(query, self.conn, params=(hours,))
            return df
        except Exception as e:
            logger.error(f"Error fetching recent weather: {e}")
            # Return default values if no weather data
            return pd.DataFrame([{
                'timestamp': datetime.now(),
                'temp_c': 20.0,
                'humidity': 50.0
            }])
    
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
                        "co2_factor": result["co2_factor_kg_per_kwh"],
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

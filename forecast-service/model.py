import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ForecastModel:
    def __init__(self, model_path: str = "models/forecast_model.pkl"):
        self.model_path = Path(model_path)
        self.model = None
        self.version = "v1.0"
        self.trained_at = None
        self.metrics = {}
        self.feature_names = []
        
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model is not None
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        return self.feature_names
    
    def create_features(self, data: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
        """
        Create features for forecasting
        
        Args:
            data: Historical consumption data
            weather: Weather data
            
        Returns:
            DataFrame with engineered features
        """
        df = data.copy()
        
        # Ensure timestamp is datetime
        if 'timestamp' not in df.columns:
            logger.error(f"DataFrame columns: {df.columns.tolist()}")
            raise ValueError("'timestamp' column not found in data")
        
        logger.info(f"DataFrame shape before timestamp parsing: {df.shape}")
        logger.info(f"Timestamp column dtype: {df['timestamp'].dtype}")
        logger.info(f"Sample timestamps: {df['timestamp'].head().tolist()}")
        
        # Handle timestamp conversion
        try:
            # Try to parse with timezone awareness first
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
        except Exception as e:
            logger.error(f"Error converting timestamp: {e}")
            logger.error(f"Sample timestamps: {df['timestamp'].head()}")
            raise
        
        # Check for NaT values after conversion
        if df['timestamp'].isna().any():
            logger.warning(f"Found {df['timestamp'].isna().sum()} invalid timestamps")
            df = df.dropna(subset=['timestamp'])
        
        df = df.sort_values('timestamp')
        
        # Time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Cyclical encoding for hour (24-hour cycle)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Lag features (recent consumption)
        if 'total_kwh' in df.columns:
            df['lag_1h'] = df['total_kwh'].shift(1)
            df['lag_24h'] = df['total_kwh'].shift(24)
            df['lag_168h'] = df['total_kwh'].shift(168)  # 1 week
            df['rolling_mean_24h'] = df['total_kwh'].rolling(window=24, min_periods=1).mean()
            df['rolling_std_24h'] = df['total_kwh'].rolling(window=24, min_periods=1).std()
        
        # Merge weather data
        if not weather.empty and 'temp_c' in weather.columns:
            weather['timestamp'] = pd.to_datetime(weather['timestamp'])
            weather = weather[['timestamp', 'temp_c', 'humidity']].drop_duplicates('timestamp')
            df = pd.merge_asof(
                df.sort_values('timestamp'),
                weather.sort_values('timestamp'),
                on='timestamp',
                direction='nearest'
            )
        else:
            # Default weather values
            df['temp_c'] = 20.0
            df['humidity'] = 50.0
        
        # Fill NaN values
        df = df.bfill().ffill().fillna(0)
        
        return df
    
    def train(self, train_data: pd.DataFrame, weather_data: pd.DataFrame) -> Dict:
        """
        Train the forecasting model
        
        Args:
            train_data: Historical training data
            weather_data: Weather data
            
        Returns:
            Dictionary with training metrics
        """
        logger.info("Starting model training...")
        
        # Create features
        df = self.create_features(train_data, weather_data)
        
        # Define feature columns
        self.feature_names = [
            'hour', 'day_of_week', 'month', 'is_weekend',
            'hour_sin', 'hour_cos', 'temp_c', 'humidity',
            'lag_1h', 'lag_24h', 'lag_168h',
            'rolling_mean_24h', 'rolling_std_24h'
        ]
        
        # Split train/validation (80/20)
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx]
        val_df = df.iloc[split_idx:]
        
        X_train = train_df[self.feature_names]
        y_train = train_df['total_kwh'] if 'total_kwh' in train_df.columns else train_df['avg_power_w'] / 1000
        
        X_val = val_df[self.feature_names]
        y_val = val_df['total_kwh'] if 'total_kwh' in val_df.columns else val_df['avg_power_w'] / 1000
        
        # Train RandomForestRegressor model (scikit-learn)
        from sklearn.ensemble import RandomForestRegressor
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train, y_train)
        
        # Calculate metrics
        y_pred = self.model.predict(X_val)
        rmse = np.sqrt(np.mean((y_val - y_pred) ** 2))
        mae = np.mean(np.abs(y_val - y_pred))
        mape = np.mean(np.abs((y_val - y_pred) / (y_val + 1e-8))) * 100
        
        self.metrics = {
            'rmse': float(rmse),
            'mae': float(mae),
            'mape': float(mape)
        }
        
        self.trained_at = datetime.now().isoformat()
        
        logger.info(f"Model trained successfully. RMSE: {rmse:.4f}, MAE: {mae:.4f}")
        
        return self.metrics
    
    def predict(
        self,
        recent_data: pd.DataFrame,
        weather: pd.DataFrame,
        horizon_hours: int = 3
    ) -> List[float]:
        """
        Make predictions for next N hours
        
        Args:
            recent_data: Recent consumption data
            weather: Current weather data
            horizon_hours: Number of hours to forecast
            
        Returns:
            List of predicted kWh values
        """
        if not self.is_loaded():
            raise ValueError("Model not loaded")
        
        # Create features
        df = self.create_features(recent_data, weather)
        
        if df.empty:
            logger.warning("No data available for prediction, returning zeros")
            return [0.0] * horizon_hours
        
        # Get last row for features
        last_row = df.iloc[-1:].copy()
        predictions = []
        
        # Forecast iteratively
        current_time = pd.to_datetime(last_row['timestamp'].values[0])
        
        for h in range(horizon_hours):
            # Update time features
            forecast_time = current_time + timedelta(hours=h+1)
            last_row['hour'] = forecast_time.hour
            last_row['day_of_week'] = forecast_time.dayofweek
            last_row['month'] = forecast_time.month
            last_row['is_weekend'] = int(forecast_time.dayofweek in [5, 6])
            last_row['hour_sin'] = np.sin(2 * np.pi * forecast_time.hour / 24)
            last_row['hour_cos'] = np.cos(2 * np.pi * forecast_time.hour / 24)
            
            # Make prediction
            X = last_row[self.feature_names]
            pred = self.model.predict(X)[0]
            predictions.append(float(max(0, pred)))  # Ensure non-negative
            
            # Update lags for next iteration
            if 'lag_1h' in self.feature_names:
                last_row['lag_1h'] = pred
        
        return predictions
    
    def save(self):
        """Save model to disk"""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'version': self.version,
            'trained_at': self.trained_at,
            'metrics': self.metrics,
            'feature_names': self.feature_names
        }
        
        joblib.dump(model_data, self.model_path)
        logger.info(f"Model saved to {self.model_path}")
    
    def load(self) -> bool:
        """Load model from disk"""
        if not self.model_path.exists():
            logger.warning(f"Model file not found: {self.model_path}")
            return False
        
        try:
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.version = model_data['version']
            self.trained_at = model_data['trained_at']
            self.metrics = model_data['metrics']
            self.feature_names = model_data['feature_names']
            logger.info(f"Model loaded from {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

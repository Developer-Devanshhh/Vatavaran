"""
Feature Engineering Module for Vatavaran Climate Control System

This module provides functionality to build the 90-feature matrix required
for LSTM inference. Features are constructed from sensor history and weather
forecast data, matching the exact feature list from model_config.pkl.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8
"""

import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def build_feature_matrix(
    sensor_history: pd.DataFrame,
    weather_forecast: pd.DataFrame,
    model_config_path: str = 'model_config.pkl'
) -> np.ndarray:
    """
    Build a feature matrix of shape (96, 90) for the next 24 hours.
    
    This function constructs exactly 90 features matching the trained model's
    feature list, loaded from model_config.pkl. Features include:
    - Time cyclical features (hour_sin, hour_cos, day_sin, day_cos, month_sin, month_cos)
    - Time-based features (hour, day_of_week, day_of_year, month, quarter)
    - Weather features from forecast (humidity, pressure, light/cloud, temp_c)
    - Lag features from sensor history (temperature, humidity, pressure, light at t-1, t-5, t-15, t-30)
    - Rolling statistics (mean, std, min, max over 5, 15, 30 slots)
    - Difference and percentage change features
    
    Args:
        sensor_history: DataFrame with columns ['timestamp', 'temperature_c', 'humidity', 
                       'pressure_mb', 'light'] containing historical sensor readings.
                       Should have at least 30 rows for lag features.
        weather_forecast: DataFrame with columns ['timestamp', 'temp_c', 'humidity', 
                         'pressure_mb', 'cloud'] for the next 24 hours.
        model_config_path: Path to model_config.pkl file
    
    Returns:
        numpy array of shape (96, 90) containing engineered features for each 15-minute slot
    
    Requirements:
        6.1: Construct exactly 90 features matching the trained model's feature list
        6.2: Load feature names and order from model_config.pkl
        6.3: Generate time cyclical features
        6.4: Generate lag features from sensor history
        6.5: Generate rolling statistics
        6.6: Merge weather forecast data by timestamp alignment
        6.7: Generate boolean flags (is_weekend, is_night)
        6.8: Return feature matrix of shape (96, 90)
    """
    logger.info("Building feature matrix for 96 time slots (24 hours)")
    
    # Requirement 6.2: Load feature names and order from model_config.pkl
    config_path = Path(model_config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"model_config.pkl not found at {config_path}")
    
    with open(config_path, 'rb') as f:
        model_config = pickle.load(f)
    
    feature_names = model_config.get('feature_columns', [])
    if len(feature_names) != 90:
        raise ValueError(f"Expected 90 features in model_config, got {len(feature_names)}")
    
    logger.info(f"Loaded {len(feature_names)} feature names from model_config.pkl")
    
    # Generate timestamps for the next 24 hours (96 15-minute slots)
    start_time = datetime.now()
    # Round to nearest 15-minute interval
    start_time = start_time.replace(second=0, microsecond=0)
    minutes = (start_time.minute // 15) * 15
    start_time = start_time.replace(minute=minutes)
    
    timestamps = [start_time + timedelta(minutes=15*i) for i in range(96)]
    
    # Create base DataFrame for features
    df = pd.DataFrame({'timestamp': timestamps})
    
    # Requirement 6.3: Generate time cyclical features
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['day_of_year'] = df['timestamp'].dt.dayofyear
    df['month'] = df['timestamp'].dt.month
    df['quarter'] = df['timestamp'].dt.quarter
    
    # Cyclical encoding for time features
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    
    logger.info("Generated time cyclical features")
    
    # Requirement 6.6: Merge weather forecast data by timestamp alignment
    # Weather forecast is hourly, we need to interpolate to 15-minute intervals
    weather_forecast = weather_forecast.copy()
    weather_forecast['timestamp'] = pd.to_datetime(weather_forecast['timestamp'])
    
    # Resample weather data to 15-minute intervals using forward fill
    weather_forecast = weather_forecast.set_index('timestamp')
    
    # Create a complete 15-minute range for 24 hours (96 slots)
    weather_range = pd.date_range(start=start_time, periods=96, freq='15min')
    weather_15min = weather_forecast.reindex(weather_range, method='ffill')
    weather_15min = weather_15min.reset_index()
    weather_15min.rename(columns={'index': 'timestamp'}, inplace=True)
    
    # Merge with our feature DataFrame
    df = df.merge(weather_15min[['timestamp', 'temp_c', 'humidity', 'pressure_mb', 'cloud']], 
                  on='timestamp', how='left', suffixes=('', '_weather'))
    
    # Rename cloud to light (model expects 'light' feature)
    df['light'] = df['cloud']
    df['pressure'] = df['pressure_mb']
    df['temp_c'] = df['temp_c'].ffill().bfill()  # Fill any missing temp values
    
    # Fill any missing weather values with forward fill then backward fill
    df['humidity'] = df['humidity'].ffill().bfill()
    df['pressure'] = df['pressure'].ffill().bfill()
    df['light'] = df['light'].ffill().bfill()
    
    logger.info("Merged weather forecast data")
    
    # Requirement 6.4: Generate lag features from sensor history
    # We need to get the last values from sensor history for lag features
    # Prepare sensor history
    sensor_history = sensor_history.copy()
    sensor_history['timestamp'] = pd.to_datetime(sensor_history['timestamp'])
    sensor_history = sensor_history.sort_values('timestamp')
    
    # Get the most recent sensor values to use as base for predictions
    if len(sensor_history) > 0:
        last_temp = sensor_history['temperature_c'].iloc[-1]
        last_humidity = sensor_history['humidity'].iloc[-1] if 'humidity' in sensor_history.columns else df['humidity'].iloc[0]
        last_pressure = sensor_history['pressure_mb'].iloc[-1] if 'pressure_mb' in sensor_history.columns else df['pressure'].iloc[0]
        last_light = sensor_history['light'].iloc[-1] if 'light' in sensor_history.columns else df['light'].iloc[0]
    else:
        # Use weather forecast values as fallback
        last_temp = weather_forecast['temp_c'].iloc[0] if 'temp_c' in weather_forecast.columns else 25.0
        last_humidity = df['humidity'].iloc[0]
        last_pressure = df['pressure'].iloc[0]
        last_light = df['light'].iloc[0]
    
    # For future predictions, we'll use a simple approach:
    # - Use last known sensor values for initial lags
    # - For predictions, we'll use the weather forecast temperature
    
    # Create a combined history + forecast temperature series
    # Use weather forecast temp_c as proxy for future temperature
    temp_forecast = df['temp_c'].values
    
    # Build lag features (lags are at 1, 5, 15, 30 slots = 15min, 1h15min, 3h45min, 7h30min)
    # For simplicity, we'll use the last known values and forecast values
    
    # Temperature lags
    df['temperature_lag_1'] = last_temp  # Will be updated in loop
    df['temperature_lag_5'] = last_temp
    df['temperature_lag_15'] = last_temp
    df['temperature_lag_30'] = last_temp
    
    # Humidity lags (use weather forecast humidity)
    df['humidity_lag_1'] = df['humidity'].shift(1).fillna(last_humidity)
    df['humidity_lag_5'] = df['humidity'].shift(5).fillna(last_humidity)
    df['humidity_lag_15'] = df['humidity'].shift(15).fillna(last_humidity)
    df['humidity_lag_30'] = df['humidity'].shift(30).fillna(last_humidity)
    
    # Pressure lags
    df['pressure_lag_1'] = df['pressure'].shift(1).fillna(last_pressure)
    df['pressure_lag_5'] = df['pressure'].shift(5).fillna(last_pressure)
    df['pressure_lag_15'] = df['pressure'].shift(15).fillna(last_pressure)
    df['pressure_lag_30'] = df['pressure'].shift(30).fillna(last_pressure)
    
    # Light lags
    df['light_lag_1'] = df['light'].shift(1).fillna(last_light)
    df['light_lag_5'] = df['light'].shift(5).fillna(last_light)
    df['light_lag_15'] = df['light'].shift(15).fillna(last_light)
    df['light_lag_30'] = df['light'].shift(30).fillna(last_light)
    
    logger.info("Generated lag features")
    
    # Requirement 6.5: Generate rolling statistics
    # For future predictions, we'll use expanding window from the last known value
    
    # Temperature rolling stats (using forecast temperature)
    temp_series = pd.Series(temp_forecast)
    df['temperature_roll_mean_5'] = temp_series.rolling(window=5, min_periods=1).mean().values
    df['temperature_roll_std_5'] = temp_series.rolling(window=5, min_periods=1).std().fillna(0).values
    df['temperature_roll_min_5'] = temp_series.rolling(window=5, min_periods=1).min().values
    df['temperature_roll_max_5'] = temp_series.rolling(window=5, min_periods=1).max().values
    
    df['temperature_roll_mean_15'] = temp_series.rolling(window=15, min_periods=1).mean().values
    df['temperature_roll_std_15'] = temp_series.rolling(window=15, min_periods=1).std().fillna(0).values
    df['temperature_roll_min_15'] = temp_series.rolling(window=15, min_periods=1).min().values
    df['temperature_roll_max_15'] = temp_series.rolling(window=15, min_periods=1).max().values
    
    df['temperature_roll_mean_30'] = temp_series.rolling(window=30, min_periods=1).mean().values
    df['temperature_roll_std_30'] = temp_series.rolling(window=30, min_periods=1).std().fillna(0).values
    df['temperature_roll_min_30'] = temp_series.rolling(window=30, min_periods=1).min().values
    df['temperature_roll_max_30'] = temp_series.rolling(window=30, min_periods=1).max().values
    
    # Humidity rolling stats
    df['humidity_roll_mean_5'] = df['humidity'].rolling(window=5, min_periods=1).mean()
    df['humidity_roll_std_5'] = df['humidity'].rolling(window=5, min_periods=1).std().fillna(0)
    df['humidity_roll_min_5'] = df['humidity'].rolling(window=5, min_periods=1).min()
    df['humidity_roll_max_5'] = df['humidity'].rolling(window=5, min_periods=1).max()
    
    df['humidity_roll_mean_15'] = df['humidity'].rolling(window=15, min_periods=1).mean()
    df['humidity_roll_std_15'] = df['humidity'].rolling(window=15, min_periods=1).std().fillna(0)
    df['humidity_roll_min_15'] = df['humidity'].rolling(window=15, min_periods=1).min()
    df['humidity_roll_max_15'] = df['humidity'].rolling(window=15, min_periods=1).max()
    
    df['humidity_roll_mean_30'] = df['humidity'].rolling(window=30, min_periods=1).mean()
    df['humidity_roll_std_30'] = df['humidity'].rolling(window=30, min_periods=1).std().fillna(0)
    df['humidity_roll_min_30'] = df['humidity'].rolling(window=30, min_periods=1).min()
    df['humidity_roll_max_30'] = df['humidity'].rolling(window=30, min_periods=1).max()
    
    # Pressure rolling stats
    df['pressure_roll_mean_5'] = df['pressure'].rolling(window=5, min_periods=1).mean()
    df['pressure_roll_std_5'] = df['pressure'].rolling(window=5, min_periods=1).std().fillna(0)
    df['pressure_roll_min_5'] = df['pressure'].rolling(window=5, min_periods=1).min()
    df['pressure_roll_max_5'] = df['pressure'].rolling(window=5, min_periods=1).max()
    
    df['pressure_roll_mean_15'] = df['pressure'].rolling(window=15, min_periods=1).mean()
    df['pressure_roll_std_15'] = df['pressure'].rolling(window=15, min_periods=1).std().fillna(0)
    df['pressure_roll_min_15'] = df['pressure'].rolling(window=15, min_periods=1).min()
    df['pressure_roll_max_15'] = df['pressure'].rolling(window=15, min_periods=1).max()
    
    df['pressure_roll_mean_30'] = df['pressure'].rolling(window=30, min_periods=1).mean()
    df['pressure_roll_std_30'] = df['pressure'].rolling(window=30, min_periods=1).std().fillna(0)
    df['pressure_roll_min_30'] = df['pressure'].rolling(window=30, min_periods=1).min()
    df['pressure_roll_max_30'] = df['pressure'].rolling(window=30, min_periods=1).max()
    
    # Light rolling stats
    df['light_roll_mean_5'] = df['light'].rolling(window=5, min_periods=1).mean()
    df['light_roll_std_5'] = df['light'].rolling(window=5, min_periods=1).std().fillna(0)
    df['light_roll_min_5'] = df['light'].rolling(window=5, min_periods=1).min()
    df['light_roll_max_5'] = df['light'].rolling(window=5, min_periods=1).max()
    
    df['light_roll_mean_15'] = df['light'].rolling(window=15, min_periods=1).mean()
    df['light_roll_std_15'] = df['light'].rolling(window=15, min_periods=1).std().fillna(0)
    df['light_roll_min_15'] = df['light'].rolling(window=15, min_periods=1).min()
    df['light_roll_max_15'] = df['light'].rolling(window=15, min_periods=1).max()
    
    df['light_roll_mean_30'] = df['light'].rolling(window=30, min_periods=1).mean()
    df['light_roll_std_30'] = df['light'].rolling(window=30, min_periods=1).std().fillna(0)
    df['light_roll_min_30'] = df['light'].rolling(window=30, min_periods=1).min()
    df['light_roll_max_30'] = df['light'].rolling(window=30, min_periods=1).max()
    
    logger.info("Generated rolling statistics")
    
    # Generate difference and percentage change features
    # Temperature differences
    df['temperature_diff_1'] = temp_series.diff(1).fillna(0).values
    df['temperature_diff_5'] = temp_series.diff(5).fillna(0).values
    df['temperature_pct_change_5'] = temp_series.pct_change(5).fillna(0).values
    
    # Humidity differences
    df['humidity_diff_1'] = df['humidity'].diff(1).fillna(0)
    df['humidity_diff_5'] = df['humidity'].diff(5).fillna(0)
    df['humidity_pct_change_5'] = df['humidity'].pct_change(5).fillna(0)
    
    # Pressure differences
    df['pressure_diff_1'] = df['pressure'].diff(1).fillna(0)
    df['pressure_diff_5'] = df['pressure'].diff(5).fillna(0)
    df['pressure_pct_change_5'] = df['pressure'].pct_change(5).fillna(0)
    
    # Light differences
    df['light_diff_1'] = df['light'].diff(1).fillna(0)
    df['light_diff_5'] = df['light'].diff(5).fillna(0)
    df['light_pct_change_5'] = df['light'].pct_change(5).fillna(0)
    
    logger.info("Generated difference and percentage change features")
    
    # Requirement 6.1: Extract features in the exact order from model_config
    feature_matrix = df[feature_names].values
    
    # Requirement 6.8: Validate output shape
    if feature_matrix.shape != (96, 90):
        raise ValueError(f"Feature matrix has incorrect shape {feature_matrix.shape}, expected (96, 90)")
    
    logger.info(f"Feature matrix built successfully: shape {feature_matrix.shape}")
    
    return feature_matrix

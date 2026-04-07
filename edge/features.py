"""
Feature Engineering Module for Vatavaran Edge (Raspberry Pi 4B)

Builds the 90-feature matrix required for LSTM inference.
Adapted from api/features.py — removed Django dependencies.

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

    Args:
        sensor_history: DataFrame with columns ['timestamp', 'temperature_c',
                       'humidity', 'pressure_mb', 'light'].
                       Should have at least 30 rows for lag features.
        weather_forecast: DataFrame with columns ['timestamp', 'temp_c',
                         'humidity', 'pressure_mb', 'cloud'] for 24 hours.
        model_config_path: Path to model_config.pkl

    Returns:
        numpy array of shape (96, 90)
    """
    logger.info("Building feature matrix for 96 time slots (24 hours)")

    # Load feature names from model config
    config_path = Path(model_config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"model_config.pkl not found at {config_path}")

    with open(config_path, 'rb') as f:
        model_config = pickle.load(f)

    feature_names = model_config.get('feature_columns', [])
    if len(feature_names) != 90:
        raise ValueError(f"Expected 90 features in model_config, got {len(feature_names)}")

    logger.info(f"Loaded {len(feature_names)} feature names from model_config.pkl")

    # Generate timestamps for next 24 hours (96 × 15-minute slots)
    start_time = datetime.now().replace(second=0, microsecond=0)
    minutes = (start_time.minute // 15) * 15
    start_time = start_time.replace(minute=minutes)
    timestamps = [start_time + timedelta(minutes=15 * i) for i in range(96)]

    df = pd.DataFrame({'timestamp': timestamps})

    # ── Time features (cyclical + integer) ────────────────────────
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['day_of_year'] = df['timestamp'].dt.dayofyear
    df['month'] = df['timestamp'].dt.month
    df['quarter'] = df['timestamp'].dt.quarter

    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

    logger.info("Generated time cyclical features")

    # ── Weather forecast (hourly → 15-min) ────────────────────────
    weather_forecast = weather_forecast.copy()
    weather_forecast['timestamp'] = pd.to_datetime(weather_forecast['timestamp'])
    weather_forecast = weather_forecast.set_index('timestamp')

    weather_range = pd.date_range(start=start_time, periods=96, freq='15min')
    weather_15min = weather_forecast.reindex(weather_range, method='ffill')
    weather_15min = weather_15min.reset_index().rename(columns={'index': 'timestamp'})

    df = df.merge(
        weather_15min[['timestamp', 'temp_c', 'humidity', 'pressure_mb', 'cloud']],
        on='timestamp', how='left', suffixes=('', '_weather')
    )

    df['light'] = df['cloud']
    df['pressure'] = df['pressure_mb']
    df['temp_c'] = df['temp_c'].ffill().bfill()
    df['humidity'] = df['humidity'].ffill().bfill()
    df['pressure'] = df['pressure'].ffill().bfill()
    df['light'] = df['light'].ffill().bfill()

    logger.info("Merged weather forecast data")

    # ── Lag features from sensor history ──────────────────────────
    sensor_history = sensor_history.copy()
    sensor_history['timestamp'] = pd.to_datetime(sensor_history['timestamp'])
    sensor_history = sensor_history.sort_values('timestamp')

    if len(sensor_history) > 0:
        last_temp = sensor_history['temperature_c'].iloc[-1]
        last_humidity = sensor_history['humidity'].iloc[-1] if 'humidity' in sensor_history.columns else df['humidity'].iloc[0]
        last_pressure = sensor_history['pressure_mb'].iloc[-1] if 'pressure_mb' in sensor_history.columns else df['pressure'].iloc[0]
        last_light = sensor_history['light'].iloc[-1] if 'light' in sensor_history.columns else df['light'].iloc[0]
    else:
        last_temp = weather_forecast['temp_c'].iloc[0] if 'temp_c' in weather_forecast.columns else 25.0
        last_humidity = df['humidity'].iloc[0]
        last_pressure = df['pressure'].iloc[0]
        last_light = df['light'].iloc[0]

    temp_forecast = df['temp_c'].values

    # Temperature lags
    df['temperature_lag_1'] = last_temp
    df['temperature_lag_5'] = last_temp
    df['temperature_lag_15'] = last_temp
    df['temperature_lag_30'] = last_temp

    # Humidity lags
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

    # ── Rolling statistics ────────────────────────────────────────
    temp_series = pd.Series(temp_forecast)

    for sensor_name, series in [('temperature', temp_series),
                                ('humidity', df['humidity']),
                                ('pressure', df['pressure']),
                                ('light', df['light'])]:
        for window in [5, 15, 30]:
            df[f'{sensor_name}_roll_mean_{window}'] = series.rolling(window=window, min_periods=1).mean().values
            df[f'{sensor_name}_roll_std_{window}'] = series.rolling(window=window, min_periods=1).std().fillna(0).values
            df[f'{sensor_name}_roll_min_{window}'] = series.rolling(window=window, min_periods=1).min().values
            df[f'{sensor_name}_roll_max_{window}'] = series.rolling(window=window, min_periods=1).max().values

    logger.info("Generated rolling statistics")

    # ── Difference / percentage-change features ───────────────────
    for sensor_name, series in [('temperature', temp_series),
                                ('humidity', df['humidity']),
                                ('pressure', df['pressure']),
                                ('light', df['light'])]:
        df[f'{sensor_name}_diff_1'] = series.diff(1).fillna(0).values
        df[f'{sensor_name}_diff_5'] = series.diff(5).fillna(0).values
        df[f'{sensor_name}_pct_change_5'] = series.pct_change(5).fillna(0).values

    logger.info("Generated difference and percentage change features")

    # ── Extract in model-config order ─────────────────────────────
    # Some features may be missing — fill with 0
    for col in feature_names:
        if col not in df.columns:
            logger.warning(f"Feature '{col}' not in DataFrame — filling with 0")
            df[col] = 0.0

    feature_matrix = df[feature_names].values

    if feature_matrix.shape != (96, 90):
        raise ValueError(f"Shape {feature_matrix.shape}, expected (96, 90)")

    logger.info(f"Feature matrix built: shape {feature_matrix.shape}")
    return feature_matrix

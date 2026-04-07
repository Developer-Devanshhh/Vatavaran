"""
Unit tests for the feature engineering module.

Tests the build_feature_matrix function to ensure it correctly generates
the 90-feature matrix required for LSTM inference.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from api.features import build_feature_matrix


def test_build_feature_matrix_shape():
    """Test that feature matrix has correct shape (96, 90)."""
    # Create mock sensor history
    sensor_history = pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(minutes=15*i) for i in range(30, 0, -1)],
        'temperature_c': np.random.uniform(20, 30, 30),
        'humidity': np.random.uniform(40, 80, 30),
        'pressure_mb': np.random.uniform(1000, 1020, 30),
        'light': np.random.uniform(0, 100, 30)
    })
    
    # Create mock weather forecast
    weather_forecast = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(hours=i) for i in range(24)],
        'temp_c': np.random.uniform(20, 30, 24),
        'humidity': np.random.uniform(40, 80, 24),
        'pressure_mb': np.random.uniform(1000, 1020, 24),
        'cloud': np.random.uniform(0, 100, 24)
    })
    
    # Build feature matrix
    feature_matrix = build_feature_matrix(sensor_history, weather_forecast)
    
    # Verify shape
    assert feature_matrix.shape == (96, 90), f"Expected shape (96, 90), got {feature_matrix.shape}"


def test_build_feature_matrix_no_nans():
    """Test that feature matrix contains no NaN values."""
    # Create mock sensor history
    sensor_history = pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(minutes=15*i) for i in range(30, 0, -1)],
        'temperature_c': np.random.uniform(20, 30, 30),
        'humidity': np.random.uniform(40, 80, 30),
        'pressure_mb': np.random.uniform(1000, 1020, 30),
        'light': np.random.uniform(0, 100, 30)
    })
    
    # Create mock weather forecast
    weather_forecast = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(hours=i) for i in range(24)],
        'temp_c': np.random.uniform(20, 30, 24),
        'humidity': np.random.uniform(40, 80, 24),
        'pressure_mb': np.random.uniform(1000, 1020, 24),
        'cloud': np.random.uniform(0, 100, 24)
    })
    
    # Build feature matrix
    feature_matrix = build_feature_matrix(sensor_history, weather_forecast)
    
    # Verify no NaN values
    assert not np.isnan(feature_matrix).any(), "Feature matrix contains NaN values"


def test_build_feature_matrix_with_minimal_history():
    """Test that feature matrix can be built with minimal sensor history."""
    # Create minimal sensor history (just 1 row)
    sensor_history = pd.DataFrame({
        'timestamp': [datetime.now()],
        'temperature_c': [25.0],
        'humidity': [60.0],
        'pressure_mb': [1013.0],
        'light': [50.0]
    })
    
    # Create mock weather forecast
    weather_forecast = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(hours=i) for i in range(24)],
        'temp_c': np.random.uniform(20, 30, 24),
        'humidity': np.random.uniform(40, 80, 24),
        'pressure_mb': np.random.uniform(1000, 1020, 24),
        'cloud': np.random.uniform(0, 100, 24)
    })
    
    # Build feature matrix
    feature_matrix = build_feature_matrix(sensor_history, weather_forecast)
    
    # Verify shape and no NaN
    assert feature_matrix.shape == (96, 90)
    assert not np.isnan(feature_matrix).any()


def test_build_feature_matrix_cyclical_features():
    """Test that cyclical features are properly bounded."""
    # Create mock data
    sensor_history = pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(minutes=15*i) for i in range(30, 0, -1)],
        'temperature_c': np.random.uniform(20, 30, 30),
        'humidity': np.random.uniform(40, 80, 30),
        'pressure_mb': np.random.uniform(1000, 1020, 30),
        'light': np.random.uniform(0, 100, 30)
    })
    
    weather_forecast = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(hours=i) for i in range(24)],
        'temp_c': np.random.uniform(20, 30, 24),
        'humidity': np.random.uniform(40, 80, 24),
        'pressure_mb': np.random.uniform(1000, 1020, 24),
        'cloud': np.random.uniform(0, 100, 24)
    })
    
    # Build feature matrix
    feature_matrix = build_feature_matrix(sensor_history, weather_forecast)
    
    # Cyclical features should be between -1 and 1
    # Features at indices 8-13 are: hour_sin, hour_cos, day_sin, day_cos, month_sin, month_cos
    cyclical_indices = [8, 9, 10, 11, 12, 13]
    
    for idx in cyclical_indices:
        values = feature_matrix[:, idx]
        assert np.all(values >= -1.0) and np.all(values <= 1.0), \
            f"Cyclical feature at index {idx} not in range [-1, 1]"


def test_build_feature_matrix_feature_count():
    """Test that exactly 90 features are generated matching model config."""
    import pickle
    
    # Load model config to verify feature count
    with open('model_config.pkl', 'rb') as f:
        model_config = pickle.load(f)
    
    expected_features = model_config.get('feature_columns', [])
    assert len(expected_features) == 90, f"Model config should have 90 features, got {len(expected_features)}"
    
    # Create mock data
    sensor_history = pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(minutes=15*i) for i in range(30, 0, -1)],
        'temperature_c': np.random.uniform(20, 30, 30),
        'humidity': np.random.uniform(40, 80, 30),
        'pressure_mb': np.random.uniform(1000, 1020, 30),
        'light': np.random.uniform(0, 100, 30)
    })
    
    weather_forecast = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(hours=i) for i in range(24)],
        'temp_c': np.random.uniform(20, 30, 24),
        'humidity': np.random.uniform(40, 80, 24),
        'pressure_mb': np.random.uniform(1000, 1020, 24),
        'cloud': np.random.uniform(0, 100, 24)
    })
    
    # Build feature matrix
    feature_matrix = build_feature_matrix(sensor_history, weather_forecast)
    
    # Verify feature count
    assert feature_matrix.shape[1] == 90, f"Expected 90 features, got {feature_matrix.shape[1]}"


def test_build_feature_matrix_empty_history():
    """Test that feature matrix can be built with empty sensor history."""
    # Create empty sensor history
    sensor_history = pd.DataFrame({
        'timestamp': [],
        'temperature_c': [],
        'humidity': [],
        'pressure_mb': [],
        'light': []
    })
    
    # Create mock weather forecast
    weather_forecast = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(hours=i) for i in range(24)],
        'temp_c': np.random.uniform(20, 30, 24),
        'humidity': np.random.uniform(40, 80, 24),
        'pressure_mb': np.random.uniform(1000, 1020, 24),
        'cloud': np.random.uniform(0, 100, 24)
    })
    
    # Build feature matrix
    feature_matrix = build_feature_matrix(sensor_history, weather_forecast)
    
    # Verify shape and no NaN
    assert feature_matrix.shape == (96, 90)
    assert not np.isnan(feature_matrix).any()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

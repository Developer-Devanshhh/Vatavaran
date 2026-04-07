"""
Weather API client for fetching forecast data from WeatherAPI.com.

This module provides functionality to fetch 24-hour weather forecasts
for Vellore, Tamil Nadu and return the data as a pandas DataFrame.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


# Vellore, Tamil Nadu coordinates
VELLORE_LAT = 12.9165
VELLORE_LON = 79.1325

# Cache configuration
CACHE_TTL_MINUTES = 30

# In-memory cache for weather data
_weather_cache = {
    'data': None,
    'timestamp': None
}


def _is_cache_valid() -> bool:
    """
    Check if the cached weather data is still valid based on TTL.
    
    Returns:
        bool: True if cache exists and is within TTL, False otherwise
    """
    if _weather_cache['data'] is None or _weather_cache['timestamp'] is None:
        return False
    
    cache_age = datetime.now() - _weather_cache['timestamp']
    return cache_age < timedelta(minutes=CACHE_TTL_MINUTES)


def _fetch_from_api() -> pd.DataFrame:
    """
    Fetch weather data from WeatherAPI.com API.
    
    Returns:
        pd.DataFrame: DataFrame with timestamp and weather fields for 24 hours
        
    Raises:
        ValueError: If WEATHERAPI_KEY environment variable is not set
        requests.RequestException: If the API request fails
    """
    api_key = os.environ.get('WEATHERAPI_KEY')
    if not api_key:
        raise ValueError("WEATHERAPI_KEY environment variable is not set")
    
    # WeatherAPI.com forecast endpoint
    url = "http://api.weatherapi.com/v1/forecast.json"
    
    params = {
        'key': api_key,
        'q': f"{VELLORE_LAT},{VELLORE_LON}",
        'days': 1,  # 24-hour forecast
        'aqi': 'no',  # We don't need air quality data
        'alerts': 'no'  # We don't need weather alerts
    }
    
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    
    # Extract hourly forecast data
    hourly_data = []
    
    # WeatherAPI returns forecast for today and tomorrow
    # We need to extract 24 hours starting from current hour
    for day in data['forecast']['forecastday']:
        for hour in day['hour']:
            hourly_data.append({
                'timestamp': hour['time'],
                'temp_c': hour['temp_c'],
                'humidity': hour['humidity'],
                'feelslike_c': hour['feelslike_c'],
                'wind_kph': hour['wind_kph'],
                'pressure_mb': hour['pressure_mb'],
                'cloud': hour['cloud'],
                'uv': hour['uv'],
                'condition_code': hour['condition']['code']
            })
    
    # Convert to DataFrame
    df = pd.DataFrame(hourly_data)
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Return only the next 24 hours from current time
    df = df.head(24)
    
    return df


def fetch_weather_forecast() -> pd.DataFrame:
    """
    Fetch 24-hour weather forecast for Vellore, Tamil Nadu from WeatherAPI.com.
    
    Uses in-memory cache with 30-minute TTL. If API request fails, returns cached
    data if available within TTL. Raises exception if no cache available and API fails.
    
    Extracts hourly values for:
    - temp_c: Temperature in Celsius
    - humidity: Humidity percentage
    - feelslike_c: Feels like temperature in Celsius
    - wind_kph: Wind speed in kilometers per hour
    - pressure_mb: Atmospheric pressure in millibars
    - cloud: Cloud cover percentage
    - uv: UV index
    - condition_code: Weather condition code
    
    Returns:
        pd.DataFrame: DataFrame with timestamp and weather fields for 24 hours
        
    Raises:
        ValueError: If WEATHERAPI_KEY environment variable is not set
        Exception: If API request fails and no valid cache is available
    """
    try:
        # Try to fetch fresh data from API
        df = _fetch_from_api()
        
        # Update cache with successful response
        _weather_cache['data'] = df.copy()
        _weather_cache['timestamp'] = datetime.now()
        
        return df
        
    except Exception as e:
        # API request failed, try to use cache
        if _is_cache_valid():
            # Return cached data
            return _weather_cache['data'].copy()
        else:
            # No valid cache available, re-raise the exception
            raise Exception(f"Weather API request failed and no valid cache available: {str(e)}")

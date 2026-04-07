"""
Weather API client for Vatavaran Edge (Raspberry Pi 4B)

Fetches 24-hour weather forecast from WeatherAPI.com.
Adapted from api/weather.py — location configurable via config.json.
"""

import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# In-memory cache for weather data
_weather_cache = {'data': None, 'timestamp': None}

# Default cache TTL
CACHE_TTL_MINUTES = 30


def _load_location(config_path=None):
    """Load location from edge config.json."""
    if config_path is None:
        config_path = Path(__file__).parent / 'config.json'

    if Path(config_path).exists():
        with open(config_path, 'r') as f:
            cfg = json.load(f)
        loc = cfg.get('location', {})
        return loc.get('lat', 12.9165), loc.get('lon', 79.1325)

    return 12.9165, 79.1325  # Default: Vellore, Tamil Nadu


def _is_cache_valid() -> bool:
    """Check if cached weather data is still fresh."""
    if _weather_cache['data'] is None or _weather_cache['timestamp'] is None:
        return False
    age = datetime.now() - _weather_cache['timestamp']
    return age < timedelta(minutes=CACHE_TTL_MINUTES)


def _fetch_from_api(config_path=None) -> pd.DataFrame:
    """Fetch weather data from WeatherAPI.com."""
    api_key = os.environ.get('WEATHERAPI_KEY')
    if not api_key:
        # Try loading from config.json
        if config_path is None:
            config_path = Path(__file__).parent / 'config.json'
        if Path(config_path).exists():
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            api_key = cfg.get('weatherapi_key')

    if not api_key:
        raise ValueError(
            "WEATHERAPI_KEY not set. Set via environment variable or config.json"
        )

    lat, lon = _load_location(config_path)

    url = "http://api.weatherapi.com/v1/forecast.json"
    params = {
        'key': api_key,
        'q': f"{lat},{lon}",
        'days': 1,
        'aqi': 'no',
        'alerts': 'no'
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    hourly_data = []
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

    df = pd.DataFrame(hourly_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.head(24)
    return df


def fetch_weather_forecast(config_path=None) -> pd.DataFrame:
    """
    Fetch 24-hour weather forecast with 30-minute caching.

    Falls back to cached data if API fails.
    """
    try:
        df = _fetch_from_api(config_path)
        _weather_cache['data'] = df.copy()
        _weather_cache['timestamp'] = datetime.now()
        logger.info(f"Weather forecast fetched: {len(df)} hours")
        return df

    except Exception as e:
        if _is_cache_valid():
            logger.warning(f"Weather API failed ({e}), using cached data")
            return _weather_cache['data'].copy()
        else:
            raise Exception(
                f"Weather API failed and no valid cache: {e}"
            )

"""
Unit tests for the weather API client module.
"""

import os
import unittest
from unittest.mock import patch, Mock
import pandas as pd
from datetime import datetime, timedelta
from api.weather import fetch_weather_forecast, VELLORE_LAT, VELLORE_LON, _weather_cache, _is_cache_valid


class TestWeatherForecast(unittest.TestCase):
    """Test cases for weather forecast functionality."""
    
    def setUp(self):
        """Clear cache before each test."""
        _weather_cache['data'] = None
        _weather_cache['timestamp'] = None
    
    def test_missing_api_key(self):
        """Test that Exception is raised when WEATHERAPI_KEY is not set."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(Exception) as context:
                fetch_weather_forecast()
            self.assertIn("WEATHERAPI_KEY", str(context.exception))
    
    @patch('api.weather.requests.get')
    def test_successful_forecast_fetch(self, mock_get):
        """Test successful weather forecast fetch and DataFrame structure."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'forecast': {
                'forecastday': [
                    {
                        'hour': [
                            {
                                'time': '2024-01-15 00:00',
                                'temp_c': 25.5,
                                'humidity': 70,
                                'feelslike_c': 26.0,
                                'wind_kph': 10.5,
                                'pressure_mb': 1013.0,
                                'cloud': 50,
                                'uv': 0.0,
                                'condition': {'code': 1000}
                            },
                            {
                                'time': '2024-01-15 01:00',
                                'temp_c': 24.8,
                                'humidity': 72,
                                'feelslike_c': 25.3,
                                'wind_kph': 9.8,
                                'pressure_mb': 1014.0,
                                'cloud': 45,
                                'uv': 0.0,
                                'condition': {'code': 1003}
                            }
                        ] * 12  # Simulate 24 hours
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'test_key'}):
            df = fetch_weather_forecast()
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn('key', call_args[1]['params'])
        self.assertEqual(call_args[1]['params']['q'], f"{VELLORE_LAT},{VELLORE_LON}")
        self.assertEqual(call_args[1]['params']['days'], 1)
        
        # Verify DataFrame structure
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 24)
        
        # Verify all required columns are present
        required_columns = [
            'timestamp', 'temp_c', 'humidity', 'feelslike_c',
            'wind_kph', 'pressure_mb', 'cloud', 'uv', 'condition_code'
        ]
        for col in required_columns:
            self.assertIn(col, df.columns)
        
        # Verify timestamp is datetime type
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['timestamp']))
        
        # Verify data types
        self.assertTrue(df['temp_c'].dtype in [float, 'float64'])
        self.assertTrue(df['humidity'].dtype in [int, 'int64'])
        self.assertTrue(df['condition_code'].dtype in [int, 'int64'])
    
    @patch('api.weather.requests.get')
    def test_api_request_failure(self, mock_get):
        """Test that RequestException is raised when API request fails."""
        mock_get.side_effect = Exception("API connection failed")
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'test_key'}):
            with self.assertRaises(Exception):
                fetch_weather_forecast()
    
    @patch('api.weather.requests.get')
    def test_http_error_handling(self, mock_get):
        """Test handling of HTTP errors from the API."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'invalid_key'}):
            with self.assertRaises(Exception):
                fetch_weather_forecast()
    
    @patch('api.weather.requests.get')
    def test_cache_on_successful_fetch(self, mock_get):
        """Test that successful API fetch updates the cache."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'forecast': {
                'forecastday': [
                    {
                        'hour': [
                            {
                                'time': '2024-01-15 00:00',
                                'temp_c': 25.5,
                                'humidity': 70,
                                'feelslike_c': 26.0,
                                'wind_kph': 10.5,
                                'pressure_mb': 1013.0,
                                'cloud': 50,
                                'uv': 0.0,
                                'condition': {'code': 1000}
                            }
                        ] * 24
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'test_key'}):
            df = fetch_weather_forecast()
        
        # Verify cache was updated
        self.assertIsNotNone(_weather_cache['data'])
        self.assertIsNotNone(_weather_cache['timestamp'])
        self.assertTrue(_is_cache_valid())
        
        # Verify cached data matches returned data
        pd.testing.assert_frame_equal(_weather_cache['data'], df)
    
    @patch('api.weather.requests.get')
    def test_cache_fallback_on_api_failure(self, mock_get):
        """Test that cached data is used when API fails."""
        # First, populate the cache with a successful request
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'forecast': {
                'forecastday': [
                    {
                        'hour': [
                            {
                                'time': '2024-01-15 00:00',
                                'temp_c': 25.5,
                                'humidity': 70,
                                'feelslike_c': 26.0,
                                'wind_kph': 10.5,
                                'pressure_mb': 1013.0,
                                'cloud': 50,
                                'uv': 0.0,
                                'condition': {'code': 1000}
                            }
                        ] * 24
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'test_key'}):
            df_first = fetch_weather_forecast()
        
        # Now make the API fail
        mock_get.side_effect = Exception("API connection failed")
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'test_key'}):
            df_cached = fetch_weather_forecast()
        
        # Verify cached data was returned
        pd.testing.assert_frame_equal(df_first, df_cached)
    
    @patch('api.weather.requests.get')
    def test_no_cache_available_on_api_failure(self, mock_get):
        """Test that exception is raised when API fails and no cache is available."""
        mock_get.side_effect = Exception("API connection failed")
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'test_key'}):
            with self.assertRaises(Exception) as context:
                fetch_weather_forecast()
            self.assertIn("no valid cache available", str(context.exception))
    
    @patch('api.weather.requests.get')
    def test_expired_cache_not_used(self, mock_get):
        """Test that expired cache is not used when API fails."""
        # First, populate the cache
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'forecast': {
                'forecastday': [
                    {
                        'hour': [
                            {
                                'time': '2024-01-15 00:00',
                                'temp_c': 25.5,
                                'humidity': 70,
                                'feelslike_c': 26.0,
                                'wind_kph': 10.5,
                                'pressure_mb': 1013.0,
                                'cloud': 50,
                                'uv': 0.0,
                                'condition': {'code': 1000}
                            }
                        ] * 24
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'test_key'}):
            fetch_weather_forecast()
        
        # Manually expire the cache by setting timestamp to 31 minutes ago
        _weather_cache['timestamp'] = datetime.now() - timedelta(minutes=31)
        
        # Verify cache is not valid
        self.assertFalse(_is_cache_valid())
        
        # Now make the API fail
        mock_get.side_effect = Exception("API connection failed")
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'test_key'}):
            with self.assertRaises(Exception) as context:
                fetch_weather_forecast()
            self.assertIn("no valid cache available", str(context.exception))
    
    @patch('api.weather.requests.get')
    def test_cache_within_ttl(self, mock_get):
        """Test that cache within TTL is considered valid."""
        # Populate the cache
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'forecast': {
                'forecastday': [
                    {
                        'hour': [
                            {
                                'time': '2024-01-15 00:00',
                                'temp_c': 25.5,
                                'humidity': 70,
                                'feelslike_c': 26.0,
                                'wind_kph': 10.5,
                                'pressure_mb': 1013.0,
                                'cloud': 50,
                                'uv': 0.0,
                                'condition': {'code': 1000}
                            }
                        ] * 24
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'WEATHERAPI_KEY': 'test_key'}):
            fetch_weather_forecast()
        
        # Set cache timestamp to 29 minutes ago (within TTL)
        _weather_cache['timestamp'] = datetime.now() - timedelta(minutes=29)
        
        # Verify cache is still valid
        self.assertTrue(_is_cache_valid())


if __name__ == '__main__':
    unittest.main()

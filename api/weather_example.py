"""
Example usage of the weather API client.

This script demonstrates how to use the fetch_weather_forecast function.
Requires WEATHERAPI_KEY environment variable to be set.
"""

import os
from api.weather import fetch_weather_forecast


def main():
    """Demonstrate weather forecast fetching."""
    # Check if API key is set
    if not os.environ.get('WEATHERAPI_KEY'):
        print("Error: WEATHERAPI_KEY environment variable is not set")
        print("Please set it in your .env file or export it:")
        print("  export WEATHERAPI_KEY='your-api-key-here'")
        return
    
    try:
        print("Fetching 24-hour weather forecast for Vellore, Tamil Nadu...")
        df = fetch_weather_forecast()
        
        print(f"\nSuccessfully fetched {len(df)} hours of forecast data")
        print("\nDataFrame shape:", df.shape)
        print("\nColumns:", list(df.columns))
        print("\nFirst 5 rows:")
        print(df.head())
        
        print("\nData types:")
        print(df.dtypes)
        
        print("\nSummary statistics:")
        print(df.describe())
        
    except Exception as e:
        print(f"Error fetching weather data: {e}")


if __name__ == '__main__':
    main()

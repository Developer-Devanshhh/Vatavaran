"""
Manual test script to demonstrate the /api/predict/ endpoint functionality.

This script shows example requests and responses for both scheduled and voice_override modes.
"""

import requests
import json
from datetime import datetime

# Base URL (adjust if needed)
BASE_URL = "http://localhost:8000/api/predict/"

def test_scheduled_mode():
    """Test scheduled mode with valid payload"""
    print("\n=== Testing Scheduled Mode ===")
    
    payload = {
        "mode": "scheduled",
        "timestamp": datetime.now().isoformat(),
        "temperature_c": 26.5,
        "device_id": "rpi_sensor_01"
    }
    
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(BASE_URL, json=payload)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body:\n{json.dumps(response.json(), indent=2)}")
    except requests.exceptions.ConnectionError:
        print("\nNote: Server not running. Start with: python manage.py runserver")
    except Exception as e:
        print(f"\nError: {e}")


def test_voice_override_mode():
    """Test voice_override mode with valid payload"""
    print("\n=== Testing Voice Override Mode ===")
    
    payload = {
        "mode": "voice_override",
        "timestamp": datetime.now().isoformat(),
        "temperature_c": 28.0,
        "device_id": "rpi_sensor_01",
        "command_text": "it's too hot"
    }
    
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(BASE_URL, json=payload)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body:\n{json.dumps(response.json(), indent=2)}")
    except requests.exceptions.ConnectionError:
        print("\nNote: Server not running. Start with: python manage.py runserver")
    except Exception as e:
        print(f"\nError: {e}")


def test_missing_mode():
    """Test error handling for missing mode field"""
    print("\n=== Testing Missing Mode Field ===")
    
    payload = {
        "timestamp": datetime.now().isoformat(),
        "temperature_c": 26.5,
        "device_id": "rpi_sensor_01"
    }
    
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(BASE_URL, json=payload)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body:\n{json.dumps(response.json(), indent=2)}")
    except requests.exceptions.ConnectionError:
        print("\nNote: Server not running. Start with: python manage.py runserver")
    except Exception as e:
        print(f"\nError: {e}")


def test_invalid_mode():
    """Test error handling for invalid mode value"""
    print("\n=== Testing Invalid Mode Value ===")
    
    payload = {
        "mode": "invalid_mode",
        "timestamp": datetime.now().isoformat(),
        "temperature_c": 26.5,
        "device_id": "rpi_sensor_01"
    }
    
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(BASE_URL, json=payload)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body:\n{json.dumps(response.json(), indent=2)}")
    except requests.exceptions.ConnectionError:
        print("\nNote: Server not running. Start with: python manage.py runserver")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Manual Test for /api/predict/ Endpoint")
    print("=" * 60)
    
    test_scheduled_mode()
    test_voice_override_mode()
    test_missing_mode()
    test_invalid_mode()
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)

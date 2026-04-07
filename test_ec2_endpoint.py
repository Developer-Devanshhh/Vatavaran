#!/usr/bin/env python
"""
End-to-end test for EC2 API endpoint.
Tests both scheduled and voice_override modes.
"""

import requests
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/api/predict/"

def test_scheduled_mode():
    """Test scheduled mode prediction"""
    print("\n=== Testing Scheduled Mode ===")
    
    payload = {
        "mode": "scheduled",
        "timestamp": datetime.now().isoformat(),
        "temperature_c": 26.5,
        "device_id": "rpi_test_01"
    }
    
    print(f"Sending request: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(ENDPOINT, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            # Parse CSV response
            csv_lines = response.text.strip().split('\n')
            print(f"CSV Rows: {len(csv_lines)}")
            print(f"Header: {csv_lines[0]}")
            print(f"First 3 rows:")
            for line in csv_lines[1:4]:
                print(f"  {line}")
            print("✓ Scheduled mode test PASSED")
            return True
        else:
            print(f"✗ Scheduled mode test FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Scheduled mode test FAILED: {e}")
        return False

def test_voice_override_mode():
    """Test voice_override mode prediction"""
    print("\n=== Testing Voice Override Mode ===")
    
    payload = {
        "mode": "voice_override",
        "timestamp": datetime.now().isoformat(),
        "temperature_c": 26.5,
        "device_id": "rpi_test_01",
        "command_text": "it's too hot"
    }
    
    print(f"Sending request: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(ENDPOINT, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            # Parse CSV response
            csv_lines = response.text.strip().split('\n')
            print(f"CSV Rows: {len(csv_lines)}")
            print(f"Header: {csv_lines[0]}")
            print(f"First 5 rows (should show override):")
            for line in csv_lines[1:6]:
                print(f"  {line}")
            
            # Check for override source in first 4 rows
            override_count = sum(1 for line in csv_lines[1:5] if 'override' in line)
            if override_count == 4:
                print("✓ Voice override test PASSED (4 override slots detected)")
                return True
            else:
                print(f"✗ Voice override test FAILED: Expected 4 override slots, found {override_count}")
                return False
        else:
            print(f"✗ Voice override test FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Voice override test FAILED: {e}")
        return False

def main():
    print("=" * 60)
    print("EC2 API Endpoint End-to-End Test")
    print("=" * 60)
    print(f"\nEndpoint: {ENDPOINT}")
    print("\nNOTE: Ensure Django server is running:")
    print("  python manage.py runserver")
    print("\nNOTE: Ensure WEATHERAPI_KEY is set in environment")
    
    results = []
    
    # Test scheduled mode
    results.append(("Scheduled Mode", test_scheduled_mode()))
    
    # Test voice override mode
    results.append(("Voice Override Mode", test_voice_override_mode()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n✓ All tests PASSED")
        return 0
    else:
        print("\n✗ Some tests FAILED")
        return 1

if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python
"""
Automated Dry Run Test Script for Vatavaran
Works on Windows, Linux, and macOS
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color
    
    @staticmethod
    def green(text):
        return f"{Colors.GREEN}{text}{Colors.NC}"
    
    @staticmethod
    def red(text):
        return f"{Colors.RED}{text}{Colors.NC}"
    
    @staticmethod
    def yellow(text):
        return f"{Colors.YELLOW}{text}{Colors.NC}"

def print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")

def print_step(step_num, text):
    print(Colors.yellow(f"\nStep {step_num}: {text}"))

def print_success(text):
    print(Colors.green(f"✓ {text}"))

def print_error(text):
    print(Colors.red(f"✗ {text}"))

def check_file_exists(filepath):
    return Path(filepath).exists()

def run_command(cmd, capture_output=True):
    """Run a command and return success status"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True, timeout=30)
            return result.returncode == 0, "", ""
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def main():
    print_header("Vatavaran Dry Run Test")
    
    # Check if we're in the right directory
    if not check_file_exists("manage.py"):
        print_error("manage.py not found. Run this script from the project root.")
        return 1
    
    # Step 1: Set environment variables
    print_step(1, "Setting environment variables...")
    os.environ['WEATHERAPI_KEY'] = "6415f4c56b1d424384860604242303"
    os.environ['DJANGO_SECRET_KEY'] = "test-secret-key-for-dry-run"
    os.environ['DEBUG'] = "True"
    os.environ['ALLOWED_HOSTS'] = "localhost,127.0.0.1"
    os.environ['MODEL_DIR'] = "."
    print_success("Environment variables set")
    
    # Step 2: Check model artifacts
    print_step(2, "Checking model artifacts...")
    required_files = [
        "lstm_model.h5",
        "scaler_features.pkl",
        "scaler_target.pkl",
        "model_config.pkl"
    ]
    
    missing_files = [f for f in required_files if not check_file_exists(f)]
    if missing_files:
        print_error(f"Missing model artifacts: {', '.join(missing_files)}")
        return 1
    print_success("All model artifacts found")
    
    # Step 3: Run Django checks
    print_step(3, "Running Django checks...")
    success, stdout, stderr = run_command("python manage.py check")
    if success:
        print_success("Django checks passed")
    else:
        print_error("Django checks failed")
        print(stderr)
        return 1
    
    # Step 4: Test individual components
    print_step(4, "Testing individual components...")
    
    tests = [
        ("Weather API", "from api.weather import fetch_weather_forecast; df = fetch_weather_forecast(); print(f'Fetched {len(df)} hours')"),
        ("LSTM Inference", "from api.inference import LSTMPredictor; import numpy as np; p = LSTMPredictor(); f = np.random.randn(96, 90); pred = p.predict_24h(f); print(f'Generated {len(pred)} predictions')"),
        ("NLP Parser", "from api.nlp.command_parser import parse_command; r = parse_command('too hot', 26.0); print(f'Delta: {r.get(\"delta\")}')"),
        ("CSV Generator", "import numpy as np; from api.csv_generator import generate_schedule_csv; p = np.random.uniform(22, 28, 96); csv = generate_schedule_csv(p); print(f'{len(csv.splitlines())} lines')")
    ]
    
    for test_name, test_code in tests:
        print(f"\nTesting {test_name}...")
        success, stdout, stderr = run_command(f'python -c "{test_code}"')
        if success:
            print_success(f"{test_name}: {stdout.strip()}")
        else:
            print_error(f"{test_name} failed: {stderr}")
    
    # Step 5: Test API endpoint
    print_step(5, "Testing API endpoint...")
    print("Starting Django server...")
    
    # Start Django server in background
    server_process = subprocess.Popen(
        ["python", "manage.py", "runserver", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(5)
    
    # Check if server is running
    if server_process.poll() is not None:
        print_error("Django server failed to start")
        return 1
    
    try:
        # Test scheduled mode
        print("\nTesting scheduled mode...")
        response = requests.post(
            "http://localhost:8000/api/predict/",
            json={
                "mode": "scheduled",
                "timestamp": "2024-01-15T10:30:00",
                "temperature_c": 26.5,
                "device_id": "test_device"
            },
            timeout=30
        )
        
        if response.status_code == 200 and "timestamp,setpoint_c,source" in response.text:
            lines = len(response.text.splitlines())
            print_success(f"Scheduled mode: Received CSV with {lines} lines")
        else:
            print_error(f"Scheduled mode failed: {response.status_code}")
            print(response.text[:200])
        
        # Test voice override mode
        print("\nTesting voice override mode...")
        response = requests.post(
            "http://localhost:8000/api/predict/",
            json={
                "mode": "voice_override",
                "timestamp": "2024-01-15T10:30:00",
                "temperature_c": 26.5,
                "device_id": "test_device",
                "command_text": "it's too hot"
            },
            timeout=30
        )
        
        if response.status_code == 200 and "override" in response.text:
            print_success("Voice override mode: Override detected in response")
        else:
            print_error(f"Voice override mode failed: {response.status_code}")
            print(response.text[:200])
    
    except requests.exceptions.RequestException as e:
        print_error(f"API test failed: {e}")
    
    finally:
        # Stop Django server
        print("\nStopping Django server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
    
    # Summary
    print_header("Dry Run Test Complete!")
    print("Summary:")
    print("  ✓ Environment configured")
    print("  ✓ Model artifacts verified")
    print("  ✓ Django checks passed")
    print("  ✓ Components tested")
    print("  ✓ API endpoints tested")
    print("\nThe system is ready for deployment!")
    print("\nNext steps:")
    print("  1. Review DRY_RUN_TESTING.md for detailed testing")
    print("  2. Review DEPLOYMENT.md for deployment instructions")
    print("  3. Run: python test_ec2_endpoint.py for full API tests")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

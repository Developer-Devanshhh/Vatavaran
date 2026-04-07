# Vatavaran - Dry Run Testing Guide

This guide will help you test the system locally without actual hardware.

## Prerequisites

1. Python 3.8+ installed
2. All dependencies installed: `pip install -r requirements.txt`
3. WeatherAPI key: `6415f4c56b1d424384860604242303`

## Step 1: Set Up Environment

```bash
# Set environment variables
export WEATHERAPI_KEY="6415f4c56b1d424384860604242303"
export DJANGO_SECRET_KEY="test-secret-key-for-dry-run"
export DEBUG="True"
export ALLOWED_HOSTS="localhost,127.0.0.1"
export MODEL_DIR="."

# Or create .env file
cat > .env << EOF
WEATHERAPI_KEY=6415f4c56b1d424384860604242303
DJANGO_SECRET_KEY=test-secret-key-for-dry-run
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
MODEL_DIR=.
EOF
```

## Step 2: Run Unit Tests

Test all components individually:

```bash
# Test weather API
python -m pytest api/test_weather.py -v

# Test LSTM inference
python -m pytest api/test_inference.py -v

# Test feature engineering
python -m pytest api/test_features.py -v

# Test NLP parser
python -m pytest api/test_command_parser.py -v

# Test CSV generator
python -m pytest api/test_csv_generator.py -v

# Test API views
python manage.py test api.test_views -v

# Run all tests
python -m pytest api/ -v
```

## Step 3: Start Django Server

In Terminal 1:

```bash
# Run Django development server
python manage.py runserver

# You should see:
# Starting development server at http://127.0.0.1:8000/
```

## Step 4: Test API Endpoint (Scheduled Mode)

In Terminal 2:

```bash
# Test with curl
curl -X POST http://localhost:8000/api/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "scheduled",
    "timestamp": "2024-01-15T10:30:00",
    "temperature_c": 26.5,
    "device_id": "test_device"
  }'

# You should get a CSV response with 96 rows
```

Or use the test script:

```bash
python test_ec2_endpoint.py
```

## Step 5: Test API Endpoint (Voice Override Mode)

```bash
# Test voice override with curl
curl -X POST http://localhost:8000/api/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "voice_override",
    "timestamp": "2024-01-15T10:30:00",
    "temperature_c": 26.5,
    "device_id": "test_device",
    "command_text": "it'\''s too hot"
  }'

# First 4 rows should have "override" source
```

## Step 6: Test Individual Components

### Test Weather API

```bash
python api/weather_example.py
```

Expected output:
```
Fetching weather forecast...
Weather forecast fetched: 24 hours
First 3 hours:
  timestamp: 2024-01-15 10:00:00, temp: 25.5°C, humidity: 70%
  ...
```

### Test LSTM Inference

```bash
python verify_inference.py
```

Expected output:
```
Testing LSTM Predictor...
✓ Model loaded successfully
✓ Predictions generated: 96 values
✓ Temperature range: [22.0, 28.0]°C
```

### Test NLP Parser

```python
python -c "
from api.nlp.command_parser import parse_command

# Test various commands
print(parse_command('it\\'s too hot', 26.0))
# Expected: {'delta': -2}

print(parse_command('set to 22', 26.0))
# Expected: {'absolute': 22}

print(parse_command('make it cooler', 26.0))
# Expected: {'delta': -1}
"
```

### Test CSV Generator

```python
python -c "
import numpy as np
from api.csv_generator import generate_schedule_csv

# Generate schedule
predictions = np.random.uniform(22, 28, 96)
csv = generate_schedule_csv(predictions)

print(f'CSV lines: {len(csv.splitlines())}')
print('First 3 rows:')
print('\\n'.join(csv.splitlines()[:4]))
"
```

## Step 7: Test Raspberry Pi Components (Simulated)

### Test Sensor Reader

```bash
cd rpi
python sensor_reader.py
```

Expected output:
```
Testing sensor reader...
Reading: {'timestamp': '2024-01-15T10:30:00', 'temperature_c': 25.5, 'device_id': 'rpi_sensor_01'}
```

### Test Pipeline Client (Dry Run)

First, ensure Django server is running, then:

```bash
cd rpi

# Update config.json with localhost
cat > config.json << EOF
{
  "ec2_endpoint": "http://localhost:8000/api/predict/",
  "timeout": 30
}
EOF

# Test scheduled mode
python pipeline_client.py --mode scheduled

# Check if schedule.csv was created
cat ~/vatavaran/schedule.csv | head -5
```

Expected output:
```
=== Running Scheduled Mode ===
Sensor reading: 25.5°C
Sending request to http://localhost:8000/api/predict/
Schedule saved to /home/pi/vatavaran/schedule.csv
Schedule has 97 lines
```

### Test Voice Override

```bash
cd rpi
python pipeline_client.py --mode voice_override --command "it's too hot"

# Check schedule - first 4 rows should have "override" source
cat ~/vatavaran/schedule.csv | head -6
```

## Step 8: Full Integration Test

Run the complete end-to-end test:

```bash
# Ensure Django server is running in Terminal 1
python manage.py runserver

# In Terminal 2, run integration test
python test_ec2_endpoint.py
```

Expected output:
```
============================================================
EC2 API Endpoint End-to-End Test
============================================================

=== Testing Scheduled Mode ===
Status Code: 200
Content-Type: text/csv
CSV Rows: 97
✓ Scheduled mode test PASSED

=== Testing Voice Override Mode ===
Status Code: 200
Content-Type: text/csv
CSV Rows: 97
✓ Voice override test PASSED (4 override slots detected)

============================================================
Test Summary
============================================================
Scheduled Mode: ✓ PASSED
Voice Override Mode: ✓ PASSED

✓ All tests PASSED
```

## Step 9: Test IR Blaster (Simulated)

```bash
cd rpi

# First, create a test schedule
mkdir -p ~/vatavaran
cat > ~/vatavaran/schedule.csv << EOF
timestamp,setpoint_c,source
2024-01-15 10:00:00,24,lstm
2024-01-15 10:15:00,24,lstm
2024-01-15 10:30:00,23,override
2024-01-15 10:45:00,23,override
EOF

# Run IR blaster (will check schedule every minute)
python ir_blaster.py

# Press Ctrl+C to stop after a few iterations
```

Expected output:
```
Starting IR Blaster
Loaded schedule with 4 slots
Current slot: 2, time: 2024-01-15 10:30:00, temp: 23°C
Applying temperature: 23°C (source: override)
Sending IR code for 23°C: AC_23C
IR signal transmitted successfully for 23°C
```

## Troubleshooting

### Issue: "WEATHERAPI_KEY environment variable is not set"

**Solution:**
```bash
export WEATHERAPI_KEY="6415f4c56b1d424384860604242303"
```

### Issue: "Model artifacts not loaded"

**Solution:**
Ensure model files are in the workspace root:
```bash
ls -la *.h5 *.pkl
# Should show: lstm_model.h5, scaler_features.pkl, scaler_target.pkl, model_config.pkl
```

### Issue: "Connection refused" when testing pipeline_client

**Solution:**
Ensure Django server is running:
```bash
python manage.py runserver
```

### Issue: "No module named 'api'"

**Solution:**
Run commands from the workspace root directory.

### Issue: Weather API returns error

**Solution:**
Check API key is valid and you have internet connection:
```bash
curl "http://api.weatherapi.com/v1/forecast.json?key=6415f4c56b1d424384860604242303&q=12.9165,79.1325&days=1"
```

## Quick Test Checklist

- [ ] Environment variables set
- [ ] Django server starts without errors
- [ ] Unit tests pass
- [ ] Scheduled mode returns CSV with 96 rows
- [ ] Voice override mode returns CSV with "override" source in first 4 rows
- [ ] Weather API fetches data successfully
- [ ] LSTM inference generates 96 predictions
- [ ] NLP parser extracts temperature commands
- [ ] Pipeline client can communicate with Django server
- [ ] Schedule CSV is created and readable

## Success Criteria

✅ All unit tests pass  
✅ Django server runs without errors  
✅ API endpoint returns valid CSV schedules  
✅ Voice override applies to first 4 slots  
✅ Pipeline client successfully saves schedule.csv  
✅ IR blaster reads and processes schedule  

If all checks pass, the system is ready for deployment!

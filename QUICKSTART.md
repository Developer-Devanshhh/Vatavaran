# Vatavaran - Quick Start Guide

Get the system up and running in 5 minutes!

## Option 1: Automated Dry Run (Recommended)

Run the automated test script:

```bash
# On Windows
python run_dry_run.py

# On Linux/Mac
python run_dry_run.py
# or
bash run_dry_run.sh
```

This will:
- ✓ Check all dependencies
- ✓ Verify model artifacts
- ✓ Test all components
- ✓ Start Django server and test API
- ✓ Verify scheduled and voice override modes

## Option 2: Manual Testing

### 1. Set Environment Variables

```bash
export WEATHERAPI_KEY="6415f4c56b1d424384860604242303"
export DJANGO_SECRET_KEY="test-key"
export DEBUG="True"
export MODEL_DIR="."
```

### 2. Start Django Server

```bash
python manage.py runserver
```

### 3. Test API (in another terminal)

```bash
# Test scheduled mode
curl -X POST http://localhost:8000/api/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "scheduled",
    "timestamp": "2024-01-15T10:30:00",
    "temperature_c": 26.5,
    "device_id": "test"
  }'

# Test voice override
curl -X POST http://localhost:8000/api/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "voice_override",
    "timestamp": "2024-01-15T10:30:00",
    "temperature_c": 26.5,
    "device_id": "test",
    "command_text": "it'\''s too hot"
  }'
```

### 4. Run Full Test Suite

```bash
python test_ec2_endpoint.py
```

## What You Should See

### Successful Response (Scheduled Mode)
```csv
timestamp,setpoint_c,source
2024-01-15 10:00:00,24,lstm
2024-01-15 10:15:00,24,lstm
2024-01-15 10:30:00,25,lstm
...
(96 rows total)
```

### Successful Response (Voice Override Mode)
```csv
timestamp,setpoint_c,source
2024-01-15 10:00:00,22,override
2024-01-15 10:15:00,22,override
2024-01-15 10:30:00,22,override
2024-01-15 10:45:00,22,override
2024-01-15 11:00:00,24,lstm
...
(First 4 rows have "override", rest have "lstm")
```

## Troubleshooting

### "Model artifacts not loaded"
**Solution:** Ensure these files exist in the project root:
- lstm_model.h5
- scaler_features.pkl
- scaler_target.pkl
- model_config.pkl

### "WEATHERAPI_KEY not set"
**Solution:** 
```bash
export WEATHERAPI_KEY="6415f4c56b1d424384860604242303"
```

### "Connection refused"
**Solution:** Make sure Django server is running:
```bash
python manage.py runserver
```

## Next Steps

1. ✅ **Dry run complete?** → See `DRY_RUN_TESTING.md` for detailed tests
2. 🚀 **Ready to deploy?** → See `DEPLOYMENT.md` for deployment guide
3. 🔧 **Need help?** → Check `HANDOVER.md` for project overview

## Quick Commands Reference

```bash
# Start Django server
python manage.py runserver

# Run all tests
python -m pytest api/ -v

# Test API endpoint
python test_ec2_endpoint.py

# Automated dry run
python run_dry_run.py

# Test individual components
python api/weather_example.py
python verify_inference.py
```

## System Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Raspberry Pi   │────────▶│   AWS EC2        │
│  (Edge Device)  │  HTTP   │  (Django Server) │
└─────────────────┘         └──────────────────┘
       │                             │
       │                             │
   ┌───▼────┐                   ┌───▼────┐
   │ Sensor │                   │  LSTM  │
   │   IR   │                   │Weather │
   │  STT   │                   │  NLP   │
   └────────┘                   └────────┘
```

## Success Checklist

- [ ] Environment variables set
- [ ] Django server starts without errors
- [ ] Scheduled mode returns 96-row CSV
- [ ] Voice override shows "override" in first 4 rows
- [ ] All unit tests pass
- [ ] API endpoint responds correctly

**All checked?** You're ready to deploy! 🎉

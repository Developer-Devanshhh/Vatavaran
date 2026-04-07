# Vatavaran Testing Guide

## 🚀 Quick Start - Choose Your Path

### Path 1: Automated Testing (Easiest)
```bash
python run_dry_run.py
```
**Time:** 2-3 minutes  
**What it does:** Tests everything automatically

### Path 2: Manual Step-by-Step
See `QUICKSTART.md` for manual testing steps  
**Time:** 5-10 minutes  
**What it does:** Test each component individually

### Path 3: Comprehensive Testing
See `DRY_RUN_TESTING.md` for detailed testing  
**Time:** 15-20 minutes  
**What it does:** Full system validation

## 📋 Testing Checklist

### Before You Start
- [ ] Python 3.8+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Model artifacts present (*.h5, *.pkl files)
- [ ] WeatherAPI key: `6415f4c56b1d424384860604242303`

### Quick Tests (5 minutes)

1. **Environment Setup**
   ```bash
   export WEATHERAPI_KEY="6415f4c56b1d424384860604242303"
   export MODEL_DIR="."
   ```

2. **Django Check**
   ```bash
   python manage.py check
   ```
   ✅ Should show: "System check identified no issues"

3. **Start Server**
   ```bash
   python manage.py runserver
   ```
   ✅ Should show: "Starting development server at http://127.0.0.1:8000/"

4. **Test API** (in new terminal)
   ```bash
   python test_ec2_endpoint.py
   ```
   ✅ Should show: "✓ All tests PASSED"

### Component Tests (10 minutes)

Run individual component tests:

```bash
# Weather API
python -m pytest api/test_weather.py -v

# LSTM Inference
python -m pytest api/test_inference.py -v

# Feature Engineering
python -m pytest api/test_features.py -v

# NLP Parser
python -m pytest api/nlp/test_command_parser.py -v

# CSV Generator
python -m pytest api/test_csv_generator.py -v

# API Views
python manage.py test api.test_views
```

✅ All tests should PASS

### Integration Tests (5 minutes)

1. **Test Scheduled Mode**
   ```bash
   curl -X POST http://localhost:8000/api/predict/ \
     -H "Content-Type: application/json" \
     -d '{"mode":"scheduled","timestamp":"2024-01-15T10:30:00","temperature_c":26.5,"device_id":"test"}'
   ```
   ✅ Should return CSV with 96 rows

2. **Test Voice Override**
   ```bash
   curl -X POST http://localhost:8000/api/predict/ \
     -H "Content-Type: application/json" \
     -d '{"mode":"voice_override","timestamp":"2024-01-15T10:30:00","temperature_c":26.5,"device_id":"test","command_text":"too hot"}'
   ```
   ✅ First 4 rows should have "override" source

### Raspberry Pi Components (Simulated)

```bash
# Test sensor reader
cd rpi
python sensor_reader.py

# Test pipeline client (requires Django server running)
python pipeline_client.py --mode scheduled

# Test with voice command
python pipeline_client.py --mode voice_override --command "it's too hot"
```

## 🎯 Expected Results

### Scheduled Mode Response
```csv
timestamp,setpoint_c,source
2024-01-15 10:00:00,24,lstm
2024-01-15 10:15:00,24,lstm
2024-01-15 10:30:00,25,lstm
...
```
- 97 lines total (1 header + 96 data rows)
- All rows have source="lstm"
- Temperatures between 18-30°C

### Voice Override Response
```csv
timestamp,setpoint_c,source
2024-01-15 10:00:00,22,override
2024-01-15 10:15:00,22,override
2024-01-15 10:30:00,22,override
2024-01-15 10:45:00,22,override
2024-01-15 11:00:00,24,lstm
...
```
- First 4 rows have source="override"
- Remaining rows have source="lstm"
- Override temperature applied based on command

## 🐛 Common Issues & Solutions

### Issue: "Model artifacts not loaded"
**Cause:** Missing model files  
**Solution:** Ensure these files exist:
```bash
ls -la lstm_model.h5 scaler_features.pkl scaler_target.pkl model_config.pkl
```

### Issue: "WEATHERAPI_KEY not set"
**Cause:** Environment variable not set  
**Solution:**
```bash
export WEATHERAPI_KEY="6415f4c56b1d424384860604242303"
```

### Issue: "Connection refused"
**Cause:** Django server not running  
**Solution:**
```bash
python manage.py runserver
```

### Issue: "Weather API failed"
**Cause:** No internet or invalid API key  
**Solution:** Check internet connection and API key

### Issue: "Import error"
**Cause:** Missing dependencies  
**Solution:**
```bash
pip install -r requirements.txt
```

## 📊 Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Weather API | 9 tests | ✅ |
| LSTM Inference | 14 tests | ✅ |
| Feature Engineering | 6 tests | ✅ |
| NLP Parser | 19 tests | ✅ |
| CSV Generator | 19 tests | ✅ |
| API Views | 9 tests | ✅ |
| **Total** | **76 tests** | ✅ |

## 🔍 Validation Criteria

### System is Ready When:
- ✅ All unit tests pass (76/76)
- ✅ Django server starts without errors
- ✅ API returns valid CSV schedules
- ✅ Scheduled mode generates 96 predictions
- ✅ Voice override applies to first 4 slots
- ✅ Weather API fetches data successfully
- ✅ LSTM generates predictions in range 18-30°C
- ✅ NLP parser extracts temperature commands

## 📚 Documentation Reference

| Document | Purpose | When to Use |
|----------|---------|-------------|
| `QUICKSTART.md` | Get started quickly | First time setup |
| `DRY_RUN_TESTING.md` | Detailed testing guide | Comprehensive validation |
| `DEPLOYMENT.md` | Production deployment | Ready to deploy |
| `HANDOVER.md` | Project overview | Understanding the system |
| `README_TESTING.md` | This file | Testing reference |

## 🎓 Testing Best Practices

1. **Always test in order:**
   - Unit tests first
   - Component tests second
   - Integration tests last

2. **Check logs for errors:**
   ```bash
   # Django logs
   tail -f /tmp/django_server.log
   
   # Application logs
   python manage.py runserver --verbosity 2
   ```

3. **Verify responses:**
   - Check HTTP status codes
   - Validate CSV format
   - Verify data ranges

4. **Test edge cases:**
   - Invalid inputs
   - Missing fields
   - Out-of-range values

## ✅ Final Checklist

Before deployment, ensure:
- [ ] All automated tests pass
- [ ] Manual API tests work
- [ ] Scheduled mode returns valid CSV
- [ ] Voice override applies correctly
- [ ] Error handling works (test with invalid inputs)
- [ ] Logs show no errors
- [ ] Performance is acceptable (< 5s response time)

## 🚀 Ready to Deploy?

If all tests pass, you're ready! See `DEPLOYMENT.md` for next steps.

**Questions?** Check `HANDOVER.md` for project details.

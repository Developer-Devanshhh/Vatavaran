# Implementation Plan: Vatavaran Climate Control System

## Overview

This implementation plan follows the component-based architecture for Vatavaran, a distributed smart climate control system. The system consists of two main environments: AWS EC2 (Django server for ML inference and weather integration) and Raspberry Pi 4 (edge device for sensing, voice input, and IR control). Implementation follows the order specified in the original specification: EC2 components first (Django setup through API endpoint), then RPi components (sensor reader through IR blaster).

## Tasks

- [x] 1. Set up Django project structure on EC2
  - Create Django project `vatavaran_server` with app `api`
  - Configure settings.py with environment variables: WEATHERAPI_KEY, DJANGO_SECRET_KEY, DEBUG, ALLOWED_HOSTS, MODEL_DIR
  - Set up URL routing for /api/predict/ endpoint
  - Create directory structure: api/, api/nlp/, models/
  - Install dependencies: django, djangorestframework, tensorflow, scikit-learn, pandas, numpy, requests, joblib, gunicorn
  - Requirements: 11.1, 13.1, 13.2, 13.3

- [ ] 2. Implement Weather API module
  - [x] 2.1 Create weather.py with WeatherAPI.com integration
    - Implement function to fetch 24-hour forecast for Vellore, Tamil Nadu (lat: 12.9165, lon: 79.1325)
    - Extract hourly fields: temp_c, humidity, feelslike_c, wind_kph, pressure_mb, cloud, uv, condition.code
    - Return DataFrame with timestamp and weather fields
    - Requirements: 5.1, 5.2, 5.3
  
  - [x] 2.2 Add weather data caching with 30-minute TTL
    - Implement in-memory cache for last successful weather response
    - Use cached data when API request fails
    - Return HTTP 500 when no cache available and API fails
    - Requirements: 5.4, 5.5, 12.1

- [ ] 3. Implement LSTM inference module
  - [x] 3.1 Create inference.py with LSTMPredictor class
    - Load all 4 model artifacts at initialization: lstm_model.h5, scaler_features.pkl, scaler_target.pkl, model_config.pkl
    - Validate model_config.pkl contains feature_names and sequence_length
    - Validate scaler compatibility with model
    - Refuse to start if artifacts fail to load
    - Requirements: 7.1, 15.1, 15.2, 15.3, 15.4
  
  - [x] 3.2 Implement predict_24h method
    - Scale input features using scaler_features.pkl
    - Run inference using lstm_model.h5 via TensorFlow
    - Descale predictions using scaler_target.pkl
    - Return array of 96 predicted temperatures
    - Log errors and raise exception on inference failure
    - Requirements: 7.2, 7.3, 7.4, 7.5, 7.6

- [ ] 4. Implement feature engineering module
  - [x] 4.1 Create features.py with build_feature_matrix function
    - Load feature names and order from model_config.pkl
    - Generate time cyclical features: hour_sin, hour_cos, day_of_week_sin, day_of_week_cos, month_sin, month_cos
    - Generate lag features: temperature at t-1, t-2, t-4, t-8, t-96
    - Generate rolling statistics: mean and std over last 4, 8, 24 slots
    - Merge weather forecast data by timestamp alignment
    - Generate boolean flags: is_weekend, is_night (22:00-06:00)
    - Return feature matrix of shape (96, 90)
    - Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8

- [ ] 5. Implement NLP command parser
  - [x] 5.1 Copy command_parser.py and lexicons.py from existing codebase
    - Place in api/nlp/ directory
    - Verify parse_command function signature: parse_command(text, current_temp_c, current_fan)
    - Requirements: 8.1
  
  - [x] 5.2 Integrate NLP parser with error handling
    - Extract temperature delta or absolute setpoint from command text
    - Return structured result with delta or absolute value
    - Return default delta of 0 and log unparseable commands
    - Requirements: 8.2, 8.3, 8.4

- [ ] 6. Implement CSV generator module
  - [x] 6.1 Create csv_generator.py with schedule generation logic
    - Generate 96 rows with timestamp, setpoint_c, source columns
    - Generate timestamps at 15-minute intervals from current time
    - Round LSTM predictions to whole degrees Celsius
    - Mark LSTM slots with source "lstm"
    - Requirements: 9.1, 9.2, 9.3, 9.4, 14.2, 14.3, 14.4
  
  - [x] 6.2 Add voice override logic
    - Apply override temperature to next 4 time slots (Override_Window)
    - Mark override slots with source "override"
    - Resume LSTM predictions after override window
    - Validate setpoint_c values are integers in range 18-30
    - Return CSV in text/csv format
    - Requirements: 9.5, 9.6, 9.7, 9.8, 14.5, 14.6

- [ ] 7. Implement Django API endpoint
  - [x] 7.1 Create views.py with POST /api/predict/ endpoint
    - Accept JSON payloads with mode field (scheduled or voice_override)
    - Parse sensor data from request body
    - Requirements: 11.1, 11.2
  
  - [x] 7.2 Orchestrate prediction pipeline for scheduled mode
    - Call Weather_Client to fetch forecast
    - Call Feature_Engine to build 90-feature matrix
    - Call LSTM_Predictor for 96 temperature predictions
    - Call CSV_Generator to produce schedule
    - Return Schedule_CSV with Content-Type: text/csv
    - Requirements: 11.2, 11.4, 11.5
  
  - [x] 7.3 Orchestrate prediction pipeline for voice_override mode
    - Call Weather_Client, Feature_Engine, LSTM_Predictor as in scheduled mode
    - Call NLP_Parser with command_text
    - Pass override to CSV_Generator
    - Return updated Schedule_CSV
    - Requirements: 11.3, 11.4, 11.5
  
  - [x] 7.4 Add comprehensive error handling and logging
    - Log all errors with timestamp and request details to file
    - Return HTTP 500 on component failures
    - Requirements: 11.6, 12.3

- [x] 8. Checkpoint - Test EC2 components end-to-end
  - Test /api/predict/ endpoint with curl or Postman in scheduled mode
  - Test /api/predict/ endpoint with voice_override mode
  - Verify CSV output format and content
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement Raspberry Pi sensor reader
  - [x] 9.1 Create rpi/sensor_reader.py
    - Read temperature from RPi sensor hardware
    - Return dict with timestamp (ISO 8601), temperature_c (float), device_id (string)
    - Log errors and return last valid reading with staleness indicator on hardware failure
    - Requirements: 1.1, 1.2, 1.3, 14.1

- [ ] 10. Implement Raspberry Pi pipeline client
  - [x] 10.1 Create rpi/pipeline_client.py with payload builder
    - Build JSON payload for scheduled mode: mode, sensor data
    - Build JSON payload for voice_override mode: mode, sensor data, command_text
    - Read EC2 endpoint URL from configuration file
    - Requirements: 3.2, 4.1, 13.5, 14.1
  
  - [x] 10.2 Implement HTTP communication with EC2
    - Send POST request to EC2 /api/predict/ endpoint
    - Receive schedule.csv in response
    - Save to /home/pi/vatavaran/schedule.csv
    - Handle connection failures gracefully (retain previous schedule)
    - Requirements: 3.3, 3.4, 4.2, 4.3, 12.2

- [ ] 11. Implement Raspberry Pi STT module
  - [x] 11.1 Create rpi/stt.py with Vosk integration
    - Install Vosk library and vosk-model-small-en-in-0.4 model (~40MB)
    - Record audio for 5 seconds after button press or wake word
    - Transcribe audio to text using on-device Vosk processing
    - Return plain text string without cloud connectivity
    - Return error indicator on transcription failure or empty output
    - Requirements: 2.1, 2.2, 2.3, 2.4, 12.4

- [x] 12. Test voice override mode end-to-end
  - Test STT module with sample voice commands
  - Test pipeline_client voice_override payload construction
  - Test EC2 NLP parsing and override application
  - Verify schedule.csv updates immediately
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Implement Raspberry Pi IR blaster module
  - [x] 13.1 Create rpi/ir_blaster.py with schedule reader
    - Read schedule.csv from /home/pi/vatavaran/schedule.csv
    - Determine current time slot based on system time
    - Read setpoint_c for current slot when time slot changes
    - Check for schedule changes every 1 minute
    - Apply new schedule on next loop iteration when CSV updates
    - Requirements: 10.1, 10.2, 10.3, 10.6, 10.7, 4.4
  
  - [x] 13.2 Implement IR signal transmission
    - Load IR code mappings from configuration file (not hardcoded)
    - Map setpoint temperature to corresponding IR signal code
    - Transmit IR signal to AC unit using lirc or python-irblaster
    - Log error and skip slot when IR code mapping is missing
    - Requirements: 10.4, 10.5, 10.8, 13.4

- [x] 14. Set up Raspberry Pi cron job for scheduled execution
  - Create cron job to run pipeline_client.py every 15 minutes
  - Cron entry: `*/15 * * * * /home/pi/vatavaran/venv/bin/python /home/pi/vatavaran/rpi/pipeline_client.py --mode scheduled`
  - Verify cron job executes and updates schedule.csv
  - Requirements: 3.1

- [x] 15. Final checkpoint - System integration test
  - Verify scheduled mode executes every 15 minutes via cron
  - Verify voice override updates schedule immediately
  - Verify IR blaster applies temperatures from schedule
  - Test error resilience: EC2 unreachable, weather API failure, sensor failure
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Implementation language: Python
- EC2 components (tasks 1-8) must be completed before RPi components (tasks 9-15)
- Model artifacts (lstm_model.h5, scaler_features.pkl, scaler_target.pkl, model_config.pkl) must be present in MODEL_DIR before starting task 3
- WeatherAPI.com API key must be configured before starting task 2
- IR code mappings must be manually configured per AC model before starting task 13
- Checkpoints ensure incremental validation at major integration points
- All timestamps use ISO 8601 format in JSON payloads and "YYYY-MM-DD HH:MM:SS" in CSV files

# Requirements Document: Vatavaran Climate Control System

## Introduction

Vatavaran is a distributed smart climate control system that automates air conditioning temperature settings using LSTM-based machine learning predictions. The system operates across two computing environments: a Raspberry Pi 4 for edge sensing, voice input, and IR control, and an AWS EC2 instance for ML inference and weather data integration. The system generates 24-hour temperature schedules (96 15-minute slots) based on sensor data, weather forecasts, and optional voice commands, then executes those schedules via IR signals to control the AC unit.

## Glossary

- **RPi_Sensor_Module**: Temperature sensor hardware connected to Raspberry Pi 4 that measures ambient temperature
- **STT_Module**: Speech-to-text module running on Raspberry Pi using Vosk or Whisper for offline voice transcription
- **Pipeline_Client**: Raspberry Pi component that builds HTTP payloads and communicates with EC2 server
- **Django_API**: REST API endpoint on EC2 that receives sensor data and returns temperature schedules
- **Weather_Client**: EC2 component that fetches forecast data from weatherapi.com
- **Feature_Engine**: EC2 component that constructs 90-feature matrix from sensor history and weather data
- **LSTM_Predictor**: EC2 component that loads model artifacts and generates 96 temperature predictions
- **NLP_Parser**: EC2 component that interprets natural language voice commands and extracts temperature adjustments
- **CSV_Generator**: EC2 component that produces schedule.csv with 96 timestamped temperature setpoints
- **IR_Blaster**: Raspberry Pi component that reads schedule and sends IR signals to AC unit
- **Schedule_CSV**: CSV file containing 96 rows of timestamp, setpoint_c, and source columns
- **Override_Window**: The next 4 time slots (1 hour) where voice command temperature adjustments are applied
- **Time_Slot**: 15-minute interval within the 24-hour schedule (96 slots total)
- **Model_Artifacts**: Four files required for LSTM inference: lstm_model.h5, scaler_features.pkl, scaler_target.pkl, model_config.pkl

## Requirements

### Requirement 1: Sensor Data Collection

**User Story:** As a system operator, I want the Raspberry Pi to read temperature sensor data, so that current environmental conditions can be used for prediction.

#### Acceptance Criteria

1. WHEN the RPi_Sensor_Module is queried, THE RPi_Sensor_Module SHALL return a reading containing timestamp, temperature in Celsius, and device identifier
2. THE RPi_Sensor_Module SHALL format sensor readings as JSON with fields: timestamp (ISO 8601), temperature_c (float), and device_id (string)
3. WHEN sensor hardware fails to respond, THE RPi_Sensor_Module SHALL log the error and return the last valid reading with a staleness indicator

### Requirement 2: Voice Command Capture

**User Story:** As a user, I want to speak voice commands to adjust temperature, so that I can override automated settings when needed.

#### Acceptance Criteria

1. WHEN a voice button is pressed or wake word is detected, THE STT_Module SHALL record audio for 5 seconds
2. WHEN audio recording completes, THE STT_Module SHALL transcribe the audio to text using on-device processing (Vosk or Whisper)
3. THE STT_Module SHALL return transcribed text as a plain string without requiring cloud connectivity
4. WHEN transcription fails or produces empty output, THE STT_Module SHALL return an error indicator

### Requirement 3: Scheduled Execution

**User Story:** As a system operator, I want the pipeline to execute automatically every 15 minutes, so that temperature schedules stay current without manual intervention.

#### Acceptance Criteria

1. THE Pipeline_Client SHALL execute in scheduled mode every 15 minutes via cron job
2. WHEN executing in scheduled mode, THE Pipeline_Client SHALL build a JSON payload containing mode "scheduled" and current sensor reading
3. WHEN executing in scheduled mode, THE Pipeline_Client SHALL send HTTP POST request to EC2 endpoint /api/predict/
4. WHEN the EC2 response is received, THE Pipeline_Client SHALL save the returned CSV to /home/pi/vatavaran/schedule.csv

### Requirement 4: Voice Override Execution

**User Story:** As a user, I want voice commands to immediately update the temperature schedule, so that I can quickly adjust comfort levels.

#### Acceptance Criteria

1. WHEN a voice command is transcribed, THE Pipeline_Client SHALL build a JSON payload containing mode "voice_override", current sensor reading, and command_text
2. WHEN executing in voice override mode, THE Pipeline_Client SHALL send HTTP POST request to EC2 endpoint /api/predict/
3. WHEN the EC2 response is received, THE Pipeline_Client SHALL replace the existing schedule.csv immediately
4. THE IR_Blaster SHALL detect the schedule change and apply the new temperature within 1 minute

### Requirement 5: Weather Data Integration

**User Story:** As a system operator, I want the system to fetch weather forecasts, so that predictions can account for external environmental conditions.

#### Acceptance Criteria

1. WHEN the Django_API receives a prediction request, THE Weather_Client SHALL fetch 24-hour forecast data from weatherapi.com for Vellore, Tamil Nadu
2. THE Weather_Client SHALL extract hourly values for: temp_c, humidity, feelslike_c, wind_kph, pressure_mb, cloud, uv, and condition code
3. THE Weather_Client SHALL return weather data as a DataFrame with timestamp and extracted fields
4. WHEN the weatherapi.com request fails, THE Weather_Client SHALL use the last cached weather response with TTL of 30 minutes
5. WHEN no cached data is available and the API fails, THE Django_API SHALL return HTTP 500 error


### Requirement 6: Feature Engineering

**User Story:** As a system operator, I want sensor and weather data transformed into ML features, so that the LSTM model receives properly formatted input.

#### Acceptance Criteria

1. WHEN the Feature_Engine processes data, THE Feature_Engine SHALL construct exactly 90 features matching the trained model's feature list
2. THE Feature_Engine SHALL load feature names and order from model_config.pkl to ensure compatibility
3. THE Feature_Engine SHALL generate time cyclical features: hour_sin, hour_cos, day_of_week_sin, day_of_week_cos, month_sin, month_cos
4. THE Feature_Engine SHALL generate lag features from sensor history: temperature at t-1, t-2, t-4, t-8, and t-96 (previous day same slot)
5. THE Feature_Engine SHALL generate rolling statistics: mean and standard deviation over last 4, 8, and 24 time slots
6. THE Feature_Engine SHALL merge weather forecast data with sensor features by timestamp alignment
7. THE Feature_Engine SHALL generate boolean flags: is_weekend and is_night (22:00-06:00)
8. THE Feature_Engine SHALL return a feature matrix of shape (96, 90) representing the next 24 hours

### Requirement 7: LSTM Inference

**User Story:** As a system operator, I want the LSTM model to predict optimal temperatures, so that the AC can be controlled automatically based on learned patterns.

#### Acceptance Criteria

1. WHEN Django starts, THE LSTM_Predictor SHALL load all four Model_Artifacts: lstm_model.h5, scaler_features.pkl, scaler_target.pkl, and model_config.pkl
2. WHEN the LSTM_Predictor receives a feature matrix, THE LSTM_Predictor SHALL scale input features using scaler_features.pkl
3. WHEN features are scaled, THE LSTM_Predictor SHALL run inference using lstm_model.h5 via TensorFlow
4. WHEN inference completes, THE LSTM_Predictor SHALL descale predictions using scaler_target.pkl
5. THE LSTM_Predictor SHALL return an array of 96 predicted temperatures (one per 15-minute slot)
6. WHEN LSTM inference fails, THE Django_API SHALL log the error and return HTTP 500

### Requirement 8: Natural Language Command Parsing

**User Story:** As a user, I want the system to understand my voice commands, so that I can request temperature changes in natural language.

#### Acceptance Criteria

1. WHEN the Django_API receives a voice_override request, THE NLP_Parser SHALL parse the command_text with current temperature context
2. THE NLP_Parser SHALL extract either a temperature delta (e.g., "too hot" → -2°C) or absolute setpoint (e.g., "set to 22" → 22°C)
3. THE NLP_Parser SHALL return a structured result containing either delta or absolute temperature value
4. WHEN command text cannot be parsed, THE NLP_Parser SHALL return a default delta of 0 and log the unparseable command

### Requirement 9: Schedule Generation

**User Story:** As a system operator, I want LSTM predictions and voice overrides combined into a single schedule, so that the IR blaster has clear instructions.

#### Acceptance Criteria

1. WHEN the CSV_Generator receives LSTM predictions, THE CSV_Generator SHALL create 96 rows with timestamp, setpoint_c, and source columns
2. THE CSV_Generator SHALL generate timestamps at 15-minute intervals starting from current time
3. THE CSV_Generator SHALL round LSTM predicted temperatures to whole degrees Celsius
4. THE CSV_Generator SHALL mark all LSTM-generated slots with source value "lstm"
5. WHEN voice override is active, THE CSV_Generator SHALL apply the override temperature to the next 4 time slots (Override_Window)
6. THE CSV_Generator SHALL mark override slots with source value "override"
7. WHEN override window ends, THE CSV_Generator SHALL resume using LSTM predictions for remaining slots
8. THE CSV_Generator SHALL return Schedule_CSV in text/csv format

### Requirement 10: IR Control Execution

**User Story:** As a system operator, I want the Raspberry Pi to send IR signals to the AC unit, so that predicted temperatures are physically applied.

#### Acceptance Criteria

1. THE IR_Blaster SHALL read Schedule_CSV from /home/pi/vatavaran/schedule.csv
2. THE IR_Blaster SHALL determine the current time slot based on system time
3. WHEN the current time slot changes, THE IR_Blaster SHALL read the setpoint_c for that slot
4. THE IR_Blaster SHALL map the setpoint temperature to the corresponding IR signal code using a configured mapping
5. THE IR_Blaster SHALL transmit the IR signal to the AC unit
6. THE IR_Blaster SHALL check for schedule changes every 1 minute
7. WHEN Schedule_CSV is updated, THE IR_Blaster SHALL apply the new schedule on the next loop iteration
8. WHEN an IR code mapping is missing for a temperature, THE IR_Blaster SHALL log an error and skip that slot

### Requirement 11: API Endpoint

**User Story:** As a developer, I want a single REST API endpoint for predictions, so that the Raspberry Pi has a simple integration point.

#### Acceptance Criteria

1. THE Django_API SHALL expose endpoint POST /api/predict/ accepting JSON payloads
2. WHEN a request with mode "scheduled" is received, THE Django_API SHALL process without NLP parsing
3. WHEN a request with mode "voice_override" is received, THE Django_API SHALL invoke the NLP_Parser with command_text
4. THE Django_API SHALL orchestrate: Weather_Client fetch, Feature_Engine processing, LSTM_Predictor inference, and CSV_Generator output
5. THE Django_API SHALL return Schedule_CSV with Content-Type: text/csv
6. WHEN any component fails, THE Django_API SHALL log the error with timestamp and request details

### Requirement 12: Error Handling and Resilience

**User Story:** As a system operator, I want the system to handle failures gracefully, so that temporary issues don't cause complete system failure.

#### Acceptance Criteria

1. WHEN the Weather_Client cannot reach weatherapi.com, THE Weather_Client SHALL use cached weather data if available within 30-minute TTL
2. WHEN the Pipeline_Client cannot reach EC2, THE IR_Blaster SHALL continue using the last valid Schedule_CSV
3. WHEN the LSTM_Predictor fails, THE Django_API SHALL return HTTP 500 and the Pipeline_Client SHALL retain the previous schedule
4. WHEN the STT_Module fails transcription, THE Pipeline_Client SHALL not send a voice_override request
5. THE Django_API SHALL log all errors to a file on EC2 with timestamp, error type, and context

### Requirement 13: Configuration Management

**User Story:** As a system operator, I want configuration stored separately from code, so that deployment-specific values can be changed without code modifications.

#### Acceptance Criteria

1. THE Django_API SHALL read WEATHERAPI_KEY from environment variable
2. THE Django_API SHALL read DJANGO_SECRET_KEY, DEBUG, and ALLOWED_HOSTS from environment variables
3. THE Django_API SHALL read MODEL_DIR path from environment variable
4. THE IR_Blaster SHALL read IR code mappings from a configuration file (not hardcoded)
5. THE Pipeline_Client SHALL read EC2 endpoint URL from a configuration file

### Requirement 14: Data Format Consistency

**User Story:** As a developer, I want consistent data formats across components, so that integration is reliable and maintainable.

#### Acceptance Criteria

1. THE Pipeline_Client SHALL format all timestamps in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
2. THE CSV_Generator SHALL format Schedule_CSV timestamps as "YYYY-MM-DD HH:MM:SS"
3. THE Schedule_CSV SHALL contain exactly 96 rows representing 24 hours at 15-minute intervals
4. THE Schedule_CSV SHALL contain columns: timestamp, setpoint_c, source
5. THE setpoint_c values SHALL be integers in the range 18-30 degrees Celsius
6. THE source values SHALL be either "lstm" or "override"

### Requirement 15: Model Artifact Management

**User Story:** As a system operator, I want model artifacts loaded once at startup, so that prediction requests have minimal latency.

#### Acceptance Criteria

1. WHEN Django application starts, THE LSTM_Predictor SHALL load all Model_Artifacts into memory
2. THE LSTM_Predictor SHALL validate that model_config.pkl contains required fields: feature_names and sequence_length
3. THE LSTM_Predictor SHALL validate that scaler_features.pkl and scaler_target.pkl are compatible with the model
4. WHEN Model_Artifacts fail to load, THE Django_API SHALL refuse to start and log the error
5. THE LSTM_Predictor SHALL reuse loaded artifacts for all prediction requests without reloading


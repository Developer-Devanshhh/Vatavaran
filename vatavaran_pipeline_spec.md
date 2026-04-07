# Vatavaran — Full Pipeline Specification
> For Kiro / AI agent implementation. Read this entire document before writing any code.

---

## Overview

Vatavaran is a smart climate control system running across two environments:

- **Raspberry Pi 4** — sensor reading, voice capture, STT, IR blaster control
- **AWS EC2 (Django, static IP)** — weather API, LSTM inference, NLP parsing, CSV generation

The RPi sends data to EC2. EC2 returns a 24-hour AC temperature schedule as a CSV (96 slots at 15-min intervals). The RPi reads that CSV and fires IR commands to the AC unit accordingly.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│              Raspberry Pi 4                 │
│                                             │
│  [Sensor] ──► [Payload Builder]             │
│  [Mic] ──► [STT on-device] ──► [Text]      │
│                    │                        │
│         HTTP POST to EC2 /predict           │
│                    │                        │
│         ◄── receives schedule.csv           │
│                    │                        │
│         [CSV Reader] ──► [IR Blaster]       │
└─────────────────────────────────────────────┘
                    │ HTTP
┌─────────────────────────────────────────────┐
│              AWS EC2 (Django)               │
│                                             │
│  /predict endpoint                          │
│      │                                      │
│      ├─► [WeatherAPI fetch]                 │
│      ├─► [Feature Engineering (90 feat)]    │
│      ├─► [LSTM Inference via .h5]           │
│      ├─► [NLP Parser] (if voice command)    │
│      └─► [CSV Generator]                    │
│                                             │
│  Returns: schedule.csv                      │
└─────────────────────────────────────────────┘
```

---

## Trigger Modes

There are two ways the pipeline is triggered:

### Mode 1 — Scheduled (every 15 minutes)

1. **Trigger Execution**
   - At midnight, initiate the weather data pipeline.

2. **API Call**
   - Call the Weather API to retrieve forecast data for the upcoming hours (typically 24 hours).

3. **Extract Relevant Data**
   - Parse the response to extract:
     - Timestamp (hourly)
     - Temperature
     - Humidity
     - Pressure
     - Other relevant weather parameters

4. **Create Structured Dataset**
   - Convert the extracted data into a structured format.

5. **Generate CSV File**
   - Store the processed data into a CSV file with timestamped entries.

### Output Format Example

| time                | temperature | humidity | pressure |
|---------------------|------------|----------|----------|
| 2026-04-07 01:00    | 30.5       | 65       | 1012     |
| 2026-04-07 02:00    | 30.0       | 67       | 1011     |

### Key Idea

Instead of making multiple API calls throughout the day, the system:
- Fetches all required forecast data in a single call
- Stores it locally
- Uses this dataset for further prediction and processing

### Mode 2 — Voice Command Override
- User speaks into mic
- RPi captures audio → runs STT on-device → gets text string
- RPi sends text + current sensor reading to EC2
- EC2 runs NLP parser → determines temperature delta or absolute setpoint
- EC2 applies override to the next N hardcoded slots in the schedule
- EC2 returns updated 96-slot CSV
- RPi updates its local schedule immediately

---

## Component Specifications

---

### 1. Raspberry Pi — Sensor Module

**File:** `rpi/sensor_reader.py`

- Reads temperature from existing RPi sensor setup (same hardware that produced the 1.5M record dataset)
- Returns a single dict:
```python
{
    "timestamp": "2025-11-09T14:30:00",
    "temperature_c": 27.4,
    "device_id": "rpi_01"
}
```

---

### 2. Raspberry Pi — Speech-to-Text (STT) Module

**File:** `rpi/stt.py`

- Runs **fully on-device**, no cloud STT
- Recommended library: **Vosk** (lightweight, offline, works on RPi 4)
  - Model to use: `vosk-model-small-en-in-0.4` (Indian English, ~40MB)
  - Install: `pip install vosk`
  - Model download: https://alphacephei.com/vosk/models
- Alternative if Vosk accuracy is poor: **Whisper tiny** via `faster-whisper`
  - Heavier (~150MB) but better accuracy
  - Install: `pip install faster-whisper`
- Records for a fixed duration (e.g. 5 seconds) after button press or wake word
- Returns a plain text string

**Output:** `"it's too hot"` or `"set temperature to 22 degrees"`

---

### 3. Raspberry Pi — Payload Builder & Sender

**File:** `rpi/pipeline_client.py`

Builds the HTTP POST payload and sends to EC2.

**Scheduled mode payload:**
```json
{
    "mode": "scheduled",
    "sensor": {
        "timestamp": "2025-11-09T14:30:00",
        "temperature_c": 27.4,
        "device_id": "rpi_01"
    }
}
```

**Voice override payload:**
```json
{
    "mode": "voice_override",
    "sensor": {
        "timestamp": "2025-11-09T14:30:00",
        "temperature_c": 27.4,
        "device_id": "rpi_01"
    },
    "command_text": "it's too hot"
}
```

- Sends POST to `http://<EC2_STATIC_IP>/api/predict/`
- Receives `schedule.csv` in response body
- Saves to `/home/pi/vatavaran/schedule.csv`

---

### 4. Raspberry Pi — IR Blaster Module

**File:** `rpi/ir_blaster.py`

- Reads current slot from `schedule.csv` based on current time
- Maps temperature setpoint → IR signal code
- Fires IR signal to AC unit
- Runs on a tight loop (every 1 min) checking if current slot has changed
- If schedule changes (new CSV received), picks up automatically on next loop

**IR library to use:** `python-irblaster` or `lirc` depending on hardware setup.

**CSV format it reads:**
```
timestamp,setpoint_c
2025-11-09 14:30:00,24
2025-11-09 14:45:00,23
2025-11-09 15:00:00,24
...
```

**Temperature → IR code mapping** must be manually configured per AC model. Store as a dict in a config file:
```python
IR_CODES = {
    18: "raw_ir_code_for_18c",
    19: "raw_ir_code_for_19c",
    ...
    30: "raw_ir_code_for_30c"
}
```

---

### 5. EC2 — Django Project Structure

```
vatavaran_server/
├── manage.py
├── vatavaran_server/
│   ├── settings.py
│   └── urls.py
├── api/
│   ├── views.py          # Main predict endpoint
│   ├── weather.py        # WeatherAPI fetch + parse
│   ├── features.py       # Feature engineering (90 features)
│   ├── inference.py      # LSTM inference wrapper
│   ├── nlp/
│   │   ├── command_parser.py   # From existing codebase
│   │   └── lexicons.py         # From existing codebase
│   └── csv_generator.py  # Builds output CSV
├── models/
│   ├── lstm_model.h5
│   ├── scaler_features.pkl
│   ├── scaler_target.pkl
│   └── model_config.pkl
└── requirements.txt
```

---

### 6. EC2 — WeatherAPI Module

**File:** `api/weather.py`

- Uses **weatherapi.com** free plan
- API key stored in environment variable: `WEATHERAPI_KEY`
- Location: Vellore, Tamil Nadu (lat: 12.9165, lon: 79.1325)
- Fetches forecast for next 24 hours at hourly resolution
- Also fetches current conditions

**Endpoint used:**
```
GET http://api.weatherapi.com/v1/forecast.json
    ?key=<API_KEY>
    &q=Vellore
    &days=2
    &aqi=no
    &alerts=no
```

**Fields extracted per hour:**
- `temp_c`
- `humidity`
- `feelslike_c`
- `wind_kph`
- `pressure_mb`
- `cloud`
- `uv`
- `condition.code`

Returns a DataFrame with hourly rows, columns = above fields + `timestamp`.

---

### 7. EC2 — Feature Engineering Module

**File:** `api/features.py`

> ⚠️ CRITICAL: This module must reproduce the exact same 90 features the LSTM was trained on. The feature names and order must match `scaler_features.pkl` exactly. Load `model_config.pkl` first and use the feature list from it — do not hardcode feature names.

**General feature categories to engineer:**
- Time cyclical features: `hour_sin`, `hour_cos`, `day_of_week_sin`, `day_of_week_cos`, `month_sin`, `month_cos`
- Lag features: temperature at t-1, t-2, t-4, t-8, t-96 (previous day same slot)
- Rolling statistics: rolling mean and std over last 4, 8, 24 slots
- Weather features from WeatherAPI (aligned by timestamp)
- Boolean flags: `is_weekend`, `is_night` (e.g. 22:00–06:00)

**Function signature:**
```python
def build_feature_matrix(sensor_history: pd.DataFrame, weather_df: pd.DataFrame, model_config: dict) -> np.ndarray:
    """
    Returns array of shape (96, n_features) for the next 24 hours.
    Uses past sensor readings for lag/rolling features.
    Uses weather_df for external weather features.
    Feature order must match model_config['feature_names'].
    """
```

---

### 8. EC2 — LSTM Inference Module

**File:** `api/inference.py`

- Loads all 4 model artifacts at Django startup (not per request)
- Uses `model_config.pkl` to determine sequence length and feature list
- Scales input with `scaler_features.pkl`
- Runs `lstm_model.h5` via TensorFlow
- Descales output with `scaler_target.pkl`
- Returns array of 96 predicted temperatures (one per 15-min slot)

```python
class LSTMPredictor:
    def __init__(self, model_dir: str):
        # Load all 4 artifacts here at init

    def predict_24h(self, feature_matrix: np.ndarray) -> np.ndarray:
        # Returns shape (96,) — predicted temp_c per slot
```

---

### 9. EC2 — NLP Parser Module

**Files:** `api/nlp/command_parser.py`, `api/nlp/lexicons.py`

- Copied directly from existing Vatavaran codebase
- `parse_command(text, current_temp_c, current_fan)` returns delta or absolute setpoint
- Used only in `voice_override` mode

**Override behaviour:**
- Hardcoded override window: **next 4 slots (1 hour)**
- After 4 slots, schedule resumes LSTM predictions
- Override slots are marked in CSV with an `override` flag column

---

### 10. EC2 — CSV Generator

**File:** `api/csv_generator.py`

Combines LSTM predictions + any NLP overrides into the final CSV.

**Output CSV format:**
```
timestamp,setpoint_c,source
2025-11-09 14:30:00,24,lstm
2025-11-09 14:45:00,24,lstm
2025-11-09 15:00:00,22,override
2025-11-09 15:15:00,22,override
2025-11-09 15:30:00,22,override
2025-11-09 15:45:00,22,override
2025-11-09 16:00:00,24,lstm
...
```

- Always 96 rows (next 24 hours from current timestamp)
- `source` column: `lstm` or `override`
- Temperatures are integers (whole degrees Celsius) — round LSTM output

---

### 11. EC2 — Django API Endpoint

**File:** `api/views.py`

**Endpoint:** `POST /api/predict/`

**Request body:** JSON (see Payload Builder section above)

**Response:** CSV file (`Content-Type: text/csv`)

**Logic flow:**
```
receive request
├── fetch weather from WeatherAPI
├── build 90-feature matrix
├── run LSTM → 96 predicted temps
├── if mode == "voice_override":
│       run NLP parser on command_text
│       apply override to next 4 slots
└── generate CSV
    return CSV response
```

**Error handling:**
- If WeatherAPI fails: use last cached weather response (cache in Django memory, TTL 30 min)
- If LSTM inference fails: return HTTP 500, RPi keeps using last valid CSV
- Log all errors to a file on EC2

---

## Environment Variables (EC2)

```
WEATHERAPI_KEY=your_key_here
DJANGO_SECRET_KEY=your_secret
DEBUG=False
ALLOWED_HOSTS=<static_ip>
MODEL_DIR=/path/to/vatavaran_server/models/
```

---

## RPi Cron Job

```cron
*/15 * * * * /home/pi/vatavaran/venv/bin/python /home/pi/vatavaran/rpi/pipeline_client.py --mode scheduled
```

---

## Dependencies

### EC2 (`requirements.txt`)
```
django>=4.2
djangorestframework
tensorflow>=2.12.0
scikit-learn>=1.2.2
pandas>=1.5.3
numpy>=1.23.5
requests
joblib
gunicorn
```

### RPi
```
requests
vosk          # or faster-whisper
pyaudio       # for mic input
RPi.GPIO
```

---

## Implementation Order for Kiro

Follow this exact order:

1. Set up Django project skeleton on EC2
2. Implement `weather.py` — verify WeatherAPI response and field extraction
3. Implement `inference.py` — load 4 model files, verify prediction shape
4. Implement `features.py` — reproduce 90 features, verify scaler compatibility
5. Implement `csv_generator.py`
6. Wire up `views.py` endpoint — test with curl/Postman
7. Implement `rpi/sensor_reader.py`
8. Implement `rpi/pipeline_client.py` — test scheduled mode end to end
9. Implement `rpi/stt.py` — test Vosk on RPi hardware
10. Test voice override mode end to end
11. Implement `rpi/ir_blaster.py` — map IR codes, test one temperature

---

## Open Decisions (resolve before coding)

| Decision | Options | Notes |
|---|---|---|
| STT library | Vosk vs Whisper tiny | Try Vosk first, switch if accuracy poor |
| IR blaster library | lirc vs python-irblaster | Depends on hardware wiring |
| Voice override window | Hardcoded 4 slots (1 hour) | Can make configurable later |
| WeatherAPI resolution | Hourly (free plan) | 15-min forecast available but may need paid plan |


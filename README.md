# Vatavaran Climate Control System

🌡️ **Distributed smart climate control system using LSTM-based ML predictions**

Vatavaran is an intelligent AC control system that uses machine learning to predict optimal temperature settings. It operates across two environments: AWS EC2 for ML inference and Raspberry Pi 4 for edge sensing and IR control.

## 🌟 Features

- **LSTM-based Temperature Prediction**: Generates 24-hour temperature schedules (96 15-minute slots)
- **Weather Integration**: Fetches real-time weather data from WeatherAPI.com
- **Voice Control**: Natural language commands for temperature adjustments
- **Dual Mode Operation**:
  - **Scheduled Mode**: Automatic predictions every 15 minutes
  - **Voice Override Mode**: Immediate temperature adjustments via voice commands
- **Edge Computing**: Raspberry Pi handles sensing, voice input, and IR control
- **Cloud ML**: AWS EC2 runs Django server for ML inference

## 🏗️ Architecture

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

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Django 6.0+
- TensorFlow 2.20+
- WeatherAPI.com API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Developer-Devanshhh/Vatavaran.git
   cd Vatavaran
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   export WEATHERAPI_KEY="your-api-key"
   export DJANGO_SECRET_KEY="your-secret-key"
   export DEBUG="True"
   export MODEL_DIR="."
   ```

4. **Run the automated test**
   ```bash
   python run_dry_run.py
   ```

5. **Start Django server**
   ```bash
   python manage.py runserver
   ```

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[DRY_RUN_TESTING.md](DRY_RUN_TESTING.md)** - Comprehensive testing guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment instructions
- **[HANDOVER.md](HANDOVER.md)** - Complete project overview
- **[README_TESTING.md](README_TESTING.md)** - Testing reference

## 🧪 Testing

Run the automated test suite:

```bash
# Automated dry run
python run_dry_run.py

# Unit tests
python -m pytest api/ -v

# API endpoint tests
python test_ec2_endpoint.py
```

## 📊 System Components

### EC2 Backend (Django)
- **Weather API Client**: Fetches 24-hour forecasts with 30-min caching
- **LSTM Inference Engine**: Generates 96 temperature predictions
- **Feature Engineering**: Constructs 90-feature matrix from sensor + weather data
- **NLP Command Parser**: Interprets natural language voice commands
- **CSV Schedule Generator**: Creates 24-hour temperature schedules

### Raspberry Pi (Edge Device)
- **Sensor Reader**: Reads temperature from DHT22/similar sensors
- **Pipeline Client**: Communicates with EC2 via HTTP
- **STT Module**: Speech-to-text using Vosk (offline)
- **IR Blaster**: Sends IR signals to AC unit

## 🔧 Configuration

### EC2 Configuration
Edit `.env`:
```env
WEATHERAPI_KEY=your-api-key
DJANGO_SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-ec2-ip,your-domain.com
MODEL_DIR=/path/to/models
```

### Raspberry Pi Configuration
Edit `rpi/config.json`:
```json
{
  "ec2_endpoint": "http://your-ec2-ip:8000/api/predict/",
  "timeout": 30
}
```

Edit `rpi/ir_codes.json` with your AC's IR codes.

## 📡 API Endpoints

### POST /api/predict/

**Scheduled Mode:**
```json
{
  "mode": "scheduled",
  "timestamp": "2024-01-15T10:30:00",
  "temperature_c": 26.5,
  "device_id": "rpi_sensor_01"
}
```

**Voice Override Mode:**
```json
{
  "mode": "voice_override",
  "timestamp": "2024-01-15T10:30:00",
  "temperature_c": 26.5,
  "device_id": "rpi_sensor_01",
  "command_text": "it's too hot"
}
```

**Response:** CSV with 96 rows (24 hours at 15-minute intervals)

## 🎯 Voice Commands

- "it's too hot" → Decrease by 2°C
- "it's cold" → Increase by 1°C
- "make it cooler" → Decrease by 1°C
- "make it warmer" → Increase by 1°C
- "set to 22" → Set to 22°C
- "very hot" → Decrease by 3°C

## 📈 Performance

- **Response Time**: < 5 seconds for predictions
- **Prediction Accuracy**: Based on LSTM trained on historical data
- **Weather Cache**: 30-minute TTL for resilience
- **Schedule Updates**: Every 15 minutes (scheduled) or immediate (voice override)

## 🛠️ Tech Stack

- **Backend**: Django 6.0, Django REST Framework
- **ML**: TensorFlow 2.20, scikit-learn, pandas, numpy
- **Weather**: WeatherAPI.com
- **NLP**: Custom rule-based parser
- **STT**: Vosk (offline speech recognition)
- **Edge**: Raspberry Pi 4, Python 3.8+

## 📝 Project Structure

```
.
├── api/                      # Django API application
│   ├── weather.py           # Weather API client
│   ├── inference.py         # LSTM predictor
│   ├── features.py          # Feature engineering
│   ├── csv_generator.py    # Schedule generator
│   ├── nlp/                 # NLP command parser
│   └── views.py             # API endpoints
├── rpi/                     # Raspberry Pi components
│   ├── sensor_reader.py    # Temperature sensor
│   ├── pipeline_client.py  # HTTP client
│   ├── stt.py              # Speech-to-text
│   └── ir_blaster.py       # IR control
├── models/                  # ML model artifacts
│   ├── lstm_model.h5
│   ├── scaler_features.pkl
│   ├── scaler_target.pkl
│   └── model_config.pkl
└── vatavaran_server/       # Django project config
```

## 🧪 Test Coverage

- **76 unit tests** covering all components
- **9 integration tests** for API endpoints
- **Automated dry run** for quick validation

## 🤝 Contributing

Contributions are welcome! Please read the documentation and ensure all tests pass before submitting PRs.

## 📄 License

This project is part of an academic/research initiative.

## 👥 Authors

- **Devansh** - [Developer-Devanshhh](https://github.com/Developer-Devanshhh)

## 🙏 Acknowledgments

- WeatherAPI.com for weather data
- Vosk for offline speech recognition
- TensorFlow team for ML framework

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Built with ❤️ for smart climate control**

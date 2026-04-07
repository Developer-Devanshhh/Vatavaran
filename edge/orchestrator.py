#!/usr/bin/env python3
"""
Vatavaran Edge Orchestrator — Runs the full prediction pipeline locally on RPi 4B

This replaces BOTH:
  - api/views.py (Django REST endpoint on EC2)
  - rpi/pipeline_client.py (HTTP client that called EC2)

Pipeline: Sensor → Weather → Features(90) → LSTM(TFLite) → NLP(optional) → CSV → disk

Usage:
    # Run one prediction cycle (for testing / cron)
    python -m edge.orchestrator --once

    # Run the continuous 15-minute loop
    python -m edge.orchestrator

    # Run one cycle with a voice override command
    python -m edge.orchestrator --once --voice "it's too hot"

    # Dry-run (no sensors, no weather API — uses mock data)
    python -m edge.orchestrator --dry-run
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Add project root to path so edge/ can be imported
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from edge.inference import LSTMPredictor
from edge.features import build_feature_matrix
from edge.weather import fetch_weather_forecast
from edge.csv_generator import generate_schedule_csv
from edge.nlp.command_parser import parse_command

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────

CONFIG_FILE = Path(__file__).parent / 'config.json'


def load_config():
    """Load configuration from edge/config.json."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    logger.warning(f"Config not found at {CONFIG_FILE}, using defaults")
    return {
        'model_dir': '.',
        'schedule_file': 'schedule.csv',
        'prediction_interval_min': 15,
    }


# ─── Sensor Reading (with hardware fallback) ─────────────────────

def read_sensor_data(config):
    """
    Read current sensor values.

    Tries real hardware first (DHT22 + BMP280 + BH1750).
    Falls back to simulated data for dry-run / development.
    """
    try:
        # Try importing the RPi sensor reader
        sys.path.insert(0, str(PROJECT_ROOT / 'rpi'))
        from sensor_reader import read_sensor
        reading = read_sensor()
        return reading
    except Exception as e:
        logger.warning(f"Hardware sensor read failed: {e}")
        logger.info("Using simulated sensor data")
        return {
            'timestamp': datetime.now().isoformat(),
            'temperature_c': 26.5,
            'humidity': 65.0,
            'pressure_mb': 1013.0,
            'light': 50.0,
            'device_id': 'rpi_sensor_01',
            'simulated': True
        }


def generate_mock_weather():
    """Generate a mock 24-hour weather forecast for dry-run mode."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hours = [now + timedelta(hours=i) for i in range(24)]
    return pd.DataFrame({
        'timestamp': hours,
        'temp_c': [26.0 + 2.0 * np.sin(2 * np.pi * h.hour / 24) for h in hours],
        'humidity': [65.0] * 24,
        'pressure_mb': [1013.0] * 24,
        'cloud': [40.0] * 24,
        'feelslike_c': [27.0] * 24,
        'wind_kph': [10.0] * 24,
        'uv': [5.0 if 6 <= h.hour <= 18 else 0.0 for h in hours],
        'condition_code': [1000] * 24,
    })


# ─── Main Pipeline ───────────────────────────────────────────────

def run_pipeline(predictor, config, voice_command=None, dry_run=False):
    """
    Execute one full prediction cycle.

    1. Read sensor data
    2. Fetch weather forecast
    3. Build 90-feature matrix
    4. Run LSTM inference (96 predictions)
    5. Optionally apply NLP voice override
    6. Generate schedule CSV
    7. Save to disk

    Returns:
        True on success, False on failure
    """
    logger.info("=" * 60)
    logger.info(f"Pipeline starting at {datetime.now().isoformat()}")
    logger.info(f"Mode: {'dry-run' if dry_run else 'live'}"
                f"{' + voice override' if voice_command else ''}")

    try:
        # ── Step 1: Read sensor ──────────────────────────────────
        logger.info("[1/6] Reading sensor data...")
        sensor_data = read_sensor_data(config)
        temperature_c = sensor_data.get('temperature_c', 26.0)
        logger.info(f"  Sensor: {temperature_c}°C")

        # Build a minimal sensor history DataFrame
        sensor_history = pd.DataFrame([{
            'timestamp': sensor_data['timestamp'],
            'temperature_c': temperature_c,
            'humidity': sensor_data.get('humidity', 65.0),
            'pressure_mb': sensor_data.get('pressure_mb', 1013.0),
            'light': sensor_data.get('light', 50.0),
        }])

        # ── Step 2: Fetch weather ────────────────────────────────
        logger.info("[2/6] Fetching weather forecast...")
        if dry_run:
            weather_forecast = generate_mock_weather()
            logger.info("  Using mock weather data (dry-run)")
        else:
            config_path = str(CONFIG_FILE)
            weather_forecast = fetch_weather_forecast(config_path)
        logger.info(f"  Weather: {len(weather_forecast)} hours")

        # ── Step 3: Feature engineering ──────────────────────────
        logger.info("[3/6] Building 90-feature matrix...")
        model_config_path = str(Path(config.get('model_dir', '.')) / 'model_config.pkl')
        feature_matrix = build_feature_matrix(
            sensor_history, weather_forecast, model_config_path
        )
        logger.info(f"  Matrix shape: {feature_matrix.shape}")

        # ── Step 4: LSTM inference ───────────────────────────────
        logger.info("[4/6] Running LSTM inference (96 predictions)...")
        predictions = predictor.predict_24h(feature_matrix)
        logger.info(f"  Predictions: {len(predictions)} values, "
                    f"range [{predictions.min():.1f}, {predictions.max():.1f}]°C")

        # ── Step 5: NLP voice override (optional) ────────────────
        override_data = None
        if voice_command:
            logger.info(f"[5/6] Parsing voice command: '{voice_command}'")
            result = parse_command(voice_command, temperature_c)
            logger.info(f"  NLP result: {result}")

            if 'absolute' in result:
                override_data = {
                    'temperature': result['absolute'],
                    'slots': 4
                }
            elif 'delta' in result and result['delta'] != 0:
                override_temp = int(predictions[0]) + result['delta']
                override_temp = max(18, min(30, override_temp))
                override_data = {
                    'temperature': override_temp,
                    'slots': 4
                }

            if override_data:
                logger.info(f"  Override: {override_data['temperature']}°C "
                            f"for {override_data['slots']} slots")
        else:
            logger.info("[5/6] No voice command — using LSTM predictions")

        # ── Step 6: Generate and save CSV ────────────────────────
        logger.info("[6/6] Generating schedule CSV...")
        csv_content = generate_schedule_csv(predictions, override_data)

        schedule_path = Path(config.get('schedule_file', 'schedule.csv'))
        schedule_path.parent.mkdir(parents=True, exist_ok=True)

        with open(schedule_path, 'w') as f:
            f.write(csv_content)

        logger.info(f"  Schedule saved to {schedule_path}")
        logger.info(f"  ({len(csv_content.splitlines())} lines)")

        # Print first few rows for visibility
        lines = csv_content.strip().split('\n')
        logger.info("  Preview:")
        for line in lines[:5]:
            logger.info(f"    {line}")

        logger.info("=" * 60)
        logger.info("Pipeline completed successfully ✓")
        return True

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return False


# ─── Entry Point ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Vatavaran Edge Orchestrator — '
                    'Runs ML climate control pipeline locally on RPi 4B'
    )
    parser.add_argument(
        '--once', action='store_true',
        help='Run a single prediction cycle and exit'
    )
    parser.add_argument(
        '--voice', type=str, default=None,
        help='Voice command text for override (e.g. "it\'s too hot")'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Use mock sensor/weather data (no hardware required)'
    )
    parser.add_argument(
        '--config', type=str, default=None,
        help='Path to config.json'
    )

    args = parser.parse_args()

    # Load config
    global CONFIG_FILE
    if args.config:
        CONFIG_FILE = Path(args.config)
    config = load_config()

    # Setup logging
    log_level = config.get('log_level', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║   Vatavaran Edge — RPi 4B Climate Controller  ║")
    logger.info("╚══════════════════════════════════════════════╝")

    # Initialize LSTM predictor (loads model once)
    logger.info("Initializing LSTM predictor...")
    model_dir = config.get('model_dir', '.')
    try:
        predictor = LSTMPredictor(model_dir=model_dir)
    except Exception as e:
        logger.error(f"Fatal: Could not load model — {e}")
        sys.exit(1)

    if args.once:
        # Single run
        success = run_pipeline(
            predictor, config,
            voice_command=args.voice,
            dry_run=args.dry_run
        )
        sys.exit(0 if success else 1)
    else:
        # Continuous loop
        interval = config.get('prediction_interval_min', 15) * 60
        logger.info(f"Starting continuous mode — interval: {interval}s")

        while True:
            try:
                run_pipeline(
                    predictor, config,
                    voice_command=args.voice,
                    dry_run=args.dry_run
                )
            except KeyboardInterrupt:
                logger.info("Stopped by user")
                break
            except Exception as e:
                logger.error(f"Cycle failed: {e}")

            logger.info(f"Sleeping {interval}s until next cycle...")
            time.sleep(interval)


if __name__ == '__main__':
    main()

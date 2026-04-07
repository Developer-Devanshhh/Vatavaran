#!/usr/bin/env python3
"""
Vatavaran Interactive Demo — Full Simulation with LCD Display

Runs a real-time simulation showing:
  - LSTM predictions on an LCD display
  - Live schedule with mode indicators (LSTM / Override)
  - Voice command input for overrides
  - Sensor readings (real or simulated)
  - IR blaster actions

Usage:
    python -m edge.demo                    # Full interactive demo
    python -m edge.demo --voice "too hot"  # Demo with a voice command
    python -m edge.demo --walk             # Walk through all 96 slots
"""

import os
import sys
import time
import json
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from edge.inference import LSTMPredictor
from edge.features import build_feature_matrix
from edge.csv_generator import generate_schedule_csv
from edge.nlp.command_parser import parse_command
from edge.lcd_display import LCDDisplay, C

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────

CONFIG_FILE = Path(__file__).parent / 'config.json'


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def generate_mock_weather():
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hours = [now + timedelta(hours=i) for i in range(24)]
    return pd.DataFrame({
        'timestamp': hours,
        'temp_c': [26.0 + 3.0 * np.sin(2 * np.pi * (h.hour - 6) / 24) for h in hours],
        'humidity': [65 + 10 * np.sin(2 * np.pi * h.hour / 24) for h in hours],
        'pressure_mb': [1013.0 + np.random.uniform(-1, 1) for _ in hours],
        'cloud': [40 + 20 * np.sin(2 * np.pi * h.hour / 24) for h in hours],
        'feelslike_c': [27.0] * 24,
        'wind_kph': [10.0] * 24,
        'uv': [5.0 if 6 <= h.hour <= 18 else 0.0 for h in hours],
        'condition_code': [1000] * 24,
    })


def generate_mock_sensor(base_temp=26.5):
    return {
        'timestamp': datetime.now().isoformat(),
        'temperature_c': base_temp + np.random.uniform(-0.5, 0.5),
        'humidity': 65.0 + np.random.uniform(-5, 5),
        'pressure_mb': 1013.0 + np.random.uniform(-2, 2),
        'light': 50.0 + np.random.uniform(-10, 10),
        'device_id': 'rpi_sensor_01',
    }


# ─── Demo Modes ───────────────────────────────────────────────────

def run_demo(predictor, config, voice_command=None, walk_mode=False):
    """
    Run the full interactive demo.

    Phases:
      Phase 1: Sensor reading animation
      Phase 2: LSTM inference with progress
      Phase 3: Display schedule on LCD
      Phase 4: Voice command override (if provided)
      Phase 5: Walk through time slots (if --walk)
    """
    lcd = LCDDisplay(cols=20, rows=4)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: Startup & Sensor Reading
    # ═══════════════════════════════════════════════════════════════
    lcd.clear()
    lcd.write_line(0, "  VATAVARAN v1.0   ")
    lcd.write_line(1, "  Climate Control  ")
    lcd.write_line(2, "                    ")
    lcd.write_line(3, " Initializing...    ")
    lcd.render_terminal()
    print(f"\n  {C.DIM}Press Enter to start...{C.RESET}")
    input()

    # Read sensor
    sensor = generate_mock_sensor()
    lcd.clear()
    lcd.write_line(0, " Reading Sensors... ")
    lcd.write_line(1, f" T: {sensor['temperature_c']:.1f}°C")
    lcd.write_line(2, f" H: {sensor['humidity']:.0f}%  P:{sensor['pressure_mb']:.0f}")
    lcd.write_line(3, f" L: {sensor['light']:.0f} lux")
    lcd.render_terminal()
    time.sleep(1.5)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: Feature Engineering & LSTM Inference
    # ═══════════════════════════════════════════════════════════════
    lcd.clear()
    lcd.write_line(0, " Building Features  ")
    lcd.write_line(1, " 90 features...     ")
    lcd.write_line(2, "                    ")
    lcd.write_line(3, "                    ")
    lcd.render_terminal()

    # Build feature matrix
    sensor_history = pd.DataFrame([{
        'timestamp': sensor['timestamp'],
        'temperature_c': sensor['temperature_c'],
        'humidity': sensor['humidity'],
        'pressure_mb': sensor['pressure_mb'],
        'light': sensor['light'],
    }])
    weather = generate_mock_weather()
    model_config_path = str(Path(config.get('model_dir', '.')) / 'model_config.pkl')
    feature_matrix = build_feature_matrix(sensor_history, weather, model_config_path)

    time.sleep(0.5)
    lcd.write_line(1, " 90 features  [OK]  ")
    lcd.write_line(2, f" Matrix: {feature_matrix.shape}")
    lcd.render_terminal()
    time.sleep(1)

    # LSTM Inference with progress bar
    lcd.clear()
    lcd.write_line(0, " LSTM Inference     ")
    lcd.write_line(1, " 96 predictions...  ")
    lcd.render_terminal()

    start_t = time.time()
    predictions = predictor.predict_24h(feature_matrix)
    elapsed = time.time() - start_t

    lcd.write_line(1, f" Done in {elapsed:.1f}s!  ")
    lcd.write_line(2, f" Range: {predictions.min():.1f}-{predictions.max():.1f}°C")
    lcd.write_line(3, f" Slots: {len(predictions)}")
    lcd.render_terminal()
    time.sleep(1.5)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: Generate Schedule & Display
    # ═══════════════════════════════════════════════════════════════
    override_data = None
    active_voice_cmd = None

    if voice_command:
        # Parse voice command
        nlp_result = parse_command(voice_command, sensor['temperature_c'])

        if 'absolute' in nlp_result:
            override_data = {'temperature': nlp_result['absolute'], 'slots': 4}
        elif 'delta' in nlp_result and nlp_result['delta'] != 0:
            override_temp = int(predictions[0]) + nlp_result['delta']
            override_temp = max(18, min(30, override_temp))
            override_data = {'temperature': override_temp, 'slots': 4}

        active_voice_cmd = voice_command

        # Show voice command processing
        lcd.clear()
        lcd.write_line(0, " Voice Command      ")
        lcd.write_line(1, f'"{voice_command[:18]}"')
        lcd.write_line(2, f" NLP: {nlp_result}")
        if override_data:
            lcd.write_line(3, f" Override: {override_data['temperature']}°C x{override_data['slots']}")
        else:
            lcd.write_line(3, " No override needed ")
        lcd.render_terminal()
        time.sleep(2)

    # Generate CSV
    csv_content = generate_schedule_csv(predictions, override_data)
    schedule_lines = csv_content.strip().split('\n')[1:]  # Skip header

    # Save schedule
    schedule_path = Path(config.get('schedule_file', 'schedule.csv'))
    with open(schedule_path, 'w') as f:
        f.write(csv_content)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: Live Display — Walk Through Schedule
    # ═══════════════════════════════════════════════════════════════
    if walk_mode:
        print(f"\n  {C.CYAN}{C.BOLD}Walking through all 96 time slots...{C.RESET}")
        print(f"  {C.DIM}Press Ctrl+C to stop{C.RESET}\n")
        time.sleep(1)

        try:
            for i, line in enumerate(schedule_lines):
                parts = line.strip().split(',')
                if len(parts) != 3:
                    continue

                ts, temp, src = parts
                setpoint = int(temp)
                sensor = generate_mock_sensor(base_temp=setpoint + np.random.uniform(-2, 2))

                lcd.show_status(
                    sensor_temp=sensor['temperature_c'],
                    setpoint=setpoint,
                    mode=src,
                    slot_time=ts,
                    humidity=sensor['humidity'],
                    pressure=sensor['pressure_mb'],
                    light=sensor['light'],
                    voice_cmd=active_voice_cmd if src == 'override' else None
                )
                lcd.show_schedule_preview(schedule_lines, current_slot=i)

                # IR blaster simulation
                print(f"\n  {C.MAGENTA}📡 IR Blaster → Sending {setpoint}°C to AC unit{C.RESET}")
                print(f"  {C.DIM}[Slot {i+1}/96 | {ts}]{C.RESET}")

                if walk_mode:
                    time.sleep(0.8)  # Fast walk-through

        except KeyboardInterrupt:
            print(f"\n\n  {C.YELLOW}Demo stopped by user{C.RESET}")
    else:
        # Just show the current slot
        parts = schedule_lines[0].strip().split(',')
        ts, temp, src = parts
        setpoint = int(temp)

        lcd.show_status(
            sensor_temp=sensor['temperature_c'],
            setpoint=setpoint,
            mode=src,
            slot_time=ts,
            humidity=sensor['humidity'],
            pressure=sensor['pressure_mb'],
            light=sensor['light'],
            voice_cmd=active_voice_cmd if src == 'override' else None
        )
        lcd.show_schedule_preview(schedule_lines, current_slot=0)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 5: Interactive Voice Command Loop
    # ═══════════════════════════════════════════════════════════════
    print(f"\n  {C.CYAN}{C.BOLD}═══ Interactive Voice Command Mode ═══{C.RESET}")
    print(f"  {C.WHITE}Type a voice command to override the schedule.{C.RESET}")
    print(f"  {C.DIM}Examples: \"too hot\", \"set to 22\", \"very cold\", \"make it cooler\"{C.RESET}")
    print(f"  {C.DIM}Type 'quit' to exit{C.RESET}\n")

    while True:
        try:
            cmd = input(f"  {C.YELLOW}🎤 Voice > {C.RESET}")
            if cmd.lower() in ('quit', 'exit', 'q'):
                break
            if not cmd.strip():
                continue

            # Parse command
            current_temp = sensor['temperature_c']
            nlp_result = parse_command(cmd, current_temp)

            # Determine override
            override_data = None
            if 'absolute' in nlp_result:
                override_data = {'temperature': nlp_result['absolute'], 'slots': 4}
            elif 'delta' in nlp_result and nlp_result['delta'] != 0:
                base = int(predictions[0])
                override_temp = base + nlp_result['delta']
                override_temp = max(18, min(30, override_temp))
                override_data = {'temperature': override_temp, 'slots': 4}

            # Regenerate schedule with override
            csv_content = generate_schedule_csv(predictions, override_data)
            schedule_lines = csv_content.strip().split('\n')[1:]

            with open(schedule_path, 'w') as f:
                f.write(csv_content)

            # Display updated schedule
            parts = schedule_lines[0].strip().split(',')
            ts, temp, src = parts
            setpoint = int(temp)

            sensor = generate_mock_sensor(base_temp=current_temp)

            lcd.show_status(
                sensor_temp=sensor['temperature_c'],
                setpoint=setpoint,
                mode=src,
                slot_time=ts,
                humidity=sensor['humidity'],
                pressure=sensor['pressure_mb'],
                light=sensor['light'],
                voice_cmd=cmd if src == 'override' else None
            )
            lcd.show_schedule_preview(schedule_lines, current_slot=0)

            print(f"\n  {C.GREEN}NLP Result: {nlp_result}{C.RESET}")
            if override_data:
                print(f"  {C.YELLOW}Override: {override_data['temperature']}°C for next {override_data['slots']} slots (1 hour){C.RESET}")
            else:
                print(f"  {C.DIM}No override — command not recognized{C.RESET}")
            print()

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    # Goodbye
    lcd.clear()
    lcd.write_line(0, "  VATAVARAN v1.0   ")
    lcd.write_line(1, "                    ")
    lcd.write_line(2, " System Standby     ")
    lcd.write_line(3, " Goodbye!           ")
    lcd.render_terminal()
    print(f"\n  {C.CYAN}╚══════════════════════════════════════════════════╝{C.RESET}")
    print(f"\n  {C.GREEN}{C.BOLD}Demo complete! Schedule saved to {schedule_path}{C.RESET}\n")


# ─── Entry Point ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Vatavaran Interactive Demo — LCD + Voice + LSTM'
    )
    parser.add_argument('--voice', type=str, default=None,
                        help='Initial voice command (e.g. "too hot")')
    parser.add_argument('--walk', action='store_true',
                        help='Walk through all 96 time slots')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to config.json')

    args = parser.parse_args()

    # Minimal logging (demo is visual, not log-heavy)
    logging.basicConfig(level=logging.WARNING)

    config = load_config()
    model_dir = config.get('model_dir', '.')

    # Clear screen
    os.system('clear' if os.name == 'posix' else 'cls')

    print(f"\n  {C.CYAN}{C.BOLD}Loading LSTM model...{C.RESET}", end=' ', flush=True)
    predictor = LSTMPredictor(model_dir=model_dir)
    print(f"{C.GREEN}✓{C.RESET}\n")

    run_demo(predictor, config, voice_command=args.voice, walk_mode=args.walk)


if __name__ == '__main__':
    main()

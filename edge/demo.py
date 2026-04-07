#!/usr/bin/env python3
"""
Vatavaran Interactive Demo — 16x2 LCD + Voice + LSTM

Usage:
    python -m edge.demo                        # Basic demo
    python -m edge.demo --voice "too hot"      # With voice override
    python -m edge.demo --walk                 # Walk all 96 slots
    python -m edge.demo --walk --voice "set to 22"
"""

import os, sys, time, json, logging, argparse
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from edge.inference import LSTMPredictor
from edge.features import build_feature_matrix
from edge.csv_generator import generate_schedule_csv
from edge.nlp.command_parser import parse_command
from edge.lcd_display import LCDDisplay, C

CONFIG_FILE = Path(__file__).parent / 'config.json'


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def mock_weather():
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hours = [now + timedelta(hours=i) for i in range(24)]
    return pd.DataFrame({
        'timestamp': hours,
        'temp_c': [26 + 3 * np.sin(2*np.pi*(h.hour-6)/24) for h in hours],
        'humidity': [65 + 10*np.sin(2*np.pi*h.hour/24) for h in hours],
        'pressure_mb': [1013 + np.random.uniform(-1,1) for _ in hours],
        'cloud': [40 + 20*np.sin(2*np.pi*h.hour/24) for h in hours],
    })


def mock_sensor(base=26.5):
    return {
        'timestamp': datetime.now().isoformat(),
        'temperature_c': base + np.random.uniform(-0.5, 0.5),
        'humidity': 65 + np.random.uniform(-5, 5),
        'pressure_mb': 1013 + np.random.uniform(-2, 2),
        'light': 50 + np.random.uniform(-10, 10),
    }


def run_demo(predictor, config, voice_command=None, walk_mode=False):
    lcd = LCDDisplay(address=0x27, cols=16, rows=2)

    # ── Phase 1: Startup ─────────────────────────────────────────
    lcd.show_startup()
    print(f"\n  {C.DIM}Press Enter to start...{C.RESET}")
    input()

    # ── Phase 2: Sensor ──────────────────────────────────────────
    sensor = mock_sensor()
    lcd.show_sensor(sensor['temperature_c'], sensor['humidity'])
    time.sleep(2)

    # ── Phase 3: Feature Engineering ─────────────────────────────
    lcd.show_building()
    sensor_df = pd.DataFrame([{
        'timestamp': sensor['timestamp'],
        'temperature_c': sensor['temperature_c'],
        'humidity': sensor['humidity'],
        'pressure_mb': sensor['pressure_mb'],
        'light': sensor['light'],
    }])
    weather = mock_weather()
    cfg_path = str(Path(config.get('model_dir', '.')) / 'model_config.pkl')
    matrix = build_feature_matrix(sensor_df, weather, cfg_path)
    time.sleep(0.5)

    # ── Phase 4: LSTM Inference ──────────────────────────────────
    lcd.show_inferring()
    t0 = time.time()
    predictions = predictor.predict_24h(matrix)
    elapsed = time.time() - t0
    lcd.show_done(elapsed, predictions.min(), predictions.max())
    time.sleep(2)

    # ── Phase 5: Voice Override ──────────────────────────────────
    override_data = None
    active_cmd = None

    if voice_command:
        nlp = parse_command(voice_command, sensor['temperature_c'])
        override_temp = None

        if 'absolute' in nlp:
            override_temp = nlp['absolute']
        elif 'delta' in nlp and nlp['delta'] != 0:
            override_temp = max(18, min(30, int(predictions[0]) + nlp['delta']))

        lcd.show_voice_cmd(voice_command, nlp, override_temp)
        time.sleep(2.5)

        if override_temp:
            override_data = {'temperature': override_temp, 'slots': 4}
            active_cmd = voice_command

    # ── Phase 6: Generate Schedule ───────────────────────────────
    csv = generate_schedule_csv(predictions, override_data)
    lines = csv.strip().split('\n')[1:]  # skip header

    path = Path(config.get('schedule_file', 'schedule.csv'))
    with open(path, 'w') as f:
        f.write(csv)

    # ── Phase 7: Display Schedule ────────────────────────────────
    if walk_mode:
        print(f"\n  {C.CYAN}Walking 96 slots — Ctrl+C to stop{C.RESET}\n")
        time.sleep(1)
        try:
            for i, line in enumerate(lines):
                parts = line.strip().split(',')
                if len(parts) != 3: continue
                ts, temp, src = parts
                sp = int(temp)
                s = mock_sensor(base=sp + np.random.uniform(-2, 2))

                lcd.show_main(
                    sensor_temp=s['temperature_c'], setpoint=sp,
                    mode=src, slot_time=ts,
                    humidity=s['humidity'], pressure=s['pressure_mb'],
                    voice_cmd=active_cmd if src == 'override' else None
                )
                # Show IR blaster action
                lcd.show_ir(sp, src)
                lcd.show_schedule(lines, current=i)
                print(f"\n  {C.MAGENTA}📡 IR → AC {sp}°C [{src}] | Slot {i+1}/96{C.RESET}")
                time.sleep(0.8)
        except KeyboardInterrupt:
            print(f"\n  {C.YELLOW}Stopped{C.RESET}")
    else:
        # Show first slot
        parts = lines[0].strip().split(',')
        ts, temp, src = parts
        sp = int(temp)
        lcd.show_main(
            sensor_temp=sensor['temperature_c'], setpoint=sp,
            mode=src, slot_time=ts,
            humidity=sensor['humidity'], pressure=sensor['pressure_mb'],
            voice_cmd=active_cmd if src == 'override' else None
        )
        lcd.show_schedule(lines)

    # ── Phase 8: Interactive Voice Loop ──────────────────────────
    print(f"\n  {C.CYAN}{C.BOLD}═══ Voice Command Mode ═══{C.RESET}")
    print(f"  {C.DIM}Type: \"too hot\", \"set to 22\", \"very cold\", \"cooler\"{C.RESET}")
    print(f"  {C.DIM}Type 'quit' to exit{C.RESET}\n")

    while True:
        try:
            cmd = input(f"  {C.YELLOW}🎤 Voice > {C.RESET}").strip()
            if cmd.lower() in ('quit', 'exit', 'q', ''):
                if cmd.lower() in ('quit', 'exit', 'q'):
                    break
                continue

            nlp = parse_command(cmd, sensor['temperature_c'])
            override_temp = None

            if 'absolute' in nlp:
                override_temp = nlp['absolute']
            elif 'delta' in nlp and nlp['delta'] != 0:
                override_temp = max(18, min(30, int(predictions[0]) + nlp['delta']))

            lcd.show_voice_cmd(cmd, nlp, override_temp)
            time.sleep(1.5)

            ov = {'temperature': override_temp, 'slots': 4} if override_temp else None
            csv = generate_schedule_csv(predictions, ov)
            lines = csv.strip().split('\n')[1:]

            with open(path, 'w') as f:
                f.write(csv)

            parts = lines[0].strip().split(',')
            ts, temp, src = parts
            sp = int(temp)

            lcd.show_main(
                sensor_temp=sensor['temperature_c'], setpoint=sp,
                mode=src, slot_time=ts,
                humidity=sensor['humidity'], pressure=sensor['pressure_mb'],
                voice_cmd=cmd if src == 'override' else None
            )

            # Show IR blaster
            lcd.show_ir(sp, src)
            lcd.show_schedule(lines)

            print(f"\n  {C.GREEN}NLP: {nlp}{C.RESET}")
            if override_temp:
                print(f"  {C.YELLOW}Override: {override_temp}°C for 1 hour{C.RESET}")
                print(f"  {C.MAGENTA}📡 IR → AC set to {override_temp}°C{C.RESET}")
            print()

        except (KeyboardInterrupt, EOFError):
            break

    lcd.show_goodbye()
    print(f"\n  {C.GREEN}Schedule saved to {path}{C.RESET}\n")


def main():
    parser = argparse.ArgumentParser(description='Vatavaran Demo')
    parser.add_argument('--voice', type=str, help='Voice command')
    parser.add_argument('--walk', action='store_true', help='Walk all slots')
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    config = load_config()

    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"\n  {C.CYAN}Loading LSTM model...{C.RESET}", end=' ', flush=True)
    predictor = LSTMPredictor(model_dir=config.get('model_dir', '.'))
    print(f"{C.GREEN}✓{C.RESET}\n")

    run_demo(predictor, config, voice_command=args.voice, walk_mode=args.walk)


if __name__ == '__main__':
    main()

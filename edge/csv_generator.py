"""
CSV Generator Module for Vatavaran Edge (Raspberry Pi 4B)

Generates 24-hour temperature schedules in CSV format (96 rows).
Direct copy from api/csv_generator.py — already pure Python.

Requirements: 9.1–9.8, 14.2–14.6
"""

import logging
from datetime import datetime, timedelta
import io

logger = logging.getLogger(__name__)


def generate_schedule_csv(lstm_predictions, override_data=None):
    """
    Generate a 24-hour temperature schedule CSV from LSTM predictions.

    Args:
        lstm_predictions: numpy array of 96 predicted temperatures
        override_data:    Optional dict with 'temperature' (int) and
                         'slots' (int, default 4) to override next N slots

    Returns:
        str: CSV content with columns: timestamp, setpoint_c, source
    """
    logger.info(f"Generating schedule CSV with {len(lstm_predictions)} predictions")

    if len(lstm_predictions) != 96:
        raise ValueError(f"Expected 96 predictions, got {len(lstm_predictions)}")

    if override_data and 'temperature' in override_data:
        t = override_data['temperature']
        if not isinstance(t, int) or not (18 <= t <= 30):
            raise ValueError(f"Override temperature must be int 18–30, got {t}")

    now = datetime.now()
    minutes = (now.minute // 15) * 15
    start_time = now.replace(minute=minutes, second=0, microsecond=0)

    csv_buffer = io.StringIO()
    csv_buffer.write("timestamp,setpoint_c,source\n")

    override_slots = 0
    override_temp = None
    if override_data:
        override_temp = override_data.get('temperature')
        override_slots = override_data.get('slots', 4)
        logger.info(f"Override: {override_temp}°C for next {override_slots} slots")

    for i in range(96):
        ts = start_time + timedelta(minutes=i * 15)
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")

        if i < override_slots and override_temp is not None:
            setpoint = override_temp
            source = "override"
        else:
            setpoint = round(lstm_predictions[i])
            source = "lstm"

        setpoint = max(18, min(30, setpoint))
        csv_buffer.write(f"{ts_str},{setpoint},{source}\n")

    csv_content = csv_buffer.getvalue()
    csv_buffer.close()

    logger.info(f"Generated CSV with 96 rows")
    return csv_content

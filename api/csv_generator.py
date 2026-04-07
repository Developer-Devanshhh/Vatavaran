"""
CSV Generator Module for Vatavaran Climate Control System

This module generates 24-hour temperature schedules in CSV format with 96 rows
representing 15-minute intervals. It combines LSTM predictions with optional
voice command overrides.

Requirements: 9.1, 9.2, 9.3, 9.4, 14.2, 14.3, 14.4
"""

import logging
from datetime import datetime, timedelta
import io

logger = logging.getLogger(__name__)


def generate_schedule_csv(lstm_predictions, override_data=None):
    """
    Generate a 24-hour temperature schedule CSV from LSTM predictions.
    
    Args:
        lstm_predictions: numpy array of 96 predicted temperatures (floats)
        override_data: Optional dict with 'temperature' (int) and 'slots' (int, default 4)
                      to override the next N time slots
    
    Returns:
        str: CSV content with columns: timestamp, setpoint_c, source
    
    Requirements:
        - 9.1: Create 96 rows with timestamp, setpoint_c, source columns
        - 9.2: Generate timestamps at 15-minute intervals from current time
        - 9.3: Round LSTM predictions to whole degrees Celsius
        - 9.4: Mark LSTM slots with source "lstm"
        - 9.5: Apply override temperature to next 4 time slots
        - 9.6: Mark override slots with source "override"
        - 9.7: Resume LSTM predictions after override window
        - 9.8: Return CSV in text/csv format
        - 14.2: Format timestamps as "YYYY-MM-DD HH:MM:SS"
        - 14.3: Exactly 96 rows representing 24 hours at 15-minute intervals
        - 14.4: Columns: timestamp, setpoint_c, source
        - 14.5: Setpoint values are integers in range 18-30
        - 14.6: Source values are either "lstm" or "override"
    """
    logger.info(f"Generating schedule CSV with {len(lstm_predictions)} predictions")
    
    # Validate input
    if len(lstm_predictions) != 96:
        raise ValueError(f"Expected 96 predictions, got {len(lstm_predictions)}")
    
    # Validate override temperature if present (Requirement 14.5)
    if override_data and 'temperature' in override_data:
        override_temp = override_data['temperature']
        if not isinstance(override_temp, int) or not (18 <= override_temp <= 30):
            raise ValueError(f"Override temperature must be an integer between 18-30°C, got {override_temp}")
    
    # Get current time and round to nearest 15-minute interval
    now = datetime.now()
    minutes = (now.minute // 15) * 15
    start_time = now.replace(minute=minutes, second=0, microsecond=0)
    
    logger.info(f"Schedule start time: {start_time}")
    
    # Build CSV content
    csv_buffer = io.StringIO()
    csv_buffer.write("timestamp,setpoint_c,source\n")
    
    # Determine override window if present
    override_slots = 0
    override_temp = None
    if override_data:
        override_temp = override_data.get('temperature')
        override_slots = override_data.get('slots', 4)
        logger.info(f"Override active: {override_temp}°C for next {override_slots} slots")
    
    # Generate 96 rows (Requirement 14.3)
    for i in range(96):
        # Generate timestamp at 15-minute intervals (Requirement 9.2, 14.2)
        timestamp = start_time + timedelta(minutes=i * 15)
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Determine setpoint and source
        if i < override_slots and override_temp is not None:
            # Use override temperature for the override window (Requirement 9.5, 9.6)
            setpoint = override_temp
            source = "override"
        else:
            # Round LSTM prediction to whole degrees (Requirement 9.3, 9.7)
            setpoint = round(lstm_predictions[i])
            source = "lstm"  # Requirement 9.4
        
        # Validate setpoint is in valid range (Requirement 14.5)
        if not (18 <= setpoint <= 30):
            logger.warning(f"Setpoint {setpoint}°C at slot {i} is out of range [18-30], clamping")
            setpoint = max(18, min(30, setpoint))
        
        # Write row (Requirement 14.4)
        csv_buffer.write(f"{timestamp_str},{setpoint},{source}\n")
    
    csv_content = csv_buffer.getvalue()
    csv_buffer.close()
    
    logger.info(f"Generated CSV with {96} rows")
    return csv_content

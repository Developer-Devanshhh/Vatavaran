"""
Raspberry Pi Sensor Reader Module

Reads temperature from RPi sensor hardware and returns formatted data.
Requirements: 1.1, 1.2, 1.3, 14.1
"""

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Last valid reading cache
_last_valid_reading = None

def read_sensor() -> Dict:
    """
    Read temperature from RPi sensor hardware.
    
    Returns:
        dict: Sensor reading with timestamp (ISO 8601), temperature_c (float), device_id (string)
    
    Requirements:
        1.1: Return dict with timestamp, temperature_c, device_id
        1.2: Format timestamp as ISO 8601
        1.3: Return last valid reading with staleness indicator on hardware failure
    """
    global _last_valid_reading
    
    try:
        # TODO: Replace with actual sensor hardware reading
        # For now, simulate sensor reading
        # In production, use libraries like Adafruit_DHT or similar
        
        # Example for DHT22 sensor:
        # import Adafruit_DHT
        # sensor = Adafruit_DHT.DHT22
        # pin = 4
        # humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
        
        # Simulated reading
        temperature_c = 25.5  # Replace with actual sensor read
        
        if temperature_c is None:
            raise Exception("Sensor returned None")
        
        # Create reading dict (Requirement 1.1, 1.2)
        reading = {
            'timestamp': datetime.now().isoformat(),
            'temperature_c': float(temperature_c),
            'device_id': 'rpi_sensor_01'
        }
        
        # Cache valid reading
        _last_valid_reading = reading
        
        logger.info(f"Sensor reading: {temperature_c}°C")
        return reading
        
    except Exception as e:
        # Requirement 1.3: Return last valid reading with staleness indicator on failure
        logger.error(f"Sensor hardware failure: {e}")
        
        if _last_valid_reading is not None:
            # Return cached reading with staleness indicator
            stale_reading = _last_valid_reading.copy()
            stale_reading['stale'] = True
            stale_reading['error'] = str(e)
            logger.warning(f"Returning stale reading from {stale_reading['timestamp']}")
            return stale_reading
        else:
            # No cached reading available
            logger.error("No cached reading available")
            raise Exception(f"Sensor failure and no cached data: {e}")


if __name__ == "__main__":
    # Test sensor reader
    logging.basicConfig(level=logging.INFO)
    
    print("Testing sensor reader...")
    try:
        reading = read_sensor()
        print(f"Reading: {reading}")
    except Exception as e:
        print(f"Error: {e}")

"""
Raspberry Pi Sensor Reader Module (Hardware-Enabled)

Reads from real sensors:
  - DHT22: Temperature + Humidity (GPIO digital)
  - BMP280: Pressure (I2C)
  - BH1750: Light/Lux (I2C)

Falls back to simulated data when hardware is not available.

Requirements: 1.1, 1.2, 1.3, 14.1
"""

import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

# Last valid reading cache
_last_valid_reading = None

# Sensor pin config (can be overridden via config.json)
DHT_PIN = 4  # GPIO4


def _read_hardware():
    """
    Read from actual sensor hardware.

    Returns:
        dict with temperature_c, humidity, pressure_mb, light
    """
    import board
    import adafruit_dht
    import adafruit_bmp280
    import adafruit_bh1750

    # DHT22 — temperature + humidity
    dht = adafruit_dht.DHT22(getattr(board, f'D{DHT_PIN}'))
    temperature_c = dht.temperature
    humidity = dht.humidity

    # BMP280 — pressure (via I2C)
    i2c = board.I2C()
    bmp = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
    pressure_mb = bmp.pressure

    # BH1750 — light intensity (via I2C)
    bh = adafruit_bh1750.BH1750(i2c)
    light = bh.lux

    return {
        'temperature_c': float(temperature_c),
        'humidity': float(humidity),
        'pressure_mb': float(pressure_mb),
        'light': float(light),
    }


def read_sensor() -> Dict:
    """
    Read all sensor values. Falls back to cached or simulated data on failure.

    Returns:
        dict: {timestamp, temperature_c, humidity, pressure_mb, light, device_id}
    """
    global _last_valid_reading

    try:
        # Try real hardware first
        values = _read_hardware()

        reading = {
            'timestamp': datetime.now().isoformat(),
            'temperature_c': values['temperature_c'],
            'humidity': values['humidity'],
            'pressure_mb': values['pressure_mb'],
            'light': values['light'],
            'device_id': 'rpi_sensor_01'
        }

        _last_valid_reading = reading
        logger.info(
            f"Sensor: T={reading['temperature_c']:.1f}°C "
            f"H={reading['humidity']:.0f}% "
            f"P={reading['pressure_mb']:.1f}hPa "
            f"L={reading['light']:.0f}lx"
        )
        return reading

    except ImportError:
        # Sensor libraries not installed (e.g., running on a PC)
        logger.warning("Sensor hardware libraries not installed — using simulated data")
        reading = {
            'timestamp': datetime.now().isoformat(),
            'temperature_c': 26.5,
            'humidity': 65.0,
            'pressure_mb': 1013.0,
            'light': 50.0,
            'device_id': 'rpi_sensor_01',
            'simulated': True
        }
        return reading

    except Exception as e:
        logger.error(f"Sensor hardware failure: {e}")

        if _last_valid_reading is not None:
            stale = _last_valid_reading.copy()
            stale['stale'] = True
            stale['error'] = str(e)
            logger.warning(f"Returning stale reading from {stale['timestamp']}")
            return stale

        # No cached reading — return simulated
        logger.error("No cached reading, returning simulated data")
        return {
            'timestamp': datetime.now().isoformat(),
            'temperature_c': 25.0,
            'humidity': 60.0,
            'pressure_mb': 1013.0,
            'light': 40.0,
            'device_id': 'rpi_sensor_01',
            'simulated': True,
            'error': str(e)
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing sensor reader...")
    reading = read_sensor()
    print(f"Reading: {reading}")

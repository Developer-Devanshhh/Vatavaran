"""
Raspberry Pi Pipeline Client

Builds JSON payloads and communicates with EC2 Django server.
Requirements: 3.2, 4.1, 4.2, 4.3, 12.2, 13.5, 14.1
"""

import json
import logging
import argparse
import requests
from pathlib import Path
from sensor_reader import read_sensor

logger = logging.getLogger(__name__)

# Configuration
CONFIG_FILE = Path(__file__).parent / 'config.json'
SCHEDULE_FILE = Path.home() / 'vatavaran' / 'schedule.csv'

def load_config():
    """Load configuration from config.json"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        # Default configuration
        return {
            'ec2_endpoint': 'http://your-ec2-ip:8000/api/predict/',
            'timeout': 30
        }

def build_scheduled_payload(sensor_data):
    """
    Build JSON payload for scheduled mode.
    
    Requirements:
        3.2: Build JSON payload with mode "scheduled" and sensor data
        14.1: Include sensor data fields
    """
    payload = {
        'mode': 'scheduled',
        'timestamp': sensor_data['timestamp'],
        'temperature_c': sensor_data['temperature_c'],
        'device_id': sensor_data['device_id']
    }
    return payload

def build_voice_override_payload(sensor_data, command_text):
    """
    Build JSON payload for voice_override mode.
    
    Requirements:
        4.1: Build JSON payload with mode "voice_override", sensor data, and command_text
        14.1: Include sensor data fields
    """
    payload = {
        'mode': 'voice_override',
        'timestamp': sensor_data['timestamp'],
        'temperature_c': sensor_data['temperature_c'],
        'device_id': sensor_data['device_id'],
        'command_text': command_text
    }
    return payload

def send_request(payload, config):
    """
    Send POST request to EC2 endpoint and save schedule.
    
    Requirements:
        3.3: Send POST request to EC2 /api/predict/
        3.4: Receive schedule.csv in response
        4.2: Send POST request for voice_override
        4.3: Save to /home/pi/vatavaran/schedule.csv
        12.2: Handle connection failures gracefully
    """
    ec2_endpoint = config['ec2_endpoint']
    timeout = config.get('timeout', 30)
    
    logger.info(f"Sending request to {ec2_endpoint}")
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Send POST request (Requirements 3.3, 4.2)
        response = requests.post(
            ec2_endpoint,
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 200:
            # Requirement 3.4, 4.3: Save schedule.csv
            schedule_csv = response.text
            
            # Ensure directory exists
            SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Save schedule
            with open(SCHEDULE_FILE, 'w') as f:
                f.write(schedule_csv)
            
            logger.info(f"Schedule saved to {SCHEDULE_FILE}")
            logger.info(f"Schedule has {len(schedule_csv.splitlines())} lines")
            return True
        else:
            logger.error(f"EC2 returned error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        # Requirement 12.2: Handle connection failures gracefully
        logger.error(f"Request timeout after {timeout}s")
        logger.info("Retaining previous schedule")
        return False
        
    except requests.exceptions.ConnectionError as e:
        # Requirement 12.2: Handle connection failures gracefully
        logger.error(f"Connection error: {e}")
        logger.info("Retaining previous schedule")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def run_scheduled_mode():
    """Execute scheduled mode pipeline"""
    logger.info("=== Running Scheduled Mode ===")
    
    # Load configuration
    config = load_config()
    
    # Read sensor data
    try:
        sensor_data = read_sensor()
    except Exception as e:
        logger.error(f"Failed to read sensor: {e}")
        return False
    
    # Build payload
    payload = build_scheduled_payload(sensor_data)
    
    # Send request
    return send_request(payload, config)

def run_voice_override_mode(command_text):
    """Execute voice_override mode pipeline"""
    logger.info("=== Running Voice Override Mode ===")
    
    # Load configuration
    config = load_config()
    
    # Read sensor data
    try:
        sensor_data = read_sensor()
    except Exception as e:
        logger.error(f"Failed to read sensor: {e}")
        return False
    
    # Build payload
    payload = build_voice_override_payload(sensor_data, command_text)
    
    # Send request
    return send_request(payload, config)

def main():
    """Main entry point for pipeline client"""
    parser = argparse.ArgumentParser(description='Vatavaran Pipeline Client')
    parser.add_argument('--mode', choices=['scheduled', 'voice_override'], required=True,
                       help='Execution mode')
    parser.add_argument('--command', type=str, help='Voice command text (required for voice_override)')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.mode == 'scheduled':
        success = run_scheduled_mode()
    elif args.mode == 'voice_override':
        if not args.command:
            logger.error("--command is required for voice_override mode")
            return 1
        success = run_voice_override_mode(args.command)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())

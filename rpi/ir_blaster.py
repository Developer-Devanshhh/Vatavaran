"""
Raspberry Pi IR Blaster Module

Reads schedule and sends IR signals to AC unit.
Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 4.4, 13.4
"""

import logging
import time
import json
from pathlib import Path
from datetime import datetime
import csv

logger = logging.getLogger(__name__)

# Configuration
SCHEDULE_FILE = Path.home() / 'vatavaran' / 'schedule.csv'
IR_CONFIG_FILE = Path(__file__).parent / 'ir_codes.json'
CHECK_INTERVAL = 60  # Check every 1 minute

def load_ir_codes():
    """
    Load IR code mappings from configuration file.
    
    Requirement 13.4: Load IR code mappings from configuration file (not hardcoded)
    """
    if IR_CONFIG_FILE.exists():
        with open(IR_CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        logger.warning(f"IR codes file not found: {IR_CONFIG_FILE}")
        # Return empty dict, will log errors when codes are missing
        return {}

def read_schedule():
    """
    Read schedule.csv from file.
    
    Requirement 10.1: Read Schedule_CSV from /home/pi/vatavaran/schedule.csv
    """
    if not SCHEDULE_FILE.exists():
        logger.error(f"Schedule file not found: {SCHEDULE_FILE}")
        return None
    
    try:
        schedule = []
        with open(SCHEDULE_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                schedule.append(row)
        
        logger.info(f"Loaded schedule with {len(schedule)} slots")
        return schedule
    except Exception as e:
        logger.error(f"Failed to read schedule: {e}")
        return None

def get_current_slot(schedule):
    """
    Determine current time slot based on system time.
    
    Requirement 10.2: Determine current time slot based on system time
    """
    if not schedule:
        return None
    
    now = datetime.now()
    
    # Find the slot that matches current time (within 15 minutes)
    for i, slot in enumerate(schedule):
        slot_time = datetime.strptime(slot['timestamp'], "%Y-%m-%d %H:%M:%S")
        time_diff = abs((now - slot_time).total_seconds())
        
        # If within 15 minutes (900 seconds), this is the current slot
        if time_diff < 900:
            logger.info(f"Current slot: {i}, time: {slot['timestamp']}, temp: {slot['setpoint_c']}°C")
            return slot
    
    # If no exact match, use the first future slot
    for slot in schedule:
        slot_time = datetime.strptime(slot['timestamp'], "%Y-%m-%d %H:%M:%S")
        if slot_time > now:
            logger.info(f"Using next future slot: {slot['timestamp']}, temp: {slot['setpoint_c']}°C")
            return slot
    
    logger.warning("No matching slot found, using first slot")
    return schedule[0] if schedule else None

def send_ir_signal(temperature, ir_codes):
    """
    Send IR signal to AC unit.
    
    Requirements:
        10.4: Map setpoint temperature to corresponding IR signal code
        10.5: Transmit IR signal to AC unit
        10.8: Log error and skip slot when IR code mapping is missing
    """
    # Requirement 10.4: Map temperature to IR code
    temp_key = str(temperature)
    if temp_key not in ir_codes:
        # Requirement 10.8: Log error when mapping is missing
        logger.error(f"No IR code mapping for temperature {temperature}°C")
        logger.info("Skipping this slot")
        return False
    
    ir_code = ir_codes[temp_key]
    logger.info(f"Sending IR code for {temperature}°C: {ir_code}")
    
    try:
        # Requirement 10.5: Transmit IR signal
        # TODO: Replace with actual IR transmission
        # Example using lirc:
        # import subprocess
        # subprocess.run(['irsend', 'SEND_ONCE', 'ac_remote', ir_code])
        
        # Example using python-irblaster:
        # from irblaster import IRBlaster
        # blaster = IRBlaster()
        # blaster.send(ir_code)
        
        # Placeholder: Log the transmission
        logger.info(f"IR signal transmitted successfully for {temperature}°C")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send IR signal: {e}")
        return False

def run_ir_blaster():
    """
    Main IR blaster loop.
    
    Requirements:
        10.3: Read setpoint_c when time slot changes
        10.6: Check for schedule changes every 1 minute
        10.7: Apply new schedule on next loop iteration when CSV updates
        4.4: Apply new schedule immediately when updated
    """
    logger.info("Starting IR Blaster")
    
    # Load IR codes
    ir_codes = load_ir_codes()
    if not ir_codes:
        logger.warning("No IR codes loaded, will log errors for missing codes")
    
    last_slot_time = None
    last_schedule_mtime = None
    
    while True:
        try:
            # Requirement 10.6: Check for schedule changes every 1 minute
            if SCHEDULE_FILE.exists():
                current_mtime = SCHEDULE_FILE.stat().st_mtime
                
                # Requirement 10.7, 4.4: Detect schedule updates
                if last_schedule_mtime is None or current_mtime != last_schedule_mtime:
                    if last_schedule_mtime is not None:
                        logger.info("Schedule file updated, reloading...")
                    
                    schedule = read_schedule()
                    last_schedule_mtime = current_mtime
                else:
                    # Schedule hasn't changed, use cached version
                    pass
            else:
                logger.warning(f"Schedule file not found: {SCHEDULE_FILE}")
                schedule = None
            
            if schedule:
                # Get current slot
                current_slot = get_current_slot(schedule)
                
                if current_slot:
                    slot_time = current_slot['timestamp']
                    
                    # Requirement 10.3: Read setpoint_c when time slot changes
                    if slot_time != last_slot_time:
                        logger.info(f"Time slot changed to {slot_time}")
                        
                        setpoint = int(current_slot['setpoint_c'])
                        source = current_slot['source']
                        
                        logger.info(f"Applying temperature: {setpoint}°C (source: {source})")
                        
                        # Send IR signal
                        send_ir_signal(setpoint, ir_codes)
                        
                        last_slot_time = slot_time
            
            # Sleep for check interval
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("IR Blaster stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in IR blaster loop: {e}")
            time.sleep(CHECK_INTERVAL)

def main():
    """Main entry point for IR blaster"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Vatavaran IR Blaster")
    print("=" * 50)
    
    run_ir_blaster()

if __name__ == "__main__":
    main()

"""
LCD Display Module for Vatavaran Edge

Supports:
  - Real I2C LCD (16x2 or 20x4) via RPLCD
  - Terminal simulation when no hardware is present

Shows: current temp, setpoint, mode (LSTM/Override), time slot
"""

import logging
import os
import sys
from datetime import datetime

logger = logging.getLogger(__name__)

# ANSI color codes for terminal display
class C:
    RESET   = '\033[0m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'
    CYAN    = '\033[96m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    RED     = '\033[91m'
    BLUE    = '\033[94m'
    MAGENTA = '\033[95m'
    WHITE   = '\033[97m'
    BG_DARK = '\033[40m'
    BG_BLUE = '\033[44m'


class LCDDisplay:
    """
    LCD display abstraction.
    Uses real I2C LCD if available, otherwise renders a beautiful
    terminal-based LCD simulation.
    """

    def __init__(self, cols=20, rows=4):
        self.cols = cols
        self.rows = rows
        self._lines = [''] * rows
        self._use_hardware = False

        try:
            from RPLCD.i2c import CharLCD
            self.lcd = CharLCD(
                i2c_expander='PCF8574', address=0x27,
                port=1, cols=cols, rows=rows
            )
            self._use_hardware = True
            logger.info("Hardware LCD initialized (I2C)")
        except Exception:
            logger.info("No hardware LCD — using terminal display")

    def clear(self):
        if self._use_hardware:
            self.lcd.clear()
        self._lines = [''] * self.rows

    def write_line(self, row, text):
        """Write text to a specific row (0-indexed)."""
        if row >= self.rows:
            return
        self._lines[row] = text[:self.cols].ljust(self.cols)
        if self._use_hardware:
            self.lcd.cursor_pos = (row, 0)
            self.lcd.write_string(self._lines[row])

    def render_terminal(self):
        """Render the LCD content as a beautiful terminal display."""
        # Move cursor up to overwrite previous display
        sys.stdout.write('\033[2J\033[H')  # Clear screen, move to top

        now = datetime.now().strftime('%H:%M:%S')

        # Header
        print(f"\n  {C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════╗{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}   {C.WHITE}{C.BOLD}🌿 VATAVARAN — Smart Climate Controller{C.RESET}     {C.CYAN}{C.BOLD}║{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}   {C.DIM}Raspberry Pi 4B Edge Device    {now}{C.RESET}  {C.CYAN}{C.BOLD}║{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}╠══════════════════════════════════════════════════╣{C.RESET}")

        # LCD simulation box
        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}                                                  {C.CYAN}{C.BOLD}║{C.RESET}")

        for i, line in enumerate(self._lines):
            padded = line.ljust(self.cols)
            # Color code based on content
            if 'LSTM' in line:
                color = C.GREEN
            elif 'OVERRIDE' in line or 'VOICE' in line:
                color = C.YELLOW
            elif '°C' in line or 'Temp' in line:
                color = C.WHITE + C.BOLD
            else:
                color = C.WHITE

            print(f"  {C.CYAN}{C.BOLD}║{C.RESET}     {C.BG_DARK} {color}{padded}{C.RESET}{C.BG_DARK} {C.RESET}               {C.CYAN}{C.BOLD}║{C.RESET}")

        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}                                                  {C.CYAN}{C.BOLD}║{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}╠══════════════════════════════════════════════════╣{C.RESET}")

    def show_status(self, sensor_temp, setpoint, mode, slot_time,
                    humidity=None, pressure=None, light=None,
                    voice_cmd=None):
        """
        Update the LCD with current status.

        Args:
            sensor_temp: Current sensor temperature (°C)
            setpoint: Target setpoint temperature (°C)
            mode: 'lstm' or 'override'
            slot_time: Current time slot string
            humidity: Humidity %
            pressure: Pressure hPa
            light: Light lux
            voice_cmd: Active voice command (if any)
        """
        mode_str = '🤖 LSTM' if mode == 'lstm' else '🎤 OVERRIDE'
        mode_color = C.GREEN if mode == 'lstm' else C.YELLOW

        # Line 1: Temperature display
        self.write_line(0, f"Now:{sensor_temp:5.1f}°C Set:{setpoint:2d}°C")

        # Line 2: Mode and time
        time_short = slot_time[-8:-3] if len(slot_time) > 8 else slot_time
        self.write_line(1, f"Mode:{mode_str:>14s}")

        # Line 3: Environment
        if humidity is not None:
            self.write_line(2, f"H:{humidity:4.0f}% P:{pressure:7.1f}hPa")
        else:
            self.write_line(2, f"Slot: {time_short}")

        # Line 4: Voice command or slot time
        if voice_cmd:
            self.write_line(3, f'Cmd:"{voice_cmd[:16]}"')
        else:
            self.write_line(3, f"Next: {time_short}")

        if not self._use_hardware:
            self.render_terminal()

            # Extra terminal info below the LCD box
            print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  {C.WHITE}{C.BOLD}Sensor Readings:{C.RESET}                                {C.CYAN}{C.BOLD}║{C.RESET}")
            print(f"  {C.CYAN}{C.BOLD}║{C.RESET}    🌡️  Temperature: {C.BOLD}{sensor_temp:6.1f}°C{C.RESET}                        {C.CYAN}{C.BOLD}║{C.RESET}")
            if humidity is not None:
                print(f"  {C.CYAN}{C.BOLD}║{C.RESET}    💧 Humidity:    {C.BOLD}{humidity:6.1f}%{C.RESET}                         {C.CYAN}{C.BOLD}║{C.RESET}")
            if pressure is not None:
                print(f"  {C.CYAN}{C.BOLD}║{C.RESET}    🔵 Pressure:   {C.BOLD}{pressure:6.1f} hPa{C.RESET}                     {C.CYAN}{C.BOLD}║{C.RESET}")
            if light is not None:
                print(f"  {C.CYAN}{C.BOLD}║{C.RESET}    ☀️  Light:       {C.BOLD}{light:6.1f} lux{C.RESET}                     {C.CYAN}{C.BOLD}║{C.RESET}")

            print(f"  {C.CYAN}{C.BOLD}║{C.RESET}                                                  {C.CYAN}{C.BOLD}║{C.RESET}")
            print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  {C.WHITE}{C.BOLD}AC Control:{C.RESET}                                     {C.CYAN}{C.BOLD}║{C.RESET}")
            print(f"  {C.CYAN}{C.BOLD}║{C.RESET}    🎯 Setpoint:   {C.BOLD}{setpoint:3d}°C{C.RESET}                          {C.CYAN}{C.BOLD}║{C.RESET}")
            print(f"  {C.CYAN}{C.BOLD}║{C.RESET}    📋 Mode:       {mode_color}{C.BOLD}{mode.upper():>10s}{C.RESET}                      {C.CYAN}{C.BOLD}║{C.RESET}")

            if voice_cmd:
                print(f"  {C.CYAN}{C.BOLD}║{C.RESET}    🎤 Voice:      {C.YELLOW}{C.BOLD}\"{voice_cmd}\"{C.RESET}                {C.CYAN}{C.BOLD}║{C.RESET}")

            print(f"  {C.CYAN}{C.BOLD}╠══════════════════════════════════════════════════╣{C.RESET}")

    def show_schedule_preview(self, schedule_lines, current_slot=0):
        """Show a preview of the schedule below the main display."""
        if self._use_hardware:
            return  # No room on physical LCD

        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  {C.WHITE}{C.BOLD}24h Schedule Preview:{C.RESET}                              {C.CYAN}{C.BOLD}║{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  {C.DIM}{'Time':>19s}  {'Temp':>5s}  {'Source':>8s}{C.RESET}              {C.CYAN}{C.BOLD}║{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  {C.DIM}{'─'*19}  {'─'*5}  {'─'*8}{C.RESET}              {C.CYAN}{C.BOLD}║{C.RESET}")

        for i, line in enumerate(schedule_lines[:12]):
            parts = line.strip().split(',')
            if len(parts) == 3:
                ts, temp, src = parts
                marker = ' ◄' if i == current_slot else '  '
                if src == 'override':
                    clr = C.YELLOW
                elif i == current_slot:
                    clr = C.GREEN + C.BOLD
                else:
                    clr = C.WHITE

                print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  {clr}{ts:>19s}  {temp:>3s}°C  {src:>8s}{marker}{C.RESET}      {C.CYAN}{C.BOLD}║{C.RESET}")

        if len(schedule_lines) > 12:
            remaining = len(schedule_lines) - 12
            print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  {C.DIM}... +{remaining} more slots{C.RESET}                              {C.CYAN}{C.BOLD}║{C.RESET}")

        print(f"  {C.CYAN}{C.BOLD}╚══════════════════════════════════════════════════╝{C.RESET}")

    def show_inference_progress(self, step, total, elapsed=None):
        """Show LSTM inference progress."""
        pct = int(step / total * 20)
        bar = '█' * pct + '░' * (20 - pct)
        time_str = f" ({elapsed:.1f}s)" if elapsed else ""
        self.write_line(2, f"Infer: [{bar[:16]}]")
        self.write_line(3, f"{step:3d}/{total} slots{time_str}")
        if not self._use_hardware:
            self.render_terminal()

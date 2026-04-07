"""
LCD Display Module for Vatavaran Edge — 16x2 I2C LCD

Hardware: 16x2 LCD with PCF8574 backpack at I2C address 0x27
Cycles through info screens since we only have 2 lines.
Also renders a terminal simulation alongside.
"""

import logging
import sys
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# ANSI colors for terminal
class C:
    RESET   = '\033[0m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'
    CYAN    = '\033[96m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    RED     = '\033[91m'
    MAGENTA = '\033[95m'
    WHITE   = '\033[97m'
    BG_DARK = '\033[40m'


class LCDDisplay:
    """
    16x2 I2C LCD display controller.
    Writes to real hardware LCD AND terminal simultaneously.
    """

    def __init__(self, address=0x27, cols=16, rows=2):
        self.cols = cols
        self.rows = rows
        self._lines = [''] * rows
        self._hw = None

        try:
            from RPLCD.i2c import CharLCD
            self._hw = CharLCD(
                i2c_expander='PCF8574', address=address,
                port=1, cols=cols, rows=rows,
                charmap='A02', auto_linebreaks=False
            )
            self._hw.clear()
            logger.info(f"Hardware LCD initialized ({cols}x{rows} at 0x{address:02x})")
        except Exception as e:
            logger.warning(f"No hardware LCD: {e}")

    def clear(self):
        if self._hw:
            self._hw.clear()
        self._lines = [''] * self.rows

    def write(self, row, text):
        """Write text to row (0 or 1). Pads/truncates to 16 chars."""
        text = str(text)[:self.cols].ljust(self.cols)
        self._lines[row] = text
        if self._hw:
            self._hw.cursor_pos = (row, 0)
            self._hw.write_string(text)

    def _print_terminal(self, extra_lines=None):
        """Print the LCD contents + extra info to terminal."""
        sys.stdout.write('\033[2J\033[H')
        now = datetime.now().strftime('%H:%M:%S')

        print(f"\n  {C.CYAN}{C.BOLD}╔════════════════════════════════════════╗{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  🌿 VATAVARAN  |  RPi 4B  |  {now}  {C.CYAN}{C.BOLD}║{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}╠════════════════════════════════════════╣{C.RESET}")

        # LCD box
        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  ┌──────────────────┐                {C.CYAN}{C.BOLD}║{C.RESET}")
        for line in self._lines:
            color = C.GREEN if 'LSTM' in line else (C.YELLOW if 'OVR' in line or 'VOICE' in line else C.WHITE)
            print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  │{C.BG_DARK}{color}{C.BOLD}{line}{C.RESET}│  ← LCD          {C.CYAN}{C.BOLD}║{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  └──────────────────┘                {C.CYAN}{C.BOLD}║{C.RESET}")

        if extra_lines:
            print(f"  {C.CYAN}{C.BOLD}╠════════════════════════════════════════╣{C.RESET}")
            for el in extra_lines:
                print(f"  {C.CYAN}{C.BOLD}║{C.RESET}  {el:<38s}{C.CYAN}{C.BOLD}║{C.RESET}")
        print(f"  {C.CYAN}{C.BOLD}╚════════════════════════════════════════╝{C.RESET}")

    # ── High-level display methods ───────────────────────────────

    def show_startup(self):
        self.write(0, " VATAVARAN  v1.0")
        self.write(1, "Initializing... ")
        self._print_terminal()

    def show_sensor(self, temp, humidity):
        self.write(0, f"T:{temp:5.1f}C H:{humidity:4.0f}%")
        self.write(1, "Reading sensors ")
        self._print_terminal()

    def show_building(self):
        self.write(0, "Building 90     ")
        self.write(1, "features...     ")
        self._print_terminal()

    def show_inferring(self, progress=None):
        self.write(0, "LSTM Inference  ")
        if progress:
            pct = int(progress * 16)
            bar = chr(0xFF) * pct + ' ' * (16 - pct)
            self.write(1, bar[:16])
        else:
            self.write(1, "96 predictions..")
        self._print_terminal()

    def show_done(self, elapsed, temp_min, temp_max):
        self.write(0, f"Done! {elapsed:.0f}s       ")
        self.write(1, f"{temp_min:.0f}-{temp_max:.0f}C 96 slots")
        self._print_terminal()

    def show_main(self, sensor_temp, setpoint, mode, slot_time,
                  humidity=None, pressure=None, voice_cmd=None):
        """
        Main operating display. Cycles through screens on LCD,
        shows everything in terminal.
        """
        mode_tag = "LSTM" if mode == "lstm" else "OVR "

        # LCD Line 1: Current temp + setpoint
        self.write(0, f"T:{sensor_temp:4.1f} SET:{setpoint:2d}C")

        # LCD Line 2: Mode + time
        t = slot_time[-8:-3] if len(slot_time) > 5 else slot_time
        self.write(1, f"{mode_tag}  {t}    ")

        # Terminal gets the full picture
        extra = []
        extra.append(f"{C.WHITE}{C.BOLD}Sensor Readings:{C.RESET}")
        extra.append(f"  🌡️  Temp:     {C.BOLD}{sensor_temp:6.1f}°C{C.RESET}")
        if humidity:
            extra.append(f"  💧 Humidity: {C.BOLD}{humidity:6.1f}%{C.RESET}")
        if pressure:
            extra.append(f"  🔵 Pressure: {C.BOLD}{pressure:6.1f} hPa{C.RESET}")
        extra.append(f"")
        extra.append(f"{C.WHITE}{C.BOLD}AC Control:{C.RESET}")
        extra.append(f"  🎯 Setpoint:  {C.BOLD}{setpoint}°C{C.RESET}")

        mode_c = C.GREEN if mode == "lstm" else C.YELLOW
        extra.append(f"  📋 Mode:      {mode_c}{C.BOLD}{mode.upper()}{C.RESET}")

        if voice_cmd:
            extra.append(f"  🎤 Command:   {C.YELLOW}\"{voice_cmd}\"{C.RESET}")

        self._print_terminal(extra)

    def show_voice_cmd(self, cmd, nlp_result, override_temp=None):
        """Show voice command being processed."""
        self.write(0, f'"{cmd[:14]}"')
        if override_temp:
            self.write(1, f"OVR -> {override_temp:2d}C     ")
        else:
            self.write(1, f"Result: {str(nlp_result)[:9]}")

        extra = [
            f"{C.YELLOW}{C.BOLD}Voice Command:{C.RESET}",
            f"  Input:  \"{cmd}\"",
            f"  NLP:    {nlp_result}",
        ]
        if override_temp:
            extra.append(f"  Action: {C.YELLOW}{C.BOLD}Override to {override_temp}°C for 1 hour{C.RESET}")
        self._print_terminal(extra)

    def show_schedule(self, lines, current=0):
        """Show schedule preview in terminal only."""
        extra = [f"{C.WHITE}{C.BOLD}Schedule (next 10 slots):{C.RESET}"]
        extra.append(f"  {C.DIM}{'Time':>19}  Temp  Source{C.RESET}")
        for i, line in enumerate(lines[:10]):
            parts = line.strip().split(',')
            if len(parts) != 3:
                continue
            ts, temp, src = parts
            marker = ' ◄' if i == current else ''
            clr = C.YELLOW if src == 'override' else (C.GREEN + C.BOLD if i == current else C.WHITE)
            extra.append(f"  {clr}{ts}  {temp:>3s}°C  {src}{marker}{C.RESET}")
        remaining = len(lines) - 10
        if remaining > 0:
            extra.append(f"  {C.DIM}... +{remaining} more{C.RESET}")
        self._print_terminal(extra)

    def show_ir(self, setpoint, mode):
        """Flash IR blaster activity on LCD."""
        self.write(0, f"IR -> AC {setpoint:2d}C   ")
        self.write(1, f"Sending...      ")
        if self._hw:
            time.sleep(0.3)
            self.write(1, f"Sent! [{mode:>4s}]   ")

    def show_goodbye(self):
        self.write(0, " VATAVARAN  v1.0")
        self.write(1, "  Goodbye!      ")
        self._print_terminal()

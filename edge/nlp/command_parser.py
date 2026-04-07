"""
NLP command parser for voice temperature control.
Extracts temperature adjustments from natural language commands.

Copied from api/nlp/command_parser.py — no changes needed (pure Python).
"""

import re
import logging
from typing import Dict, Optional, Union
from .lexicons import (
    TOO_HOT_KEYWORDS,
    TOO_COLD_KEYWORDS,
    WANT_WARMER_KEYWORDS,
    WANT_COOLER_KEYWORDS,
    INTENSITY_MODIFIERS,
    SETPOINT_KEYWORDS,
    NUMBER_WORDS
)

logger = logging.getLogger(__name__)


def parse_command(text: str, current_temp_c: float, current_fan: Optional[str] = None) -> Dict[str, Union[int, float, None]]:
    """
    Parse natural language temperature command.

    Args:
        text: Voice command text (e.g., "it's too hot", "set to 22 degrees")
        current_temp_c: Current temperature in Celsius
        current_fan: Current fan setting (not used in current implementation)

    Returns:
        Dictionary with either:
        - {"delta": int} for relative adjustments (e.g., -2, +1)
        - {"absolute": int} for absolute setpoints (e.g., 22)
        - {"delta": 0} if command cannot be parsed
    """
    if not text or not isinstance(text, str):
        logger.warning(f"Invalid command text: {text}")
        return {"delta": 0}

    text = text.lower().strip()

    # Try absolute setpoint first
    absolute_temp = _extract_absolute_setpoint(text)
    if absolute_temp is not None:
        if 18 <= absolute_temp <= 30:
            return {"absolute": absolute_temp}
        else:
            logger.warning(f"Temperature {absolute_temp} out of range (18-30°C)")
            return {"delta": 0}

    # Try relative delta
    delta = _extract_temperature_delta(text)
    if delta != 0:
        return {"delta": delta}

    logger.info(f"Could not parse command: '{text}'")
    return {"delta": 0}


def _extract_absolute_setpoint(text: str) -> Optional[int]:
    """Extract absolute temperature setpoint from command."""
    has_setpoint_keyword = any(keyword in text for keyword in SETPOINT_KEYWORDS)

    if not has_setpoint_keyword:
        return None

    number_pattern = r'\b(\d{1,2})\s*(?:degrees?|celsius|c)?\b'
    match = re.search(number_pattern, text)

    if match:
        return int(match.group(1))

    for word, value in NUMBER_WORDS.items():
        if word in text and 18 <= value <= 30:
            return value

    return None


def _extract_temperature_delta(text: str) -> int:
    """Extract relative temperature delta from command."""
    feels_hot = any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in TOO_HOT_KEYWORDS)
    feels_cold = any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in TOO_COLD_KEYWORDS)
    wants_warmer = any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in WANT_WARMER_KEYWORDS)
    wants_cooler = any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in WANT_COOLER_KEYWORDS)

    decrease_temp = feels_hot or wants_cooler
    increase_temp = feels_cold or wants_warmer

    if not decrease_temp and not increase_temp:
        return 0

    intensity = 1
    for modifier, value in INTENSITY_MODIFIERS.items():
        if re.search(r'\b' + re.escape(modifier) + r'\b', text):
            intensity = max(intensity, value)

    if decrease_temp and not increase_temp:
        return -intensity
    elif increase_temp and not decrease_temp:
        return +intensity
    else:
        return 0

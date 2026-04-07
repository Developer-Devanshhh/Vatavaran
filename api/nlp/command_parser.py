"""
NLP command parser for voice temperature control.
Extracts temperature adjustments from natural language commands.
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
    
    Examples:
        >>> parse_command("it's too hot", 26.0)
        {"delta": -2}
        >>> parse_command("set temperature to 22", 26.0)
        {"absolute": 22}
        >>> parse_command("make it cooler", 26.0)
        {"delta": -1}
    """
    if not text or not isinstance(text, str):
        logger.warning(f"Invalid command text: {text}")
        return {"delta": 0}
    
    # Normalize text
    text = text.lower().strip()
    
    # Try to extract absolute setpoint first
    absolute_temp = _extract_absolute_setpoint(text)
    if absolute_temp is not None:
        # Validate temperature range (18-30°C)
        if 18 <= absolute_temp <= 30:
            return {"absolute": absolute_temp}
        else:
            logger.warning(f"Temperature {absolute_temp} out of range (18-30°C)")
            return {"delta": 0}
    
    # Try to extract relative delta
    delta = _extract_temperature_delta(text)
    if delta != 0:
        return {"delta": delta}
    
    # Could not parse command
    logger.info(f"Could not parse command: '{text}'")
    return {"delta": 0}


def _extract_absolute_setpoint(text: str) -> Optional[int]:
    """
    Extract absolute temperature setpoint from command.
    
    Examples:
        "set to 22" -> 22
        "make it twenty-three degrees" -> 23
        "change temperature to 24" -> 24
    """
    # Check if command contains setpoint keywords
    has_setpoint_keyword = any(keyword in text for keyword in SETPOINT_KEYWORDS)
    
    if not has_setpoint_keyword:
        return None
    
    # Try to find numeric temperature
    # Pattern: number followed by optional "degrees" or "celsius"
    number_pattern = r'\b(\d{1,2})\s*(?:degrees?|celsius|c)?\b'
    match = re.search(number_pattern, text)
    
    if match:
        temp = int(match.group(1))
        return temp
    
    # Try to find word-based numbers
    for word, value in NUMBER_WORDS.items():
        if word in text and 18 <= value <= 30:
            return value
    
    return None


def _extract_temperature_delta(text: str) -> int:
    """
    Extract relative temperature delta from command.
    
    Examples:
        "too hot" -> -2 (decrease temperature)
        "it's cold" -> +1 (increase temperature)
        "make it warmer" -> +1 (increase temperature)
        "make it cooler" -> -1 (decrease temperature)
        "very cool" -> -3 (decrease temperature)
    """
    # Use word boundaries to avoid partial matches
    import re
    
    # Check if user feels too hot/cold or wants warmer/cooler
    feels_hot = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in TOO_HOT_KEYWORDS)
    feels_cold = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in TOO_COLD_KEYWORDS)
    wants_warmer = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in WANT_WARMER_KEYWORDS)
    wants_cooler = any(re.search(r'\b' + re.escape(keyword) + r'\b', text) for keyword in WANT_COOLER_KEYWORDS)
    
    # Determine direction
    decrease_temp = feels_hot or wants_cooler
    increase_temp = feels_cold or wants_warmer
    
    if not decrease_temp and not increase_temp:
        return 0
    
    # Determine intensity
    intensity = 1  # Default
    
    for modifier, value in INTENSITY_MODIFIERS.items():
        if re.search(r'\b' + re.escape(modifier) + r'\b', text):
            intensity = max(intensity, value)  # Use highest intensity found
    
    # Calculate delta
    if decrease_temp and not increase_temp:
        # User wants temperature decreased
        delta = -intensity
    elif increase_temp and not decrease_temp:
        # User wants temperature increased
        delta = +intensity
    else:
        # Conflicting signals, default to 0
        delta = 0
    
    return delta

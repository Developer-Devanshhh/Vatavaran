"""
Lexicons for NLP command parsing.
Contains keyword mappings for temperature adjustment commands.

Copied from api/nlp/lexicons.py — no changes needed (pure Python).
"""

# Keywords indicating user feels hot (wants temperature decreased)
TOO_HOT_KEYWORDS = [
    "hot", "hotter", "warm"
]

# Keywords indicating user feels cold (wants temperature increased)
TOO_COLD_KEYWORDS = [
    "cold", "colder", "cool"
]

# Keywords indicating user wants warmer (increase temperature)
WANT_WARMER_KEYWORDS = [
    "warmer", "increase", "up", "raise", "higher"
]

# Keywords indicating user wants cooler (decrease temperature)
WANT_COOLER_KEYWORDS = [
    "cooler", "decrease", "down", "lower", "reduce"
]

# Intensity modifiers
INTENSITY_MODIFIERS = {
    "very": 3,
    "too": 2,
    "bit": 1,
    "little": 1,
    "slightly": 1,
    "much": 2,
}

# Absolute setpoint keywords
SETPOINT_KEYWORDS = [
    "set", "make", "change", "adjust", "temperature"
]

# Number words to digits
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "twenty-one": 21,
    "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
    "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27,
    "twenty-eight": 28, "twenty-nine": 29, "thirty": 30
}

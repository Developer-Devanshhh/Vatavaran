"""
Unit tests for NLP command parser.
"""

import pytest
from api.nlp.command_parser import parse_command


def test_parse_command_too_hot():
    """Test parsing 'too hot' command."""
    result = parse_command("it's too hot", 26.0)
    assert "delta" in result
    assert result["delta"] == -2


def test_parse_command_cold():
    """Test parsing 'cold' command."""
    result = parse_command("it's cold", 26.0)
    assert "delta" in result
    assert result["delta"] == 1  # Default intensity without modifier


def test_parse_command_absolute_setpoint():
    """Test parsing absolute temperature setpoint."""
    result = parse_command("set temperature to 22", 26.0)
    assert "absolute" in result
    assert result["absolute"] == 22


def test_parse_command_absolute_setpoint_degrees():
    """Test parsing absolute setpoint with 'degrees'."""
    result = parse_command("set to 24 degrees", 26.0)
    assert "absolute" in result
    assert result["absolute"] == 24


def test_parse_command_cooler():
    """Test parsing 'cooler' command."""
    result = parse_command("make it cooler", 26.0)
    assert "delta" in result
    assert result["delta"] == -1


def test_parse_command_warmer():
    """Test parsing 'warmer' command."""
    result = parse_command("make it warmer", 20.0)
    assert "delta" in result
    assert result["delta"] == 1


def test_parse_command_very_cold():
    """Test parsing 'very cold' with intensity modifier."""
    result = parse_command("it's very cold", 26.0)
    assert "delta" in result
    assert result["delta"] == 3


def test_parse_command_unparseable():
    """Test unparseable command returns delta 0."""
    result = parse_command("hello world", 26.0)
    assert "delta" in result
    assert result["delta"] == 0


def test_parse_command_empty():
    """Test empty command returns delta 0."""
    result = parse_command("", 26.0)
    assert "delta" in result
    assert result["delta"] == 0


def test_parse_command_out_of_range():
    """Test temperature out of range returns delta 0."""
    result = parse_command("set to 35", 26.0)
    assert "delta" in result
    assert result["delta"] == 0


def test_parse_command_with_current_fan():
    """Test parse_command accepts current_fan parameter."""
    result = parse_command("too hot", 26.0, current_fan="high")
    assert "delta" in result
    assert result["delta"] == -2


def test_parse_command_none_input():
    """Test None input returns delta 0 and logs warning."""
    result = parse_command(None, 26.0)
    assert "delta" in result
    assert result["delta"] == 0


def test_parse_command_invalid_type():
    """Test invalid type input returns delta 0."""
    result = parse_command(123, 26.0)
    assert "delta" in result
    assert result["delta"] == 0


def test_parse_command_absolute_lower_bound():
    """Test absolute setpoint at lower bound (18°C)."""
    result = parse_command("set to 18", 26.0)
    assert "absolute" in result
    assert result["absolute"] == 18


def test_parse_command_absolute_upper_bound():
    """Test absolute setpoint at upper bound (30°C)."""
    result = parse_command("set to 30", 26.0)
    assert "absolute" in result
    assert result["absolute"] == 30


def test_parse_command_absolute_below_range():
    """Test absolute setpoint below range returns delta 0."""
    result = parse_command("set to 15", 26.0)
    assert "delta" in result
    assert result["delta"] == 0


def test_parse_command_absolute_above_range():
    """Test absolute setpoint above range returns delta 0."""
    result = parse_command("set to 35", 26.0)
    assert "delta" in result
    assert result["delta"] == 0


def test_parse_command_structured_result_delta():
    """Test structured result contains only delta key for relative commands."""
    result = parse_command("too hot", 26.0)
    assert "delta" in result
    assert "absolute" not in result
    assert isinstance(result["delta"], int)


def test_parse_command_structured_result_absolute():
    """Test structured result contains only absolute key for setpoint commands."""
    result = parse_command("set to 22", 26.0)
    assert "absolute" in result
    assert "delta" not in result
    assert isinstance(result["absolute"], int)

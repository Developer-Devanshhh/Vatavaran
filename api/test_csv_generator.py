"""
Unit tests for CSV Generator module

Tests the schedule generation logic including timestamp formatting,
LSTM prediction rounding, and source marking.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from api.csv_generator import generate_schedule_csv


class TestCSVGenerator:
    """Test suite for CSV generator functionality"""
    
    def test_generates_96_rows(self):
        """Test that exactly 96 rows are generated (Requirement 14.3)"""
        predictions = np.random.uniform(18, 30, 96)
        csv_content = generate_schedule_csv(predictions)
        
        lines = csv_content.strip().split('\n')
        # 1 header + 96 data rows
        assert len(lines) == 97
    
    def test_csv_header_format(self):
        """Test CSV header contains correct columns (Requirement 14.4)"""
        predictions = np.random.uniform(18, 30, 96)
        csv_content = generate_schedule_csv(predictions)
        
        lines = csv_content.strip().split('\n')
        header = lines[0]
        assert header == "timestamp,setpoint_c,source"
    
    def test_timestamp_format(self):
        """Test timestamps are formatted as YYYY-MM-DD HH:MM:SS (Requirement 14.2)"""
        predictions = np.random.uniform(18, 30, 96)
        csv_content = generate_schedule_csv(predictions)
        
        lines = csv_content.strip().split('\n')
        first_data_row = lines[1].split(',')
        timestamp_str = first_data_row[0]
        
        # Verify format by parsing
        try:
            datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pytest.fail(f"Timestamp format incorrect: {timestamp_str}")
    
    def test_15_minute_intervals(self):
        """Test timestamps are at 15-minute intervals (Requirement 9.2)"""
        predictions = np.random.uniform(18, 30, 96)
        csv_content = generate_schedule_csv(predictions)
        
        lines = csv_content.strip().split('\n')
        
        # Parse first two timestamps
        ts1_str = lines[1].split(',')[0]
        ts2_str = lines[2].split(',')[0]
        
        ts1 = datetime.strptime(ts1_str, "%Y-%m-%d %H:%M:%S")
        ts2 = datetime.strptime(ts2_str, "%Y-%m-%d %H:%M:%S")
        
        # Verify 15-minute difference
        diff = (ts2 - ts1).total_seconds()
        assert diff == 15 * 60  # 15 minutes in seconds
    
    def test_lstm_predictions_rounded(self):
        """Test LSTM predictions are rounded to whole degrees (Requirement 9.3)"""
        # Use predictions with decimal values
        predictions = np.array([22.3, 23.7, 24.5, 25.1] + [22.0] * 92)
        csv_content = generate_schedule_csv(predictions)
        
        lines = csv_content.strip().split('\n')
        
        # Check first few setpoints are integers
        setpoint1 = int(lines[1].split(',')[1])
        setpoint2 = int(lines[2].split(',')[1])
        setpoint3 = int(lines[3].split(',')[1])
        setpoint4 = int(lines[4].split(',')[1])
        
        assert setpoint1 == 22  # 22.3 rounds to 22
        assert setpoint2 == 24  # 23.7 rounds to 24
        assert setpoint3 == 24  # 24.5 rounds to 24 (banker's rounding) or 25
        assert setpoint4 == 25  # 25.1 rounds to 25
    
    def test_lstm_source_marking(self):
        """Test LSTM slots are marked with source 'lstm' (Requirement 9.4)"""
        predictions = np.random.uniform(18, 30, 96)
        csv_content = generate_schedule_csv(predictions)
        
        lines = csv_content.strip().split('\n')
        
        # Check all rows have 'lstm' source when no override
        for i in range(1, 97):
            source = lines[i].split(',')[2]
            assert source == "lstm"
    
    def test_invalid_prediction_count(self):
        """Test that non-96 prediction arrays raise ValueError"""
        predictions = np.random.uniform(18, 30, 50)
        
        with pytest.raises(ValueError, match="Expected 96 predictions"):
            generate_schedule_csv(predictions)
    
    def test_csv_row_format(self):
        """Test each row has exactly 3 columns"""
        predictions = np.random.uniform(18, 30, 96)
        csv_content = generate_schedule_csv(predictions)
        
        lines = csv_content.strip().split('\n')
        
        # Check all data rows have 3 columns
        for i in range(1, 97):
            columns = lines[i].split(',')
            assert len(columns) == 3
    
    def test_setpoint_values_are_integers(self):
        """Test that setpoint_c values are integers"""
        predictions = np.array([22.3, 23.7, 24.5] + [22.0] * 93)
        csv_content = generate_schedule_csv(predictions)
        
        lines = csv_content.strip().split('\n')
        
        # Check setpoints can be parsed as integers
        for i in range(1, 97):
            setpoint_str = lines[i].split(',')[1]
            try:
                int(setpoint_str)
            except ValueError:
                pytest.fail(f"Setpoint is not an integer: {setpoint_str}")


class TestVoiceOverride:
    """Test suite for voice override functionality (Requirements 9.5-9.8, 14.5, 14.6)"""
    
    def test_override_applies_to_next_4_slots(self):
        """Test override temperature is applied to next 4 time slots (Requirement 9.5)"""
        predictions = np.full(96, 24.0)
        override_data = {'temperature': 22, 'slots': 4}
        
        csv_content = generate_schedule_csv(predictions, override_data)
        lines = csv_content.strip().split('\n')
        
        # First 4 slots should have override temperature
        for i in range(1, 5):
            setpoint = int(lines[i].split(',')[1])
            assert setpoint == 22
    
    def test_override_slots_marked_with_override_source(self):
        """Test override slots are marked with source 'override' (Requirement 9.6)"""
        predictions = np.full(96, 24.0)
        override_data = {'temperature': 22, 'slots': 4}
        
        csv_content = generate_schedule_csv(predictions, override_data)
        lines = csv_content.strip().split('\n')
        
        # First 4 slots should have 'override' source
        for i in range(1, 5):
            source = lines[i].split(',')[2]
            assert source == "override"
    
    def test_lstm_predictions_resume_after_override(self):
        """Test LSTM predictions resume after override window (Requirement 9.7)"""
        predictions = np.full(96, 24.0)
        override_data = {'temperature': 22, 'slots': 4}
        
        csv_content = generate_schedule_csv(predictions, override_data)
        lines = csv_content.strip().split('\n')
        
        # Slots 5-96 should use LSTM predictions
        for i in range(5, 97):
            setpoint = int(lines[i].split(',')[1])
            source = lines[i].split(',')[2]
            assert setpoint == 24  # LSTM prediction
            assert source == "lstm"
    
    def test_override_with_custom_slot_count(self):
        """Test override can use custom slot count instead of default 4"""
        predictions = np.full(96, 24.0)
        override_data = {'temperature': 20, 'slots': 8}
        
        csv_content = generate_schedule_csv(predictions, override_data)
        lines = csv_content.strip().split('\n')
        
        # First 8 slots should have override
        for i in range(1, 9):
            setpoint = int(lines[i].split(',')[1])
            source = lines[i].split(',')[2]
            assert setpoint == 20
            assert source == "override"
        
        # Slot 9 onwards should use LSTM
        for i in range(9, 97):
            setpoint = int(lines[i].split(',')[1])
            source = lines[i].split(',')[2]
            assert setpoint == 24
            assert source == "lstm"
    
    def test_override_temperature_validation_range(self):
        """Test override temperature must be in range 18-30 (Requirement 14.5)"""
        predictions = np.full(96, 24.0)
        
        # Test below range
        override_data = {'temperature': 17}
        with pytest.raises(ValueError, match="must be an integer between 18-30"):
            generate_schedule_csv(predictions, override_data)
        
        # Test above range
        override_data = {'temperature': 31}
        with pytest.raises(ValueError, match="must be an integer between 18-30"):
            generate_schedule_csv(predictions, override_data)
    
    def test_override_temperature_validation_type(self):
        """Test override temperature must be an integer (Requirement 14.5)"""
        predictions = np.full(96, 24.0)
        
        # Test float value
        override_data = {'temperature': 22.5}
        with pytest.raises(ValueError, match="must be an integer"):
            generate_schedule_csv(predictions, override_data)
    
    def test_valid_override_temperatures(self):
        """Test valid override temperatures at boundaries (Requirement 14.5)"""
        predictions = np.full(96, 24.0)
        
        # Test minimum valid temperature
        override_data = {'temperature': 18}
        csv_content = generate_schedule_csv(predictions, override_data)
        lines = csv_content.strip().split('\n')
        assert int(lines[1].split(',')[1]) == 18
        
        # Test maximum valid temperature
        override_data = {'temperature': 30}
        csv_content = generate_schedule_csv(predictions, override_data)
        lines = csv_content.strip().split('\n')
        assert int(lines[1].split(',')[1]) == 30
    
    def test_source_values_are_valid(self):
        """Test source values are either 'lstm' or 'override' (Requirement 14.6)"""
        predictions = np.full(96, 24.0)
        override_data = {'temperature': 22, 'slots': 4}
        
        csv_content = generate_schedule_csv(predictions, override_data)
        lines = csv_content.strip().split('\n')
        
        # Check all source values are valid
        for i in range(1, 97):
            source = lines[i].split(',')[2]
            assert source in ["lstm", "override"], f"Invalid source value: {source}"
    
    def test_lstm_predictions_clamped_to_valid_range(self):
        """Test LSTM predictions outside range are clamped to 18-30 (Requirement 14.5)"""
        # Create predictions with out-of-range values
        predictions = np.array([15.0, 17.5, 18.0, 30.0, 32.0, 35.0] + [24.0] * 90)
        
        csv_content = generate_schedule_csv(predictions)
        lines = csv_content.strip().split('\n')
        
        # Check first few setpoints are clamped
        assert int(lines[1].split(',')[1]) == 18  # 15.0 clamped to 18
        assert int(lines[2].split(',')[1]) == 18  # 17.5 clamped to 18
        assert int(lines[3].split(',')[1]) == 18  # 18.0 stays 18
        assert int(lines[4].split(',')[1]) == 30  # 30.0 stays 30
        assert int(lines[5].split(',')[1]) == 30  # 32.0 clamped to 30
        assert int(lines[6].split(',')[1]) == 30  # 35.0 clamped to 30
    
    def test_csv_format_with_override(self):
        """Test CSV format is text/csv compatible with override (Requirement 9.8)"""
        predictions = np.full(96, 24.0)
        override_data = {'temperature': 22, 'slots': 4}
        
        csv_content = generate_schedule_csv(predictions, override_data)
        
        # Verify it's a string (text format)
        assert isinstance(csv_content, str)
        
        # Verify CSV structure
        lines = csv_content.strip().split('\n')
        assert len(lines) == 97  # Header + 96 rows
        assert lines[0] == "timestamp,setpoint_c,source"
        
        # Verify all rows have 3 columns
        for i in range(1, 97):
            columns = lines[i].split(',')
            assert len(columns) == 3

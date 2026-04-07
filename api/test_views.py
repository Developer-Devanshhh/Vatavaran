"""
Tests for the /api/predict/ endpoint.

**Validates: Requirements 11.1, 11.2**
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
import json


class PredictEndpointTestCase(TestCase):
    """Test cases for POST /api/predict/ endpoint"""
    
    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
        self.url = '/api/predict/'
    
    def test_missing_mode_field(self):
        """Test that missing mode field returns 400"""
        payload = {
            "timestamp": "2024-01-15T10:30:00",
            "temperature_c": 26.5,
            "device_id": "rpi_sensor_01"
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('mode', response.data['error'].lower())
    
    def test_invalid_mode_value(self):
        """Test that invalid mode value returns 400"""
        payload = {
            "mode": "invalid_mode",
            "timestamp": "2024-01-15T10:30:00",
            "temperature_c": 26.5,
            "device_id": "rpi_sensor_01"
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('invalid mode', response.data['error'].lower())
    
    def test_missing_sensor_fields(self):
        """Test that missing sensor fields return 400"""
        # Missing timestamp
        payload = {
            "mode": "scheduled",
            "temperature_c": 26.5,
            "device_id": "rpi_sensor_01"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('timestamp', response.data['error'].lower())
        
        # Missing temperature_c
        payload = {
            "mode": "scheduled",
            "timestamp": "2024-01-15T10:30:00",
            "device_id": "rpi_sensor_01"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('temperature_c', response.data['error'].lower())
        
        # Missing device_id
        payload = {
            "mode": "scheduled",
            "timestamp": "2024-01-15T10:30:00",
            "temperature_c": 26.5
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('device_id', response.data['error'].lower())
    
    def test_invalid_temperature_value(self):
        """Test that non-numeric temperature_c returns 400"""
        payload = {
            "mode": "scheduled",
            "timestamp": "2024-01-15T10:30:00",
            "temperature_c": "not_a_number",
            "device_id": "rpi_sensor_01"
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('temperature_c', response.data['error'].lower())
    
    def test_scheduled_mode_valid_payload(self):
        """Test that valid scheduled mode payload is accepted"""
        payload = {
            "mode": "scheduled",
            "timestamp": "2024-01-15T10:30:00",
            "temperature_c": 26.5,
            "device_id": "rpi_sensor_01"
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        # Should return 501 (not implemented) since orchestration is pending
        # But validation should pass
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
    
    def test_voice_override_missing_command_text(self):
        """Test that voice_override mode without command_text returns 400"""
        payload = {
            "mode": "voice_override",
            "timestamp": "2024-01-15T10:30:00",
            "temperature_c": 26.5,
            "device_id": "rpi_sensor_01"
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('command_text', response.data['error'].lower())
    
    def test_voice_override_valid_payload(self):
        """Test that valid voice_override mode payload is accepted"""
        payload = {
            "mode": "voice_override",
            "timestamp": "2024-01-15T10:30:00",
            "temperature_c": 26.5,
            "device_id": "rpi_sensor_01",
            "command_text": "it's too hot"
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        # Should return 501 (not implemented) since orchestration is pending
        # But validation should pass
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
    
    def test_temperature_as_integer(self):
        """Test that temperature_c can be an integer"""
        payload = {
            "mode": "scheduled",
            "timestamp": "2024-01-15T10:30:00",
            "temperature_c": 26,
            "device_id": "rpi_sensor_01"
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        # Should pass validation
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
    
    def test_invalid_json_payload(self):
        """Test that invalid JSON returns 400"""
        response = self.client.post(
            self.url,
            data="not valid json",
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging
import pandas as pd
from datetime import datetime

from .weather import fetch_weather_forecast
from .features import build_feature_matrix
from .inference import LSTMPredictor
from .csv_generator import generate_schedule_csv

logger = logging.getLogger(__name__)

# Initialize LSTM predictor once at module load (Requirement 15.1)
try:
    lstm_predictor = LSTMPredictor()
    logger.info("LSTM predictor initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize LSTM predictor: {e}")
    lstm_predictor = None

# Create your views here.

@api_view(['POST'])
def predict(request):
    """
    API endpoint for temperature schedule prediction.
    
    **Validates: Requirements 11.1, 11.2**
    
    Accepts JSON payload with mode (scheduled or voice_override) and sensor data.
    Returns CSV schedule with 96 15-minute time slots.
    
    Expected JSON payload:
    {
        "mode": "scheduled" | "voice_override",
        "timestamp": "ISO 8601 timestamp",
        "temperature_c": float,
        "device_id": "string",
        "command_text": "string" (required only for voice_override mode)
    }
    
    Returns:
        - 200 OK: CSV schedule with columns: timestamp, setpoint_c, source
        - 400 Bad Request: Invalid payload or missing required fields
        - 500 Internal Server Error: Processing failure
    """
    logger.info(f"Received prediction request from {request.META.get('REMOTE_ADDR')}")
    
    # Parse request body
    try:
        data = request.data
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        return Response(
            {"error": "Invalid JSON payload"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate mode field (Requirement 11.1)
    mode = data.get('mode')
    if not mode:
        logger.warning("Missing 'mode' field in request")
        return Response(
            {"error": "Missing required field: 'mode'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if mode not in ['scheduled', 'voice_override']:
        logger.warning(f"Invalid mode: {mode}")
        return Response(
            {"error": f"Invalid mode: '{mode}'. Must be 'scheduled' or 'voice_override'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    logger.info(f"Processing request in mode: {mode}")
    
    # Parse sensor data from request body
    timestamp = data.get('timestamp')
    temperature_c = data.get('temperature_c')
    device_id = data.get('device_id')
    
    # Validate required sensor fields
    missing_fields = []
    if timestamp is None:
        missing_fields.append('timestamp')
    if temperature_c is None:
        missing_fields.append('temperature_c')
    if device_id is None:
        missing_fields.append('device_id')
    
    if missing_fields:
        logger.warning(f"Missing required sensor fields: {missing_fields}")
        return Response(
            {"error": f"Missing required fields: {', '.join(missing_fields)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate temperature_c is a number
    try:
        temperature_c = float(temperature_c)
    except (ValueError, TypeError):
        logger.warning(f"Invalid temperature_c value: {temperature_c}")
        return Response(
            {"error": "Field 'temperature_c' must be a number"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    logger.info(f"Sensor data: timestamp={timestamp}, temp={temperature_c}°C, device={device_id}")
    
    # For voice_override mode, validate command_text is present (Requirement 11.3)
    if mode == 'voice_override':
        command_text = data.get('command_text')
        if not command_text:
            logger.warning("Missing 'command_text' for voice_override mode")
            return Response(
                {"error": "Field 'command_text' is required for voice_override mode"},
                status=status.HTTP_400_BAD_REQUEST
            )
        logger.info(f"Voice command: '{command_text}'")
    
    # Check if LSTM predictor is available
    if lstm_predictor is None:
        logger.error("LSTM predictor not initialized")
        return Response(
            {"error": "Model artifacts not loaded"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Orchestrate prediction pipeline (Requirements 11.2, 11.4, 11.5)
    try:
        # Step 1: Call Weather_Client to fetch forecast (Requirement 11.4)
        logger.info("Fetching weather forecast")
        weather_forecast = fetch_weather_forecast()
        logger.info(f"Weather forecast fetched: {len(weather_forecast)} hours")
        
        # Step 2: Prepare sensor history for feature engineering
        # For now, create a minimal sensor history with current reading
        sensor_history = pd.DataFrame([{
            'timestamp': timestamp,
            'temperature_c': temperature_c,
            'humidity': weather_forecast['humidity'].iloc[0] if len(weather_forecast) > 0 else 50.0,
            'pressure_mb': weather_forecast['pressure_mb'].iloc[0] if len(weather_forecast) > 0 else 1013.0,
            'light': weather_forecast['cloud'].iloc[0] if len(weather_forecast) > 0 else 50.0
        }])
        
        # Step 3: Call Feature_Engine to build 90-feature matrix (Requirement 11.4)
        logger.info("Building feature matrix")
        feature_matrix = build_feature_matrix(sensor_history, weather_forecast)
        logger.info(f"Feature matrix built: shape {feature_matrix.shape}")
        
        # Step 4: Call LSTM_Predictor for 96 temperature predictions (Requirement 11.4)
        logger.info("Running LSTM inference")
        predictions = lstm_predictor.predict_24h(feature_matrix)
        logger.info(f"LSTM predictions generated: {len(predictions)} values")
        
        # Step 5: Prepare override data for voice_override mode (Requirement 11.3)
        override_data = None
        if mode == 'voice_override':
            from .nlp.command_parser import parse_command
            
            logger.info("Parsing voice command with NLP")
            command_result = parse_command(command_text, temperature_c)
            logger.info(f"NLP parse result: {command_result}")
            
            # Determine override temperature
            if 'absolute' in command_result:
                override_temp = command_result['absolute']
                logger.info(f"Absolute temperature override: {override_temp}°C")
            elif 'delta' in command_result and command_result['delta'] != 0:
                # Apply delta to first LSTM prediction
                override_temp = int(predictions[0]) + command_result['delta']
                # Clamp to valid range
                override_temp = max(18, min(30, override_temp))
                logger.info(f"Delta override: {command_result['delta']}°C, resulting temp: {override_temp}°C")
            else:
                # No valid override, use LSTM predictions
                logger.info("No valid override from command, using LSTM predictions")
                override_temp = None
            
            if override_temp is not None:
                override_data = {
                    'temperature': override_temp,
                    'slots': 4  # Override next 4 slots (1 hour)
                }
        
        # Step 6: Call CSV_Generator to produce schedule (Requirement 11.4)
        logger.info("Generating schedule CSV")
        schedule_csv = generate_schedule_csv(predictions, override_data)
        logger.info("Schedule CSV generated successfully")
        
        # Step 7: Return Schedule_CSV with Content-Type: text/csv (Requirement 11.5)
        return HttpResponse(
            schedule_csv,
            content_type='text/csv',
            status=200
        )
        
    except Exception as e:
        # Requirement 11.6: Log errors with timestamp and request details
        logger.error(f"Prediction pipeline failed: {e}", exc_info=True)
        return Response(
            {"error": f"Prediction pipeline failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


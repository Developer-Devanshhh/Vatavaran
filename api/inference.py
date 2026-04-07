"""
LSTM Inference Module for Vatavaran Climate Control System

This module provides the LSTMPredictor class that loads model artifacts
and generates temperature predictions for the next 24 hours (96 15-minute slots).

Requirements: 7.1, 15.1, 15.2, 15.3, 15.4
"""

import os
import logging
from pathlib import Path
import numpy as np
import joblib
import pickle
from tensorflow import keras

logger = logging.getLogger(__name__)


class LSTMPredictor:
    """
    LSTM-based temperature predictor that loads model artifacts at initialization
    and provides inference capabilities for 24-hour temperature predictions.
    
    Validates all model artifacts on startup and refuses to initialize if any
    artifact is missing or invalid.
    """
    
    def __init__(self, model_dir=None):
        """
        Initialize the LSTM predictor by loading all model artifacts.
        
        Args:
            model_dir: Directory containing model artifacts. If None, uses workspace root.
        
        Raises:
            FileNotFoundError: If any model artifact is missing
            ValueError: If model artifacts are invalid or incompatible
            Exception: If model loading fails for any reason
        """
        # Determine model directory
        if model_dir is None:
            from django.conf import settings
            model_dir = getattr(settings, 'MODEL_DIR', os.getcwd())
        
        self.model_dir = Path(model_dir)
        logger.info(f"Initializing LSTMPredictor with model_dir: {self.model_dir}")
        
        # Define artifact paths
        self.lstm_model_path = self.model_dir / 'lstm_model.h5'
        self.scaler_features_path = self.model_dir / 'scaler_features.pkl'
        self.scaler_target_path = self.model_dir / 'scaler_target.pkl'
        self.model_config_path = self.model_dir / 'model_config.pkl'
        
        # Load all artifacts
        try:
            self._load_and_validate_artifacts()
            logger.info("LSTMPredictor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LSTMPredictor: {e}")
            raise
    
    def _load_and_validate_artifacts(self):
        """
        Load all four model artifacts and validate their compatibility.
        
        Requirement 15.1: Load all Model_Artifacts into memory
        Requirement 15.2: Validate model_config.pkl contains required fields
        Requirement 15.3: Validate scaler compatibility with model
        Requirement 15.4: Refuse to start if artifacts fail to load
        
        Raises:
            FileNotFoundError: If any artifact file is missing
            ValueError: If artifacts are invalid or incompatible
        """
        # Check all files exist
        missing_files = []
        for path in [self.lstm_model_path, self.scaler_features_path, 
                     self.scaler_target_path, self.model_config_path]:
            if not path.exists():
                missing_files.append(str(path))
        
        if missing_files:
            error_msg = f"Missing model artifacts: {', '.join(missing_files)}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Load model_config.pkl first (needed for validation)
        logger.info(f"Loading model config from {self.model_config_path}")
        try:
            with open(self.model_config_path, 'rb') as f:
                self.model_config = pickle.load(f)
        except Exception as e:
            error_msg = f"Failed to load model_config.pkl: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate model_config contains required fields
        # Note: The actual config uses 'feature_columns' not 'feature_names'
        required_fields = ['feature_columns', 'sequence_length']
        missing_fields = [field for field in required_fields if field not in self.model_config]
        
        if missing_fields:
            error_msg = f"model_config.pkl missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Store config values for easy access
        self.feature_names = self.model_config['feature_columns']
        self.sequence_length = self.model_config['sequence_length']
        self.prediction_horizon = self.model_config.get('prediction_horizon', 1)
        
        logger.info(f"Model config loaded: {len(self.feature_names)} features, "
                   f"sequence_length={self.sequence_length}, "
                   f"prediction_horizon={self.prediction_horizon}")
        
        # Load scaler_features.pkl
        logger.info(f"Loading feature scaler from {self.scaler_features_path}")
        try:
            self.scaler_features = joblib.load(self.scaler_features_path)
        except Exception as e:
            error_msg = f"Failed to load scaler_features.pkl: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Load scaler_target.pkl
        logger.info(f"Loading target scaler from {self.scaler_target_path}")
        try:
            self.scaler_target = joblib.load(self.scaler_target_path)
        except Exception as e:
            error_msg = f"Failed to load scaler_target.pkl: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate scaler compatibility with model
        expected_n_features = len(self.feature_names)
        if hasattr(self.scaler_features, 'n_features_in_'):
            actual_n_features = self.scaler_features.n_features_in_
            if actual_n_features != expected_n_features:
                error_msg = (f"Scaler feature count mismatch: scaler expects {actual_n_features} "
                           f"features but model config has {expected_n_features}")
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        if hasattr(self.scaler_target, 'n_features_in_'):
            if self.scaler_target.n_features_in_ != 1:
                error_msg = f"Target scaler expects {self.scaler_target.n_features_in_} features, expected 1"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        logger.info(f"Scalers validated: feature_scaler={type(self.scaler_features).__name__}, "
                   f"target_scaler={type(self.scaler_target).__name__}")
        
        # Load LSTM model
        logger.info(f"Loading LSTM model from {self.lstm_model_path}")
        try:
            # Load with compile=False to avoid deserialization issues with metrics/loss
            # The model will be used for inference only, so compilation is not needed
            self.model = keras.models.load_model(self.lstm_model_path, compile=False)
            logger.info(f"LSTM model loaded successfully")
        except Exception as e:
            error_msg = f"Failed to load lstm_model.h5: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def predict_24h(self, feature_matrix):
        """
        Generate 96 temperature predictions for the next 24 hours.
        
        Args:
            feature_matrix: numpy array of shape (96, n_features) containing
                          engineered features for each 15-minute slot
        
        Returns:
            numpy array of shape (96,) containing predicted temperatures in Celsius
        
        Raises:
            ValueError: If feature_matrix has incorrect shape or features
            Exception: If inference fails
        
        Requirements: 7.2, 7.3, 7.4, 7.5
        """
        logger.info(f"Starting prediction for feature_matrix shape: {feature_matrix.shape}")
        
        # Validate input shape
        if len(feature_matrix.shape) != 2:
            raise ValueError(f"feature_matrix must be 2D, got shape {feature_matrix.shape}")
        
        n_samples, n_features = feature_matrix.shape
        expected_n_features = len(self.feature_names)
        
        if n_features != expected_n_features:
            raise ValueError(f"feature_matrix has {n_features} features, expected {expected_n_features}")
        
        try:
            # Scale input features using scaler_features.pkl (Requirement 7.2)
            logger.info("Scaling input features")
            scaled_features = self.scaler_features.transform(feature_matrix)
            
            # Run inference using lstm_model.h5 via TensorFlow (Requirement 7.3)
            logger.info("Running LSTM inference")
            # Note: LSTM expects shape (batch_size, sequence_length, n_features)
            # We need to reshape for sequence-based prediction
            predictions_scaled = []
            
            # For each time slot, we need to provide a sequence
            # This is a simplified approach - actual implementation may need historical data
            for i in range(n_samples):
                # Create a sequence by repeating the current features
                # In production, this should use actual historical sequences
                sequence = np.tile(scaled_features[i:i+1], (self.sequence_length, 1))
                sequence = sequence.reshape(1, self.sequence_length, n_features)
                
                # Predict
                pred = self.model.predict(sequence, verbose=0)
                predictions_scaled.append(pred[0, 0])
            
            predictions_scaled = np.array(predictions_scaled).reshape(-1, 1)
            
            # Descale predictions using scaler_target.pkl (Requirement 7.4)
            logger.info("Descaling predictions")
            predictions = self.scaler_target.inverse_transform(predictions_scaled)
            
            # Return array of 96 predicted temperatures (Requirement 7.5)
            predictions = predictions.flatten()
            logger.info(f"Prediction complete: {len(predictions)} values, "
                       f"range [{predictions.min():.1f}, {predictions.max():.1f}]°C")
            
            return predictions
            
        except Exception as e:
            # Requirement 7.6: Log errors and raise exception on inference failure
            error_msg = f"LSTM inference failed: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

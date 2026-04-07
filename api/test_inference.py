"""
Unit tests for LSTM Inference Module

Tests the LSTMPredictor class initialization, artifact loading,
validation, and prediction capabilities.

Requirements: 7.1, 15.1, 15.2, 15.3, 15.4
"""

import os
import pytest
import numpy as np
import tempfile
import shutil
from pathlib import Path
import pickle
import joblib
from unittest.mock import Mock, patch
from tensorflow import keras

from api.inference import LSTMPredictor


class TestLSTMPredictorInitialization:
    """Test LSTMPredictor initialization and artifact loading"""
    
    def test_initialization_with_valid_artifacts(self):
        """Test successful initialization when all artifacts are present and valid"""
        # Use workspace root which has the actual model artifacts
        predictor = LSTMPredictor(model_dir='.')
        
        # Verify all artifacts are loaded
        assert predictor.model is not None
        assert predictor.scaler_features is not None
        assert predictor.scaler_target is not None
        assert predictor.model_config is not None
        
        # Verify config fields
        assert 'feature_columns' in predictor.model_config
        assert 'sequence_length' in predictor.model_config
        assert predictor.feature_names is not None
        assert len(predictor.feature_names) > 0
        assert predictor.sequence_length > 0
    
    def test_initialization_fails_with_missing_lstm_model(self):
        """Test that initialization fails when lstm_model.h5 is missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only some artifacts
            config = {'feature_columns': ['temp'], 'sequence_length': 30}
            with open(os.path.join(tmpdir, 'model_config.pkl'), 'wb') as f:
                pickle.dump(config, f)
            
            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError, match="Missing model artifacts"):
                LSTMPredictor(model_dir=tmpdir)
    
    def test_initialization_fails_with_missing_scaler_features(self):
        """Test that initialization fails when scaler_features.pkl is missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only config
            config = {'feature_columns': ['temp'], 'sequence_length': 30}
            with open(os.path.join(tmpdir, 'model_config.pkl'), 'wb') as f:
                pickle.dump(config, f)
            
            # Create dummy model file
            Path(tmpdir, 'lstm_model.h5').touch()
            
            with pytest.raises(FileNotFoundError, match="Missing model artifacts"):
                LSTMPredictor(model_dir=tmpdir)
    
    def test_initialization_fails_with_missing_scaler_target(self):
        """Test that initialization fails when scaler_target.pkl is missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'feature_columns': ['temp'], 'sequence_length': 30}
            with open(os.path.join(tmpdir, 'model_config.pkl'), 'wb') as f:
                pickle.dump(config, f)
            
            Path(tmpdir, 'lstm_model.h5').touch()
            Path(tmpdir, 'scaler_features.pkl').touch()
            
            with pytest.raises(FileNotFoundError, match="Missing model artifacts"):
                LSTMPredictor(model_dir=tmpdir)
    
    def test_initialization_fails_with_missing_model_config(self):
        """Test that initialization fails when model_config.pkl is missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'lstm_model.h5').touch()
            Path(tmpdir, 'scaler_features.pkl').touch()
            Path(tmpdir, 'scaler_target.pkl').touch()
            
            with pytest.raises(FileNotFoundError, match="Missing model artifacts"):
                LSTMPredictor(model_dir=tmpdir)


class TestModelConfigValidation:
    """Test model_config.pkl validation (Requirement 15.2)"""
    
    def test_config_missing_feature_columns(self):
        """Test that initialization fails when feature_columns is missing from config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config without feature_columns
            config = {'sequence_length': 30}
            with open(os.path.join(tmpdir, 'model_config.pkl'), 'wb') as f:
                pickle.dump(config, f)
            
            # Create dummy files
            Path(tmpdir, 'lstm_model.h5').touch()
            Path(tmpdir, 'scaler_features.pkl').touch()
            Path(tmpdir, 'scaler_target.pkl').touch()
            
            with pytest.raises(ValueError, match="missing required fields.*feature_columns"):
                LSTMPredictor(model_dir=tmpdir)
    
    def test_config_missing_sequence_length(self):
        """Test that initialization fails when sequence_length is missing from config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config without sequence_length
            config = {'feature_columns': ['temp', 'humidity']}
            with open(os.path.join(tmpdir, 'model_config.pkl'), 'wb') as f:
                pickle.dump(config, f)
            
            Path(tmpdir, 'lstm_model.h5').touch()
            Path(tmpdir, 'scaler_features.pkl').touch()
            Path(tmpdir, 'scaler_target.pkl').touch()
            
            with pytest.raises(ValueError, match="missing required fields.*sequence_length"):
                LSTMPredictor(model_dir=tmpdir)
    
    def test_config_with_all_required_fields(self):
        """Test that config validation passes with all required fields"""
        predictor = LSTMPredictor(model_dir='.')
        
        # Verify required fields are present
        assert hasattr(predictor, 'feature_names')
        assert hasattr(predictor, 'sequence_length')
        assert isinstance(predictor.feature_names, list)
        assert isinstance(predictor.sequence_length, int)


class TestScalerCompatibility:
    """Test scaler compatibility validation (Requirement 15.3)"""
    
    def test_scaler_features_loaded_correctly(self):
        """Test that scaler_features is loaded and has correct properties"""
        predictor = LSTMPredictor(model_dir='.')
        
        # Verify scaler is loaded
        assert predictor.scaler_features is not None
        assert hasattr(predictor.scaler_features, 'transform')
        
        # Verify feature count matches config
        if hasattr(predictor.scaler_features, 'n_features_in_'):
            assert predictor.scaler_features.n_features_in_ == len(predictor.feature_names)
    
    def test_scaler_target_loaded_correctly(self):
        """Test that scaler_target is loaded and expects 1 feature"""
        predictor = LSTMPredictor(model_dir='.')
        
        # Verify scaler is loaded
        assert predictor.scaler_target is not None
        assert hasattr(predictor.scaler_target, 'transform')
        assert hasattr(predictor.scaler_target, 'inverse_transform')
        
        # Verify target scaler expects 1 feature
        if hasattr(predictor.scaler_target, 'n_features_in_'):
            assert predictor.scaler_target.n_features_in_ == 1


class TestPrediction:
    """Test prediction functionality"""
    
    def test_predict_24h_with_valid_input(self):
        """Test prediction with valid feature matrix"""
        predictor = LSTMPredictor(model_dir='.')
        
        # Create dummy feature matrix (96 samples, 90 features)
        n_features = len(predictor.feature_names)
        feature_matrix = np.random.randn(96, n_features)
        
        # Run prediction
        predictions = predictor.predict_24h(feature_matrix)
        
        # Verify output
        assert predictions is not None
        assert len(predictions) == 96
        assert isinstance(predictions, np.ndarray)
        assert predictions.dtype in [np.float32, np.float64]
    
    def test_predict_24h_fails_with_wrong_feature_count(self):
        """Test that prediction fails when feature count doesn't match"""
        predictor = LSTMPredictor(model_dir='.')
        
        # Create feature matrix with wrong number of features
        wrong_feature_matrix = np.random.randn(96, 50)  # Wrong: should be 90
        
        with pytest.raises(ValueError, match="features, expected"):
            predictor.predict_24h(wrong_feature_matrix)
    
    def test_predict_24h_fails_with_1d_input(self):
        """Test that prediction fails with 1D input"""
        predictor = LSTMPredictor(model_dir='.')
        
        # Create 1D array
        wrong_input = np.random.randn(96)
        
        with pytest.raises(ValueError, match="must be 2D"):
            predictor.predict_24h(wrong_input)


class TestArtifactReuse:
    """Test that artifacts are loaded once and reused (Requirement 15.5)"""
    
    def test_artifacts_loaded_once_at_initialization(self):
        """Test that artifacts are loaded during initialization, not per request"""
        predictor = LSTMPredictor(model_dir='.')
        
        # Store references to loaded artifacts
        model_ref = predictor.model
        scaler_features_ref = predictor.scaler_features
        scaler_target_ref = predictor.scaler_target
        config_ref = predictor.model_config
        
        # Run multiple predictions
        n_features = len(predictor.feature_names)
        feature_matrix = np.random.randn(96, n_features)
        
        predictor.predict_24h(feature_matrix)
        predictor.predict_24h(feature_matrix)
        
        # Verify same objects are used (not reloaded)
        assert predictor.model is model_ref
        assert predictor.scaler_features is scaler_features_ref
        assert predictor.scaler_target is scaler_target_ref
        assert predictor.model_config is config_ref

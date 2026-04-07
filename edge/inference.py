"""
LSTM Inference Module for Vatavaran Edge (Raspberry Pi 4B)

Replaces the cloud-based api/inference.py:
  - Uses tflite_runtime instead of full TensorFlow (~400 MB RAM saved)
  - Loads .tflite model instead of .h5 (~4x smaller)
  - Same predict_24h() interface for drop-in compatibility

Requirements: 7.1, 15.1, 15.2, 15.3, 15.4
"""

import os
import logging
from pathlib import Path
import numpy as np
import joblib
import pickle

logger = logging.getLogger(__name__)


class LSTMPredictor:
    """
    LSTM-based temperature predictor optimised for Raspberry Pi 4B.

    Uses TFLite runtime for minimal memory footprint (~80 MB vs ~500 MB
    for full TensorFlow). Provides the same predict_24h() interface as
    the cloud version.
    """

    def __init__(self, model_dir=None):
        """
        Initialize the LSTM predictor by loading all model artefacts.

        Args:
            model_dir: Directory containing model artefacts.
                       Defaults to './models' relative to project root.
        """
        if model_dir is None:
            # Default: look in the project root's models/ or current dir
            model_dir = os.environ.get('MODEL_DIR', '.')

        self.model_dir = Path(model_dir)
        logger.info(f"Initializing Edge LSTMPredictor with model_dir: {self.model_dir}")

        # Define artefact paths (same file names as cloud version)
        self.tflite_model_path = self.model_dir / 'lstm_model.tflite'
        self.h5_model_path = self.model_dir / 'lstm_model.h5'
        self.scaler_features_path = self.model_dir / 'scaler_features.pkl'
        self.scaler_target_path = self.model_dir / 'scaler_target.pkl'
        self.model_config_path = self.model_dir / 'model_config.pkl'

        try:
            self._load_and_validate_artefacts()
            logger.info("Edge LSTMPredictor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Edge LSTMPredictor: {e}")
            raise

    def _load_and_validate_artefacts(self):
        """Load all four model artefacts and validate compatibility."""

        # ── model_config.pkl ──────────────────────────────────────
        if not self.model_config_path.exists():
            raise FileNotFoundError(f"Missing: {self.model_config_path}")

        with open(self.model_config_path, 'rb') as f:
            self.model_config = pickle.load(f)

        required_fields = ['feature_columns', 'sequence_length']
        missing = [f for f in required_fields if f not in self.model_config]
        if missing:
            raise ValueError(f"model_config.pkl missing: {', '.join(missing)}")

        self.feature_names = self.model_config['feature_columns']
        self.sequence_length = self.model_config['sequence_length']
        self.prediction_horizon = self.model_config.get('prediction_horizon', 1)

        logger.info(f"Config: {len(self.feature_names)} features, "
                    f"seq_len={self.sequence_length}")

        # ── scalers ───────────────────────────────────────────────
        for path, label in [(self.scaler_features_path, 'feature'),
                            (self.scaler_target_path, 'target')]:
            if not path.exists():
                raise FileNotFoundError(f"Missing: {path}")

        self.scaler_features = joblib.load(self.scaler_features_path)
        self.scaler_target = joblib.load(self.scaler_target_path)

        # Validate scaler dimensions
        if hasattr(self.scaler_features, 'n_features_in_'):
            if self.scaler_features.n_features_in_ != len(self.feature_names):
                raise ValueError(
                    f"Scaler expects {self.scaler_features.n_features_in_} features, "
                    f"config has {len(self.feature_names)}"
                )
        logger.info("Scalers loaded and validated")

        # ── TFLite model ──────────────────────────────────────────
        # Prefer .tflite; fall back to .h5 using full TF (slower)
        if self.tflite_model_path.exists():
            self._load_tflite_model()
            self._use_tflite = True
        elif self.h5_model_path.exists():
            logger.warning(
                "TFLite model not found — falling back to .h5 via full TensorFlow. "
                "Run convert_model.py to create the optimised .tflite file."
            )
            self._load_h5_model()
            self._use_tflite = False
        else:
            raise FileNotFoundError(
                f"No model found. Expected {self.tflite_model_path} or {self.h5_model_path}"
            )

    def _load_tflite_model(self):
        """Load .tflite model using the lightweight runtime."""
        try:
            import tflite_runtime.interpreter as tflite
        except ImportError:
            # Some installations use the full TF's lite interpreter
            import tensorflow.lite as tflite_mod
            tflite = tflite_mod

        logger.info(f"Loading TFLite model from {self.tflite_model_path}")
        self.interpreter = tflite.Interpreter(model_path=str(self.tflite_model_path))
        self.interpreter.allocate_tensors()

        self._input_details = self.interpreter.get_input_details()
        self._output_details = self.interpreter.get_output_details()

        expected_shape = (1, self.sequence_length, len(self.feature_names))
        actual_shape = tuple(self._input_details[0]['shape'])
        logger.info(f"TFLite model loaded — input shape: {actual_shape}")

    def _load_h5_model(self):
        """Fallback: load .h5 model via full TensorFlow/Keras."""
        from tensorflow import keras

        logger.info(f"Loading H5 model from {self.h5_model_path}")
        self.keras_model = keras.models.load_model(
            str(self.h5_model_path), compile=False
        )
        logger.info("H5 model loaded (fallback mode)")

    # ── Inference ─────────────────────────────────────────────────

    def _predict_single(self, scaled_row):
        """
        Run a single inference for one time slot.

        Args:
            scaled_row: 1-D array of shape (n_features,)

        Returns:
            Scalar — raw (scaled) prediction
        """
        seq = np.tile(scaled_row, (self.sequence_length, 1))
        batch = seq.reshape(1, self.sequence_length, len(self.feature_names))

        if self._use_tflite:
            batch = batch.astype(np.float32)
            self.interpreter.set_tensor(
                self._input_details[0]['index'], batch
            )
            self.interpreter.invoke()
            pred = self.interpreter.get_tensor(
                self._output_details[0]['index']
            )
            return pred[0, 0]
        else:
            pred = self.keras_model.predict(batch, verbose=0)
            return pred[0, 0]

    def predict_24h(self, feature_matrix):
        """
        Generate 96 temperature predictions for the next 24 hours.

        Args:
            feature_matrix: numpy array (96, n_features)

        Returns:
            numpy array (96,) — predicted temperatures in °C
        """
        logger.info(f"Starting 24h prediction — matrix shape: {feature_matrix.shape}")

        if len(feature_matrix.shape) != 2:
            raise ValueError(f"Expected 2-D matrix, got {feature_matrix.shape}")

        n_samples, n_features = feature_matrix.shape
        expected = len(self.feature_names)
        if n_features != expected:
            raise ValueError(f"Got {n_features} features, expected {expected}")

        try:
            # Scale features
            scaled = self.scaler_features.transform(feature_matrix)

            # Run 96 sequential inferences
            preds_scaled = np.array([
                self._predict_single(scaled[i]) for i in range(n_samples)
            ]).reshape(-1, 1)

            # Inverse-scale to °C
            preds = self.scaler_target.inverse_transform(preds_scaled).flatten()
            logger.info(
                f"Predictions complete: {len(preds)} values, "
                f"range [{preds.min():.1f}, {preds.max():.1f}]°C"
            )
            return preds

        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise

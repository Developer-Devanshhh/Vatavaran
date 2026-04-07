#!/usr/bin/env python3
"""
Convert Vatavaran LSTM model from .h5 (Keras) to .tflite (TFLite)

Run this on a development PC (not on the RPi) since it needs full TensorFlow.

Usage:
    python convert_model.py
    python convert_model.py --input lstm_model.h5 --output models/lstm_model.tflite
"""

import argparse
import os
from pathlib import Path


def convert(input_path, output_path, quantize='float16'):
    """
    Convert a Keras .h5 model to TFLite format.

    Args:
        input_path: Path to .h5 model
        output_path: Output .tflite path
        quantize: 'float16' (recommended for ARM), 'int8', or 'none'
    """
    import tensorflow as tf

    print(f"Loading model: {input_path}")
    model = tf.keras.models.load_model(input_path, compile=False)
    model.summary()

    print(f"\nConverting to TFLite (quantization: {quantize})...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    if quantize == 'float16':
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]
    elif quantize == 'int8':
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
    # else: no quantization

    tflite_model = converter.convert()

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(tflite_model)

    h5_size = os.path.getsize(input_path) / 1024
    tflite_size = len(tflite_model) / 1024
    ratio = h5_size / tflite_size if tflite_size > 0 else 0

    print(f"\n✓ Conversion complete!")
    print(f"  Input:  {input_path} ({h5_size:.1f} KB)")
    print(f"  Output: {output_path} ({tflite_size:.1f} KB)")
    print(f"  Compression: {ratio:.1f}x smaller")
    print(f"\nCopy {output_path} to your Raspberry Pi.")


def main():
    parser = argparse.ArgumentParser(
        description='Convert Vatavaran LSTM .h5 model to .tflite'
    )
    parser.add_argument(
        '--input', '-i', type=str, default='lstm_model.h5',
        help='Path to .h5 model (default: lstm_model.h5)'
    )
    parser.add_argument(
        '--output', '-o', type=str, default='lstm_model.tflite',
        help='Output .tflite path (default: lstm_model.tflite)'
    )
    parser.add_argument(
        '--quantize', '-q', type=str, default='float16',
        choices=['float16', 'int8', 'none'],
        help='Quantization type (default: float16, best for ARM)'
    )

    args = parser.parse_args()
    convert(args.input, args.output, args.quantize)


if __name__ == '__main__':
    main()

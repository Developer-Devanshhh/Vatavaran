#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# Vatavaran Edge — Raspberry Pi 4B Setup Script
# Run this once after cloning the repo on your Pi.
#
# Usage:
#   chmod +x setup_rpi.sh
#   ./setup_rpi.sh
# ─────────────────────────────────────────────────────────────────

set -e

echo "╔══════════════════════════════════════════════╗"
echo "║   Vatavaran Edge — RPi 4B Setup              ║"
echo "╚══════════════════════════════════════════════╝"

# ── 1. System packages ───────────────────────────────────────────
echo ""
echo "[1/7] Installing system packages..."
sudo apt update
sudo apt install -y python3-venv python3-pip i2c-tools \
    libopenblas-dev libhdf5-dev libjpeg-dev \
    portaudio19-dev python3-pyaudio \
    libgpiod2

# ── 2. Enable I2C and SPI ────────────────────────────────────────
echo ""
echo "[2/7] Checking I2C/SPI interfaces..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt 2>/dev/null; then
    echo "  → Enabling I2C..."
    sudo raspi-config nonint do_i2c 0
fi
if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null; then
    echo "  → Enabling SPI..."
    sudo raspi-config nonint do_spi 0
fi

# ── 3. Python virtual environment ────────────────────────────────
echo ""
echo "[3/7] Creating Python virtual environment..."
VENV_DIR="$(pwd)/venv"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --upgrade pip

# ── 4. Install Python dependencies ───────────────────────────────
echo ""
echo "[4/7] Installing Python dependencies..."
pip install -r requirements_rpi.txt

# ── 5. Download Vosk speech model ────────────────────────────────
echo ""
echo "[5/7] Downloading Vosk speech recognition model..."
VOSK_MODEL="vosk-model-small-en-in-0.4"
if [ ! -d "$VOSK_MODEL" ]; then
    echo "  Downloading $VOSK_MODEL..."
    wget -q "https://alphacephei.com/vosk/models/$VOSK_MODEL.zip"
    unzip -q "$VOSK_MODEL.zip"
    rm "$VOSK_MODEL.zip"
    echo "  ✓ Model downloaded"
else
    echo "  ✓ Model already exists"
fi

# ── 6. Convert model (if .tflite doesn't exist) ──────────────────
echo ""
echo "[6/7] Checking model files..."
if [ -f "lstm_model.tflite" ]; then
    echo "  ✓ TFLite model found"
elif [ -f "lstm_model.h5" ]; then
    echo "  ⚠ Only .h5 model found. The edge engine will use TF fallback."
    echo "  → For best performance, run convert_model.py on a PC and copy lstm_model.tflite here."
else
    echo "  ✗ No model file found! Make sure lstm_model.h5 or lstm_model.tflite is in this directory."
fi

# Check scalers
for f in scaler_features.pkl scaler_target.pkl model_config.pkl; do
    if [ -f "$f" ]; then
        echo "  ✓ $f found"
    else
        echo "  ✗ $f NOT FOUND — model will not work!"
    fi
done

# ── 7. Install systemd services ──────────────────────────────────
echo ""
echo "[7/7] Installing systemd services..."
sudo cp systemd/vatavaran-orchestrator.service /etc/systemd/system/
sudo cp systemd/vatavaran-ir-blaster.service /etc/systemd/system/

# Update WorkingDirectory in service files to current directory
sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$(pwd)|" /etc/systemd/system/vatavaran-orchestrator.service
sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$(pwd)|" /etc/systemd/system/vatavaran-ir-blaster.service

# Update ExecStart python path
sudo sed -i "s|ExecStart=.*/python|ExecStart=$VENV_DIR/bin/python|" /etc/systemd/system/vatavaran-orchestrator.service
sudo sed -i "s|ExecStart=.*/python|ExecStart=$VENV_DIR/bin/python|" /etc/systemd/system/vatavaran-ir-blaster.service

sudo systemctl daemon-reload

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✓ Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Edit edge/config.json — set your WeatherAPI key"
echo "  2. Wire sensors: DHT22 (GPIO4), BMP280+BH1750 (I2C)"
echo "  3. Test: python -m edge.orchestrator --dry-run --once"
echo "  4. Enable auto-start:"
echo "     sudo systemctl enable vatavaran-orchestrator"
echo "     sudo systemctl enable vatavaran-ir-blaster"
echo "     sudo systemctl start vatavaran-orchestrator"
echo "═══════════════════════════════════════════════"

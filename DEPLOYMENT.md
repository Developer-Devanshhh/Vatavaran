# Vatavaran Climate Control System - Deployment Guide

## EC2 Deployment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export WEATHERAPI_KEY="6415f4c56b1d424384860604242303"
export DJANGO_SECRET_KEY="your-production-secret-key"
export DEBUG="False"
export ALLOWED_HOSTS="your-ec2-ip,your-domain.com"
export MODEL_DIR="/path/to/models"
```

### 3. Run Django Server

Development:
```bash
python manage.py runserver 0.0.0.0:8000
```

Production (with Gunicorn):
```bash
gunicorn vatavaran_server.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### 4. Test Endpoint

```bash
python test_ec2_endpoint.py
```

## Raspberry Pi Deployment

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv portaudio19-dev
```

### 2. Create Virtual Environment

```bash
mkdir -p /home/pi/vatavaran
cd /home/pi/vatavaran
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install requests vosk pyaudio
```

### 4. Download Vosk Model

```bash
mkdir -p /home/pi/vatavaran
cd /home/pi/vatavaran
wget https://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip
unzip vosk-model-small-en-in-0.4.zip
```

### 5. Configure EC2 Endpoint

Edit `rpi/config.json`:
```json
{
  "ec2_endpoint": "http://your-ec2-ip:8000/api/predict/",
  "timeout": 30
}
```

### 6. Configure IR Codes

Edit `rpi/ir_codes.json` with your AC's IR codes.

### 7. Set Up Cron Job

```bash
cd /home/pi/vatavaran/rpi
chmod +x setup_cron.sh
./setup_cron.sh
```

### 8. Start IR Blaster

```bash
python rpi/ir_blaster.py
```

## Testing

### Test Scheduled Mode
```bash
python rpi/pipeline_client.py --mode scheduled
```

### Test Voice Override Mode
```bash
python rpi/pipeline_client.py --mode voice_override --command "it's too hot"
```

### Test STT Module
```bash
python rpi/stt.py
```

## Monitoring

### Check Cron Logs
```bash
tail -f /home/pi/vatavaran/logs/cron.log
```

### Check Schedule File
```bash
cat /home/pi/vatavaran/schedule.csv
```

## Troubleshooting

### EC2 Connection Issues
- Check EC2 security group allows inbound on port 8000
- Verify EC2 endpoint URL in config.json
- Check network connectivity: `ping your-ec2-ip`

### Sensor Issues
- Check sensor wiring
- Verify sensor library is installed
- Check sensor permissions

### IR Blaster Issues
- Verify IR codes in ir_codes.json
- Check IR LED wiring
- Test IR transmission manually

### Vosk Issues
- Ensure model is downloaded and extracted
- Check microphone permissions
- Test microphone: `arecord -d 5 test.wav`

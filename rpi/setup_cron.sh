#!/bin/bash
# Setup cron job for Vatavaran scheduled execution
# Requirement 3.1: Execute pipeline_client.py every 15 minutes

echo "Setting up Vatavaran cron job..."

# Cron entry
CRON_ENTRY="*/15 * * * * /home/pi/vatavaran/venv/bin/python /home/pi/vatavaran/rpi/pipeline_client.py --mode scheduled >> /home/pi/vatavaran/logs/cron.log 2>&1"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "pipeline_client.py"; then
    echo "Cron job already exists"
else
    # Add cron entry
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "Cron job added successfully"
fi

# Display current crontab
echo ""
echo "Current crontab:"
crontab -l

echo ""
echo "Cron job will execute every 15 minutes"
echo "Logs will be written to: /home/pi/vatavaran/logs/cron.log"

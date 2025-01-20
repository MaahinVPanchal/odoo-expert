#!/bin/bash
set -e

# Create necessary directories and files
mkdir -p /app/logs
touch /app/logs/cron.log
chmod 0644 /app/logs/cron.log

if [ "$1" = "updater" ]; then
    echo "Starting cron service..."
    service cron start || true
    
    echo "Starting updater service..."
    # Run initial update and process files
    ./pull_rawdata.sh
    
    # Force process all files on first run
    echo "Processing all files..."
    python main.py process-raw --raw-dir ./raw_data --output-dir ./markdown --process-docs
    
    # Then run the regular check-updates
    python main.py check-updates
    
    # Keep container running and monitor logs
    exec tail -f /app/logs/cron.log
else
    # For UI and API services, execute the command directly
    exec "$@"
fi
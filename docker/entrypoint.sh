#!/bin/bash
set -e

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

if [ "$1" = "updater" ]; then
    log "Starting updater service..."
    
    # Initial setup
    log "Creating necessary directories..."
    mkdir -p /app/logs
    chmod -R 755 /app/logs
    
    # Start cron service
    log "Starting cron service..."
    service cron start || true
    
    # Run initial update
    log "Starting initial documentation pull..."
    ./pull_rawdata.sh 2>&1 | while IFS= read -r line; do
        log "[pull_rawdata] $line"
    done
    
    # Process initial files
    log "Processing all documentation files..."
    python main.py process-raw --raw-dir ./raw_data --output-dir ./markdown --process-docs 2>&1 | while IFS= read -r line; do
        log "[process-raw] $line"
    done
    
    # Run initial check-updates
    log "Running initial update check..."
    python main.py check-updates 2>&1 | while IFS= read -r line; do
        log "[check-updates] $line"
    done
    
    # Monitor logs but with proper timestamp and labeling
    log "Entering monitoring mode..."
    tail -f /app/logs/cron.log | while read line; do
        log "[cron] $line"
    done
else
    # For UI and API services, execute the command directly
    exec "$@"
fi
#!/bin/bash
# Restore script for CSC Job Scraper data

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found."
    exit 1
fi

echo "Extracting backup..."
mkdir -p temp_restore
tar -xzf "$BACKUP_FILE" -C temp_restore

# The extracted folder is the timestamp string
EXTRACTED_DIR=$(ls temp_restore | head -n 1)

echo "Restoring database..."
if [ -f "temp_restore/$EXTRACTED_DIR/csc_jobs.db" ]; then
    mkdir -p data
    cp "temp_restore/$EXTRACTED_DIR/csc_jobs.db" data/
fi

echo "Restoring configuration..."
if [ -f "temp_restore/$EXTRACTED_DIR/config.yaml" ]; then
    mkdir -p config
    cp "temp_restore/$EXTRACTED_DIR/config.yaml" config/
fi
if [ -f "temp_restore/$EXTRACTED_DIR/.env" ]; then
    cp "temp_restore/$EXTRACTED_DIR/.env" .
fi

rm -rf temp_restore
echo "Restore complete! Please restart the application."

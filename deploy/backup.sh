#!/bin/bash
# Backup script for CSC Job Scraper data

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backing up SQLite database..."
if [ -f data/csc_jobs.db ]; then
    cp data/csc_jobs.db "$BACKUP_DIR/"
fi

echo "Backing up configuration..."
if [ -f config/config.yaml ]; then
    cp config/config.yaml "$BACKUP_DIR/"
fi
if [ -f .env ]; then
    cp .env "$BACKUP_DIR/"
fi

# Optional: compress backup
tar -czf "${BACKUP_DIR}.tar.gz" -C backups "$(basename $BACKUP_DIR)"
rm -rf "$BACKUP_DIR"

echo "Backup complete: ${BACKUP_DIR}.tar.gz"

#!/bin/bash
set -e

echo "=========================================="
echo "CSC Bicol Job Scraper - Setup Script"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not installed."
    exit 1
fi

# Create directories
echo "Creating required directories..."
mkdir -p data logs config

# Create default .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp config/.env.example .env 2>/dev/null || touch .env
    echo "Please edit the .env file with your Telegram/Discord tokens before starting."
fi

# Build and start container
echo "Building and starting Docker container..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d --build
else
    docker compose up -d --build
fi

echo "=========================================="
echo "Setup complete! The scraper is now running in the background."
echo "To view logs, run: docker logs -f csc_scraper"
echo "=========================================="

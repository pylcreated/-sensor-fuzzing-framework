#!/usr/bin/env bash
# Sensor Fuzzing Framework - Quick Setup Script (Linux/macOS)
# Usage: ./setup_and_run.sh [zip_file_path]

set -e

echo "Sensor Fuzzing Framework - Quick Setup"
echo "======================================="

if [ $# -eq 0 ]; then
    echo "Please provide the project zip file path."
    echo "Usage: $0 <sensor-fuzzing-framework.zip>"
    exit 1
fi

ZIP_FILE="$1"

if [ ! -f "$ZIP_FILE" ]; then
    echo "File not found: $ZIP_FILE"
    exit 1
fi

echo "Extracting project archive..."
unzip -q "$ZIP_FILE"
PROJECT_DIR=$(basename "$ZIP_FILE" .zip)
cd "$PROJECT_DIR"

echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Validating installation..."
python -c "import sensor_fuzz; print('Module import succeeded')"

echo "Starting framework..."
python -m sensor_fuzz

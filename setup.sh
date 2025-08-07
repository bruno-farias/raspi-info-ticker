#!/bin/bash

# Setup script for Raspberry Pi
echo "Setting up Python virtual environment..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

echo "Setup complete!"
echo "To activate the environment, run: source venv/bin/activate"
echo "To run the application: python main.py"
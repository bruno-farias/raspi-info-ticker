#!/bin/bash

# Setup script for Raspberry Pi
echo "Setting up currency ticker on Raspberry Pi..."

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi"
fi

# Enable SPI interface (needed for e-paper display)
echo "Checking SPI interface..."
if ! lsmod | grep -q spi_bcm; then
    echo "SPI might not be enabled. Please run 'sudo raspi-config' and enable SPI in Interface Options"
fi

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-dev python3-setuptools

# Install system packages needed for cairosvg (SVG support) and numpy
echo "Installing SVG support and math libraries..."
sudo apt-get install -y libcairo2-dev libgirepository1.0-dev pkg-config

# Install system packages for numpy (math/array processing)
echo "Installing numpy dependencies..."
sudo apt-get install -y python3-numpy python3-scipy libatlas-base-dev gfortran

# Install Python dependencies system-wide (needed for GPIO access)
echo "Installing Python dependencies system-wide..."
sudo pip3 install --break-system-packages --upgrade pip
sudo pip3 install --break-system-packages -r requirements.txt

# Copy Waveshare e-Paper library if available
if [ -d "../e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd" ]; then
    echo "Copying Waveshare e-Paper library..."
    cp -r ../e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd ./
    cp -r ../e-Paper/RaspberryPi_JetsonNano/python/pic ./
    echo "Waveshare library copied successfully"
else
    echo "Waveshare e-Paper library not found at ../e-Paper/"
    echo "Please manually copy the waveshare_epd folder to this directory"
    echo "Or clone it: git clone https://github.com/waveshareteam/e-Paper.git"
fi

# Copy .env.example to .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env and add your FREE_CURRENCY_API_KEY"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your FREE_CURRENCY_API_KEY and CRYPTO_API_KEY"
echo "2. If SPI warning appeared, enable SPI: sudo raspi-config -> Interface Options -> SPI -> Enable"
echo "3. To run the application: ./run.sh"
echo "   (or directly: sudo python3 main.py)"
echo ""
echo "Features:"
echo "- Configurable screen order and caching in .env"
echo "- SVG logo support for Bitcoin screen"  
echo "- The app will run in simulation mode if e-paper display is not connected"
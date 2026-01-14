#!/bin/bash

# Quick fix script for installation issues on Raspberry Pi Zero W

set -e

echo "================================================"
echo "  Raspi Info Ticker - Installation Fix"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check network connectivity
echo -e "${GREEN}Checking network connectivity...${NC}"
if ping -c 1 google.com &>/dev/null; then
    echo "✓ Internet connection OK"
else
    echo -e "${RED}✗ No internet connection${NC}"
    echo "Please check your network settings"
    exit 1
fi

# Step 2: Try different methods to clone Waveshare library
echo -e "${GREEN}Installing Waveshare e-Paper library...${NC}"

if [ ! -d "$HOME/e-Paper" ]; then
    cd $HOME

    # Method 1: Try HTTPS with different timeouts
    echo "Attempting to clone via HTTPS..."
    if git clone --depth 1 https://github.com/waveshare/e-Paper.git 2>/dev/null; then
        echo "✓ Successfully cloned via HTTPS"
    else
        echo "HTTPS failed, trying alternative methods..."

        # Method 2: Try using curl to download as ZIP
        echo "Attempting to download as ZIP..."
        if curl -L -o e-Paper.zip https://github.com/waveshare/e-Paper/archive/refs/heads/master.zip 2>/dev/null; then
            unzip -q e-Paper.zip
            mv e-Paper-master e-Paper
            rm e-Paper.zip
            echo "✓ Successfully downloaded and extracted ZIP"
        else
            # Method 3: Try wget as fallback
            echo "Attempting with wget..."
            if wget -O e-Paper.zip https://github.com/waveshare/e-Paper/archive/refs/heads/master.zip 2>/dev/null; then
                unzip -q e-Paper.zip
                mv e-Paper-master e-Paper
                rm e-Paper.zip
                echo "✓ Successfully downloaded with wget"
            else
                echo -e "${YELLOW}Warning: Could not download Waveshare library${NC}"
                echo "You can manually download it later from:"
                echo "https://github.com/waveshare/e-Paper"
            fi
        fi
    fi

    # Install if directory exists
    if [ -d "$HOME/e-Paper" ]; then
        cd e-Paper/RaspberryPi_JetsonNano/python
        sudo python3 setup.py install
        cd $HOME
        echo "✓ Waveshare library installed"
    fi
else
    echo "Waveshare library already exists"
fi

# Step 3: Continue with project setup
PROJECT_DIR="$HOME/raspi-info-ticker"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}Project directory not found at $PROJECT_DIR${NC}"
    echo "Creating directory..."
    mkdir -p "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# Step 4: Create virtual environment
echo -e "${GREEN}Setting up Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv --system-site-packages
    echo "✓ Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Step 5: Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip wheel setuptools

# Step 6: Install Python packages
echo -e "${GREEN}Installing Python packages...${NC}"
if [ -f "requirements-pi-zero.txt" ]; then
    pip install --no-cache-dir -r requirements-pi-zero.txt
    echo "✓ Python packages installed"
else
    echo -e "${YELLOW}requirements-pi-zero.txt not found${NC}"
    echo "Installing minimal requirements..."
    pip install --no-cache-dir python-dotenv Pillow requests PyYAML pydantic aiohttp
fi

# Step 7: Create config if missing
echo -e "${GREEN}Setting up configuration...${NC}"
if [ ! -f "config/config.yaml" ]; then
    if [ -f "config/config-pi-zero.yaml" ]; then
        cp config/config-pi-zero.yaml config/config.yaml
        echo "✓ Configuration created from template"
    else
        echo -e "${YELLOW}No config template found${NC}"
        echo "Please create config/config.yaml manually"
    fi
else
    echo "Configuration already exists"
fi

echo ""
echo "================================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Reboot to enable SPI: sudo reboot"
echo "2. Edit configuration: nano config/config.yaml"
echo "3. Test display: python src/main_v2.py test --pattern"
echo ""
echo "If Waveshare library failed to install:"
echo "1. Check network: ping github.com"
echo "2. Try manual download from https://github.com/waveshare/e-Paper"
echo "3. Or skip and use simulation mode for testing"
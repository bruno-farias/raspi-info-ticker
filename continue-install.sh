#!/bin/bash

# Continue Installation Script for Raspi Info Ticker
# Use this after the Waveshare library has been installed

set -e

echo "================================================"
echo "  Continuing Raspi Info Ticker Installation"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}✓ Waveshare library already installed${NC}"
echo -e "${YELLOW}Note: The Jetson.GPIO error you saw is normal - it's only for NVIDIA boards${NC}"
echo ""

# Check if we can import waveshare_epd
echo "Verifying Waveshare installation..."
if python3 -c "import waveshare_epd" 2>/dev/null; then
    echo -e "${GREEN}✓ Waveshare library is working correctly${NC}"
else
    echo -e "${YELLOW}Testing with system Python...${NC}"
    if sudo python3 -c "import waveshare_epd" 2>/dev/null; then
        echo -e "${GREEN}✓ Waveshare library installed system-wide${NC}"
    else
        echo -e "${YELLOW}Warning: Could not verify Waveshare installation${NC}"
    fi
fi

PROJECT_DIR="$HOME/raspi-info-ticker"
cd "$PROJECT_DIR"

# Step 1: Create virtual environment (if not exists)
echo ""
echo -e "${GREEN}Step 1: Setting up Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv --system-site-packages
    echo "Virtual environment created with system packages access"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Step 2: Install Python packages
echo ""
echo -e "${GREEN}Step 2: Installing Python packages...${NC}"
echo "This will take 5-10 minutes on Pi Zero W..."

# Upgrade pip first
pip install --upgrade pip wheel setuptools

# Install requirements
if [ -f "requirements-pi-zero.txt" ]; then
    pip install --no-cache-dir -r requirements-pi-zero.txt
else
    echo -e "${YELLOW}Using standard requirements (may use more memory)${NC}"
    pip install --no-cache-dir -r requirements.txt
fi

# Step 3: Create configuration
echo ""
echo -e "${GREEN}Step 3: Setting up configuration...${NC}"
if [ ! -f "config/config.yaml" ]; then
    if [ -f "config/config-pi-zero.yaml" ]; then
        cp config/config-pi-zero.yaml config/config.yaml
        echo "Created config.yaml from Pi Zero template"
    else
        cp config/config.example.yaml config/config.yaml
        echo "Created config.yaml from example"
    fi
else
    echo "config.yaml already exists"
fi

# Step 4: Test the display
echo ""
echo -e "${GREEN}Step 4: Testing e-paper display...${NC}"
echo "This will display a test pattern on your e-paper screen"
read -p "Run display test? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python src/main_v2.py test --pattern
fi

# Step 5: Configure API keys
echo ""
echo -e "${GREEN}Step 5: Configure API keys${NC}"
echo "You need to add your API keys to config/config.yaml:"
echo "  - OpenWeatherMap API key (free tier available)"
echo "  - FreeCurrencyAPI key (free tier available)"
echo ""
read -p "Edit config now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    nano config/config.yaml
fi

# Step 6: Create systemd service
echo ""
echo -e "${GREEN}Step 6: Setting up auto-start service...${NC}"
read -p "Create systemd service? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo tee /etc/systemd/system/info-ticker.service > /dev/null <<EOF
[Unit]
Description=Raspi Info Ticker Display
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=$PROJECT_DIR"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/main_v2.py display
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable info-ticker.service
    echo "Service created and enabled"
fi

# Create helper scripts
echo ""
echo -e "${GREEN}Creating helper scripts...${NC}"

cat > start.sh <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python src/main_v2.py display
EOF
chmod +x start.sh

cat > test.sh <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python src/main_v2.py test --pattern
EOF
chmod +x test.sh

echo ""
echo "================================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "================================================"
echo ""
echo "Quick commands:"
echo "  ./test.sh    - Test e-paper display"
echo "  ./start.sh   - Start display manually"
echo "  nano config/config.yaml - Edit configuration"
echo ""
echo "To start the service:"
echo "  sudo systemctl start info-ticker.service"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u info-ticker.service -f"
echo ""

# Check if SPI is enabled
if ! lsmod | grep -q spi_bcm2835; then
    echo -e "${YELLOW}IMPORTANT: SPI is not enabled. You need to reboot!${NC}"
    echo "Run: sudo reboot"
fi
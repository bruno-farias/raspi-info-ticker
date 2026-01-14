#!/bin/bash

# Raspberry Pi Zero W Installation Script for Raspi Info Ticker v2.0
# This script optimizes installation for limited resources (512MB RAM)

set -e  # Exit on error

echo "================================================"
echo "  Raspi Info Ticker - Pi Zero W Installation"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo -e "${YELLOW}Warning: This script is optimized for Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Update system
echo -e "${GREEN}Step 1: Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y

# Step 2: Install system dependencies
echo -e "${GREEN}Step 2: Installing system dependencies...${NC}"

# Detect OS version for package compatibility
OS_VERSION=$(lsb_release -cs 2>/dev/null || echo "unknown")
echo "Detected OS: $OS_VERSION"

# Base packages that work across versions
PACKAGES="python3-pip python3-venv python3-dev git"
PACKAGES="$PACKAGES libopenjp2-7 libatlas-base-dev"
PACKAGES="$PACKAGES libxml2-dev libxslt1-dev libffi-dev"
PACKAGES="$PACKAGES libcairo2-dev libgirepository1.0-dev"
PACKAGES="$PACKAGES python3-spidev python3-rpi.gpio"

# Handle libtiff version differences
if apt-cache show libtiff6 &>/dev/null; then
    echo "Installing libtiff6 (Bookworm)"
    PACKAGES="$PACKAGES libtiff6"
elif apt-cache show libtiff5 &>/dev/null; then
    echo "Installing libtiff5 (Bullseye)"
    PACKAGES="$PACKAGES libtiff5"
else
    echo -e "${YELLOW}Warning: No compatible libtiff package found${NC}"
fi

# Install all packages
sudo apt install -y $PACKAGES

# Step 3: Enable SPI interface
echo -e "${GREEN}Step 3: Checking SPI interface...${NC}"
if ! lsmod | grep -q spi_bcm2835; then
    echo "SPI is not enabled. Enabling now..."
    sudo raspi-config nonint do_spi 0
    echo -e "${YELLOW}SPI enabled. Reboot required after installation.${NC}"
    REBOOT_REQUIRED=true
else
    echo "SPI is already enabled."
fi

# Step 4: Install Waveshare e-Paper library
echo -e "${GREEN}Step 4: Installing Waveshare e-Paper library...${NC}"
if [ ! -d "$HOME/e-Paper" ]; then
    cd $HOME
    git clone https://github.com/waveshare/e-Paper.git
    cd e-Paper/RaspberryPi_JetsonNano/python

    # Install Waveshare library - Jetson.GPIO error is expected and can be ignored
    echo "Installing Waveshare library (Jetson.GPIO errors are normal on Raspberry Pi)..."
    if sudo python3 setup.py install 2>&1 | tee /tmp/waveshare_install.log; then
        echo "Waveshare library installation completed."
    else
        # Check if the main waveshare_epd module was installed despite Jetson.GPIO error
        if grep -q "waveshare_epd.*\.egg" /tmp/waveshare_install.log; then
            echo -e "${GREEN}✓ Waveshare e-paper library installed successfully${NC}"
            echo -e "${YELLOW}Note: Jetson.GPIO error is expected - it's only for NVIDIA boards${NC}"
        else
            echo -e "${RED}Failed to install Waveshare library${NC}"
            exit 1
        fi
    fi

    cd $HOME
else
    echo "Waveshare library already exists."
    # Verify it's actually installed
    if python3 -c "import waveshare_epd" 2>/dev/null; then
        echo -e "${GREEN}✓ Waveshare library verified${NC}"
    else
        echo -e "${YELLOW}Waveshare directory exists but module not installed. Reinstalling...${NC}"
        cd $HOME/e-Paper/RaspberryPi_JetsonNano/python
        sudo python3 setup.py install 2>&1 | grep -v "Jetson.GPIO" || true
        cd $HOME
    fi
fi

# Step 5: Setup project directory
echo -e "${GREEN}Step 5: Setting up project directory...${NC}"
PROJECT_DIR="$HOME/raspi-info-ticker"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}Project directory not found at $PROJECT_DIR${NC}"
    echo "Please ensure the project files are in $PROJECT_DIR"
    echo "You can copy them using:"
    echo "  scp -r * bruno@zero.local:~/raspi-info-ticker/"
    exit 1
fi

cd "$PROJECT_DIR"

# Step 6: Create virtual environment
echo -e "${GREEN}Step 6: Creating Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv --system-site-packages
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
source venv/bin/activate

# Step 7: Upgrade pip
echo -e "${GREEN}Step 7: Upgrading pip...${NC}"
pip install --upgrade pip wheel setuptools

# Step 8: Install Python packages
echo -e "${GREEN}Step 8: Installing Python packages (this may take a while)...${NC}"
if [ -f "requirements-pi-zero.txt" ]; then
    echo "Using optimized requirements for Pi Zero W..."
    pip install --no-cache-dir -r requirements-pi-zero.txt
else
    echo -e "${YELLOW}Warning: requirements-pi-zero.txt not found, using standard requirements${NC}"
    pip install --no-cache-dir -r requirements.txt
fi

# Step 9: Create configuration
echo -e "${GREEN}Step 9: Setting up configuration...${NC}"
if [ ! -f "config/config.yaml" ]; then
    if [ -f "config/config-pi-zero.yaml" ]; then
        cp config/config-pi-zero.yaml config/config.yaml
        echo "Created config.yaml from Pi Zero W template"
    elif [ -f "config/config.example.yaml" ]; then
        cp config/config.example.yaml config/config.yaml
        echo "Created config.yaml from example"
    else
        echo -e "${YELLOW}Warning: No config file found. Please create config/config.yaml${NC}"
    fi
else
    echo "config.yaml already exists"
fi

# Step 10: Increase swap (optional but recommended for Pi Zero W)
echo -e "${GREEN}Step 10: Configuring swap file...${NC}"
read -p "Increase swap size to 256MB? Recommended for Pi Zero W (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo dphys-swapfile swapoff
    sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=256/' /etc/dphys-swapfile
    sudo dphys-swapfile setup
    sudo dphys-swapfile swapon
    echo "Swap increased to 256MB"
fi

# Step 11: Create systemd service
echo -e "${GREEN}Step 11: Creating systemd service...${NC}"
read -p "Create systemd service for auto-start? (y/n): " -n 1 -r
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
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable info-ticker.service
    echo "Systemd service created and enabled"
    echo "Start with: sudo systemctl start info-ticker.service"
    echo "View logs: sudo journalctl -u info-ticker.service -f"
fi

# Step 12: Test installation
echo -e "${GREEN}Step 12: Testing installation...${NC}"
echo "Testing Python imports..."
python -c "
try:
    import pydantic
    import aiohttp
    import PIL
    import yaml
    print('✓ Core packages imported successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    exit(1)
"

# Step 13: Create helper scripts
echo -e "${GREEN}Step 13: Creating helper scripts...${NC}"

# Create start script
cat > start.sh <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python src/main_v2.py display
EOF
chmod +x start.sh

# Create status script
cat > status.sh <<'EOF'
#!/bin/bash
echo "=== Info Ticker Status ==="
sudo systemctl status info-ticker.service --no-pager
echo ""
echo "=== Recent Logs ==="
sudo journalctl -u info-ticker.service -n 20 --no-pager
EOF
chmod +x status.sh

# Create update script
cat > update.sh <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
git pull
source venv/bin/activate
pip install --no-cache-dir -r requirements-pi-zero.txt
sudo systemctl restart info-ticker.service
EOF
chmod +x update.sh

echo ""
echo "================================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Edit configuration: nano config/config.yaml"
echo "2. Add your API keys to the configuration"
echo "3. Test manually: ./start.sh"
echo "4. Start service: sudo systemctl start info-ticker.service"
echo "5. Check status: ./status.sh"
echo ""

if [ "$REBOOT_REQUIRED" = true ]; then
    echo -e "${YELLOW}IMPORTANT: Reboot required to enable SPI interface${NC}"
    echo "Run: sudo reboot"
fi

echo ""
echo "Helper scripts created:"
echo "  ./start.sh   - Start display manually"
echo "  ./status.sh  - Check service status"
echo "  ./update.sh  - Update from git"
echo ""
echo "For help, see README_NEW.md"
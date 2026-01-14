# Deployment Guide for Raspberry Pi Zero W

This guide provides step-by-step instructions for deploying the Raspi Info Ticker v2.0 on your Raspberry Pi Zero W.

## Prerequisites

- Raspberry Pi Zero W with Raspbian OS (Bookworm) installed
- 8GB+ SD card
- 2.13" e-Paper display (Waveshare or compatible)
- Network connection (WiFi configured)
- SSH access enabled (user: `bruno`, hostname: `zero.local`)

## Quick Installation

### Method 1: Automated Installation (Recommended)

1. **Transfer files to your Pi Zero W:**
```bash
# From your Mac (Bruno's MacBook Pro)
cd /Users/brunofarias/code/bruno/raspi-info-ticker
scp -r * bruno@zero.local:~/raspi-info-ticker/

# Or use rsync for better progress tracking
rsync -avz --progress --exclude 'venv' --exclude '__pycache__' \
  --exclude '.git' --exclude '*.pyc' \
  ./ bruno@zero.local:~/raspi-info-ticker/
```

2. **SSH into your Pi:**
```bash
ssh bruno@zero.local
```

3. **Run installation script:**
```bash
cd ~/raspi-info-ticker
chmod +x install-pi.sh
./install-pi.sh
```

4. **Configure API keys:**
```bash
nano config/config.yaml
# Add your API keys:
# - OpenWeatherMap API key
# - FreeCurrencyAPI key
```

5. **Start the service:**
```bash
sudo systemctl start info-ticker.service
```

### Method 2: Manual Installation

If the automated script fails, follow these manual steps:

#### Step 1: System Preparation
```bash
# SSH into your Pi
ssh bruno@zero.local

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv python3-dev git
sudo apt install -y libopenjp2-7 libatlas-base-dev
sudo apt install -y python3-spidev python3-rpi.gpio

# Note: Bookworm uses libtiff6 instead of libtiff5
# The script automatically detects the correct version
sudo apt install -y libtiff6  # For Bookworm (Debian 12)
# or
# sudo apt install -y libtiff5  # For Bullseye (Debian 11)
```

#### Step 2: Enable SPI
```bash
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable
# Reboot after enabling
sudo reboot
```

After reboot, reconnect:
```bash
ssh bruno@zero.local
```

#### Step 3: Install Waveshare Library
```bash
cd ~
git clone https://github.com/waveshare/e-Paper.git
cd e-Paper/RaspberryPi_JetsonNano/python
sudo python3 setup.py install
```

#### Step 4: Setup Project
```bash
cd ~/raspi-info-ticker
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install --no-cache-dir -r requirements-pi-zero.txt
```

#### Step 5: Configure
```bash
cp config/config-pi-zero.yaml config/config.yaml
nano config/config.yaml  # Add your API keys
```

#### Step 6: Test
```bash
# Test the display
python src/main_v2.py test --pattern

# Run display mode
python src/main_v2.py display
```

## Configuration

### Essential API Keys

1. **OpenWeatherMap** (Free tier available)
   - Sign up at: https://openweathermap.org/api
   - Get API key from your account
   - Add to config.yaml: `plugins.weather.api_key`

2. **FreeCurrencyAPI** (Free tier available)
   - Sign up at: https://freecurrencyapi.com/
   - Get API key from dashboard
   - Add to config.yaml: `plugins.currency.api_key`

### Performance Tuning for Pi Zero W

The included `config-pi-zero.yaml` is pre-optimized, but you can further adjust:

```yaml
# Reduce refresh rate (seconds)
display:
  refresh_interval: 60  # Increase to reduce CPU usage

# Disable unused plugins
plugins:
  crypto:
    enabled: false  # Save memory
  stock:
    enabled: false  # Save memory

# Reduce API calls
plugins:
  weather:
    update_interval: 900  # 15 minutes
    cache_ttl: 1800      # 30 minutes
```

### Memory Optimization

If you experience crashes or slow performance:

1. **Increase swap space:**
```bash
ssh bruno@zero.local
sudo nano /etc/dphys-swapfile
# Change: CONF_SWAPSIZE=256
sudo dphys-swapfile swapoff
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

2. **Monitor resources:**
```bash
# Check memory usage
free -h

# Check temperature
vcgencmd measure_temp

# Monitor processes
htop
```

## Service Management

### Setup Systemd Service

1. **Create service file:**
```bash
sudo nano /etc/systemd/system/info-ticker.service
```

2. **Add this content:**
```ini
[Unit]
Description=Raspi Info Ticker Display Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=bruno
Group=bruno
WorkingDirectory=/home/bruno/raspi-info-ticker
Environment="PATH=/home/bruno/raspi-info-ticker/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/home/bruno/raspi-info-ticker"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/bruno/raspi-info-ticker/venv/bin/python /home/bruno/raspi-info-ticker/src/main_v2.py display
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. **Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable info-ticker.service
sudo systemctl start info-ticker.service
```

### Service Commands
```bash
# Start
sudo systemctl start info-ticker.service

# Stop
sudo systemctl stop info-ticker.service

# Restart
sudo systemctl restart info-ticker.service

# View status
sudo systemctl status info-ticker.service

# View logs
sudo journalctl -u info-ticker.service -f
```

## Helper Scripts

Create these helper scripts for easier management:

### start.sh
```bash
nano ~/raspi-info-ticker/start.sh
```
Add content:
```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python src/main_v2.py display
```
Make executable:
```bash
chmod +x ~/raspi-info-ticker/start.sh
```

### status.sh
```bash
nano ~/raspi-info-ticker/status.sh
```
Add content:
```bash
#!/bin/bash
echo "=== Info Ticker Status ==="
sudo systemctl status info-ticker.service --no-pager
echo ""
echo "=== Recent Logs ==="
sudo journalctl -u info-ticker.service -n 20 --no-pager
```
Make executable:
```bash
chmod +x ~/raspi-info-ticker/status.sh
```

## Troubleshooting

### Display Not Working

1. **Check SPI is enabled:**
```bash
ssh bruno@zero.local
ls /dev/spi*
# Should show: /dev/spidev0.0
```

2. **Check connections:**
- Verify all pins are connected correctly
- Ensure display has power (3.3V, not 5V!)

3. **Test with example:**
```bash
cd ~/e-Paper/RaspberryPi_JetsonNano/python/examples
python epd_2in13_V4_test.py
```

### Out of Memory Errors

1. **Check current memory:**
```bash
ssh bruno@zero.local
free -h
df -h
```

2. **Disable unused plugins:**
```bash
nano ~/raspi-info-ticker/config/config.yaml
# Set enabled: false for unused plugins
```

3. **Use lighter version:**
```bash
# Use main_v2.py instead of main.py
python src/main_v2.py display
```

### Service Won't Start

1. **Check logs:**
```bash
ssh bruno@zero.local
sudo journalctl -u info-ticker.service -n 50
```

2. **Test manually:**
```bash
cd ~/raspi-info-ticker
source venv/bin/activate
python src/main_v2.py test --pattern
```

3. **Check permissions:**
```bash
ls -la /home/bruno/raspi-info-ticker/
sudo chown -R bruno:bruno /home/bruno/raspi-info-ticker/
```

### Slow Performance

1. **Monitor CPU and temperature:**
```bash
ssh bruno@zero.local
# In one terminal
watch -n 2 "vcgencmd measure_temp && top -bn1 | head -10"
```

2. **Reduce refresh interval:**
```bash
nano ~/raspi-info-ticker/config/config.yaml
# Set refresh_interval: 120  # 2 minutes
```

## Remote Management

### SSH Access from your Mac
```bash
# Quick SSH
ssh bruno@zero.local

# SSH with display output monitoring
ssh bruno@zero.local -t "sudo journalctl -u info-ticker.service -f"
```

### Update Configuration Remotely
```bash
# Edit config via SSH
ssh bruno@zero.local "nano ~/raspi-info-ticker/config/config.yaml"

# Restart service
ssh bruno@zero.local "sudo systemctl restart info-ticker.service"
```

### Push Updates from Mac
```bash
# One-line deploy from Mac
cd /Users/brunofarias/code/bruno/raspi-info-ticker && \
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  ./ bruno@zero.local:~/raspi-info-ticker/ && \
ssh bruno@zero.local "sudo systemctl restart info-ticker.service"
```

### Web Management Interface (Optional)
```bash
# Start management interface on Pi
ssh bruno@zero.local
cd ~/raspi-info-ticker
source venv/bin/activate
python src/main_v2.py management --host 0.0.0.0 --port 8080

# Access from Mac's browser
open http://zero.local:8080
```

## Backup and Restore

### Backup Configuration
```bash
# On Pi
tar czf ticker-backup-$(date +%Y%m%d).tar.gz \
  ~/raspi-info-ticker/config/ \
  ~/raspi-info-ticker/data/

# Copy to Mac
scp bruno@zero.local:~/ticker-backup-*.tar.gz ~/Desktop/
```

### Restore Configuration
```bash
# Copy backup to Pi
scp ~/Desktop/ticker-backup-*.tar.gz bruno@zero.local:~/

# On Pi
ssh bruno@zero.local
tar xzf ticker-backup-*.tar.gz
sudo systemctl restart info-ticker.service
```

## Power Considerations

The Pi Zero W with e-paper display is relatively power-efficient:

- **Idle**: ~100-150mA
- **Active refresh**: ~200-250mA
- **With WiFi**: +50-100mA

For battery operation:
- Use a 10,000mAh power bank for ~24-48 hours runtime
- Consider solar charging for outdoor installations
- Increase refresh intervals to save power

## Security Notes

For production deployments:

1. **Change default password:**
```bash
passwd
```

2. **Disable password SSH (use keys only):**
```bash
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
```

3. **Setup firewall:**
```bash
sudo apt install ufw
sudo ufw allow ssh
sudo ufw enable
```

4. **Keep API keys secure:**
- Never commit config.yaml with keys to git
- Use environment variables if preferred

## Quick Commands Reference

```bash
# From Mac - Deploy
cd /Users/brunofarias/code/bruno/raspi-info-ticker
scp -r * bruno@zero.local:~/raspi-info-ticker/

# From Mac - Quick SSH
ssh bruno@zero.local

# On Pi - Start service
sudo systemctl start info-ticker.service

# On Pi - View logs
sudo journalctl -u info-ticker.service -f

# On Pi - Test display
cd ~/raspi-info-ticker && source venv/bin/activate
python src/main_v2.py test --pattern

# On Pi - Manual run
cd ~/raspi-info-ticker && source venv/bin/activate
python src/main_v2.py display

# On Pi - Check status
./status.sh
```

## Network Setup Notes

Your Pi Zero W is accessible at:
- Hostname: `zero.local`
- User: `bruno`
- IPv6: `2804:1530:68f:e300:33a:c34b:4db1:109d` (may change with DHCP)

Make sure both your Mac and Pi are on the same network for local access.

## Support

For issues:
1. Check logs: `ssh bruno@zero.local "sudo journalctl -u info-ticker.service -f"`
2. Test manually: `ssh bruno@zero.local "cd ~/raspi-info-ticker && ./start.sh"`
3. Monitor resources: `ssh bruno@zero.local "htop"`
4. Check temperature: `ssh bruno@zero.local "vcgencmd measure_temp"`

For additional help, check the main README_NEW.md or open an issue on GitHub.
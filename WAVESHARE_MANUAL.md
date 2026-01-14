# Manual Waveshare e-Paper Library Installation

If the automatic installation fails due to network issues, follow these steps:

## Option 1: Download on your Mac and Transfer

1. **On your Mac, download the library:**
```bash
cd /tmp
curl -L -o e-Paper.zip https://github.com/waveshare/e-Paper/archive/refs/heads/master.zip
# or use browser: https://github.com/waveshare/e-Paper/archive/refs/heads/master.zip
```

2. **Transfer to your Pi:**
```bash
scp /tmp/e-Paper.zip bruno@zero.local:~/
```

3. **On your Pi, extract and install:**
```bash
ssh bruno@zero.local
cd ~
unzip e-Paper.zip
mv e-Paper-master e-Paper
cd e-Paper/RaspberryPi_JetsonNano/python
sudo python3 setup.py install
```

## Option 2: Clone via SSH (if HTTPS fails)

1. **Try using SSH protocol:**
```bash
ssh bruno@zero.local
cd ~
git clone git@github.com:waveshare/e-Paper.git
```

2. **If that fails, try with different DNS:**
```bash
# Use Google DNS temporarily
sudo sh -c "echo 'nameserver 8.8.8.8' > /etc/resolv.conf"
git clone https://github.com/waveshare/e-Paper.git
```

## Option 3: Use Alternative Mirror

1. **Try Gitee mirror (China):**
```bash
git clone https://gitee.com/waveshare/e-Paper.git
```

2. **Or use a proxy/VPN if available**

## Option 4: Skip Waveshare Library (Testing Only)

You can run the ticker in simulation mode without the e-paper library:

1. **Edit the display runner to skip hardware init:**
```bash
nano ~/raspi-info-ticker/src/display/runner_v2.py
# Comment out the waveshare import lines
```

2. **Run in simulation mode:**
```bash
cd ~/raspi-info-ticker
source venv/bin/activate
python src/main_v2.py display
# Will save images as PNG files instead of displaying
```

## Testing the Installation

Once installed, test with:

```bash
# Test Waveshare examples
cd ~/e-Paper/RaspberryPi_JetsonNano/python/examples
sudo python3 epd_2in13_V4_test.py

# Test our display
cd ~/raspi-info-ticker
source venv/bin/activate
python src/main_v2.py test --pattern
```

## Troubleshooting Network Issues

1. **Check DNS resolution:**
```bash
nslookup github.com
# or
dig github.com
```

2. **Check routing:**
```bash
traceroute github.com
```

3. **Try different network:**
- Switch to mobile hotspot
- Use ethernet adapter
- Check router firewall settings

4. **Update certificates:**
```bash
sudo apt update
sudo apt install ca-certificates
sudo update-ca-certificates
```

## Required Files

The essential Waveshare files for 2.13" V4 display are:
- `waveshare_epd/epd2in13_V4.py`
- `waveshare_epd/epdconfig.py`

If you only need these, you can copy them directly to your project.
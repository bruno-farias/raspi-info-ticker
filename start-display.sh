#!/bin/bash
# Start the info ticker display

cd /home/bruno/raspi-info-ticker
source venv/bin/activate
python src/main_v2.py display

#!/bin/bash

# Run the currency ticker with proper permissions
cd "$(dirname "$0")"
source venv/bin/activate
sudo -E venv/bin/python main.py
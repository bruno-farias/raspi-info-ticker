#!/bin/bash

# Run the currency ticker with proper permissions
cd "$(dirname "$0")"

# Use the full path to the venv python with sudo
sudo "$(pwd)/venv/bin/python" main.py
#!/bin/bash
# Run tests with coverage

set -e

echo "======================================"
echo "Running Raspi Info Ticker Test Suite"
echo "======================================"

# Determine pip command
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo "Error: Neither pip nor pip3 found. Please install pip."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    PIP_CMD="pip"  # Use pip inside venv
else
    echo "No virtual environment found. Consider creating one with:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo ""
fi

# Install test dependencies
echo "Installing test dependencies..."
$PIP_CMD install -q -r requirements-dev.txt

# Run tests
echo ""
echo "Running tests..."
python3 -m pytest

# Check coverage
echo ""
echo "Coverage report generated in htmlcov/"
echo "Open htmlcov/index.html in your browser to view detailed coverage"

exit 0

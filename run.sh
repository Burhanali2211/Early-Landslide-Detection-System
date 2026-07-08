#!/bin/bash
echo "Setting up Python Virtual Environment..."

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

echo "Installing requirements in virtual environment..."
pip install -r requirements

cd src
echo "Starting ALPROS server..."
if command -v xdg-open > /dev/null; then
  xdg-open http://127.0.0.1:5000/dashboard &
elif command -v open > /dev/null; then
  open http://127.0.0.1:5000/dashboard &
elif command -v chromium-browser > /dev/null; then
  chromium-browser http://127.0.0.1:5000/dashboard &
fi

python app.py

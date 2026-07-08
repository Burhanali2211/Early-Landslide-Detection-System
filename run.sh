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

# Modern Raspberry Pi OS requires libcamerify to bridge the CSI camera to OpenCV (V4L2)
if command -v libcamerify > /dev/null; then
    echo "libcamerify found! Launching with Pi Camera support..."
    libcamerify python app.py
else
    # Fallback to standard execution (for laptops, older Pis, or USB webcams)
    python app.py
fi

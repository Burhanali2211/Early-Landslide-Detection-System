#!/bin/bash
echo "Installing requirements..."
pip install -r requirements
cd src
echo "Starting ALPROS server..."
if command -v xdg-open > /dev/null; then
  xdg-open http://127.0.0.1:5000/dashboard &
elif command -v open > /dev/null; then
  open http://127.0.0.1:5000/dashboard &
fi
python app.py

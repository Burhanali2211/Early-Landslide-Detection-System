#!/bin/bash
echo "Installing Raspberry Pi Camera Dependencies..."

# Update package lists
sudo apt-get update

# Install system-level OpenCV which has properly compiled V4L2 and libcamera bindings for Raspberry Pi
echo "Installing system OpenCV and camera utilities..."
sudo apt-get install -y python3-opencv libcamera-apps libcamera-dev v4l-utils

echo "=========================================================="
echo "INSTALLATION COMPLETE!"
echo "If your camera is still not detected, you MUST enable it:"
echo "1. Run: sudo raspi-config"
echo "2. Go to 'Interface Options' -> 'Camera' (or 'Legacy Camera')"
echo "3. Select 'Yes' to enable, then reboot."
echo "=========================================================="

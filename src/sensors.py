import time
import math
import random

try:
    import smbus2 as smbus
    import RPi.GPIO as GPIO
    import adafruit_dht
    import board
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("WARNING: Hardware libraries (smbus2, RPi.GPIO, adafruit_dht) missing. Running in mock mode.")

# -----------------------------
# 🔹 Hardware Configuration
# -----------------------------
# DHT11 setup
DHT_PIN = board.D4 if HARDWARE_AVAILABLE else None

# Digital Sensors (GPIO)
VIBRATION_SENSOR_PIN = 17  # Digital pin for SW-420 vibration sensor
MOISTURE_SENSOR_PIN = 27   # Digital pin for Soil Moisture comparator output (if not using ADC)

# I2C MPU6050 setup
MPU6050_ADDR = 0x68
PWR_MGMT_1   = 0x6B
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F

if HARDWARE_AVAILABLE:
    try:
        # Init GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(VIBRATION_SENSOR_PIN, GPIO.IN)
        GPIO.setup(MOISTURE_SENSOR_PIN, GPIO.IN)

        # Init DHT11
        dht_device = adafruit_dht.DHT11(DHT_PIN)

        # Init I2C for MPU6050
        bus = smbus.SMBus(1)
        bus.write_byte_data(MPU6050_ADDR, PWR_MGMT_1, 0)
    except Exception as e:
        print(f"Hardware init error: {e}")
        HARDWARE_AVAILABLE = False


def read_word_2c(addr, reg):
    """Read two bytes of data from I2C and convert to 2's complement."""
    high = bus.read_byte_data(addr, reg)
    low = bus.read_byte_data(addr, reg + 1)
    val = (high << 8) + low
    if val >= 0x8000:
        return -((65535 - val) + 1)
    return val

def get_real_vibration():
    """Reads MPU6050 accelerometer and calculates vibration magnitude."""
    if not HARDWARE_AVAILABLE:
        return round(random.uniform(0.01, 0.06), 3)

    try:
        accel_x = read_word_2c(MPU6050_ADDR, ACCEL_XOUT_H) / 16384.0
        accel_y = read_word_2c(MPU6050_ADDR, ACCEL_YOUT_H) / 16384.0
        accel_z = read_word_2c(MPU6050_ADDR, ACCEL_ZOUT_H) / 16384.0
        magnitude = math.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
        vibration = abs(magnitude - 1.0)
        return round(vibration, 3)
    except Exception as e:
        print(f"Error reading MPU6050: {e}")
        return 0.0

def get_real_tilt():
    """Reads MPU6050 accelerometer and calculates maximum tilt angle (pitch/roll) in degrees."""
    if not HARDWARE_AVAILABLE:
        return round(random.uniform(0.0, 5.0), 1)
        
    try:
        accel_x = read_word_2c(MPU6050_ADDR, ACCEL_XOUT_H) / 16384.0
        accel_y = read_word_2c(MPU6050_ADDR, ACCEL_YOUT_H) / 16384.0
        accel_z = read_word_2c(MPU6050_ADDR, ACCEL_ZOUT_H) / 16384.0
        
        # Calculate Pitch and Roll
        pitch = math.atan2(accel_y, math.sqrt(accel_x**2 + accel_z**2)) * 180 / math.pi
        roll = math.atan2(-accel_x, accel_z) * 180 / math.pi
        
        # Return the maximum absolute tilt angle
        max_tilt = max(abs(pitch), abs(roll))
        return round(max_tilt, 1)
    except Exception as e:
        print(f"Error reading MPU6050 tilt: {e}")
        return 0.0

def get_digital_vibration():
    """Reads simple digital vibration sensor (SW-420). Returns 1 for motion, 0 for still."""
    if not HARDWARE_AVAILABLE:
        return 0
    # Usually SW-420 goes HIGH when vibration is detected
    return GPIO.input(VIBRATION_SENSOR_PIN)

def get_real_soil_moisture():
    """Reads digital soil moisture sensor. Returns 0% (Dry) or 100% (Wet)."""
    if not HARDWARE_AVAILABLE:
        return None
    
    # Standard digital moisture sensor outputs HIGH when dry, LOW when wet
    is_dry = GPIO.input(MOISTURE_SENSOR_PIN)
    return 0.0 if is_dry else 100.0

def get_real_climate():
    """Reads Temperature and Humidity from DHT11."""
    if not HARDWARE_AVAILABLE:
        return None, None
    
    try:
        temp = dht_device.temperature
        hum = dht_device.humidity
        return temp, hum
    except RuntimeError as e:
        # DHT sensors commonly throw runtime errors from timing issues
        print(f"DHT11 Error (retrying next time): {e.args[0]}")
        return None, None
    except Exception as e:
        print(f"DHT11 Fatal Error: {e}")
        return None, None

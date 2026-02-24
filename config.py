"""
Motor Configuration File
Edit these values to match YOUR actual hardware setup
"""

# GPIO Pin Configuration - MOTOR A
# ================================
GPIO_IN1_PIN = 17      # Motor A direction control pin 1 (Forward/Backward)
GPIO_IN2_PIN = 27      # Motor A direction control pin 2 (Forward/Backward)
GPIO_ENA_PIN = 22      # Motor A PWM speed control pin (0-100%)

# GPIO Pin Configuration - MOTOR B
# ================================
GPIO_IN3_PIN = 23      # Motor B direction control pin 1 (Forward/Backward)
GPIO_IN4_PIN = 24      # Motor B direction control pin 2 (Forward/Backward)
GPIO_ENB_PIN = 25      # Motor B PWM speed control pin (0-100%)

# PWM Configuration
PWM_FREQUENCY = 1000   # Frequency in Hz (1000 Hz is standard)

# Motor Configuration
MOTOR_MAX_SPEED = 100  # Maximum speed percentage (0-100)
MOTOR_DEFAULT_SPEED = 70  # Default rotation speed

# Debugging
VERBOSE_MODE = True    # Print debug information

import os as _os_env
api_key = _os_env.environ.get("GROQ_API_KEY", "")  # Set GROQ_API_KEY environment variable

# ================================
# YDLidar G2 Configuration
# ================================
LIDAR_PORT = "/dev/ttyUSB0"       # Serial port (run: ls /dev/ttyUSB*)
LIDAR_BAUDRATE = 230400           # G2/G2B baud rate
LIDAR_SCAN_FREQUENCY = 10.0      # Scan frequency in Hz
LIDAR_SAMPLE_RATE = 5             # Sample rate in kHz
LIDAR_MAX_RANGE = 12.0            # Max detection range (metres)
LIDAR_MIN_RANGE = 0.1             # Min detection range (metres)

# ================================
# Autonomous Navigation
# ================================
NAV_SPEED = 50                    # Driving speed during navigation (0-100%)
NAV_OBSTACLE_THRESHOLD = 0.35    # Distance to obstacle that triggers avoidance (metres)
NAV_SECTOR_COUNT = 12             # Number of angular sectors for path planning
NAV_FRONT_SECTOR_HALF = 2        # How many sectors left/right of centre count as "front"

# ================================
# Occupancy Grid
# ================================
GRID_RESOLUTION = 0.05            # Metres per cell (5 cm)
GRID_SIZE_M = 10.0                # Map side length in metres (10m × 10m)

# ================================
# Dead Reckoning
# ================================
DR_WHEEL_BASE = 0.15              # Distance between wheels in metres (measure your car!)
DR_MAX_SPEED_MPS = 0.3            # Max forward speed in m/s at 100% PWM (calibrate!)

# ================================
# Exploration
# ================================
EXPLORE_SPEED = 40                # PWM% during autonomous exploration
EXPLORE_TURN_DURATION = 0.8       # Seconds per 90° turn (calibrate!)
EXPLORE_COMPLETE_PCT = 90         # Consider mapping done at this % explored
EXPLORE_FRONTIER_MIN_DIST = 0.20  # Ignore frontiers closer than this (metres)

# ================================
# Map Storage
# ================================
import os as _os
MAPS_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "maps")
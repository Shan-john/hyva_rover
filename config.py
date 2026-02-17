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


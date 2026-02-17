#!/usr/bin/env python3
"""
Motor B (Right Motor) Diagnostic - Test individual pins
Run with: sudo python3 diagnose_motor_b.py
Use a multimeter to verify voltage on each pin
"""

import RPi.GPIO as GPIO
import time
from config import *

print("\n" + "=" * 60)
print("MOTOR B (RIGHT MOTOR) DIAGNOSTIC TEST")
print("=" * 60)
print(f"\nMotor B GPIO Pins:")
print(f"  IN3 (Direction) : GPIO {GPIO_IN3_PIN}")
print(f"  IN4 (Direction) : GPIO {GPIO_IN4_PIN}")
print(f"  ENB (Speed PWM) : GPIO {GPIO_ENB_PIN}")
print("\n" + "=" * 60)
print("IMPORTANT: Use a multimeter to check voltages!")
print("Expected: ~3.3V when HIGH, ~0V when LOW")
print("=" * 60)

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup Motor B pins
    GPIO.setup(GPIO_IN3_PIN, GPIO.OUT)
    GPIO.setup(GPIO_IN4_PIN, GPIO.OUT)
    GPIO.setup(GPIO_ENB_PIN, GPIO.OUT)
    
    print("\n[STEP 1] GPIO Setup Complete")
    print(f"  ✓ GPIO {GPIO_IN3_PIN} configured as OUT")
    print(f"  ✓ GPIO {GPIO_IN4_PIN} configured as OUT")
    print(f"  ✓ GPIO {GPIO_ENB_PIN} configured as OUT")
    
    # Test Motor B pins
    print("\n" + "=" * 60)
    print("[STEP 2] Testing IN3 (GPIO {})".format(GPIO_IN3_PIN))
    print("=" * 60)
    
    print(f"\nSetting GPIO {GPIO_IN3_PIN} HIGH")
    print("  ⚠ Check pin voltage with multimeter (~3.3V)")
    GPIO.output(GPIO_IN3_PIN, GPIO.HIGH)
    time.sleep(2)
    
    print(f"Setting GPIO {GPIO_IN3_PIN} LOW")
    print("  ⚠ Check pin voltage with multimeter (~0V)")
    GPIO.output(GPIO_IN3_PIN, GPIO.LOW)
    time.sleep(1)
    
    print("\n" + "=" * 60)
    print("[STEP 3] Testing IN4 (GPIO {})".format(GPIO_IN4_PIN))
    print("=" * 60)
    
    print(f"\nSetting GPIO {GPIO_IN4_PIN} HIGH")
    print("  ⚠ Check pin voltage with multimeter (~3.3V)")
    GPIO.output(GPIO_IN4_PIN, GPIO.HIGH)
    time.sleep(2)
    
    print(f"Setting GPIO {GPIO_IN4_PIN} LOW")
    print("  ⚠ Check pin voltage with multimeter (~0V)")
    GPIO.output(GPIO_IN4_PIN, GPIO.LOW)
    time.sleep(1)
    
    print("\n" + "=" * 60)
    print("[STEP 4] Testing ENB PWM (GPIO {})".format(GPIO_ENB_PIN))
    print("=" * 60)
    
    pwm = GPIO.PWM(GPIO_ENB_PIN, 1000)
    pwm.start(0)
    
    print(f"\nTesting PWM on GPIO {GPIO_ENB_PIN}")
    for speed in [0, 50, 100]:
        pwm.ChangeDutyCycle(speed)
        print(f"  PWM {speed}% - Check voltage variation with multimeter")
        time.sleep(1)
    
    pwm.stop()
    
    print("\n" + "=" * 60)
    print("[STEP 5] Motor B Forward Simulation")
    print("=" * 60)
    
    print(f"\nSetting Motor B FORWARD:")
    print(f"  GPIO {GPIO_IN3_PIN} (IN3) -> HIGH")
    print(f"  GPIO {GPIO_IN4_PIN} (IN4) -> LOW")
    print(f"  GPIO {GPIO_ENB_PIN} (ENB) -> PWM 100%")
    
    GPIO.output(GPIO_IN3_PIN, GPIO.HIGH)
    GPIO.output(GPIO_IN4_PIN, GPIO.LOW)
    
    pwm = GPIO.PWM(GPIO_ENB_PIN, 1000)
    pwm.start(100)
    
    print("\n  ⚠ Motor B should rotate in one direction")
    print("  ⚠ Check L298N OUT3/OUT4 pins for ~12V voltage")
    time.sleep(3)
    
    print("\n" + "=" * 60)
    print("[STEP 6] Motor B Backward Simulation")
    print("=" * 60)
    
    print(f"\nSetting Motor B BACKWARD:")
    print(f"  GPIO {GPIO_IN3_PIN} (IN3) -> LOW")
    print(f"  GPIO {GPIO_IN4_PIN} (IN4) -> HIGH")
    print(f"  GPIO {GPIO_ENB_PIN} (ENB) -> PWM 100%")
    
    GPIO.output(GPIO_IN3_PIN, GPIO.LOW)
    GPIO.output(GPIO_IN4_PIN, GPIO.HIGH)
    
    print("\n  ⚠ Motor B should rotate in opposite direction")
    print("  ⚠ Voltage on OUT3/OUT4 should reverse")
    time.sleep(3)
    
    GPIO.output(GPIO_IN3_PIN, GPIO.LOW)
    GPIO.output(GPIO_IN4_PIN, GPIO.LOW)
    pwm.ChangeDutyCycle(0)
    pwm.stop()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC RESULTS")
    print("=" * 60)
    
    print("\n✓ If GPIO pins showed correct voltage (3.3V HIGH, 0V LOW):")
    print("    Problem is with L298N Motor B section or motor wiring")
    print("\n✓ If GPIO pins showed NO voltage change:")
    print("    Check GPIO pin numbers - they may be wrong")
    print("\nCommon Motor B Issues:")
    print("  1. Wrong GPIO pin numbers in config.py")
    print("  2. L298N Motor B OUT3/OUT4 not connected to motor")
    print("  3. Motor B power supply not connected to L298N")
    print("  4. L298N Motor B section defective")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("  Run with: sudo python3 diagnose_motor_b.py")
finally:
    GPIO.cleanup()
    print("\n✓ GPIO cleanup complete\n")

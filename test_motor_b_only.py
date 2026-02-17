#!/usr/bin/env python3
"""
Motor B Only Test - Isolate and test the right motor
Run with: sudo python3 test_motor_b_only.py
"""

import time
import RPi.GPIO as GPIO
from config import *

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

print("\n" + "=" * 60)
print("MOTOR B (RIGHT MOTOR) - ISOLATED TEST")
print("=" * 60)
print(f"Motor B Pins: IN3={GPIO_IN3_PIN}, IN4={GPIO_IN4_PIN}, ENB={GPIO_ENB_PIN}\n")

try:
    # Setup Motor B pins ONLY
    GPIO.setup(GPIO_IN3_PIN, GPIO.OUT)
    GPIO.setup(GPIO_IN4_PIN, GPIO.OUT)
    GPIO.setup(GPIO_ENB_PIN, GPIO.OUT)
    
    # Initialize PWM
    pwm_b = GPIO.PWM(GPIO_ENB_PIN, 1000)
    pwm_b.start(0)
    
    print("✓ Motor B initialized\n")
    
    # Test 1: Forward
    print("[TEST 1] Motor B FORWARD at 100% for 3 seconds")
    print(f"  IN3 -> HIGH, IN4 -> LOW, ENB -> 100%")
    GPIO.output(GPIO_IN3_PIN, GPIO.HIGH)
    GPIO.output(GPIO_IN4_PIN, GPIO.LOW)
    pwm_b.ChangeDutyCycle(100)
    print("  ⚠ Listen and feel for motor rotation")
    time.sleep(3)
    
    # Test 2: Stop
    print("\n[TEST 2] Motor B STOP")
    GPIO.output(GPIO_IN3_PIN, GPIO.LOW)
    GPIO.output(GPIO_IN4_PIN, GPIO.LOW)
    pwm_b.ChangeDutyCycle(0)
    print("  Motor stopped")
    time.sleep(1)
    
    # Test 3: Backward
    print("\n[TEST 3] Motor B BACKWARD at 100% for 3 seconds")
    print(f"  IN3 -> LOW, IN4 -> HIGH, ENB -> 100%")
    GPIO.output(GPIO_IN3_PIN, GPIO.LOW)
    GPIO.output(GPIO_IN4_PIN, GPIO.HIGH)
    pwm_b.ChangeDutyCycle(100)
    print("  ⚠ Motor should rotate opposite direction")
    time.sleep(3)
    
    # Test 4: Speed variation
    print("\n[TEST 4] Motor B - Speed Control (0% -> 100%)")
    GPIO.output(GPIO_IN3_PIN, GPIO.HIGH)
    GPIO.output(GPIO_IN4_PIN, GPIO.LOW)
    for speed in [0, 25, 50, 75, 100]:
        pwm_b.ChangeDutyCycle(speed)
        print(f"  Speed: {speed}%")
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("MOTOR B TEST COMPLETE")
    print("=" * 60)
    print("\n✓ If motor ran in tests - wiring is correct!")
    print("✗ If motor didn't run - check:")
    print("  1. Power supply to L298N connected")
    print("  2. Motor wires connected to OUT3/OUT4")
    print("  3. GPIO pin numbers correct in config.py")
    
    GPIO.output(GPIO_IN3_PIN, GPIO.LOW)
    GPIO.output(GPIO_IN4_PIN, GPIO.LOW)
    pwm_b.ChangeDutyCycle(0)
    pwm_b.stop()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("  Run with: sudo python3 test_motor_b_only.py")
finally:
    GPIO.cleanup()
    print("\n✓ Cleanup complete\n")

#!/usr/bin/env python3
"""Motor diagnostic and testing script"""

import RPi.GPIO as GPIO
import time

# GPIO Configuration
IN1_PIN = 17
IN2_PIN = 27
ENA_PIN = 22

print("=" * 50)
print("L298N Motor Diagnostic Test")
print("=" * 50)
print(f"\nPin Configuration:")
print(f"  IN1 (Direction) : GPIO {IN1_PIN}")
print(f"  IN2 (Direction) : GPIO {IN2_PIN}")
print(f"  ENA (Speed PWM) : GPIO {ENA_PIN}")
print("\n" + "=" * 50)
print("Prerequisites Check:")
print("=" * 50)
print("✓ GPIO library imported")
print("✓ Running on Raspberry Pi")
print("\nWiring Check:")
print("  L298N Connections:")
print("    - GND     -> Raspberry Pi GND")
print("    - +5V/+12V -> Power Supply")
print("    - IN1     -> GPIO 17")
print("    - IN2     -> GPIO 27")
print("    - ENA     -> GPIO 22")
print("    - OUT1/OUT2 -> Motor A")
print("    - OUT3/OUT4 -> Motor B (if used)")
print("\n" + "=" * 50)

try:
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    GPIO.setup(IN1_PIN, GPIO.OUT)
    GPIO.setup(IN2_PIN, GPIO.OUT)
    GPIO.setup(ENA_PIN, GPIO.OUT)
    
    print("\n[TEST 1] GPIO Setup")
    print("=" * 50)
    print("✓ GPIO pins configured successfully")
    
    # Create PWM
    pwm = GPIO.PWM(ENA_PIN, 1000)
    pwm.start(0)
    print("✓ PWM initialized at 1000 Hz")
    
    # Test 1: IN1 HIGH, IN2 LOW (Forward)
    print("\n[TEST 2] Motor Forward Direction")
    print("=" * 50)
    print("Setting: IN1=HIGH, IN2=LOW")
    GPIO.output(IN1_PIN, GPIO.HIGH)
    GPIO.output(IN2_PIN, GPIO.LOW)
    pwm.ChangeDutyCycle(100)
    print("✓ Full speed forward (100%)")
    print("⚠ Motor should rotate in one direction")
    time.sleep(3)
    
    # Test 2: IN1 LOW, IN2 HIGH (Backward)
    print("\n[TEST 3] Motor Backward Direction")
    print("=" * 50)
    print("Setting: IN1=LOW, IN2=HIGH")
    GPIO.output(IN1_PIN, GPIO.LOW)
    GPIO.output(IN2_PIN, GPIO.HIGH)
    print("✓ Full speed backward (100%)")
    print("⚠ Motor should rotate in opposite direction")
    time.sleep(3)
    
    # Test 3: Both LOW (Stop)
    print("\n[TEST 4] Motor Stop")
    print("=" * 50)
    print("Setting: IN1=LOW, IN2=LOW, PWM=0%")
    GPIO.output(IN1_PIN, GPIO.LOW)
    GPIO.output(IN2_PIN, GPIO.LOW)
    pwm.ChangeDutyCycle(0)
    print("✓ Motor stopped")
    time.sleep(1)
    
    # Test 4: Speed control
    print("\n[TEST 5] Speed Control (Acceleration)")
    print("=" * 50)
    GPIO.output(IN1_PIN, GPIO.HIGH)
    GPIO.output(IN2_PIN, GPIO.LOW)
    for speed in [0, 25, 50, 75, 100]:
        pwm.ChangeDutyCycle(speed)
        print(f"Speed: {speed}%")
        time.sleep(1)
    
    GPIO.output(IN1_PIN, GPIO.LOW)
    GPIO.output(IN2_PIN, GPIO.LOW)
    pwm.ChangeDutyCycle(0)
    pwm.stop()
    
    print("\n" + "=" * 50)
    print("ALL TESTS COMPLETED")
    print("=" * 50)
    print("\n✓ If motor moved in tests, GPIO wiring is correct!")
    print("✗ If motor didn't move, check:")
    print("  1. Power supply to L298N is connected and sufficient")
    print("  2. Motor connections to L298N OUT1/OUT2 are secure")
    print("  3. GPIO pin numbers match actual connections")
    print("  4. L298N GND is connected to Raspberry Pi GND")
    
except RuntimeError as e:
    print(f"\n✗ GPIO Error: {e}")
    print("  Make sure you're running with sudo: sudo python3 test_motor.py")
except Exception as e:
    print(f"\n✗ Error: {e}")
finally:
    GPIO.cleanup()
    print("\n✓ GPIO cleanup complete")

#!/usr/bin/env python3
"""
GPIO Signal Diagnostic - Check which pins are actually sending signals
Run with: sudo python3 diagnose_pins.py
"""

import RPi.GPIO as GPIO
import time

print("\n" + "=" * 60)
print("GPIO PIN SIGNAL DIAGNOSTIC")
print("=" * 60)
print("\nUse a multimeter to check voltage on each pin during tests")
print("Expected: ~3.3V when HIGH, ~0V when LOW\n")

# Test pin configuration
TEST_PINS = {
    17: "IN1",
    27: "IN2", 
    22: "ENA (PWM)"
}

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup all pins
    for pin in TEST_PINS.keys():
        GPIO.setup(pin, GPIO.OUT)
        print(f"✓ GPIO {pin} ({TEST_PINS[pin]}) configured")
    
    print("\n" + "=" * 60)
    print("TEST 1: Individual Pin Toggling")
    print("=" * 60)
    
    for pin in TEST_PINS.keys():
        print(f"\nTesting GPIO {pin} ({TEST_PINS[pin]}):")
        
        # Set HIGH
        GPIO.output(pin, GPIO.HIGH)
        print(f"  Set HIGH - Check pin voltage with multimeter")
        print(f"  Pin should read ~3.3V")
        time.sleep(2)
        
        # Set LOW
        GPIO.output(pin, GPIO.LOW)
        print(f"  Set LOW - Pin should read ~0V")
        time.sleep(1)
        
        # Reset to LOW
        GPIO.output(pin, GPIO.LOW)
    
    print("\n" + "=" * 60)
    print("TEST 2: Motor Forward Simulation")
    print("=" * 60)
    print("\nSending FORWARD command (IN1=HIGH, IN2=LOW, ENA=100%):")
    GPIO.output(17, GPIO.HIGH)   # IN1 HIGH
    GPIO.output(27, GPIO.LOW)    # IN2 LOW
    
    pwm = GPIO.PWM(22, 1000)
    pwm.start(100)  # Full speed
    
    print("  GPIO 17 (IN1) -> HIGH (~3.3V)")
    print("  GPIO 27 (IN2) -> LOW (~0V)")
    print("  GPIO 22 (ENA) -> PWM 100%")
    print("\n  ✓ Check L298N output pins (OUT1/OUT2) with multimeter")
    print("  ✓ Should have ~12V across motor terminals")
    time.sleep(3)
    
    print("\n" + "=" * 60)
    print("TEST 3: Motor Backward Simulation")
    print("=" * 60)
    print("\nSending BACKWARD command (IN1=LOW, IN2=HIGH, ENA=100%):")
    GPIO.output(17, GPIO.LOW)    # IN1 LOW
    GPIO.output(27, GPIO.HIGH)   # IN2 HIGH
    
    print("  GPIO 17 (IN1) -> LOW (~0V)")
    print("  GPIO 27 (IN2) -> HIGH (~3.3V)")
    print("  GPIO 22 (ENA) -> PWM 100%")
    print("\n  ✓ Voltage should reverse on L298N outputs")
    time.sleep(3)
    
    print("\n" + "=" * 60)
    print("TEST 4: PWM Speed Control")
    print("=" * 60)
    print("\nTesting PWM speed variation (IN1=HIGH, IN2=LOW):")
    GPIO.output(17, GPIO.HIGH)
    GPIO.output(27, GPIO.LOW)
    
    for speed in [0, 25, 50, 75, 100]:
        pwm.ChangeDutyCycle(speed)
        print(f"  PWM {speed:3d}% - Frequency: 1000Hz")
        time.sleep(1)
    
    pwm.stop()
    GPIO.output(17, GPIO.LOW)
    GPIO.output(27, GPIO.LOW)
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS HELP")
    print("=" * 60)
    print("\nIf GPIO pins show correct voltage (3.3V HIGH, 0V LOW):")
    print("  ✓ Raspberry Pi GPIO is working correctly")
    print("  ✗ Problem is with L298N or motor wiring")
    print("\nIf GPIO pins show NO voltage change:")
    print("  ✗ Check Raspberry Pi GPIO or pin numbers are wrong")
    print("\nCommon L298N Issues:")
    print("  1. Missing external power supply to L298N")
    print("  2. Motor not connected to OUT1/OUT2")
    print("  3. Wrong pin numbers (check your actual wiring)")
    print("  4. L298N defective")
    
except Exception as e:
    print(f"✗ Error: {e}")
    print("  Make sure to run with: sudo python3 diagnose_pins.py")
finally:
    GPIO.cleanup()
    print("\n✓ GPIO cleanup complete\n")

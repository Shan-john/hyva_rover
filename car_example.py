#!/usr/bin/env python3
"""
Simple Dual Motor Control Example
Use this as a template for your robotics project
"""

import time
import sys
sys.path.insert(0, '/home/shan/Downloads/prccar/carprc')

from main_dual_motor import L298NDualMotor
from config import *

def car_forward(motors, speed=70, duration=3):
    """Move car forward"""
    print(f"Moving forward at {speed}% for {duration}s")
    motors.both_forward(speed, speed)
    time.sleep(duration)

def car_backward(motors, speed=70, duration=3):
    """Move car backward"""
    print(f"Moving backward at {speed}% for {duration}s")
    motors.both_backward(speed, speed)
    time.sleep(duration)

def car_stop(motors):
    """Stop car"""
    print("Stopping...")
    motors.both_stop()
    time.sleep(1)

def car_turn_left(motors, speed=70, duration=2):
    """Turn left"""
    print(f"Turning LEFT for {duration}s")
    motors.turn_left(50, 80)  # Motor A slower, Motor B faster
    time.sleep(duration)

def car_turn_right(motors, speed=70, duration=2):
    """Turn right"""
    print(f"Turning RIGHT for {duration}s")
    motors.turn_right(80, 50)  # Motor A faster, Motor B slower
    time.sleep(duration)

if __name__ == "__main__":
    motors = None
    try:
        motors = L298NDualMotor()
        print("\n" + "=" * 60)
        print("CAR MOVEMENT DEMO")
        print("=" * 60 + "\n")
        
        # Simple movement sequence
        car_forward(motors, 70, 2)
        car_stop(motors)
        
        car_turn_left(motors, 70, 1)
        car_stop(motors)
        
        car_turn_right(motors, 70, 1)
        car_stop(motors)
        
        car_backward(motors, 70, 2)
        car_stop(motors)
        
        print("\nDemo complete!")
        
    except KeyboardInterrupt:
        print("\nInterrupted!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if motors:
            motors.cleanup()

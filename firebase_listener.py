#!/usr/bin/env python3
"""
Firebase Realtime Database listener for motor control.
Reads joystick commands from Firebase and drives L298N dual motors.

Usage:
    sudo python3 firebase_listener.py

Requires:
    - firebase_credentials.json (download from Firebase Console)
    - pip install firebase-admin
"""

import sys
import os
import time
import threading
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================
# Firebase Setup
# ============================================
try:
    import firebase_admin
    from firebase_admin import credentials, db as firebase_db
except ImportError:
    print("✗ firebase-admin not installed. Run:")
    print("  pip install firebase-admin")
    sys.exit(1)

CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firebase_credentials.json")
DATABASE_URL = "https://hyva-rover-default-rtdb.firebaseio.com"

if not os.path.exists(CREDENTIALS_FILE):
    print("✗ firebase_credentials.json not found!")
    print("  Download it from Firebase Console:")
    print("  Project Settings → Service Accounts → Generate New Private Key")
    print(f"  Save it as: {CREDENTIALS_FILE}")
    sys.exit(1)

# Initialize Firebase Admin
cred = credentials.Certificate(CREDENTIALS_FILE)
firebase_admin.initialize_app(cred, {"databaseURL": DATABASE_URL})

print("✓ Firebase Admin initialized")

# ============================================
# Motor Setup
# ============================================
SIMULATION_MODE = False

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    from main_dual_motor import L298NDualMotor
    from config import MOTOR_DEFAULT_SPEED
except (ImportError, RuntimeError):
    SIMULATION_MODE = True
    MOTOR_DEFAULT_SPEED = 70
    print("⚠  RPi.GPIO not available — running in SIMULATION mode")

motors = None


def init_motors():
    global motors
    if not SIMULATION_MODE:
        try:
            motors = L298NDualMotor()
            print("✓ Motors initialized")
        except Exception as e:
            print(f"✗ Motor init failed: {e}")


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def apply_joystick(x, y):
    """
    Differential drive mapping:
    left_speed  = y + x
    right_speed = y - x
    """
    DEAD_ZONE = 5

    if abs(x) < DEAD_ZONE:
        x = 0
    if abs(y) < DEAD_ZONE:
        y = 0

    left_raw = clamp(y + x, -100, 100)
    right_raw = clamp(y - x, -100, 100)

    left_speed = abs(int(left_raw))
    right_speed = abs(int(right_raw))
    left_dir = "forward" if left_raw > 0 else ("backward" if left_raw < 0 else "stop")
    right_dir = "forward" if right_raw > 0 else ("backward" if right_raw < 0 else "stop")

    # Drive real motors
    if motors and not SIMULATION_MODE:
        if left_dir == "forward":
            motors.motor_a_forward(left_speed)
        elif left_dir == "backward":
            motors.motor_a_backward(left_speed)
        else:
            motors.motor_a_stop()

        if right_dir == "forward":
            motors.motor_b_forward(right_speed)
        elif right_dir == "backward":
            motors.motor_b_backward(right_speed)
        else:
            motors.motor_b_stop()

    state = {
        "motor_a": {"direction": left_dir, "speed": left_speed},
        "motor_b": {"direction": right_dir, "speed": right_speed},
    }

    # Write motor status back to Firebase
    try:
        firebase_db.reference("car/motor_status").set(state)
    except Exception as e:
        print(f"⚠ Firebase write error: {e}")

    return state


# ============================================
# Safety Timeout
# ============================================
last_command_time = time.time()
SAFETY_TIMEOUT = 0.8  # seconds — stop if no command for this long
already_stopped = True  # start as stopped


def safety_watchdog():
    """Stop motors if no joystick input received recently."""
    global last_command_time, already_stopped
    while True:
        time.sleep(0.3)
        if time.time() - last_command_time > SAFETY_TIMEOUT:
            if not already_stopped:
                apply_joystick(0, 0)
                already_stopped = True


# ============================================
# Firebase Listener
# ============================================
def on_joystick_change(event):
    """Called when /car/joystick changes in Firebase."""
    global last_command_time, already_stopped
    data = event.data

    if data is None:
        return

    # Handle both dict and path-level updates
    if isinstance(data, dict):
        x = data.get("x", 0)
        y = data.get("y", 0)
    else:
        # Partial update — ignore
        return

    last_command_time = time.time()
    already_stopped = False
    state = apply_joystick(x, y)
    print(f"  Joystick x={x:4}, y={y:4}  →  A: {state['motor_a']['direction']:8} {state['motor_a']['speed']:3}% | B: {state['motor_b']['direction']:8} {state['motor_b']['speed']:3}%")


def on_emergency_stop(event):
    """Called when /car/emergency_stop changes."""
    if event.data is not None:
        print("🛑 EMERGENCY STOP received!")
        apply_joystick(0, 0)


# ============================================
# Main
# ============================================
if __name__ == "__main__":
    init_motors()

    mode_label = "SIMULATION" if SIMULATION_MODE else "REAL GPIO"
    print("\n" + "=" * 60)
    print("FIREBASE MOTOR CONTROL LISTENER")
    print("=" * 60)
    print(f"  Mode:     {mode_label}")
    print(f"  Firebase: {DATABASE_URL}")
    print(f"  Timeout:  {SAFETY_TIMEOUT}s")
    print("=" * 60)
    print("Listening for joystick commands… (Ctrl+C to stop)\n")

    # Start safety watchdog
    watchdog = threading.Thread(target=safety_watchdog, daemon=True)
    watchdog.start()

    # Listen for joystick changes
    joystick_ref = firebase_db.reference("car/joystick")
    joystick_ref.listen(on_joystick_change)

    # Listen for emergency stop
    estop_ref = firebase_db.reference("car/emergency_stop")
    estop_ref.listen(on_emergency_stop)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⚠ Shutting down…")
    finally:
        apply_joystick(0, 0)
        if motors:
            motors.cleanup()
        if not SIMULATION_MODE:
            try:
                GPIO.cleanup()
            except Exception:
                pass
        print("✓ Stopped")

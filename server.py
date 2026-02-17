#!/usr/bin/env python3
"""
Flask + SocketIO server for joystick motor control.
Receives joystick {x, y} over WebSocket and drives L298N dual motors
using differential drive mapping.
"""

import sys
import os
import time
import threading

from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# ============================================
# GPIO / Motor Setup
# ============================================
# Try to import real GPIO and motor driver.
# If not on Raspberry Pi, fall back to simulation mode.
SIMULATION_MODE = False

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    from main_dual_motor import L298NDualMotor
    from config import MOTOR_DEFAULT_SPEED
except (ImportError, RuntimeError):
    SIMULATION_MODE = True
    MOTOR_DEFAULT_SPEED = 70
    print("⚠  RPi.GPIO not available — running in SIMULATION mode")


# ============================================
# Flask App
# ============================================
app = Flask(__name__)
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Motor state (shared between threads)
motor_state = {
    "motor_a": {"direction": "stop", "speed": 0},
    "motor_b": {"direction": "stop", "speed": 0},
}
motors = None


def init_motors():
    """Initialize real motors if available."""
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
    Map joystick (x, y) in range [-100, 100] to differential drive.
    x = steering (-100 left … +100 right)
    y = throttle (-100 backward … +100 forward)

    left_speed  = y + x
    right_speed = y - x
    Positive → forward, Negative → backward
    """
    global motor_state

    DEAD_ZONE = 5

    # Apply dead zone
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
        # Motor A (left)
        if left_dir == "forward":
            motors.motor_a_forward(left_speed)
        elif left_dir == "backward":
            motors.motor_a_backward(left_speed)
        else:
            motors.motor_a_stop()

        # Motor B (right)
        if right_dir == "forward":
            motors.motor_b_forward(right_speed)
        elif right_dir == "backward":
            motors.motor_b_backward(right_speed)
        else:
            motors.motor_b_stop()

    motor_state = {
        "motor_a": {"direction": left_dir, "speed": left_speed},
        "motor_b": {"direction": right_dir, "speed": right_speed},
    }
    return motor_state


# ============================================
# REST Endpoints
# ============================================
@app.route("/")
def index():
    return jsonify({"status": "ok", "simulation": SIMULATION_MODE})


@app.route("/status")
def status():
    return jsonify(motor_state)


@app.route("/stop")
def stop():
    if motors and not SIMULATION_MODE:
        motors.both_stop()
    motor_state["motor_a"] = {"direction": "stop", "speed": 0}
    motor_state["motor_b"] = {"direction": "stop", "speed": 0}
    return jsonify(motor_state)


# ============================================
# WebSocket Events
# ============================================
@socketio.on("connect")
def handle_connect():
    print("🔌 Client connected")
    emit("motor_status", motor_state)


@socketio.on("disconnect")
def handle_disconnect():
    print("🔌 Client disconnected — stopping motors")
    apply_joystick(0, 0)


@socketio.on("joystick")
def handle_joystick(data):
    """Receive joystick data: {x: -100..100, y: -100..100}"""
    x = data.get("x", 0)
    y = data.get("y", 0)
    # Negate Y so joystick-up = car-forward
    state = apply_joystick(x, -y)
    emit("motor_status", state)


@socketio.on("emergency_stop")
def handle_emergency_stop():
    print("🛑 EMERGENCY STOP")
    state = apply_joystick(0, 0)
    emit("motor_status", state)


# ============================================
# Main
# ============================================
if __name__ == "__main__":
    init_motors()
    print("\n" + "=" * 60)
    print("MOTOR CONTROL SERVER")
    print("=" * 60)
    mode_label = "SIMULATION" if SIMULATION_MODE else "REAL GPIO"
    print(f"  Mode:    {mode_label}")
    print(f"  Address: http://0.0.0.0:5000")
    print("=" * 60 + "\n")

    try:
        socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n⚠ Shutting down…")
    finally:
        if motors:
            motors.cleanup()
        if not SIMULATION_MODE:
            try:
                GPIO.cleanup()
            except Exception:
                pass
        print("✓ Server stopped")

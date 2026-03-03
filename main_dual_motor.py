import time
import gpiod
from gpiod.line import Direction, Value

# ============================================
# Motor & Hardware Configuration
# ============================================

# GPIO Pin Configuration - MOTOR A
GPIO_IN1_PIN = 27      # Motor A direction control pin 1
GPIO_IN2_PIN = 17      # Motor A direction control pin 2
GPIO_ENA_PIN = 22      # Motor A PWM speed control pin (0-100%)

# GPIO Pin Configuration - MOTOR B
GPIO_IN3_PIN = 23      # Motor B direction control pin 1
GPIO_IN4_PIN = 24      # Motor B direction control pin 2
GPIO_ENB_PIN = 25      # Motor B PWM speed control pin (0-100%)

# PWM Configuration
PWM_FREQUENCY = 1000   # Frequency in Hz

# Motor Configuration
MOTOR_MAX_SPEED = 100  # Maximum speed percentage (0-100)
MOTOR_DEFAULT_SPEED = 70  # Default rotation speed

# Debugging
VERBOSE_MODE = True    # Print debug information

# ============================================
# L298N Dual Motor Driver (Pi 5 Compatible via gpiod)
# ============================================

class L298NDualMotor:
    """Control two DC motors with L298N driver using gpiod (Pi 5 compatible)"""
    
    def __init__(self, chip_path='/dev/gpiochip4',
                 motor_a_pins=(GPIO_IN1_PIN, GPIO_IN2_PIN, GPIO_ENA_PIN),
                 motor_b_pins=(GPIO_IN3_PIN, GPIO_IN4_PIN, GPIO_ENB_PIN)):
        """
        Initialize L298N dual motor driver using gpiod
        """
        self.chip_path = chip_path
        self.pins_a = motor_a_pins
        self.pins_b = motor_b_pins
        
        # Combine all pins for a single request
        self.all_pins = list(motor_a_pins) + list(motor_b_pins)
        
        try:
            self.request = gpiod.request_lines(
                self.chip_path,
                consumer="L298NDualMotor",
                config={
                    tuple(self.all_pins): gpiod.LineSettings(
                        direction=Direction.OUTPUT, output_value=Value.INACTIVE
                    )
                },
            )
            
            self.motor_a_speed = 0
            self.motor_a_direction = "stop"
            self.motor_b_speed = 0
            self.motor_b_direction = "stop"
            
            if VERBOSE_MODE:
                print(f"\nInitializing L298N Dual Motor Driver (gpiod on {chip_path}):")
                print(f"  Motor A: IN1={self.pins_a[0]}, IN2={self.pins_a[1]}, ENA={self.pins_a[2]}")
                print(f"  Motor B: IN3={self.pins_b[0]}, IN4={self.pins_b[1]}, ENB={self.pins_b[2]}")
                print("✓ Both motors initialized")
        except Exception as e:
            print(f"✗ Failed to initialize gpiod on {chip_path}: {e}")
            raise
    
    def _set_motor(self, motor_pins, forward=True, speed=0):
        """Helper to set motor state. Speed > 0 turns it ON (digital, no PWM)"""
        in1, in2, en = motor_pins
        if speed == 0:
            self.request.set_value(in1, Value.INACTIVE)
            self.request.set_value(in2, Value.INACTIVE)
            self.request.set_value(en, Value.INACTIVE)
        else:
            if forward:
                self.request.set_value(in1, Value.ACTIVE)
                self.request.set_value(in2, Value.INACTIVE)
            else:
                self.request.set_value(in1, Value.INACTIVE)
                self.request.set_value(in2, Value.ACTIVE)
            self.request.set_value(en, Value.ACTIVE)

    # ========== MOTOR A CONTROLS ==========
    
    def motor_a_forward(self, speed=MOTOR_DEFAULT_SPEED):
        self._set_motor(self.pins_a, forward=True, speed=speed)
        self.motor_a_speed = speed
        self.motor_a_direction = "forward"
        if VERBOSE_MODE: print(f"[Motor A] FORWARD at {speed}%")
    
    def motor_a_backward(self, speed=MOTOR_DEFAULT_SPEED):
        self._set_motor(self.pins_a, forward=False, speed=speed)
        self.motor_a_speed = speed
        self.motor_a_direction = "backward"
        if VERBOSE_MODE: print(f"[Motor A] BACKWARD at {speed}%")
    
    def motor_a_stop(self):
        self._set_motor(self.pins_a, speed=0)
        self.motor_a_speed = 0
        self.motor_a_direction = "stop"
        if VERBOSE_MODE: print("[Motor A] STOPPED")
    
    # ========== MOTOR B CONTROLS ==========
    
    def motor_b_forward(self, speed=MOTOR_DEFAULT_SPEED):
        self._set_motor(self.pins_b, forward=True, speed=speed)
        self.motor_b_speed = speed
        self.motor_b_direction = "forward"
        if VERBOSE_MODE: print(f"[Motor B] FORWARD at {speed}%")
    
    def motor_b_backward(self, speed=MOTOR_DEFAULT_SPEED):
        self._set_motor(self.pins_b, forward=False, speed=speed)
        self.motor_b_speed = speed
        self.motor_b_direction = "backward"
        if VERBOSE_MODE: print(f"[Motor B] BACKWARD at {speed}%")
    
    def motor_b_stop(self):
        self._set_motor(self.pins_b, speed=0)
        self.motor_b_speed = 0
        self.motor_b_direction = "stop"
        if VERBOSE_MODE: print("[Motor B] STOPPED")
    
    # ========== COMBINED CONTROLS ==========
    
    def both_forward(self, speed_a=MOTOR_DEFAULT_SPEED, speed_b=MOTOR_DEFAULT_SPEED):
        self.motor_a_forward(speed_a)
        self.motor_b_forward(speed_b)
    
    def both_backward(self, speed_a=MOTOR_DEFAULT_SPEED, speed_b=MOTOR_DEFAULT_SPEED):
        self.motor_a_backward(speed_a)
        self.motor_b_backward(speed_b)
    
    def both_stop(self):
        self.motor_a_stop()
        self.motor_b_stop()
    
    def turn_left(self, speed_a=MOTOR_DEFAULT_SPEED, speed_b=None):
        if speed_b is None: speed_b = MOTOR_DEFAULT_SPEED
        self.motor_a_forward(speed_a)
        self.motor_b_forward(speed_b)
    
    def turn_right(self, speed_a=None, speed_b=MOTOR_DEFAULT_SPEED):
        if speed_a is None: speed_a = MOTOR_DEFAULT_SPEED
        self.motor_a_forward(speed_a)
        self.motor_b_forward(speed_b)

    # ========== HIGH-LEVEL ACTIONS ==========

    def wiggle(self, count=3, duration=0.15, stop_event=None):
        """Oscillate left/right — both motors same direction to spin in place"""
        for _ in range(count):
            if stop_event and stop_event.is_set(): break
            self.both_forward()
            time.sleep(duration)
            
            if stop_event and stop_event.is_set(): break
            self.both_backward()
            time.sleep(duration)
        self.both_stop()

    def spin_180(self, stop_event=None):
        """Half rotation (approx 1.25s) — both motors same direction to spin in place"""
        start_time = time.time()
        while time.time() - start_time < 1.25:
            if stop_event and stop_event.is_set(): break
            self.both_forward()
            time.sleep(0.05)
        self.both_stop()

    def spin_360(self, stop_event=None):
        """Full rotation (approx 2.5s) — both motors same direction to spin in place"""
        start_time = time.time()
        while time.time() - start_time < 2.5:
            if stop_event and stop_event.is_set(): break
            self.both_forward()
            time.sleep(0.05)
        self.both_stop()
    
    def get_status(self):
        return {
            'motor_a': {'direction': self.motor_a_direction, 'speed': self.motor_a_speed},
            'motor_b': {'direction': self.motor_b_direction, 'speed': self.motor_b_speed}
        }
    
    def cleanup(self):
        self.both_stop()
        if hasattr(self, 'request'):
            self.request.release()
        if VERBOSE_MODE:
            print("✓ Motor cleanup complete")


if __name__ == "__main__":
    print("\nL298N DUAL MOTOR DRIVER - PI 5 COMPATIBLE (gpiod)")
    motors = L298NDualMotor()
    try:
        print("[TEST] Both motors FORWARD at 50% for 2s")
        motors.both_forward(50, 50)
        time.sleep(2)
        motors.both_stop()
        print("✓ Test complete")
    finally:
        motors.cleanup()

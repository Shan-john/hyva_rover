import time
import RPi.GPIO as GPIO
from config import *

# Set GPIO mode (REAL GPIO ONLY - NO MOCK)
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

print("\n" + "=" * 60)
print("L298N DUAL MOTOR DRIVER - REAL GPIO MODE")
print("=" * 60)
print(f"Running on REAL Raspberry Pi Hardware")
print(f"Motor A (Left):  IN1={GPIO_IN1_PIN}, IN2={GPIO_IN2_PIN}, ENA={GPIO_ENA_PIN}")
print(f"Motor B (Right): IN3={GPIO_IN3_PIN}, IN4={GPIO_IN4_PIN}, ENB={GPIO_ENB_PIN}")
print("=" * 60)

# ============================================
# L298N Dual Motor Driver
# ============================================

class L298NDualMotor:
    """Control two DC motors with L298N driver"""
    
    def __init__(self, motor_a_pins=(GPIO_IN1_PIN, GPIO_IN2_PIN, GPIO_ENA_PIN),
                 motor_b_pins=(GPIO_IN3_PIN, GPIO_IN4_PIN, GPIO_ENB_PIN),
                 pwm_frequency=PWM_FREQUENCY):
        """Initialize L298N dual motor driver"""
        # Motor A configuration
        self.motor_a_in1, self.motor_a_in2, self.motor_a_ena = motor_a_pins
        self.motor_a_speed = 0
        self.motor_a_direction = "stop"
        
        # Motor B configuration
        self.motor_b_in3, self.motor_b_in4, self.motor_b_enb = motor_b_pins
        self.motor_b_speed = 0
        self.motor_b_direction = "stop"
        
        if VERBOSE_MODE:
            print(f"\nInitializing L298N Dual Motor Driver:")
            print(f"  Motor A (Left):  IN1={self.motor_a_in1}, IN2={self.motor_a_in2}, ENA={self.motor_a_ena}")
            print(f"  Motor B (Right): IN3={self.motor_b_in3}, IN4={self.motor_b_in4}, ENB={self.motor_b_enb}")
        
        # Setup Motor A pins
        GPIO.setup(self.motor_a_in1, GPIO.OUT)
        GPIO.setup(self.motor_a_in2, GPIO.OUT)
        GPIO.setup(self.motor_a_ena, GPIO.OUT)
        
        # Setup Motor B pins
        GPIO.setup(self.motor_b_in3, GPIO.OUT)
        GPIO.setup(self.motor_b_in4, GPIO.OUT)
        GPIO.setup(self.motor_b_enb, GPIO.OUT)
        
        # Initialize PWM for Motor A
        self.pwm_a = GPIO.PWM(self.motor_a_ena, pwm_frequency)
        self.pwm_a.start(0)
        
        # Initialize PWM for Motor B
        self.pwm_b = GPIO.PWM(self.motor_b_enb, pwm_frequency)
        self.pwm_b.start(0)
        
        if VERBOSE_MODE:
            print("✓ Both motors initialized")
    
    # ========== MOTOR A (LEFT) CONTROLS ==========
    
    def motor_a_forward(self, speed=MOTOR_DEFAULT_SPEED):
        """Move Motor A forward"""
        speed = max(0, min(100, speed))
        GPIO.output(self.motor_a_in1, GPIO.HIGH)
        GPIO.output(self.motor_a_in2, GPIO.LOW)
        self.pwm_a.ChangeDutyCycle(speed)
        self.motor_a_speed = speed
        self.motor_a_direction = "forward"
        if VERBOSE_MODE:
            print(f"[Motor A - LEFT] FORWARD at {speed}%")
    
    def motor_a_backward(self, speed=MOTOR_DEFAULT_SPEED):
        """Move Motor A backward"""
        speed = max(0, min(100, speed))
        GPIO.output(self.motor_a_in1, GPIO.LOW)
        GPIO.output(self.motor_a_in2, GPIO.HIGH)
        self.pwm_a.ChangeDutyCycle(speed)
        self.motor_a_speed = speed
        self.motor_a_direction = "backward"
        if VERBOSE_MODE:
            print(f"[Motor A - LEFT] BACKWARD at {speed}%")
    
    def motor_a_stop(self):
        """Stop Motor A"""
        GPIO.output(self.motor_a_in1, GPIO.LOW)
        GPIO.output(self.motor_a_in2, GPIO.LOW)
        self.pwm_a.ChangeDutyCycle(0)
        self.motor_a_speed = 0
        self.motor_a_direction = "stop"
        if VERBOSE_MODE:
            print("[Motor A - LEFT] STOPPED")
    
    def motor_a_set_speed(self, speed):
        """Change Motor A speed"""
        speed = max(0, min(100, speed))
        self.pwm_a.ChangeDutyCycle(speed)
        self.motor_a_speed = speed
        if VERBOSE_MODE:
            print(f"[Motor A - LEFT] Speed: {speed}%")
    
    # ========== MOTOR B (RIGHT) CONTROLS ==========
    
    def motor_b_forward(self, speed=MOTOR_DEFAULT_SPEED):
        """Move Motor B forward"""
        speed = max(0, min(100, speed))
        GPIO.output(self.motor_b_in3, GPIO.HIGH)
        GPIO.output(self.motor_b_in4, GPIO.LOW)
        self.pwm_b.ChangeDutyCycle(speed)
        self.motor_b_speed = speed
        self.motor_b_direction = "forward"
        if VERBOSE_MODE:
            print(f"[Motor B - RIGHT] FORWARD at {speed}%")
    
    def motor_b_backward(self, speed=MOTOR_DEFAULT_SPEED):
        """Move Motor B backward"""
        speed = max(0, min(100, speed))
        GPIO.output(self.motor_b_in3, GPIO.LOW)
        GPIO.output(self.motor_b_in4, GPIO.HIGH)
        self.pwm_b.ChangeDutyCycle(speed)
        self.motor_b_speed = speed
        self.motor_b_direction = "backward"
        if VERBOSE_MODE:
            print(f"[Motor B - RIGHT] BACKWARD at {speed}%")
    
    def motor_b_stop(self):
        """Stop Motor B"""
        GPIO.output(self.motor_b_in3, GPIO.LOW)
        GPIO.output(self.motor_b_in4, GPIO.LOW)
        self.pwm_b.ChangeDutyCycle(0)
        self.motor_b_speed = 0
        self.motor_b_direction = "stop"
        if VERBOSE_MODE:
            print("[Motor B - RIGHT] STOPPED")
    
    def motor_b_set_speed(self, speed):
        """Change Motor B speed"""
        speed = max(0, min(100, speed))
        self.pwm_b.ChangeDutyCycle(speed)
        self.motor_b_speed = speed
        if VERBOSE_MODE:
            print(f"[Motor B - RIGHT] Speed: {speed}%")
    
    # ========== BOTH MOTORS CONTROLS ==========
    
    def both_forward(self, speed_a=MOTOR_DEFAULT_SPEED, speed_b=MOTOR_DEFAULT_SPEED):
        """Move both motors forward at same time"""
        self.motor_a_forward(speed_a)
        self.motor_b_forward(speed_b)
    
    def both_backward(self, speed_a=MOTOR_DEFAULT_SPEED, speed_b=MOTOR_DEFAULT_SPEED):
        """Move both motors backward at same time"""
        self.motor_a_backward(speed_a)
        self.motor_b_backward(speed_b)
    
    def both_stop(self):
        """Stop both motors at same time"""
        self.motor_a_stop()
        self.motor_b_stop()
    
    def get_status(self):
        """Get status of both motors"""
        return {
            'motor_a': {'direction': self.motor_a_direction, 'speed': self.motor_a_speed},
            'motor_b': {'direction': self.motor_b_direction, 'speed': self.motor_b_speed}
        }
    
    def cleanup(self):
        """Cleanup and release GPIO"""
        self.both_stop()
        self.pwm_a.stop()
        self.pwm_b.stop()
        if VERBOSE_MODE:
            print("✓ Motor cleanup complete")


# ============================================
# Example Usage
# ============================================
if __name__ == "__main__":
    print("\n✓ Dual motor controller initializing...")
    
    motors = None
    try:
        motors = L298NDualMotor()
        print("✓ Both motors initialized successfully!")
        print(f"✓ BOTH motors running continuously at {MOTOR_DEFAULT_SPEED}% speed")
        print("Press Ctrl+C to stop\n")
        
        # Start BOTH motors forward at same time
        motors.both_forward(MOTOR_DEFAULT_SPEED, MOTOR_DEFAULT_SPEED)
        
        # Keep both motors running continuously
        counter = 0
        while True:
            time.sleep(1)
            counter += 1
            status = motors.get_status()
            print(f"[{counter}s] A: {status['motor_a']['direction']:8} @ {status['motor_a']['speed']:3}% | B: {status['motor_b']['direction']:8} @ {status['motor_b']['speed']:3}%")
        
    except KeyboardInterrupt:
        print("\n⚠ Stopping both motors...")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        print(f"✗ Make sure you:")
        print(f"  1. Run with sudo: sudo python3 main.py")
        print(f"  2. Check GPIO pins in config.py")
        print(f"  3. Verify L298N connections for both motors")
    finally:
        if motors:
            motors.both_stop()
            motors.cleanup()
        GPIO.cleanup()
        print("✓ GPIO cleanup complete")

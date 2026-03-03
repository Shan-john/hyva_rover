import gpiod
from gpiod.line import Direction, Value
import time
from config import (
    GPIO_IN1_PIN, GPIO_IN2_PIN, GPIO_ENA_PIN,
    GPIO_IN3_PIN, GPIO_IN4_PIN, GPIO_ENB_PIN
)

def test_pins(chip_path, pin_dict):
    print(f"Opening {chip_path}...")
    try:
        with gpiod.request_lines(
            chip_path,
            consumer="test_gpio_v2",
            config={
                tuple(pin_dict.values()): gpiod.LineSettings(
                    direction=Direction.OUTPUT, output_value=Value.INACTIVE
                )
            },
        ) as request:
            for name, offset in pin_dict.items():
                print(f"Testing {name} (GPIO {offset})...")
                print(f"  Setting {name} ACTIVE")
                request.set_value(offset, Value.ACTIVE)
                time.sleep(1)
                
                print(f"  Setting {name} INACTIVE")
                request.set_value(offset, Value.INACTIVE)
                time.sleep(0.5)
                
            print("\n--- Summary ---")
            print("All configured GPIO pins were toggled successfully.")
            print("If the motors didn't' move, check the power supply to the L298N.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Raspberry Pi 5 gpiochip4
    pins = {
        "Motor A IN1": GPIO_IN1_PIN,
        "Motor A IN2": GPIO_IN2_PIN,
        "Motor A ENA": GPIO_ENA_PIN,
        "Motor B IN3": GPIO_IN3_PIN,
        "Motor B IN4": GPIO_IN4_PIN,
        "Motor B ENB": GPIO_ENB_PIN
    }
    
    test_pins('/dev/gpiochip4', pins)

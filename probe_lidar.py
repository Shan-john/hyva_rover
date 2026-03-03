import sys
import serial
from rplidar import RPLidar

def probe_lidar(port, baudrate):
    print(f"Probing {port} at {baudrate} baud...")
    lidar = None
    try:
        lidar = RPLidar(port, baudrate=baudrate)
        info = lidar.get_info()
        print(f"✓ Success! Info: {info}")
        health = lidar.get_health()
        print(f"✓ Health: {health}")
        lidar.disconnect()
        return True
    except Exception as e:
        print(f"✗ Failed at {baudrate}: {e}")
        if lidar:
            try: lidar.disconnect()
            except: pass
    return False

if __name__ == "__main__":
    port = "/dev/ttyUSB0"
    bauds = [115200, 256000, 921600, 230400]
    for b in bauds:
        if probe_lidar(port, b):
            print(f"\nFound working baud rate: {b}")
            sys.exit(0)
    print("\nCould not find a working baud rate.")

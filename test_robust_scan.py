import time
import serial
from rplidar import RPLidar

def test_robust_scan():
    port = "/dev/ttyUSB0"
    baud = 115200
    print(f"Testing robust scan on {port}...")
    lidar = None
    try:
        lidar = RPLidar(port, baudrate=baud, timeout=3)
        print("✓ Connected. Resetting LiDAR...")
        lidar.reset()
        time.sleep(2)  # Wait for reset
        
        print("✓ Getting info...")
        print(f"  Info: {lidar.get_info()}")
        
        print("✓ Starting motor...")
        lidar.start_motor()
        time.sleep(2)  # Give motor time to stabilize
        
        # Clear any garbage from buffer
        print("✓ Clearing buffer...")
        lidar._serial.reset_input_buffer()
        
        print("✓ Starting scan (iter_measurments)...")
        count = 0
        # Try iter_measurments instead of iter_scans for more granular control
        for meas in lidar.iter_measurements():
            new_scan, quality, angle, distance = meas
            if distance > 0:
                print(f"✓ Received meas: ang={angle:.1f}, dist={distance:.1f}")
                count += 1
            if count >= 20:
                break
        
        print("✓ Robust scan test success.")
    except Exception as e:
        print(f"✗ Scan failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if lidar:
            print("Cleaning up...")
            try:
                lidar.stop()
                lidar.stop_motor()
                lidar.disconnect()
            except: pass

if __name__ == "__main__":
    test_robust_scan()

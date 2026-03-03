import time
from rplidar import RPLidar

def test_single_process_scan():
    port = "/dev/ttyUSB0"
    baud = 115200
    print(f"Testing single process scan on {port}...")
    lidar = None
    try:
        lidar = RPLidar(port, baudrate=baud)
        print("✓ Connected. Starting motor...")
        lidar.start_motor()
        time.sleep(1)
        
        print("✓ Starting scan...")
        count = 0
        for scan in lidar.iter_scans():
            print(f"✓ Received scan {count+1} with {len(scan)} points")
            count += 1
            if count >= 5:
                break
        
        print("✓ Scan test success.")
    except Exception as e:
        print(f"✗ Scan failed: {e}")
    finally:
        if lidar:
            print("Cleaning up...")
            lidar.stop()
            lidar.stop_motor()
            lidar.disconnect()

if __name__ == "__main__":
    test_single_process_scan()

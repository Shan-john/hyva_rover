import sys
import os
import time
from lidar_scanner import LidarScanner

def test_lidar():
    print("Testing LiDAR Scanner...")
    scanner = LidarScanner()
    if scanner.start():
        print("✓ Scanner started. Waiting for data...")
        start_time = time.time()
        while time.time() - start_time < 5:
            scan = scanner.get_latest_scan()
            if scan:
                print(f"✓ Received scan with {len(scan['points'])} points")
                scanner.stop()
                return True
            time.sleep(0.5)
        print("✗ Timeout waiting for scan data")
        scanner.stop()
    else:
        print("✗ Failed to start scanner")
    return False

if __name__ == "__main__":
    test_lidar()

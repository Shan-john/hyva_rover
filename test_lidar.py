#!/usr/bin/env python3
"""Minimal LiDAR test — modeled directly after YDLidar SDK tri_test.py"""

import sys
import os

# Add SDK build path
sdk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "lidar", "YDLidar-SDK", "build", "python")
if os.path.isdir(sdk_path):
    sys.path.insert(0, sdk_path)

import ydlidar
import time

# List available ports
ports = ydlidar.lidarPortList()
print(f"Available ports: {ports}")
port = "/dev/ttyUSB0"
for key, value in ports.items():
    port = value
    print(f"Using port: {port}")

laser = ydlidar.CYdLidar()
laser.setlidaropt(ydlidar.LidarPropSerialPort, port)
laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, 230400)
laser.setlidaropt(ydlidar.LidarPropLidarType, ydlidar.TYPE_TRIANGLE)
laser.setlidaropt(ydlidar.LidarPropDeviceType, ydlidar.YDLIDAR_TYPE_SERIAL)
laser.setlidaropt(ydlidar.LidarPropScanFrequency, 10.0)
laser.setlidaropt(ydlidar.LidarPropSampleRate, 5)
laser.setlidaropt(ydlidar.LidarPropSingleChannel, False)
laser.setlidaropt(ydlidar.LidarPropMaxAngle, 180.0)
laser.setlidaropt(ydlidar.LidarPropMinAngle, -180.0)
laser.setlidaropt(ydlidar.LidarPropMaxRange, 12.0)
laser.setlidaropt(ydlidar.LidarPropMinRange, 0.1)
laser.setlidaropt(ydlidar.LidarPropIntenstiy, False)

ret = laser.initialize()
if ret:
    print("✓ LiDAR initialized")
    ret = laser.turnOn()
    if ret:
        print("✓ LiDAR turnOn success!")
    else:
        print("✗ LiDAR turnOn FAILED")
else:
    print("✗ LiDAR initialize FAILED")
    sys.exit(1)

scan = ydlidar.LaserScan()
count = 0
while ret and ydlidar.os_isOk() and count < 5:
    r = laser.doProcessSimple(scan)
    if r:
        count += 1
        print(f"Scan {count}: {scan.points.size()} points, "
              f"stamp={scan.stamp}, "
              f"config.scan_time={scan.config.scan_time}")
    else:
        print("Failed to get Lidar Data")
    time.sleep(0.5)

laser.turnOff()
laser.disconnecting()
print("✓ Done")

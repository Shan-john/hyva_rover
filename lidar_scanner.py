#!/usr/bin/env python3
"""
LiDAR Scanner Module — wraps YDLidar G2 SDK for 2D scanning.

Runs the actual SDK in a **child process** so that the SDK's own signal
handlers and any C++ segfaults cannot crash the Flask server.
Scan data is sent back to the parent via a multiprocessing.Queue.
"""

import math
import time
import threading
import multiprocessing as mp
import sys
import os
import signal

# Add the YDLidar SDK build dir to path (needed when running under sudo)
_sdk_build_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "lidar", "YDLidar-SDK", "build", "python"
)
if os.path.isdir(_sdk_build_path):
    sys.path.insert(0, _sdk_build_path)

try:
    import ydlidar
    LIDAR_AVAILABLE = True
except ImportError:
    LIDAR_AVAILABLE = False
    print("⚠  ydlidar SDK not available — LiDAR features disabled")

from config import (
    LIDAR_PORT, LIDAR_BAUDRATE, LIDAR_SCAN_FREQUENCY,
    LIDAR_SAMPLE_RATE, LIDAR_MAX_RANGE, LIDAR_MIN_RANGE, VERBOSE_MODE
)


# ------------------------------------------------------------------
# Child-process worker (runs the ydlidar C SDK)
# ------------------------------------------------------------------

def _lidar_worker(out_queue: mp.Queue, stop_evt: mp.Event, cfg: dict):
    """
    Runs inside a separate process.
    Initialises the LiDAR, continuously scans, and pushes parsed
    frames into *out_queue*.  Exits when *stop_evt* is set.
    """
    # Ignore SIGINT in the child — let parent handle it
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # Make sure SDK path is available in the child too
    sdk = cfg.get("sdk_path")
    if sdk and os.path.isdir(sdk):
        sys.path.insert(0, sdk)

    try:
        import ydlidar as yd
    except ImportError:
        out_queue.put({"type": "error", "msg": "ydlidar SDK not found in child"})
        return

    try:
        yd.os_init()
        laser = yd.CYdLidar()
        laser.setlidaropt(yd.LidarPropSerialPort, cfg["port"])
        laser.setlidaropt(yd.LidarPropSerialBaudrate, cfg["baud"])
        laser.setlidaropt(yd.LidarPropLidarType, yd.TYPE_TRIANGLE)
        laser.setlidaropt(yd.LidarPropDeviceType, yd.YDLIDAR_TYPE_SERIAL)
        laser.setlidaropt(yd.LidarPropScanFrequency, cfg["freq"])
        laser.setlidaropt(yd.LidarPropSampleRate, cfg["sample_rate"])
        laser.setlidaropt(yd.LidarPropSingleChannel, False)
        laser.setlidaropt(yd.LidarPropMaxAngle, 180.0)
        laser.setlidaropt(yd.LidarPropMinAngle, -180.0)
        laser.setlidaropt(yd.LidarPropMaxRange, cfg["max_range"])
        laser.setlidaropt(yd.LidarPropMinRange, cfg["min_range"])
        laser.setlidaropt(yd.LidarPropIntenstiy, False)

        if not laser.initialize():
            out_queue.put({"type": "error", "msg": "LiDAR initialize() failed"})
            return

        if not laser.turnOn():
            out_queue.put({"type": "error", "msg": "LiDAR turnOn() failed"})
            try:
                laser.disconnecting()
            except Exception:
                pass
            return

        out_queue.put({"type": "started"})

        scan = yd.LaserScan()
        while not stop_evt.is_set():
            r = laser.doProcessSimple(scan)
            if r and scan.points.size() > 5:
                points = []
                for pt in scan.points:
                    d = pt.range
                    if d <= 0.01:
                        continue
                    a = pt.angle
                    points.append({
                        "angle": round(math.degrees(a), 2),
                        "distance": round(d, 4),
                        "x": round(d * math.cos(a), 4),
                        "y": round(d * math.sin(a), 4),
                    })
                # Non-blocking put — drop oldest frame if queue full
                try:
                    out_queue.put_nowait({
                        "type": "scan",
                        "timestamp": time.time(),
                        "point_count": len(points),
                        "points": points,
                    })
                except Exception:
                    pass  # queue full, drop frame
            time.sleep(0.02)

    except Exception as e:
        out_queue.put({"type": "error", "msg": str(e)})
    finally:
        try:
            laser.turnOff()
            laser.disconnecting()
        except Exception:
            pass


# ------------------------------------------------------------------
# Main-process scanner API
# ------------------------------------------------------------------

class LidarScanner:
    """Controls the YDLidar G2 via a child process and provides scan data."""

    def __init__(self):
        self._process = None
        self._queue = None
        self._stop_evt = None
        self._reader_thread = None
        self.running = False
        self.latest_scan = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Spawn the child process and start scanning. Returns True on success."""
        if not LIDAR_AVAILABLE:
            print("⚠  LiDAR SDK not installed — cannot start")
            return False

        if self.running:
            return True

        self._queue = mp.Queue(maxsize=10)
        self._stop_evt = mp.Event()

        cfg = {
            "port": LIDAR_PORT,
            "baud": LIDAR_BAUDRATE,
            "freq": LIDAR_SCAN_FREQUENCY,
            "sample_rate": LIDAR_SAMPLE_RATE,
            "max_range": LIDAR_MAX_RANGE,
            "min_range": LIDAR_MIN_RANGE,
            "sdk_path": _sdk_build_path,
        }

        self._process = mp.Process(target=_lidar_worker,
                                   args=(self._queue, self._stop_evt, cfg),
                                   daemon=True)
        self._process.start()

        # Wait for either "started" or "error"
        try:
            msg = self._queue.get(timeout=15)
        except Exception:
            msg = {"type": "error", "msg": "timeout waiting for LiDAR worker"}

        if msg.get("type") != "started":
            print(f"✗ LiDAR start failed: {msg.get('msg', 'unknown')}")
            self._cleanup_process()
            return False

        self.running = True
        # Start background reader thread
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

        if VERBOSE_MODE:
            print("✓ LiDAR scanning started (subprocess)")
        return True

    def stop(self):
        """Stop scanning."""
        self.running = False
        if self._stop_evt:
            self._stop_evt.set()
        if self._reader_thread:
            self._reader_thread.join(timeout=2)
        self._cleanup_process()
        if VERBOSE_MODE:
            print("✓ LiDAR scanning stopped")

    def disconnect(self):
        """Fully disconnect from LiDAR."""
        self.stop()

    def _cleanup_process(self):
        """Forcefully clean up the child process."""
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=3)
            if self._process.is_alive():
                self._process.kill()
        self._process = None
        self._queue = None
        self._stop_evt = None

    # ------------------------------------------------------------------
    # Reader thread (runs in main process)
    # ------------------------------------------------------------------

    def _reader_loop(self):
        """Drain frames from the child process queue into latest_scan."""
        while self.running:
            try:
                msg = self._queue.get(timeout=0.5)
                if msg["type"] == "scan":
                    with self._lock:
                        self.latest_scan = msg
                elif msg["type"] == "error":
                    print(f"⚠ LiDAR worker error: {msg['msg']}")
                    self.running = False
                    break
            except Exception:
                # Queue.get timeout — check if process is still alive
                if self._process and not self._process.is_alive():
                    print("⚠ LiDAR worker process died")
                    self.running = False
                    break

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_latest_scan(self):
        """Return the most recent scan data dict (or None)."""
        with self._lock:
            return self.latest_scan

    @property
    def is_running(self):
        return self.running

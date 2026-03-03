#!/usr/bin/env python3
"""
LiDAR Scanner Module — wraps RPLidar (A1/A2) for 2D scanning.

Runs the actual library in a **child process** so that any USB serial
hangs or SDK errors cannot crash the Flask server.
Scan data is sent back to the parent via a multiprocessing.Queue.
"""

import math
import time
import threading
import multiprocessing as mp
import sys
import os
import signal

try:
    from rplidar import RPLidar, RPLidarException
    LIDAR_AVAILABLE = True
except ImportError:
    LIDAR_AVAILABLE = False
    print("⚠  rplidar library not available — LiDAR features disabled")

from config import (
    LIDAR_PORT, LIDAR_BAUDRATE, LIDAR_SCAN_FREQUENCY,
    LIDAR_MAX_RANGE, LIDAR_MIN_RANGE, VERBOSE_MODE
)


# ------------------------------------------------------------------
# Child-process worker (runs the rplidar library)
# ------------------------------------------------------------------

def _lidar_worker(out_queue: mp.Queue, stop_evt: mp.Event, cfg: dict):
    """
    Runs inside a separate process.
    Initialises the LiDAR, continuously scans, and pushes parsed
    frames into *out_queue*.  Exits when *stop_evt* is set.
    """
    # Ignore SIGINT in the child — let parent handle it
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    if not LIDAR_AVAILABLE:
        out_queue.put({"type": "error", "msg": "rplidar library not found in child"})
        return

    lidar = None
    try:
        lidar = RPLidar(cfg["port"], baudrate=cfg["baud"], timeout=3)

        # Robust startup sequence:
        # 1. Stop any active scan/motor first
        try:
            lidar.stop()
            lidar.stop_motor()
        except Exception:
            pass
        time.sleep(0.5)

        # 2. Clear serial buffer of any leftover bytes
        try:
            lidar._serial.reset_input_buffer()
            lidar._serial.reset_output_buffer()
        except Exception:
            pass
        time.sleep(0.3)

        # 3. Start motor and wait for spin-up
        lidar.start_motor()
        time.sleep(2)  # Give motor adequate time to reach full speed

        # 4. Clear buffer again after motor start vibration settles garbage
        try:
            lidar._serial.reset_input_buffer()
        except Exception:
            pass
        time.sleep(0.3)

        # 5. Confirm health
        health = lidar.get_health()
        if health[0] != 'Good':
            out_queue.put({"type": "error", "msg": f"LiDAR health bad: {health}"})
            lidar.stop()
            lidar.stop_motor()
            lidar.disconnect()
            return

        out_queue.put({"type": "started"})

        scan_error_count = 0
        MAX_CONSECUTIVE_ERRORS = 5

        while not stop_evt.is_set():
            try:
                # iter_scans gives lists of (quality, angle, distance_mm)
                for scan in lidar.iter_scans(max_buf_meas=500):
                    if stop_evt.is_set():
                        break

                    # Reset error counter on a successful scan
                    scan_error_count = 0

                    if len(scan) < 5:
                        continue

                    points = []
                    for _, angle, dist_mm in scan:
                        d = dist_mm / 1000.0  # Convert to metres
                        if d < cfg["min_range"] or d > cfg["max_range"]:
                            continue

                        a_rad = math.radians(angle)
                        points.append({
                            "angle": round(angle, 2),
                            "distance": round(d, 4),
                            "x": round(d * math.cos(a_rad), 4),
                            "y": round(d * math.sin(a_rad), 4),
                        })

                    if not points:
                        continue

                    # Non-blocking put — drop oldest frame if queue full
                    try:
                        while out_queue.full():
                            try:
                                out_queue.get_nowait()
                            except Exception:
                                break

                        out_queue.put_nowait({
                            "type": "scan",
                            "timestamp": time.time(),
                            "point_count": len(points),
                            "points": points,
                        })
                    except Exception:
                        pass  # queue full, drop frame

            except RPLidarException as e:
                scan_error_count += 1
                err_msg = str(e)
                print(f"⚠ LiDAR scan error (#{scan_error_count}): {err_msg}")

                if scan_error_count >= MAX_CONSECUTIVE_ERRORS:
                    out_queue.put({"type": "error", "msg": f"Too many consecutive scan errors: {err_msg}"})
                    break

                # Attempt re-sync: stop scan, clear buffer, restart scan
                try:
                    lidar.stop()
                    time.sleep(0.3)
                    try:
                        lidar._serial.reset_input_buffer()
                    except Exception:
                        pass
                    time.sleep(0.3)
                    # Continue outer while loop to restart iter_scans
                except Exception as re:
                    out_queue.put({"type": "error", "msg": f"Re-sync failed: {re}"})
                    break

            except Exception as e:
                out_queue.put({"type": "error", "msg": str(e)})
                break

    except RPLidarException as e:
        out_queue.put({"type": "error", "msg": f"RPLidar Error: {str(e)}"})
    except Exception as e:
        out_queue.put({"type": "error", "msg": str(e)})
    finally:
        if lidar:
            try:
                lidar.stop()
                lidar.stop_motor()
                lidar.disconnect()
            except Exception:
                pass


# ------------------------------------------------------------------
# Main-process scanner API
# ------------------------------------------------------------------

class LidarScanner:
    """Controls the RPLidar A1/A2 via a child process."""

    def __init__(self):
        self._process = None
        self._queue = None
        self._stop_evt = None
        self._reader_thread = None
        self.running = False
        self.latest_scan = None
        self._lock = threading.Lock()

    def start(self):
        """Spawn the child process and start scanning."""
        if not LIDAR_AVAILABLE:
            print("⚠  rplidar library not installed — cannot start")
            return False

        if self.running:
            return True

        self._queue = mp.Queue(maxsize=5)
        self._stop_evt = mp.Event()

        cfg = {
            "port": LIDAR_PORT,
            "baud": LIDAR_BAUDRATE,
            "max_range": LIDAR_MAX_RANGE,
            "min_range": LIDAR_MIN_RANGE,
        }

        self._process = mp.Process(target=_lidar_worker,
                                   args=(self._queue, self._stop_evt, cfg),
                                   daemon=True)
        self._process.start()

        # Wait for "started" or "error" — give it more time due to motor spin-up
        try:
            msg = self._queue.get(timeout=15)
        except Exception:
            msg = {"type": "error", "msg": "timeout waiting for RPLidar worker"}

        if msg.get("type") != "started":
            print(f"✗ LiDAR start failed: {msg.get('msg', 'unknown')}")
            self._cleanup_process()
            return False

        self.running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

        if VERBOSE_MODE:
            print("✓ RPLidar scanning started (subprocess)")
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
            print("✓ RPLidar scanning stopped")

    def disconnect(self):
        self.stop()

    def _cleanup_process(self):
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=3)
            if self._process.is_alive():
                self._process.kill()
        self._process = None
        self._queue = None
        self._stop_evt = None

    def _reader_loop(self):
        while self.running:
            try:
                msg = self._queue.get(timeout=1.0)
                if msg["type"] == "scan":
                    with self._lock:
                        self.latest_scan = msg
                elif msg["type"] == "error":
                    print(f"⚠ LiDAR worker error: {msg['msg']}")
                    self.running = False
                    break
            except Exception:
                if self._process and not self._process.is_alive():
                    self.running = False
                    break

    def get_latest_scan(self):
        with self._lock:
            return self.latest_scan

    @property
    def is_running(self):
        return self.running

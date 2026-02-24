#!/usr/bin/env python3
"""
Pose Estimator Module — tracks robot position using dead reckoning.

Without wheel encoders, position is estimated from motor commands and time.
Optional scan-matching can reduce drift when an occupancy grid is available.
"""

import math
import time
from config import (
    DR_WHEEL_BASE, DR_MAX_SPEED_MPS,
    MOTOR_MAX_SPEED,
)


class PoseEstimator:
    """
    Tracks (x, y, heading) using differential-drive kinematics.

    Coordinate frame:
        x = rightward
        y = forward
        heading = 0 → facing +y, increases counter-clockwise (radians)
    """

    def __init__(self):
        self.x = 0.0       # metres
        self.y = 0.0       # metres
        self.heading = 0.0  # radians
        self.start_pose = (0.0, 0.0, 0.0)
        self._last_time = time.time()
        self._total_distance = 0.0
        self._history = []  # list of (x, y, heading, timestamp)

    # ------------------------------------------------------------------
    # Dead reckoning update
    # ------------------------------------------------------------------

    def update(self, left_speed, right_speed, left_dir, right_dir, dt=None):
        """
        Update pose from motor state.

        Args:
            left_speed:  0-100 PWM duty cycle for left motor
            right_speed: 0-100 PWM duty cycle for right motor
            left_dir:    "forward", "backward", or "stop"
            right_dir:   "forward", "backward", or "stop"
            dt:          time delta in seconds (auto-computed if None)
        """
        now = time.time()
        if dt is None:
            dt = now - self._last_time
        self._last_time = now

        if dt <= 0 or dt > 2.0:  # skip unreasonable deltas
            return

        # Convert PWM% → m/s
        vl = self._pwm_to_mps(left_speed, left_dir)
        vr = self._pwm_to_mps(right_speed, right_dir)

        # Differential drive kinematics
        v = (vl + vr) / 2.0          # linear velocity
        omega = (vr - vl) / DR_WHEEL_BASE  # angular velocity

        if abs(omega) < 1e-6:
            # Straight line
            self.x += v * math.cos(self.heading + math.pi / 2) * dt
            self.y += v * math.sin(self.heading + math.pi / 2) * dt
        else:
            # Arc
            R = v / omega
            dh = omega * dt
            self.x += R * (math.sin(self.heading + math.pi / 2 + dh) -
                           math.sin(self.heading + math.pi / 2))
            self.y -= R * (math.cos(self.heading + math.pi / 2 + dh) -
                           math.cos(self.heading + math.pi / 2))
            self.heading += dh

        # Normalise heading to [-pi, pi]
        self.heading = math.atan2(math.sin(self.heading),
                                   math.cos(self.heading))

        self._total_distance += abs(v) * dt

        # Record history (keep last 500 poses for path drawing)
        self._history.append((self.x, self.y, self.heading, now))
        if len(self._history) > 500:
            self._history = self._history[-500:]

    def _pwm_to_mps(self, speed, direction):
        """Convert PWM duty cycle (0-100) and direction to m/s."""
        if direction == "stop" or speed <= 5:
            return 0.0
        v = (speed / MOTOR_MAX_SPEED) * DR_MAX_SPEED_MPS
        if direction == "backward":
            v = -v
        return v

    # ------------------------------------------------------------------
    # Scan-matching drift correction (simple nearest-scan approach)
    # ------------------------------------------------------------------

    def correct_from_scan(self, grid, scan_points):
        """
        Reduce pose drift by comparing current scan to the occupancy grid.
        Uses a simple translational scan-match (no rotation correction).
        Only corrects if confidence is high enough.
        """
        if grid is None or scan_points is None or len(scan_points) < 20:
            return False

        best_score = 0
        best_dx, best_dy = 0.0, 0.0

        # Try small offsets around current pose
        for dx in [-0.05, 0.0, 0.05]:
            for dy in [-0.05, 0.0, 0.05]:
                score = 0
                test_x = self.x + dx
                test_y = self.y + dy
                for pt in scan_points[:100]:  # limit for speed
                    d = pt["distance"]
                    if d < 0.05 or d > 8.0:
                        continue
                    angle = math.radians(pt["angle"]) + self.heading
                    wx = test_x + d * math.cos(angle)
                    wy = test_y + d * math.sin(angle)
                    r, c = grid.world_to_cell(wx, wy)
                    if grid.in_bounds(r, c) and grid.grid[r, c] == 100:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_dx = dx
                    best_dy = dy

        # Only apply correction if significantly better than no-offset
        if best_score > 10 and (best_dx != 0 or best_dy != 0):
            self.x += best_dx
            self.y += best_dy
            return True
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_pose(self):
        """Return current (x, y, heading) in metres and radians."""
        return (round(self.x, 4), round(self.y, 4), round(self.heading, 4))

    def get_pose_dict(self):
        """Return pose as dict for JSON serialisation."""
        return {
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "heading": round(math.degrees(self.heading), 1),
            "total_distance": round(self._total_distance, 3),
        }

    def get_path(self):
        """Return recent path as list of (x, y) for UI display."""
        return [{"x": round(h[0], 3), "y": round(h[1], 3)} for h in self._history]

    def reset(self, x=0.0, y=0.0, heading=0.0):
        """Reset pose to given position."""
        self.x = x
        self.y = y
        self.heading = heading
        self.start_pose = (x, y, heading)
        self._last_time = time.time()
        self._total_distance = 0.0
        self._history = []

    def distance_to_start(self):
        """Distance from current position to start position."""
        sx, sy, _ = self.start_pose
        return math.sqrt((self.x - sx) ** 2 + (self.y - sy) ** 2)

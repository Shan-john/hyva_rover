#!/usr/bin/env python3
"""
Path Planner Module — reactive obstacle-avoidance navigation.
Uses LiDAR scan data to decide motor commands (forward / turn / stop).
"""

import math
from config import (
    NAV_SPEED, NAV_OBSTACLE_THRESHOLD,
    NAV_SECTOR_COUNT, NAV_FRONT_SECTOR_HALF, VERBOSE_MODE
)


class PathPlanner:
    """
    Simple sector-based reactive planner.

    Strategy:
        1. Divide the 360° scan into N angular sectors.
        2. Compute the average distance for each sector.
        3. If the front sectors are clear → drive forward.
        4. Otherwise turn towards the widest (deepest) open sector.
        5. If everything is blocked → stop.
    """

    def __init__(self, sector_count=NAV_SECTOR_COUNT,
                 obstacle_threshold=NAV_OBSTACLE_THRESHOLD,
                 speed=NAV_SPEED,
                 front_half=NAV_FRONT_SECTOR_HALF):
        self.sector_count = sector_count
        self.obstacle_threshold = obstacle_threshold
        self.speed = speed
        self.front_half = front_half          # sectors each side of 0°
        self.sector_width = 360.0 / sector_count

    # ------------------------------------------------------------------
    # Core planning
    # ------------------------------------------------------------------

    def plan_step(self, scan_data):
        """
        Given scan_data dict (with "points" list), return a motor command:
        {
            "action": "forward" | "turn_left" | "turn_right" | "stop",
            "speed": int,
            "steering": int,     # -100..100 (left..right)
            "sector_distances": [...],  # avg distance per sector (for UI)
            "best_sector": int,
        }
        """
        if not scan_data or not scan_data.get("points"):
            return self._cmd("stop", 0, 0, [], -1)

        sectors = self._build_sectors(scan_data["points"])
        best = self._best_sector(sectors)

        # Is the front clear?
        front_clear = self._front_is_clear(sectors)

        if front_clear:
            return self._cmd("forward", self.speed, 0, sectors, best)

        if best < 0:
            return self._cmd("stop", 0, 0, sectors, best)

        # Determine turn direction based on best open sector
        centre = self.sector_count // 2  # sector index for 0° / forward
        if best < centre:
            # Best sector is on the right half (sector 0 = +180° → clockwise)
            steering = int(min(100, max(20, (centre - best) * (100 / centre))))
            return self._cmd("turn_right", self.speed, steering, sectors, best)
        else:
            steering = int(min(100, max(20, (best - centre) * (100 / centre))))
            return self._cmd("turn_left", self.speed, -steering, sectors, best)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_sectors(self, points):
        """Return list[sector_count] of average distance per sector."""
        sums = [0.0] * self.sector_count
        counts = [0] * self.sector_count

        for p in points:
            angle = p["angle"]  # degrees, -180..180
            # Normalise to 0..360
            norm = (angle + 180.0) % 360.0
            idx = int(norm / self.sector_width)
            idx = min(idx, self.sector_count - 1)
            sums[idx] += p["distance"]
            counts[idx] += 1

        # Average, default to 0 (unknown) for empty sectors
        sectors = []
        for i in range(self.sector_count):
            if counts[i] > 0:
                sectors.append(round(sums[i] / counts[i], 3))
            else:
                sectors.append(0.0)
        return sectors

    def _front_is_clear(self, sectors):
        """Check if the front-facing sectors are all above threshold."""
        # Centre sector index (0° = forward)
        centre = self.sector_count // 2
        for i in range(centre - self.front_half, centre + self.front_half + 1):
            idx = i % self.sector_count
            if sectors[idx] < self.obstacle_threshold or sectors[idx] == 0:
                return False
        return True

    def _best_sector(self, sectors):
        """Return index of the sector with the largest average distance."""
        best_idx = -1
        best_dist = 0.0
        for i, d in enumerate(sectors):
            if d > best_dist:
                best_dist = d
                best_idx = i
        # If the best is still below threshold, return -1
        if best_dist < self.obstacle_threshold:
            return -1
        return best_idx

    @staticmethod
    def _cmd(action, speed, steering, sectors, best_sector):
        return {
            "action": action,
            "speed": speed,
            "steering": steering,
            "sector_distances": sectors,
            "best_sector": best_sector,
        }

    # ------------------------------------------------------------------
    # Convert plan to joystick-like (x, y) values for the motor driver
    # ------------------------------------------------------------------

    @staticmethod
    def command_to_joystick(cmd):
        """
        Convert a plan command to joystick-style (x, y) for apply_joystick().
        x = steering (-100 left, 100 right)
        y = throttle (100 forward, -100 backward)
        """
        action = cmd["action"]
        speed = cmd["speed"]
        steering = cmd.get("steering", 0)

        if action == "forward":
            return (0, speed)
        elif action == "turn_left":
            return (steering, int(speed * 0.5))
        elif action == "turn_right":
            return (steering, int(speed * 0.5))
        else:  # stop
            return (0, 0)


# =====================================================================
# Exploration Planner — autonomous room mapping
# =====================================================================

import heapq
from config import (
    EXPLORE_SPEED, EXPLORE_FRONTIER_MIN_DIST, EXPLORE_COMPLETE_PCT,
    GRID_RESOLUTION,
)


class ExplorationPlanner:
    """
    High-level planner for autonomous room exploration.

    Modes:
        "explore"    — frontier-based exploration (default)
        "coverage"   — systematic grid sweep
        "boundary"   — follow room perimeter
        "corners"    — visit detected corners first
        "return"     — return to start position
    """

    def __init__(self, grid, pose_estimator):
        """
        Args:
            grid: OccupancyGrid instance
            pose_estimator: PoseEstimator instance
        """
        self.grid = grid
        self.pose = pose_estimator
        self.mode = "explore"
        self.waypoints = []       # list of (x, y) targets
        self.current_wp_idx = 0
        self.complete = False
        self._reactive_planner = PathPlanner(speed=EXPLORE_SPEED)

    # ------------------------------------------------------------------
    # Main planning step
    # ------------------------------------------------------------------

    def plan_step(self, scan_data):
        """
        High-level plan step. Returns a motor command dict.
        Automatically picks frontiers or follows waypoints.
        """
        if self.complete:
            return PathPlanner._cmd("stop", 0, 0, [], -1)

        # Check if mapping is complete
        stats = self.grid.get_stats()
        if stats["explored_pct"] >= EXPLORE_COMPLETE_PCT:
            self.complete = True
            return PathPlanner._cmd("stop", 0, 0, [], -1)

        # Get current target waypoint
        target = self._get_current_target()
        if target is None:
            # No more targets — try to find frontiers
            self._refresh_waypoints()
            target = self._get_current_target()
            if target is None:
                self.complete = True
                return PathPlanner._cmd("stop", 0, 0, [], -1)

        # Navigate towards target using reactive avoidance
        px, py, ph = self.pose.get_pose()
        tx, ty = target

        # Check if we reached the waypoint
        dist = math.sqrt((tx - px) ** 2 + (ty - py) ** 2)
        if dist < 0.20:  # within 20cm
            self.current_wp_idx += 1
            return self.plan_step(scan_data)  # recurse to next wp

        # Compute desired heading to target
        desired_heading = math.atan2(ty - py, tx - px) - math.pi / 2
        heading_error = self._angle_diff(desired_heading, ph)

        # First check for obstacles using reactive planner
        reactive_cmd = self._reactive_planner.plan_step(scan_data)
        if reactive_cmd["action"] == "stop":
            # Fully blocked — skip this waypoint
            self.current_wp_idx += 1
            return reactive_cmd

        # If obstacle in front but not blocked, use reactive avoidance
        if reactive_cmd["action"] != "forward":
            return reactive_cmd

        # Clear path — steer towards target
        if abs(heading_error) > 0.4:  # > ~23 degrees
            steering = int(min(100, max(-100, heading_error * 80)))
            if heading_error > 0:
                return PathPlanner._cmd("turn_left", EXPLORE_SPEED, -abs(steering), [], -1)
            else:
                return PathPlanner._cmd("turn_right", EXPLORE_SPEED, abs(steering), [], -1)

        return PathPlanner._cmd("forward", EXPLORE_SPEED, 0, [], -1)

    # ------------------------------------------------------------------
    # Mode-specific waypoint generation
    # ------------------------------------------------------------------

    def set_mode(self, mode):
        """Change exploration mode and regenerate waypoints."""
        self.mode = mode
        self.complete = False
        self.current_wp_idx = 0
        self._refresh_waypoints()

    def _refresh_waypoints(self):
        """Generate waypoints based on current mode."""
        if self.mode == "explore":
            self._gen_frontier_waypoints()
        elif self.mode == "coverage":
            self._gen_coverage_waypoints()
        elif self.mode == "boundary":
            self._gen_boundary_waypoints()
        elif self.mode == "corners":
            self._gen_corner_waypoints()
        elif self.mode == "return":
            self._gen_return_waypoints()
        self.current_wp_idx = 0

    def _gen_frontier_waypoints(self):
        """Visit the nearest unexplored frontier."""
        frontiers = self.grid.get_frontiers()
        px, py, _ = self.pose.get_pose()

        # Filter out faraway or too-close frontiers
        valid = []
        for f in frontiers:
            d = math.sqrt((f["x"] - px) ** 2 + (f["y"] - py) ** 2)
            if d >= EXPLORE_FRONTIER_MIN_DIST:
                valid.append((d, f))
        valid.sort(key=lambda t: t[0])

        if valid:
            # Take nearest frontier
            target = valid[0][1]
            self.waypoints = [(target["x"], target["y"])]
        else:
            self.waypoints = []

    def _gen_coverage_waypoints(self):
        """Generate systematic grid-sweep waypoints across free space."""
        bounds = self.grid.get_room_bounds()
        if not bounds:
            self.waypoints = []
            return

        step = 0.30  # 30cm between sweep lines
        wps = []
        x = bounds["x_min"] + step
        direction = 1
        while x < bounds["x_max"]:
            if direction == 1:
                wps.append((x, bounds["y_min"] + step))
                wps.append((x, bounds["y_max"] - step))
            else:
                wps.append((x, bounds["y_max"] - step))
                wps.append((x, bounds["y_min"] + step))
            direction *= -1
            x += step

        self.waypoints = wps

    def _gen_boundary_waypoints(self):
        """Follow the room perimeter (detected walls)."""
        self.grid.detect_walls_and_corners()
        if not self.grid.walls:
            # Fall back to frontier exploration
            self._gen_frontier_waypoints()
            return

        # Collect wall endpoints as boundary waypoints
        wps = []
        for w in self.grid.walls:
            wps.append((w["x1"], w["y1"]))
            wps.append((w["x2"], w["y2"]))

        # Sort by angle from centre to create a perimeter path
        cx, cy = 0, 0
        if wps:
            cx = sum(p[0] for p in wps) / len(wps)
            cy = sum(p[1] for p in wps) / len(wps)
        wps.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))

        self.waypoints = wps

    def _gen_corner_waypoints(self):
        """Visit detected corners first, then frontiers."""
        self.grid.detect_walls_and_corners()
        px, py, _ = self.pose.get_pose()
        wps = [(c["x"], c["y"]) for c in self.grid.corners]
        # Sort by distance
        wps.sort(key=lambda p: math.sqrt((p[0] - px) ** 2 + (p[1] - py) ** 2))
        # Add frontiers after corners
        frontiers = self.grid.get_frontiers()
        for f in frontiers:
            wps.append((f["x"], f["y"]))
        self.waypoints = wps

    def _gen_return_waypoints(self):
        """Plan path back to start using A*."""
        sx, sy, _ = self.pose.start_pose
        px, py, _ = self.pose.get_pose()
        path = self._a_star(px, py, sx, sy)
        self.waypoints = path if path else [(sx, sy)]

    # ------------------------------------------------------------------
    # A* Pathfinding on grid
    # ------------------------------------------------------------------

    def _a_star(self, sx, sy, gx, gy):
        """A* from (sx,sy) to (gx,gy) in world coords. Returns list of (x,y) waypoints."""
        sr, sc = self.grid.world_to_cell(sx, sy)
        gr, gc = self.grid.world_to_cell(gx, gy)

        if not self.grid.in_bounds(sr, sc) or not self.grid.in_bounds(gr, gc):
            return []

        # Heuristic
        def h(r, c):
            return abs(r - gr) + abs(c - gc)

        open_set = [(h(sr, sc), 0, sr, sc)]
        came_from = {}
        g_score = {(sr, sc): 0}
        visited = set()

        while open_set:
            _, cost, r, c = heapq.heappop(open_set)
            if (r, c) in visited:
                continue
            visited.add((r, c))

            if r == gr and c == gc:
                # Reconstruct path
                path = []
                curr = (gr, gc)
                while curr in came_from:
                    wx, wy = self.grid.cell_to_world(curr[0], curr[1])
                    path.append((wx, wy))
                    curr = came_from[curr]
                path.reverse()
                # Downsample path (every 10 cells)
                return path[::10] if len(path) > 10 else path

            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (not self.grid.in_bounds(nr, nc) or
                        (nr, nc) in visited or
                        self.grid.grid[nr, nc] == 100):
                    continue
                # Prefer free cells, allow unknown with penalty
                move_cost = 1 if self.grid.grid[nr, nc] == 1 else 5
                new_g = cost + move_cost
                if new_g < g_score.get((nr, nc), float("inf")):
                    g_score[(nr, nc)] = new_g
                    came_from[(nr, nc)] = (r, c)
                    heapq.heappush(open_set, (new_g + h(nr, nc), new_g, nr, nc))

        return []  # no path found

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_current_target(self):
        """Return current waypoint or None."""
        if self.current_wp_idx < len(self.waypoints):
            return self.waypoints[self.current_wp_idx]
        return None

    @staticmethod
    def _angle_diff(a, b):
        """Signed angle difference a - b, normalized to [-pi, pi]."""
        d = a - b
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        return d

    def get_status(self):
        """Return exploration status dict for UI."""
        stats = self.grid.get_stats()
        return {
            "mode": self.mode,
            "complete": self.complete,
            "explored_pct": stats["explored_pct"],
            "scan_count": stats["scan_count"],
            "waypoints_total": len(self.waypoints),
            "waypoints_done": self.current_wp_idx,
            "wall_count": stats["wall_count"],
            "corner_count": stats["corner_count"],
        }


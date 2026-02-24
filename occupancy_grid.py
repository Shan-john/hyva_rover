#!/usr/bin/env python3
"""
Occupancy Grid Module — builds a 2D map from LiDAR scans.

Grid cells are:
  0  = UNKNOWN
  1  = FREE
  100 = OCCUPIED
"""

import math
import json
import time
import io
import base64
import numpy as np
from config import (
    GRID_RESOLUTION, GRID_SIZE_M,
    LIDAR_MAX_RANGE, LIDAR_MIN_RANGE,
)

# Cell values
UNKNOWN = 0
FREE = 1
OCCUPIED = 100


class OccupancyGrid:
    """2D occupancy grid for SLAM-like mapping."""

    def __init__(self, size_m=GRID_SIZE_M, resolution=GRID_RESOLUTION):
        """
        Args:
            size_m: map side length in metres (square map)
            resolution: metres per cell
        """
        self.resolution = resolution
        self.size_m = size_m
        self.cells = int(size_m / resolution)
        self.grid = np.zeros((self.cells, self.cells), dtype=np.uint8)
        # Origin is at centre of grid
        self.origin_cell = self.cells // 2
        # Metadata
        self.created = time.time()
        self.scan_count = 0
        self.walls = []       # list of wall segment dicts
        self.corners = []     # list of corner point dicts
        self.obstacles = []   # list of obstacle cluster centroids

    # ------------------------------------------------------------------
    # Coordinate transforms
    # ------------------------------------------------------------------

    def world_to_cell(self, x, y):
        """Convert world (metres) to grid cell (row, col)."""
        col = int(x / self.resolution) + self.origin_cell
        row = int(-y / self.resolution) + self.origin_cell  # y-up → row-down
        return row, col

    def cell_to_world(self, row, col):
        """Convert grid cell to world (metres)."""
        x = (col - self.origin_cell) * self.resolution
        y = -(row - self.origin_cell) * self.resolution
        return x, y

    def in_bounds(self, row, col):
        return 0 <= row < self.cells and 0 <= col < self.cells

    # ------------------------------------------------------------------
    # Update from LiDAR scan
    # ------------------------------------------------------------------

    def update_from_scan(self, pose, scan_points):
        """
        Update grid using a single LiDAR scan.

        Args:
            pose: (x, y, heading) in metres and radians
            scan_points: list of {"angle": deg, "distance": m}
        """
        rx, ry, rh = pose
        r0, c0 = self.world_to_cell(rx, ry)

        for pt in scan_points:
            d = pt["distance"]
            if d < LIDAR_MIN_RANGE or d > LIDAR_MAX_RANGE:
                continue

            # World-frame angle of this point
            angle_rad = math.radians(pt["angle"]) + rh
            # Endpoint in world coords
            ex = rx + d * math.cos(angle_rad)
            ey = ry + d * math.sin(angle_rad)
            er, ec = self.world_to_cell(ex, ey)

            # Ray-cast from robot to endpoint → mark FREE
            self._ray_cast_free(r0, c0, er, ec)

            # Mark endpoint as OCCUPIED
            if self.in_bounds(er, ec):
                self.grid[er, ec] = OCCUPIED

        self.scan_count += 1

    def _ray_cast_free(self, r0, c0, r1, c1):
        """Bresenham line from (r0,c0) to (r1,c1), marking cells as FREE."""
        dr = abs(r1 - r0)
        dc = abs(c1 - c0)
        sr = 1 if r1 > r0 else -1
        sc = 1 if c1 > c0 else -1
        err = dr - dc
        r, c = r0, c0
        steps = 0
        max_steps = dr + dc + 1

        while steps < max_steps:
            if self.in_bounds(r, c) and self.grid[r, c] != OCCUPIED:
                self.grid[r, c] = FREE
            if r == r1 and c == c1:
                break
            e2 = 2 * err
            if e2 > -dc:
                err -= dc
                r += sr
            if e2 < dr:
                err += dr
                c += sc
            steps += 1

    # ------------------------------------------------------------------
    # Frontier detection
    # ------------------------------------------------------------------

    def get_frontiers(self):
        """
        Find frontier cells — FREE cells adjacent to UNKNOWN cells.
        Returns list of (world_x, world_y) cluster centroids.
        """
        frontier_cells = []
        for r in range(1, self.cells - 1):
            for c in range(1, self.cells - 1):
                if self.grid[r, c] != FREE:
                    continue
                # Check 4-connected neighbours
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if self.grid[r + dr, c + dc] == UNKNOWN:
                        frontier_cells.append((r, c))
                        break

        if not frontier_cells:
            return []

        # Cluster nearby frontier cells (simple flood-fill grouping)
        visited = set()
        clusters = []
        for cell in frontier_cells:
            if cell in visited:
                continue
            cluster = []
            stack = [cell]
            while stack:
                cr, cc = stack.pop()
                if (cr, cc) in visited:
                    continue
                visited.add((cr, cc))
                cluster.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if (nr, nc) not in visited and (nr, nc) in set(frontier_cells):
                        stack.append((nr, nc))
            if len(cluster) >= 3:  # ignore tiny clusters
                clusters.append(cluster)

        # Convert to world centroids
        centroids = []
        for cluster in clusters:
            avg_r = sum(c[0] for c in cluster) / len(cluster)
            avg_c = sum(c[1] for c in cluster) / len(cluster)
            wx, wy = self.cell_to_world(avg_r, avg_c)
            centroids.append({
                "x": round(wx, 3),
                "y": round(wy, 3),
                "size": len(cluster),
            })

        # Sort by size (prefer larger frontiers)
        centroids.sort(key=lambda f: f["size"], reverse=True)
        return centroids

    # ------------------------------------------------------------------
    # Wall and corner detection
    # ------------------------------------------------------------------

    def detect_walls_and_corners(self):
        """Extract wall segments and corners from occupied cells."""
        occupied = set()
        for r in range(self.cells):
            for c in range(self.cells):
                if self.grid[r, c] == OCCUPIED:
                    occupied.add((r, c))

        if not occupied:
            self.walls = []
            self.corners = []
            return

        # Simple wall detection: connected runs of occupied cells
        # Horizontal walls
        h_walls = self._find_runs(occupied, axis="horizontal")
        # Vertical walls
        v_walls = self._find_runs(occupied, axis="vertical")

        self.walls = h_walls + v_walls

        # Corners: cells where horizontal and vertical walls meet
        corners = []
        wall_endpoints = set()
        for w in self.walls:
            wall_endpoints.add((w["r1"], w["c1"]))
            wall_endpoints.add((w["r2"], w["c2"]))

        # Find points that appear as endpoints of both H and V walls
        for pt in wall_endpoints:
            r, c = pt
            wx, wy = self.cell_to_world(r, c)
            # Check if this point has walls in different directions
            h_count = sum(1 for w in h_walls if (w["r1"], w["c1"]) == pt or (w["r2"], w["c2"]) == pt)
            v_count = sum(1 for w in v_walls if (w["r1"], w["c1"]) == pt or (w["r2"], w["c2"]) == pt)
            if h_count > 0 and v_count > 0:
                corners.append({"x": round(wx, 3), "y": round(wy, 3)})

        self.corners = corners

    def _find_runs(self, occupied, axis="horizontal"):
        """Find linear runs of occupied cells."""
        walls = []
        visited = set()

        for r, c in sorted(occupied):
            if (r, c) in visited:
                continue

            if axis == "horizontal":
                # Extend right
                run = [(r, c)]
                visited.add((r, c))
                nc = c + 1
                while (r, nc) in occupied and (r, nc) not in visited:
                    run.append((r, nc))
                    visited.add((r, nc))
                    nc += 1
            else:
                # Extend down
                run = [(r, c)]
                visited.add((r, c))
                nr = r + 1
                while (nr, c) in occupied and (nr, c) not in visited:
                    run.append((nr, c))
                    visited.add((nr, c))
                    nr += 1

            if len(run) >= 5:  # minimum wall length
                r1, c1 = run[0]
                r2, c2 = run[-1]
                wx1, wy1 = self.cell_to_world(r1, c1)
                wx2, wy2 = self.cell_to_world(r2, c2)
                walls.append({
                    "r1": r1, "c1": c1, "r2": r2, "c2": c2,
                    "x1": round(wx1, 3), "y1": round(wy1, 3),
                    "x2": round(wx2, 3), "y2": round(wy2, 3),
                    "length": round(math.dist((wx1, wy1), (wx2, wy2)), 3),
                    "axis": axis,
                })
        return walls

    # ------------------------------------------------------------------
    # Room metrics
    # ------------------------------------------------------------------

    def get_stats(self):
        """Return mapping statistics."""
        total = self.cells * self.cells
        free_count = int(np.sum(self.grid == FREE))
        occ_count = int(np.sum(self.grid == OCCUPIED))
        unk_count = total - free_count - occ_count
        explored_pct = round(100 * (free_count + occ_count) / total, 1) if total > 0 else 0

        return {
            "grid_cells": total,
            "free": free_count,
            "occupied": occ_count,
            "unknown": unk_count,
            "explored_pct": explored_pct,
            "scan_count": self.scan_count,
            "resolution_m": self.resolution,
            "size_m": self.size_m,
            "wall_count": len(self.walls),
            "corner_count": len(self.corners),
        }

    def get_room_bounds(self):
        """Compute bounding box of occupied cells (the room)."""
        occ = np.argwhere(self.grid == OCCUPIED)
        if len(occ) == 0:
            return None
        r_min, c_min = occ.min(axis=0)
        r_max, c_max = occ.max(axis=0)
        x_min, y_max = self.cell_to_world(r_min, c_min)
        x_max, y_min = self.cell_to_world(r_max, c_max)
        return {
            "x_min": round(x_min, 3), "y_min": round(y_min, 3),
            "x_max": round(x_max, 3), "y_max": round(y_max, 3),
            "width": round(abs(x_max - x_min), 3),
            "height": round(abs(y_max - y_min), 3),
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def save(self, filepath):
        """Save grid + metadata to JSON."""
        self.detect_walls_and_corners()
        data = {
            "version": 1,
            "created": self.created,
            "saved": time.time(),
            "resolution": self.resolution,
            "size_m": self.size_m,
            "cells": self.cells,
            "scan_count": self.scan_count,
            "grid": self.grid.tolist(),
            "walls": self.walls,
            "corners": self.corners,
            "room_bounds": self.get_room_bounds(),
            "stats": self.get_stats(),
        }
        with open(filepath, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, filepath):
        """Load grid from JSON."""
        with open(filepath, "r") as f:
            data = json.load(f)
        g = cls(size_m=data["size_m"], resolution=data["resolution"])
        g.grid = np.array(data["grid"], dtype=np.uint8)
        g.created = data.get("created", 0)
        g.scan_count = data.get("scan_count", 0)
        g.walls = data.get("walls", [])
        g.corners = data.get("corners", [])
        return g

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def to_data_url(self):
        """Render grid as a base64 PNG data URL for the UI."""
        try:
            from PIL import Image
        except ImportError:
            return self._to_simple_data_url()

        img = Image.new("RGB", (self.cells, self.cells))
        pixels = img.load()
        for r in range(self.cells):
            for c in range(self.cells):
                v = self.grid[r, c]
                if v == UNKNOWN:
                    pixels[c, r] = (30, 30, 40)       # dark gray
                elif v == FREE:
                    pixels[c, r] = (15, 20, 35)        # very dark blue
                elif v == OCCUPIED:
                    pixels[c, r] = (220, 220, 230)     # white wall
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"

    def _to_simple_data_url(self):
        """Fallback if PIL is not available — return grid as compact JSON."""
        return None

    def to_ui_json(self):
        """Return a lightweight dict for real-time UI updates."""
        # Downsample grid if too large
        step = max(1, self.cells // 100)
        small = self.grid[::step, ::step].tolist()
        return {
            "grid": small,
            "resolution": self.resolution * step,
            "size_m": self.size_m,
            "origin": self.origin_cell // step,
            "stats": self.get_stats(),
        }

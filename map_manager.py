#!/usr/bin/env python3
"""
Map Manager — save, load, list, and delete room maps.

Maps are stored as JSON files in the MAPS_DIR directory.
Each map has a corresponding PNG preview image.
"""

import os
import json
import time
import glob
from config import MAPS_DIR


class MapManager:
    """Manage saved occupancy-grid maps."""

    def __init__(self, maps_dir=MAPS_DIR):
        self.maps_dir = maps_dir
        os.makedirs(self.maps_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def save(self, grid, name):
        """
        Save an OccupancyGrid with a human-readable name.
        Returns metadata dict.
        """
        safe_name = self._sanitize(name)
        filepath = os.path.join(self.maps_dir, f"{safe_name}.json")
        grid.save(filepath)

        meta = {
            "name": name,
            "filename": f"{safe_name}.json",
            "saved": time.time(),
            "stats": grid.get_stats(),
            "room_bounds": grid.get_room_bounds(),
        }
        # Save a small metadata sidecar for quick listing
        meta_path = os.path.join(self.maps_dir, f"{safe_name}.meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        return meta

    def load(self, name):
        """Load an OccupancyGrid by name. Returns grid or None."""
        from occupancy_grid import OccupancyGrid
        safe_name = self._sanitize(name)
        filepath = os.path.join(self.maps_dir, f"{safe_name}.json")
        if not os.path.exists(filepath):
            return None
        return OccupancyGrid.load(filepath)

    def delete(self, name):
        """Delete a saved map by name. Returns True if deleted."""
        safe_name = self._sanitize(name)
        deleted = False
        for ext in [".json", ".meta.json", ".png"]:
            fp = os.path.join(self.maps_dir, f"{safe_name}{ext}")
            if os.path.exists(fp):
                os.remove(fp)
                deleted = True
        return deleted

    def list_maps(self):
        """Return list of saved map metadata dicts."""
        maps = []
        for meta_file in sorted(glob.glob(os.path.join(self.maps_dir, "*.meta.json"))):
            try:
                with open(meta_file, "r") as f:
                    meta = json.load(f)
                maps.append(meta)
            except Exception:
                continue
        # Sort by saved time, newest first
        maps.sort(key=lambda m: m.get("saved", 0), reverse=True)
        return maps

    def exists(self, name):
        """Check if a map with this name exists."""
        safe_name = self._sanitize(name)
        return os.path.exists(os.path.join(self.maps_dir, f"{safe_name}.json"))

    def rename(self, old_name, new_name):
        """Rename a saved map."""
        old_safe = self._sanitize(old_name)
        new_safe = self._sanitize(new_name)
        for ext in [".json", ".meta.json", ".png"]:
            old_fp = os.path.join(self.maps_dir, f"{old_safe}{ext}")
            new_fp = os.path.join(self.maps_dir, f"{new_safe}{ext}")
            if os.path.exists(old_fp):
                os.rename(old_fp, new_fp)
        # Update name inside meta
        meta_path = os.path.join(self.maps_dir, f"{new_safe}.meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
            meta["name"] = new_name
            meta["filename"] = f"{new_safe}.json"
            with open(meta_path, "w") as f:
                json.dump(meta, f)

    @staticmethod
    def _sanitize(name):
        """Convert name to safe filename."""
        safe = "".join(c if c.isalnum() or c in "-_ " else "" for c in name)
        return safe.strip().replace(" ", "_").lower() or "unnamed"

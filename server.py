#!/usr/bin/env python3
"""
Flask + SocketIO server for joystick motor control + LiDAR mapping + autonomous navigation.
Receives joystick {x, y} over WebSocket and drives L298N dual motors
using differential drive mapping.
"""

import sys
import os
import time
import threading

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# ============================================
# GPIO / Motor Setup
# ============================================
SIMULATION_MODE = False

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    from main_dual_motor import L298NDualMotor
    from config import MOTOR_DEFAULT_SPEED
except (ImportError, RuntimeError):
    SIMULATION_MODE = True
    MOTOR_DEFAULT_SPEED = 70
    print("⚠  RPi.GPIO not available — running in SIMULATION mode")

# LiDAR imports
try:
    from lidar_scanner import LidarScanner
    from path_planner import PathPlanner, ExplorationPlanner
    from occupancy_grid import OccupancyGrid
    from pose_estimator import PoseEstimator
    from map_manager import MapManager
    LIDAR_MODULES_AVAILABLE = True
except ImportError as e:
    LIDAR_MODULES_AVAILABLE = False
    print(f"⚠  LiDAR modules not available: {e}")


# ============================================
# Flask App
# ============================================
app = Flask(__name__)
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Motor state (shared between threads)
motor_state = {
    "motor_a": {"direction": "stop", "speed": 0},
    "motor_b": {"direction": "stop", "speed": 0},
}
motors = None

# LiDAR state
lidar_scanner = None
path_planner = None
map_manager = None
occupancy_grid = None
pose_estimator = None
exploration_planner = None

mapping_active = False
navigation_active = False
exploration_active = False

nav_thread = None
nav_stop_event = threading.Event()
mapping_thread = None
mapping_stop_event = threading.Event()
explore_thread = None
explore_stop_event = threading.Event()


def init_motors():
    """Initialize real motors if available."""
    global motors
    if not SIMULATION_MODE:
        try:
            motors = L298NDualMotor()
            print("✓ Motors initialized")
        except Exception as e:
            print(f"✗ Motor init failed: {e}")


def init_lidar():
    """Initialize LiDAR scanner and path planner."""
    global lidar_scanner, path_planner, map_manager, occupancy_grid, pose_estimator
    if LIDAR_MODULES_AVAILABLE:
        lidar_scanner = LidarScanner()
        path_planner = PathPlanner()
        map_manager = MapManager()
        occupancy_grid = OccupancyGrid()
        pose_estimator = PoseEstimator()
        print("✓ LiDAR modules loaded")
    else:
        print("⚠  LiDAR modules not loaded")


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def apply_joystick(x, y):
    """
    Map joystick (x, y) in range [-100, 100] to differential drive.
    """
    global motor_state

    DEAD_ZONE = 5

    if abs(x) < DEAD_ZONE:
        x = 0
    if abs(y) < DEAD_ZONE:
        y = 0

    left_raw = clamp(y + x, -100, 100)
    right_raw = clamp(y - x, -100, 100)

    left_speed = abs(int(left_raw))
    right_speed = abs(int(right_raw))
    left_dir = "forward" if left_raw > 0 else ("backward" if left_raw < 0 else "stop")
    right_dir = "forward" if right_raw > 0 else ("backward" if right_raw < 0 else "stop")

    if motors and not SIMULATION_MODE:
        if left_dir == "forward":
            motors.motor_a_forward(left_speed)
        elif left_dir == "backward":
            motors.motor_a_backward(left_speed)
        else:
            motors.motor_a_stop()

        if right_dir == "forward":
            motors.motor_b_forward(right_speed)
        elif right_dir == "backward":
            motors.motor_b_backward(right_speed)
        else:
            motors.motor_b_stop()

    motor_state = {
        "motor_a": {"direction": left_dir, "speed": left_speed},
        "motor_b": {"direction": right_dir, "speed": right_speed},
    }

    # Update pose estimator if running
    if pose_estimator:
        pose_estimator.update(left_speed, right_speed, left_dir, right_dir)

    return motor_state


# ============================================
# REST Endpoints
# ============================================
@app.route("/")
def index():
    return jsonify({"status": "ok", "simulation": SIMULATION_MODE})


@app.route("/status")
def status():
    return jsonify(motor_state)


@app.route("/stop")
def stop():
    if motors and not SIMULATION_MODE:
        motors.both_stop()
    motor_state["motor_a"] = {"direction": "stop", "speed": 0}
    motor_state["motor_b"] = {"direction": "stop", "speed": 0}
    return jsonify(motor_state)


@app.route("/api/lidar/status")
def lidar_status():
    return jsonify({
        "available": LIDAR_MODULES_AVAILABLE,
        "mapping": mapping_active,
        "navigating": navigation_active,
        "exploring": exploration_active,
        "has_scan": lidar_scanner.latest_scan is not None if lidar_scanner else False,
    })


# ---- Map management REST endpoints ----

@app.route("/api/maps", methods=["GET"])
def api_list_maps():
    if not map_manager:
        return jsonify([])
    return jsonify(map_manager.list_maps())


@app.route("/api/maps/save", methods=["POST"])
def api_save_map():
    if not map_manager or not occupancy_grid:
        return jsonify({"error": "No map data"}), 400
    data = request.get_json() or {}
    name = data.get("name", f"map_{int(time.time())}")
    meta = map_manager.save(occupancy_grid, name)
    return jsonify(meta)


@app.route("/api/maps/<name>", methods=["DELETE"])
def api_delete_map(name):
    if not map_manager:
        return jsonify({"error": "Maps not available"}), 400
    deleted = map_manager.delete(name)
    return jsonify({"deleted": deleted})


@app.route("/api/maps/<name>/load", methods=["POST"])
def api_load_map(name):
    global occupancy_grid
    if not map_manager:
        return jsonify({"error": "Maps not available"}), 400
    grid = map_manager.load(name)
    if grid is None:
        return jsonify({"error": "Map not found"}), 404
    occupancy_grid = grid
    return jsonify({"loaded": name, "stats": grid.get_stats()})


@app.route("/api/exploration/status")
def api_exploration_status():
    result = {
        "active": exploration_active,
        "pose": pose_estimator.get_pose_dict() if pose_estimator else None,
        "grid_stats": occupancy_grid.get_stats() if occupancy_grid else None,
    }
    if exploration_planner:
        result["exploration"] = exploration_planner.get_status()
    return jsonify(result)


# ============================================
# WebSocket Events — Motor Control
# ============================================
@socketio.on("connect")
def handle_connect():
    print("🔌 Client connected")
    emit("motor_status", motor_state)
    _emit_lidar_state()


@socketio.on("disconnect")
def handle_disconnect():
    print("🔌 Client disconnected — stopping motors")
    apply_joystick(0, 0)


def _emit_lidar_state(broadcast=False):
    """Helper to send consistent lidar state."""
    state = {
        "mapping": mapping_active,
        "navigating": navigation_active,
        "exploring": exploration_active,
        "available": LIDAR_MODULES_AVAILABLE,
    }
    if broadcast:
        socketio.emit("lidar_state", state)
    else:
        emit("lidar_state", state)


# ============================================
# Action Logic
# ============================================
current_action_thread = None
stop_action_event = threading.Event()
action_lock = threading.Lock()


def run_continuous_action(action_name):
    """Run an action continuously until stopped."""
    global current_action_thread
    print(f"🎬 Starting continuous action: {action_name}")

    while not stop_action_event.is_set():
        try:
            if action_name == "spin_left":
                apply_joystick(-100, 0)
            elif action_name == "spin_right":
                apply_joystick(100, 0)
            elif action_name == "wiggle":
                apply_joystick(-100, 0)
                socketio.emit("motor_status", motor_state)
                if stop_action_event.wait(0.15): break
                apply_joystick(100, 0)
                socketio.emit("motor_status", motor_state)
                if stop_action_event.wait(0.15): break
                continue

            elif action_name == "spin_360":
                duration = 2.5
                start_time = time.time()
                while time.time() - start_time < duration:
                    apply_joystick(-100, 0)
                    socketio.emit("motor_status", motor_state)
                    if stop_action_event.wait(0.1): break
                break

            elif action_name == "spin_180":
                duration = 1.25
                start_time = time.time()
                while time.time() - start_time < duration:
                    apply_joystick(-100, 0)
                    socketio.emit("motor_status", motor_state)
                    if stop_action_event.wait(0.1): break
                break

            socketio.emit("motor_status", motor_state)
            if stop_action_event.wait(0.1):
                break

        except Exception as e:
            print(f"Action error: {e}")
            break

    apply_joystick(0, 0)
    socketio.emit("motor_status", motor_state)
    print("🎬 Action stopped")


@socketio.on("start_action")
def handle_start_action(data):
    """Start a continuous action."""
    global current_action_thread
    action = data.get("type")

    with action_lock:
        stop_action_event.set()
        if current_action_thread and current_action_thread.is_alive():
            current_action_thread.join(timeout=0.2)

        stop_action_event.clear()
        current_action_thread = threading.Thread(target=run_continuous_action, args=(action,))
        current_action_thread.start()


@socketio.on("stop_action")
def handle_stop_action():
    """Stop the current action."""
    stop_action_event.set()


@socketio.on("joystick")
def handle_joystick(data):
    """Receive joystick data: {x: -100..100, y: -100..100}"""
    if current_action_thread and current_action_thread.is_alive():
        stop_action_event.set()

    x = data.get("x", 0)
    y = data.get("y", 0)
    state = apply_joystick(x, y)
    emit("motor_status", state)


@socketio.on("emergency_stop")
def handle_emergency_stop():
    print("🛑 EMERGENCY STOP")
    # Stop everything
    stop_action_event.set()
    nav_stop_event.set()
    mapping_stop_event.set()
    explore_stop_event.set()
    state = apply_joystick(0, 0)
    global navigation_active, mapping_active, exploration_active
    navigation_active = False
    mapping_active = False
    exploration_active = False
    emit("motor_status", state)
    _emit_lidar_state()


# ============================================
# LiDAR Mapping
# ============================================

def _mapping_loop():
    """Background thread: continuously read scans and emit to clients."""
    global mapping_active
    print("🗺️  Mapping loop started")

    if not lidar_scanner:
        print("✗ No LiDAR scanner available")
        mapping_active = False
        _emit_lidar_state_broadcast()
        return

    if not lidar_scanner.start():
        print("✗ Failed to start LiDAR")
        mapping_active = False
        _emit_lidar_state_broadcast()
        return

    while not mapping_stop_event.is_set():
        scan = lidar_scanner.get_latest_scan()
        if scan:
            # Update occupancy grid with scan
            if occupancy_grid and pose_estimator:
                occupancy_grid.update_from_scan(
                    pose_estimator.get_pose(),
                    scan["points"]
                )
                # Attempt drift correction
                pose_estimator.correct_from_scan(occupancy_grid, scan["points"])

            # Send scan data to all connected clients
            points = scan["points"]
            if len(points) > 360:
                step = len(points) // 360
                points = points[::step]
            socketio.emit("map_data", {
                "points": points,
                "point_count": len(points),
                "timestamp": scan["timestamp"],
            })

            # Send grid data periodically (every ~2 seconds)
            if occupancy_grid and scan.get("timestamp", 0) % 2 < 0.2:
                _emit_grid_and_pose()

        mapping_stop_event.wait(0.15)

    lidar_scanner.stop()
    mapping_active = False
    print("🗺️  Mapping loop stopped")
    _emit_lidar_state_broadcast()


def _emit_lidar_state_broadcast():
    """Broadcast lidar state to all clients."""
    socketio.emit("lidar_state", {
        "mapping": mapping_active,
        "navigating": navigation_active,
        "exploring": exploration_active,
        "available": LIDAR_MODULES_AVAILABLE,
    })


def _emit_grid_and_pose():
    """Send occupancy grid and pose to frontend."""
    data = {}
    if occupancy_grid:
        data["grid"] = occupancy_grid.to_ui_json()
    if pose_estimator:
        data["pose"] = pose_estimator.get_pose_dict()
        data["path"] = pose_estimator.get_path()
    socketio.emit("grid_update", data)


@socketio.on("start_mapping")
def handle_start_mapping():
    """Start LiDAR mapping."""
    global mapping_active, mapping_thread
    print("🗺️  Start mapping requested")

    if mapping_active:
        _emit_lidar_state()
        return

    if not LIDAR_MODULES_AVAILABLE or not lidar_scanner:
        emit("lidar_state", {"mapping": False, "navigating": navigation_active,
                              "exploring": exploration_active, "available": False,
                              "error": "LiDAR not available"})
        return

    # Reset grid and pose for fresh mapping
    if occupancy_grid:
        occupancy_grid.__init__()
    if pose_estimator:
        pose_estimator.reset()

    mapping_stop_event.clear()
    mapping_active = True
    mapping_thread = threading.Thread(target=_mapping_loop, daemon=True)
    mapping_thread.start()
    _emit_lidar_state()


@socketio.on("stop_mapping")
def handle_stop_mapping():
    """Stop LiDAR mapping."""
    global mapping_active
    print("🗺️  Stop mapping requested")
    mapping_stop_event.set()
    mapping_active = False
    _emit_lidar_state()


# ============================================
# Autonomous Exploration
# ============================================

def _exploration_loop():
    """Background thread: frontier-based autonomous exploration."""
    global exploration_active, exploration_planner
    print("🔍 Exploration loop started")

    if not lidar_scanner or not occupancy_grid or not pose_estimator:
        print("✗ Missing modules for exploration")
        exploration_active = False
        _emit_lidar_state_broadcast()
        return

    # Start LiDAR if not running
    if not lidar_scanner.is_running:
        if not lidar_scanner.start():
            print("✗ Failed to start LiDAR for exploration")
            exploration_active = False
            _emit_lidar_state_broadcast()
            return

    # Reset pose and grid
    pose_estimator.reset()
    occupancy_grid.__init__()

    # Create exploration planner
    exploration_planner = ExplorationPlanner(occupancy_grid, pose_estimator)

    scan_count = 0
    while not explore_stop_event.is_set():
        scan = lidar_scanner.get_latest_scan()
        if scan:
            # Update grid
            pose = pose_estimator.get_pose()
            occupancy_grid.update_from_scan(pose, scan["points"])
            pose_estimator.correct_from_scan(occupancy_grid, scan["points"])

            # Plan next move
            cmd = exploration_planner.plan_step(scan)
            x, y = PathPlanner.command_to_joystick(cmd)
            state = apply_joystick(x, y)
            socketio.emit("motor_status", state)

            # Send scan points for radar display
            points = scan["points"]
            if len(points) > 360:
                step = len(points) // 360
                points = points[::step]
            socketio.emit("map_data", {
                "points": points,
                "point_count": len(points),
                "timestamp": scan["timestamp"],
            })

            # Send exploration status
            socketio.emit("explore_status", exploration_planner.get_status())

            # Send grid periodically
            scan_count += 1
            if scan_count % 15 == 0:  # ~every 2 seconds
                _emit_grid_and_pose()

            # Check if exploration complete
            if exploration_planner.complete:
                print("🔍 Exploration complete!")
                break

        explore_stop_event.wait(0.15)

    # Stop motors
    apply_joystick(0, 0)
    socketio.emit("motor_status", motor_state)

    # Final grid update
    _emit_grid_and_pose()

    # Detect walls and corners
    if occupancy_grid:
        occupancy_grid.detect_walls_and_corners()

    # Stop LiDAR if mapping isn't active
    if not mapping_active and lidar_scanner.is_running:
        lidar_scanner.stop()

    exploration_active = False
    print("🔍 Exploration loop stopped")
    _emit_lidar_state_broadcast()
    socketio.emit("explore_status", {
        "complete": True,
        "explored_pct": occupancy_grid.get_stats()["explored_pct"] if occupancy_grid else 0,
    })


@socketio.on("start_exploration")
def handle_start_exploration(data=None):
    """Start autonomous exploration."""
    global exploration_active, explore_thread
    mode = (data or {}).get("mode", "explore")
    print(f"🔍 Start exploration requested (mode={mode})")

    if exploration_active:
        _emit_lidar_state()
        return

    if not LIDAR_MODULES_AVAILABLE or not lidar_scanner:
        emit("lidar_state", {"mapping": mapping_active, "navigating": navigation_active,
                              "exploring": False, "available": False,
                              "error": "LiDAR not available"})
        return

    explore_stop_event.clear()
    exploration_active = True
    explore_thread = threading.Thread(target=_exploration_loop, daemon=True)
    explore_thread.start()
    _emit_lidar_state()


@socketio.on("stop_exploration")
def handle_stop_exploration():
    """Stop autonomous exploration."""
    global exploration_active
    print("🔍 Stop exploration requested")
    explore_stop_event.set()
    exploration_active = False
    _emit_lidar_state()


@socketio.on("set_explore_mode")
def handle_set_explore_mode(data):
    """Change exploration mode while running."""
    mode = data.get("mode", "explore")
    if exploration_planner:
        exploration_planner.set_mode(mode)
        emit("explore_status", exploration_planner.get_status())


# ============================================
# Autonomous Navigation (with saved map)
# ============================================

def _navigation_loop():
    """Background thread: scan → plan → drive, repeat."""
    global navigation_active
    print("🚗 Navigation loop started")

    if not lidar_scanner or not path_planner:
        print("✗ LiDAR or path planner not available")
        navigation_active = False
        _emit_lidar_state_broadcast()
        return

    # Start LiDAR if not already running
    if not lidar_scanner.is_running:
        if not lidar_scanner.start():
            print("✗ Failed to start LiDAR for navigation")
            navigation_active = False
            _emit_lidar_state_broadcast()
            return

    while not nav_stop_event.is_set():
        scan = lidar_scanner.get_latest_scan()
        if scan:
            # Update pose
            if occupancy_grid and pose_estimator:
                occupancy_grid.update_from_scan(
                    pose_estimator.get_pose(), scan["points"]
                )
                pose_estimator.correct_from_scan(occupancy_grid, scan["points"])

            # Plan the next movement
            cmd = path_planner.plan_step(scan)
            x, y = PathPlanner.command_to_joystick(cmd)
            state = apply_joystick(x, y)
            socketio.emit("motor_status", state)
            socketio.emit("nav_status", {
                "action": cmd["action"],
                "speed": cmd["speed"],
                "steering": cmd["steering"],
                "sector_distances": cmd["sector_distances"],
                "best_sector": cmd["best_sector"],
            })

            # Also send map data for live display
            points = scan["points"]
            if len(points) > 360:
                step = len(points) // 360
                points = points[::step]
            socketio.emit("map_data", {
                "points": points,
                "point_count": len(points),
                "timestamp": scan["timestamp"],
            })
        nav_stop_event.wait(0.15)

    # Stop motors when navigation ends
    apply_joystick(0, 0)
    socketio.emit("motor_status", motor_state)

    # Only stop LiDAR if mapping isn't active
    if not mapping_active and lidar_scanner.is_running:
        lidar_scanner.stop()

    navigation_active = False
    print("🚗 Navigation loop stopped")
    _emit_lidar_state_broadcast()


@socketio.on("start_navigation")
def handle_start_navigation():
    """Start autonomous navigation."""
    global navigation_active, nav_thread
    print("🚗 Start navigation requested")

    if navigation_active:
        _emit_lidar_state()
        return

    if not LIDAR_MODULES_AVAILABLE or not lidar_scanner:
        emit("lidar_state", {"mapping": mapping_active, "navigating": False,
                              "exploring": exploration_active, "available": False,
                              "error": "LiDAR not available"})
        return

    nav_stop_event.clear()
    navigation_active = True
    nav_thread = threading.Thread(target=_navigation_loop, daemon=True)
    nav_thread.start()
    _emit_lidar_state()


@socketio.on("stop_navigation")
def handle_stop_navigation():
    """Stop autonomous navigation."""
    global navigation_active
    print("🚗 Stop navigation requested")
    nav_stop_event.set()
    navigation_active = False
    _emit_lidar_state()


# ============================================
# Map Management (SocketIO)
# ============================================

@socketio.on("save_map")
def handle_save_map(data):
    """Save current occupancy grid as named map."""
    if not map_manager or not occupancy_grid:
        emit("map_saved", {"error": "No map data available"})
        return
    name = data.get("name", f"map_{int(time.time())}")
    meta = map_manager.save(occupancy_grid, name)
    emit("map_saved", meta)
    emit("map_list", map_manager.list_maps())


@socketio.on("load_map")
def handle_load_map(data):
    """Load a saved map."""
    global occupancy_grid
    if not map_manager:
        emit("map_loaded", {"error": "Maps not available"})
        return
    name = data.get("name")
    grid = map_manager.load(name)
    if grid is None:
        emit("map_loaded", {"error": f"Map '{name}' not found"})
        return
    occupancy_grid = grid
    emit("map_loaded", {"name": name, "stats": grid.get_stats()})
    _emit_grid_and_pose()


@socketio.on("delete_map")
def handle_delete_map(data):
    """Delete a saved map."""
    if not map_manager:
        return
    name = data.get("name")
    map_manager.delete(name)
    emit("map_list", map_manager.list_maps())


@socketio.on("list_maps")
def handle_list_maps():
    """List all saved maps."""
    if not map_manager:
        emit("map_list", [])
        return
    emit("map_list", map_manager.list_maps())


@socketio.on("return_to_start")
def handle_return_to_start():
    """Set exploration mode to return-to-start."""
    if exploration_planner:
        exploration_planner.set_mode("return")
        emit("explore_status", exploration_planner.get_status())


# ============================================
# Main
# ============================================
if __name__ == "__main__":
    import signal

    _shutting_down = False

    def _graceful_shutdown(signum, frame):
        global _shutting_down
        if _shutting_down:
            return  # prevent re-entry
        _shutting_down = True
        print("\n⚠ Shutting down…")
        # Stop active LiDAR operations
        mapping_stop_event.set()
        nav_stop_event.set()
        explore_stop_event.set()
        if lidar_scanner:
            try:
                lidar_scanner.disconnect()
            except Exception:
                pass
        if motors:
            try:
                motors.cleanup()
            except Exception:
                pass
        if not SIMULATION_MODE:
            try:
                GPIO.cleanup()
            except Exception:
                pass
        print("✓ Server stopped")
        os._exit(0)

    # Install our handler BEFORE any SDK calls
    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)

    init_motors()
    init_lidar()
    print("\n" + "=" * 60)
    print("MOTOR CONTROL SERVER + LiDAR + Exploration")
    print("=" * 60)
    mode_label = "SIMULATION" if SIMULATION_MODE else "REAL GPIO"
    lidar_label = "AVAILABLE" if LIDAR_MODULES_AVAILABLE else "NOT AVAILABLE"
    print(f"  Mode:    {mode_label}")
    print(f"  LiDAR:   {lidar_label}")
    print(f"  Address: http://0.0.0.0:5000")
    print("=" * 60 + "\n")

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)

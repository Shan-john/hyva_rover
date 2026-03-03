#!/usr/bin/env python3
"""Quick test: connect via WebSocket, trigger mapping, check for map_data events."""
import time
import sys

try:
    import socketio
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "python-socketio[client]", "websocket-client"], check=True)
    import socketio

received = []

sio = socketio.SimpleClient()

try:
    sio.connect("http://localhost:5000")
    print("✓ Connected to server")

    # Trigger mapping
    sio.emit("start_mapping")
    print("✓ Triggered start_mapping")

    # Wait up to 20s for map_data events (LiDAR takes ~5s to spin up)
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            event = sio.receive(timeout=1)
            if event[0] == "map_data":
                pts = event[1].get("points", [])
                print(f"✓ Received map_data with {len(pts)} points!")
                received.append(len(pts))
                if len(received) >= 3:
                    break
            elif event[0] == "lidar_state":
                print(f"  lidar_state: {event[1]}")
        except Exception:
            pass

    sio.emit("stop_mapping")
    sio.disconnect()

    if received:
        print(f"\n✅ SUCCESS — map data is flowing ({len(received)} frames, avg {sum(received)//len(received)} points/frame)")
    else:
        print("\n❌ FAIL — no map_data received within 20 seconds")

except Exception as e:
    print(f"✗ Error: {e}")

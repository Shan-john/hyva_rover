# 🚗 Hyva Rover

A **Raspberry Pi-powered autonomous rover** with a web-based control interface. Drive manually with a touch joystick, scan your surroundings with an **RPLidar A1**, build occupancy-grid maps in real time, and let the rover explore on its own using frontier-based autonomous navigation.

Built with **Flask + Socket.IO** (backend) and **React + Vite** (frontend).

---

## ✨ Features

### 🎮 Manual Control
- **Touch Joystick** — responsive dual-axis control (throttle + steering)
- **Differential Drive** — smooth turns via independent left/right motor speeds
- **Special Actions** — 360° spin, 180° spin, wiggle, spin left/right (tap or hold)
- **Emergency Stop** — instant motor kill from the UI

### 🗺️ LiDAR Mapping
- **RPLidar A1** integration via a crash-safe child process
- **Real-time occupancy grid** streamed to the browser over WebSocket
- **Dead reckoning** pose estimation (wheel-base odometry)
- **Save / Load / Delete** named maps

### 🤖 Autonomous Modes
- **Frontier-based exploration** — the rover discovers unmapped areas automatically
- **Autonomous navigation** — path planning on a saved map
- **Return-to-start** — one-tap command to navigate home

### 🔒 Safety
- Auto-stop on connection loss or joystick release
- Joystick touch instantly cancels any running action
- Graceful shutdown with `SIGINT` / `SIGTERM` handlers

---

## 🛠️ Hardware

| Component | Details |
|---|---|
| **SBC** | Raspberry Pi 3 / 4 / Zero W |
| **Motor Driver** | L298N (dual H-bridge) |
| **Motors** | 2 × DC gear motors + chassis + wheels |
| **LiDAR** | RPLidar A1 (USB serial) |
| **Power** | Battery pack for Pi + separate battery for L298N |

### Wiring (Default GPIO — BCM)

| L298N Pin | RPi GPIO |
|---|---|
| ENA | 22 |
| IN1 | 17 |
| IN2 | 27 |
| IN3 | 23 |
| IN4 | 24 |
| ENB | 25 |

> Pin mappings are configurable in `config.py`.

---

## 🚀 Getting Started

### 1. Clone
```bash
git clone https://github.com/Shan-john/hyva_rover.git
cd hyva_rover
```

### 2. Backend Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Dependencies:** `flask`, `flask-cors`, `flask-socketio`, `rplidar-roboticia`, `RPi.GPIO`

### 3. Frontend Setup
```bash
cd web
npm install
```

### 4. Run

**Start the server** (requires `sudo` for GPIO):
```bash
sudo python3 server.py
```

**Start the frontend dev server:**
```bash
cd web
npm run dev -- --host
```

Open `http://<PI_IP>:5173` on your phone or laptop.

---

## 🔧 Configuration

All tunables live in **`config.py`**:

| Parameter | Default | Description |
|---|---|---|
| `MOTOR_DEFAULT_SPEED` | 70 | Default motor PWM % |
| `LIDAR_PORT` | `/dev/ttyUSB0` | RPLidar serial port |
| `LIDAR_BAUDRATE` | 115200 | RPLidar A1 baud rate |
| `LIDAR_MAX_RANGE` | 12.0 m | Max detection range |
| `GRID_RESOLUTION` | 0.05 m | Occupancy grid cell size |
| `NAV_OBSTACLE_THRESHOLD` | 0.35 m | Obstacle avoidance distance |
| `EXPLORE_SPEED` | 40 | PWM % during exploration |

---

## 📂 Project Structure

```
carprc/
├── server.py              # Flask + Socket.IO server (motor, LiDAR, nav events)
├── main_dual_motor.py     # L298N dual motor driver (RPi.GPIO)
├── lidar_scanner.py       # RPLidar A1 child-process wrapper
├── occupancy_grid.py      # 2D occupancy grid (log-odds)
├── path_planner.py        # Frontier detection + path planning
├── pose_estimator.py      # Dead-reckoning pose tracker
├── map_manager.py         # Save / load / delete maps
├── config.py              # All hardware & navigation constants
├── requirements.txt       # Python dependencies
├── web/                   # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx        # Main UI + socket logic
│   │   ├── index.css      # Styles
│   │   └── components/
│   │       ├── Joystick.jsx    # Touch joystick component
│   │       └── MotorStatus.jsx # Motor status display
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── maps/                  # Saved map files
```

---

## 📜 License

MIT License

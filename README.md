# 🏎️ WiFi Car Control Project

A web-based car control system powered by **Raspberry Pi**, **Flask** (Python), and **React** (Vite). It features a responsive joystick interface, real-time WebSocket communication, and special action buttons for automated maneuvers.

## ✨ Features

- **Real-time Control:** Low-latency WebSocket communication (Socket.IO).
- **Responsive Interface:** Works on mobile and desktop with touch support.
- **Dual Joystick Axes:** 
  - **Y-Axis:** Throttle (Forward/Backward)
  - **X-Axis:** Steering (Left/Right) - Differential Drive
- **Special Actions:**
  - **🔄 Spin L/R:** Quick 360° turn (Hold to activate)
  - **💃 Wiggle:** Rapid left-right shake (Hold to activate)
  - **🌪️ 360° Spin:** Automated full 360 degree spin (Single tap, 2.5s duration)
  - **💫 180° Spin:** Automated half 180 degree spin (Single tap, 1.25s duration)
- **Safety Features:**
  - **⛔ Emergency Stop:** Immediately cuts power to motors.
  - **Auto-Stop:** Motors stop if connection is lost or joystick is released.
  - **Action Interrupt:** Touching the joystick immediately cancels any automated action.

## 🛠️ Hardware Requirements

- **Raspberry Pi** (3, 4, or Zero W) with WiFi capability.
- **L298N Motor Driver Module**.
- **DC Motors** (2x) + Chassis + Wheels.
- **Power Supply** (Battery pack for Pi + separate battery for motors/L298N).
- **Jumper Wires**.

### wiring (Default GPIO Config)

| L298N Pin | Raspberry Pi GPIO (BCM) |
| :--- | :--- |
| **ENA** | GPIO 22 |
| **IN1** | GPIO 17 |
| **IN2** | GPIO 27 |
| **IN3** | GPIO 23 |
| **IN4** | GPIO 24 |
| **ENB** | GPIO 25 |

> **Note:** Pin mappings can be changed in `config.py`.

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd carprc
```

### 2. Setup Backend (Flask)
```bash
# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
*Dependencies: `flask`, `flask-cors`, `flask-socketio`, `RPi.GPIO`*

### 3. Setup Frontend (React)
```bash
cd web
npm install
```

## 🎮 Usage

### 1. Start the Backend Server (on Raspberry Pi)
Requires `sudo` for GPIO access.
```bash
# From project root
sudo python3 server.py
```
*Server runs on port 5000.*

### 2. Start the Frontend Dev Server
```bash
# From project root
cd web
npm run dev -- --host
```
*Access the controller via `http://<YOUR_PI_IP>:5173` on your phone or laptop.*

## 🔧 Configuration
- **Motor Speed:** Adjust `MOTOR_DEFAULT_SPEED` in `config.py`.
- **Pin Mapping:** Modify GPIO pin numbers in `config.py`.
- **Joystick Sensitivity:** Adjust `DEAD_ZONE` in `server.py` or scaling factors in `Joystick.jsx`.

## 📂 Project Structure
- `server.py`: Flask application handling WebSocket events and motor logic.
- `main_dual_motor.py`: Low-level motor control class using RPi.GPIO.
- `config.py`: Configuration file for pins and constants.
- `web/`: React frontend application.
  - `src/components/Joystick.jsx`: Touch-enabled joystick component.
  - `src/App.jsx`: Main UI logic and socket communication.

## 📜 License
MIT License

#!/bin/bash

# --- Start Rover Script ---

# 1. Kill any existing processes (optional, but helps avoid port conflicts)
echo "🛑 Stopping any existing services..."
sudo pkill -f server.py
pkill -f vite

# 2. Start Backend Server
echo "🚀 Starting Backend Server (with sudo for GPIO)..."
# We use & to run it in the background
sudo ./venv/bin/python server.py &
BACKEND_PID=$!

# 3. Wait a moment for backend to initialize
sleep 2

# 4. Start Frontend
echo "🌐 Starting Frontend Dev Server..."
cd web
npm run dev

# After the user stops (Ctrl+C), cleanup
trap "kill $BACKEND_PID; exit" INT

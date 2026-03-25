#!/bin/bash

# Regulatory Risk Analysis System - Start Script

# Function to handle cleanup on exit
cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    exit
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

echo "Starting Regulatory Risk Analysis System..."

# Start the backend
echo "Starting Backend on http://127.0.0.1:6969..."
(
    source .venv/bin/activate
    export PYTHONPATH=$PYTHONPATH:.
    python backend/main.py
) &
BACKEND_PID=$!

# Wait a moment for backend to initialize
sleep 3

# Start the frontend
echo "Starting Frontend on http://localhost:5173..."
cd frontend
# Ensure no python env variables leak to npm
unset VIRTUAL_ENV
npm run dev -- --port 5173 --host 127.0.0.1

# When frontend stops, cleanup will be called
cleanup

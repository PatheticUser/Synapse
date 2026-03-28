#!/bin/bash

# Research Agent Pro Run Script
# Provides an option to run the CLI or the Full Stack (API + Frontend)

echo "==================================================="
echo "Starting Synapse AI Agent (Linux Edition)"
echo "==================================================="

# Ensure uv is available/environment is created. We assume uv is installed as per pyproject.toml
if command -v uv &> /dev/null; then
    # We can just rely on uv run
    PYTHON_CMD="uv run"
else
    # Fallback to local venv
    if [ -f .venv/bin/activate ]; then
        source .venv/bin/activate
        PYTHON_CMD="python"
    else
        echo "Error: 'uv' is not installed and '.venv' not found."
        echo "Please install dependencies or use uv."
        exit 1
    fi
fi

# Trap to kill all background processes on script exit
trap "trap - SIGTERM && kill -- -$$ 2>/dev/null" SIGINT SIGTERM EXIT

run_stack() {
    echo ""
    echo "[1/2] Starting FastAPI Backend..."
    # Start backend in background
    $PYTHON_CMD main.py &
    BACKEND_PID=$!
    
    echo "[2/2] Starting React Frontend..."
    cd frontend || { echo "Frontend directory not found!"; exit 1; }
    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        echo "Error: npm is not installed. Required for frontend."
        exit 1
    fi
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    echo ""
    echo "Both services are starting up!"
    echo "- Backend will be available at http://localhost:8000"
    echo "- Frontend will be available at http://localhost:5173"
    echo ""
    
    echo "Opening browser in 3 seconds..."
    sleep 3
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:5173 >/dev/null 2>&1 &
    elif command -v python3 &> /dev/null; then
        python3 -m webbrowser http://localhost:5173 >/dev/null 2>&1 &
    fi

    echo "Press Ctrl+C to stop both services."
    
    # Wait for processes
    wait $BACKEND_PID $FRONTEND_PID
}

run_stack

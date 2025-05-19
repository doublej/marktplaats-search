#!/bin/bash
# start_services.sh - Manage MarktplaatsSearch services
#
# This script:
# 1. Kills any running instances of the API server and Gradio UI
# 2. Starts the API server in the background
# 3. Starts the Gradio UI in the background
# 4. Tests the API to verify it's working

# Text colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🐒 MarktplaatsSearch Service Manager 🐒"
echo "--------------------------------------"

# Project directory - adjust if needed
PROJECT_DIR="$(pwd)"
API_SCRIPT="$PROJECT_DIR/app/main.py"  # Updated path to the correct location
GRADIO_SCRIPT="$PROJECT_DIR/marktplaats_gradio_ui.py"  # Updated path to the correct location
PYTHON_EXECUTABLE="$PROJECT_DIR/.venv/bin/python"  # Use the venv Python

# Directory for logs
LOG_DIR="$HOME/Library/Logs/MarktplaatsSearch"
API_LOG="$LOG_DIR/api.log"
GRADIO_LOG="$LOG_DIR/gradio.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to kill a process if it's running
kill_process() {
    local process_name="$1"
    local pids=$(pgrep -f "$process_name")
    
    if [ -n "$pids" ]; then
        echo "🛑 Stopping existing $process_name processes..."
        echo "$pids" | xargs kill -9
        echo "✅ Stopped $process_name processes."
    else
        echo "ℹ️ No running $process_name processes found."
    fi
}

# Print project structure to help debug
echo "📂 Project structure (to help identify correct paths):"
find "$PROJECT_DIR" -name "*.py" | grep -E "main.py|app.py|marktplaats_gradio_ui.py" | head -10
echo ""

# Kill any existing processes
kill_process "main.py"
kill_process "marktplaats_gradio_ui.py"

echo ""
echo "🚀 Starting services..."

# Check if the script files exist
if [ ! -f "$API_SCRIPT" ]; then
    echo "❌ API script not found at: $API_SCRIPT"
    echo "Please update the API_SCRIPT path in the script."
    exit 1
fi

if [ ! -f "$GRADIO_SCRIPT" ]; then
    echo "❌ Gradio script not found at: $GRADIO_SCRIPT"
    echo "Please update the GRADIO_SCRIPT path in the script."
    exit 1
fi

# Clear existing log files
> "$API_LOG"
> "$GRADIO_LOG"

# Start API service
echo "🔌 Starting API server..."
cd "$PROJECT_DIR" && "$PYTHON_EXECUTABLE" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$API_LOG" 2>&1 &
API_PID=$!
echo "✅ API server started with PID: $API_PID"

# Give the API a moment to start
sleep 2

# Start Gradio interface
echo "🖥️ Starting Gradio interface..."
cd "$PROJECT_DIR" && "$PYTHON_EXECUTABLE" "$GRADIO_SCRIPT" > "$GRADIO_LOG" 2>&1 &
GRADIO_PID=$!
echo "✅ Gradio interface started with PID: $GRADIO_PID"

# Display API routes to help debugging
echo ""
echo "🔎 Checking API routes..."
sleep 3  # Give API a moment to fully start
echo "API routes check: (use these in the client)"
curl -s http://localhost:8000/openapi.json | jq -r '.paths | keys[]' | sort | head -10
echo "..."

echo ""
echo "📝 Opening logs in macOS Console..."

# Open Console app
open -a Console "$API_LOG" "$GRADIO_LOG"

# Test the API
echo ""
echo "🧪 Testing API connectivity..."
curl -s http://localhost:8000/health | grep -q "ok" && echo "✅ API is responding correctly" || echo "❌ API test failed"

echo ""
echo "📊 Services status:"
echo "API server (PID: $API_PID) - Log: $API_LOG"
echo "Gradio interface (PID: $GRADIO_PID) - Log: $GRADIO_LOG"
echo ""
echo "🔍 You can view the logs in the macOS Console app"
echo "🌐 API is available at: http://localhost:8000"
echo "🖱️ Gradio UI is available at: http://localhost:7860"
echo ""
echo "To stop services, run: kill -9 $API_PID $GRADIO_PID" 
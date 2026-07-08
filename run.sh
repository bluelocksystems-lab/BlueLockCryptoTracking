#!/usr/bin/env bash
# =============================================================================
# BlueLock Crypto Tracking V1.4
# =============================================================================
# Usage: chmod +x run.sh && ./run.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  BlueLock Crypto Tracking V1.4"
echo "============================================================"

# Check Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "ERROR: Python 3 is not installed or not in PATH."
    echo "Install it from https://www.python.org/downloads/"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo ""
    echo "ERROR: Python 3.10 or higher is required. You have $PYTHON_VERSION."
    echo "Download the latest Python from https://www.python.org/downloads/"
    echo ""
    exit 1
fi

echo "Python $PYTHON_VERSION found."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install or update dependencies
echo "Checking dependencies..."
pip install -r backend/requirements.txt --quiet

# Verify critical packages actually import (catches partial/corrupt installs
# that pip itself didn't flag as a failure)
if ! python -c "import fastapi, uvicorn, httpx, pydantic" &> /dev/null; then
    echo ""
    echo "ERROR: One or more required packages failed to import."
    echo "Try deleting the 'venv' folder and running this script again."
    echo ""
    exit 1
fi

# Create data directory
mkdir -p data

# Read the actual bind address from config.py, so this script, the port
# check below, and the server itself can never drift out of sync.
SERVER_HOST=$(python -c "import sys; sys.path.insert(0, 'backend'); import config; print(config.SERVER_HOST)")
SERVER_PORT=$(python -c "import sys; sys.path.insert(0, 'backend'); import config; print(config.SERVER_PORT)")

# Friendly check for a stale server already bound to the port - this is the
# most common "it won't start" report, and the raw uvicorn/asyncio error for
# it is not obvious to a non-technical user.
if python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.5)
import sys
sys.exit(0 if s.connect_ex(('$SERVER_HOST', $SERVER_PORT)) == 0 else 1)
"; then
    echo ""
    echo "ERROR: Port $SERVER_PORT is already in use."
    echo "BlueLock may already be running in another window or terminal -"
    echo "check for it there, or stop whatever else is using port $SERVER_PORT."
    echo ""
    exit 1
fi

echo ""
echo "Starting server at http://$SERVER_HOST:$SERVER_PORT"
echo "Press Ctrl+C to stop."
echo ""

# Open browser (best-effort, don't fail if it doesn't work)
if command -v xdg-open &> /dev/null; then
    (sleep 2 && xdg-open "http://$SERVER_HOST:$SERVER_PORT") &
elif command -v open &> /dev/null; then
    (sleep 2 && open "http://$SERVER_HOST:$SERVER_PORT") &
fi

cd backend
python main.py

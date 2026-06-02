#!/usr/bin/env bash
# =============================================================================
# BlueLock Crypto Tracking — Linux / macOS Launcher
# =============================================================================
# Usage: chmod +x run.sh && ./run.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  BlueLock Crypto Tracking"
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

# Create data directory
mkdir -p data

echo ""
echo "Starting server at http://127.0.0.1:8765"
echo "Press Ctrl+C to stop."
echo ""

# Open browser (best-effort, don't fail if it doesn't work)
if command -v xdg-open &> /dev/null; then
    (sleep 2 && xdg-open http://127.0.0.1:8765) &
elif command -v open &> /dev/null; then
    (sleep 2 && open http://127.0.0.1:8765) &
fi

cd backend
uvicorn main:app --host 127.0.0.1 --port 8765

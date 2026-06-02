@echo off
:: =============================================================================
:: BlueLock Crypto Tracking V1 — Windows Launcher
:: =============================================================================
:: This script:
::   1. Checks Python is installed
::   2. Creates a virtual environment (if needed)
::   3. Installs required packages
::   4. Initializes the database
::   5. Opens the browser
::   6. Starts the FastAPI server
:: =============================================================================

title BlueLock Crypto Tracking V1
color 0B

echo.
echo  BlueLock Crypto Tracking V1
echo  Open-source Privacy-Focused Crypto Tracker
echo  ============================================================
echo.

:: Change to the directory containing this script
cd /d "%~dp0"

:: ---------------------------------------------------------------------------
:: Step 1: Check Python Installation
:: ---------------------------------------------------------------------------
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python is not installed or not in PATH.
    echo.
    echo  Please install Python 3.10 or higher from:
    echo  https://www.python.org/downloads/
    echo.
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

python --version
echo  Python found.
echo.

:: ---------------------------------------------------------------------------
:: Step 2: Create Virtual Environment
:: ---------------------------------------------------------------------------
echo [2/5] Setting up virtual environment...

if not exist "venv\" (
    echo  Creating new virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  Virtual environment created.
) else (
    echo  Virtual environment already exists.
)
echo.

:: ---------------------------------------------------------------------------
:: Step 3: Install Requirements
:: ---------------------------------------------------------------------------
echo [3/5] Installing requirements...
call venv\Scripts\activate.bat

pip install --quiet --upgrade pip
pip install --quiet -r backend\requirements.txt

if %errorlevel% neq 0 (
    echo  ERROR: Failed to install requirements.
    echo  Check your internet connection and try again.
    pause
    exit /b 1
)
echo  Requirements installed.
echo.

:: ---------------------------------------------------------------------------
:: Step 4: Create Data Directory
:: ---------------------------------------------------------------------------
echo [4/5] Initializing data directory...
if not exist "data\" (
    mkdir data
    echo  Created data directory.
) else (
    echo  Data directory ready.
)
echo.

:: ---------------------------------------------------------------------------
:: Step 5: Start Server and Open Browser
:: ---------------------------------------------------------------------------
echo [5/5] Starting BlueLock server...
echo.
echo  Server URL: http://127.0.0.1:8765
echo  Press Ctrl+C to stop the server.
echo.
echo  ============================================================
echo.

:: Wait a moment then open browser
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8765"

:: Start the FastAPI server (this blocks until Ctrl+C)
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8765 --reload

echo.
echo  Server stopped. Press any key to exit.
pause >nul

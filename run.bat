@echo off
:: =============================================================================
:: BlueLock Crypto Tracking V1.4 — Windows Launcher
:: =============================================================================
:: This script:
::   1. Changes to the script directory
::   2. Verifies Python 3.10+ is installed
::   3. Creates a virtual environment (if missing)
::   4. Upgrades pip safely using python -m pip
::   5. Installs all required packages
::   6. Verifies installation succeeded
::   7. Creates the data directory if missing
::   8. Reads host/port from backend\config.py and checks the port is free
::   9. Starts the FastAPI server
::   10. Opens the browser once the server is ready
:: =============================================================================

title BlueLock Crypto Tracking V1.4
color 0B
setlocal enabledelayedexpansion

echo.
echo  ============================================================
echo   BlueLock Crypto Tracking V1.4
echo   Open-source Privacy-Focused Crypto Tracker
echo  ============================================================
echo.

:: ---------------------------------------------------------------------------
:: Step 0: Change to the directory containing this script
:: This ensures all relative paths work regardless of where cmd.exe was opened.
:: ---------------------------------------------------------------------------
cd /d "%~dp0"

:: ---------------------------------------------------------------------------
:: Step 1: Verify Python Installation
:: ---------------------------------------------------------------------------
echo  [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python is not installed or not in your PATH.
    echo.
    echo  Please download and install Python 3.10 or higher:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During installation, check the box that says:
    echo  "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

:: Check Python version is 3.10+
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PYVER=%%V
for /f "tokens=1,2 delims=." %%A in ("%PYVER%") do (
    set PYMAJ=%%A
    set PYMIN=%%B
)
if %PYMAJ% LSS 3 (
    echo  ERROR: Python 3.10+ required. Found Python %PYVER%.
    echo  Download from https://www.python.org/downloads/
    pause
    exit /b 1
)
if %PYMAJ% EQU 3 if %PYMIN% LSS 10 (
    echo  ERROR: Python 3.10+ required. Found Python %PYVER%.
    echo  Download from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo   Python %PYVER% found. OK
echo.

:: ---------------------------------------------------------------------------
:: Step 2: Create Virtual Environment (if missing)
:: ---------------------------------------------------------------------------
echo  [2/6] Setting up virtual environment...

if not exist "venv\Scripts\python.exe" (
    echo   Creating new virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: Failed to create virtual environment.
        echo  Make sure you have write permission to this folder.
        echo.
        pause
        exit /b 1
    )
    echo   Virtual environment created.
) else (
    echo   Virtual environment ready.
)
echo.

:: ---------------------------------------------------------------------------
:: Step 3: Upgrade pip (using python -m pip to avoid pip.exe lock issues)
:: ---------------------------------------------------------------------------
echo  [3/6] Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo   WARNING: pip upgrade failed. Continuing with existing pip version.
)
echo   pip ready.
echo.

:: ---------------------------------------------------------------------------
:: Step 4: Install Requirements
:: ---------------------------------------------------------------------------
echo  [4/6] Installing dependencies...
venv\Scripts\python.exe -m pip install -r backend\requirements.txt --quiet
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Failed to install dependencies.
    echo.
    echo  Possible causes:
    echo    - No internet connection
    echo    - Firewall blocking pip
    echo    - Disk space issue
    echo.
    echo  Try running this command manually to see the full error:
    echo  venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    echo.
    pause
    exit /b 1
)
echo   Dependencies installed.
echo.

:: ---------------------------------------------------------------------------
:: Step 5: Verify Critical Packages Loaded
:: ---------------------------------------------------------------------------
echo  [5/6] Verifying installation...
venv\Scripts\python.exe -c "import fastapi, uvicorn, httpx, pydantic" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: One or more required packages failed to import.
    echo  Please delete the 'venv' folder and run this script again.
    echo.
    pause
    exit /b 1
)
echo   All packages verified.
echo.

:: ---------------------------------------------------------------------------
:: Step 6: Create Data Directory
:: ---------------------------------------------------------------------------
echo  [6/6] Checking data directory...
if not exist "data\" (
    mkdir data
    echo   Created data directory.
) else (
    echo   Data directory ready.
)
echo.

:: ---------------------------------------------------------------------------
:: Step 6a: Read Host/Port From config.py
:: This is what makes editing backend\config.py actually change where the
:: server binds - the port check, the server itself, and the browser URL
:: all read from the same place instead of three separately hardcoded 8765s.
:: ---------------------------------------------------------------------------
for /f "delims=" %%H in ('venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); import config; print(config.SERVER_HOST)"') do set SERVERHOST=%%H
for /f "delims=" %%P in ('venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); import config; print(config.SERVER_PORT)"') do set SERVERPORT=%%P

:: ---------------------------------------------------------------------------
:: Step 6b: Check The Configured Port Isn't Already In Use
:: This is the most common "it won't start" report, and the raw uvicorn
:: error for it is not obvious to a non-technical user.
:: ---------------------------------------------------------------------------
netstat -an | findstr "%SERVERHOST%:%SERVERPORT%" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo  ERROR: Port %SERVERPORT% is already in use.
    echo  BlueLock may already be running in another window - check for it
    echo  there, or close whatever else is using port %SERVERPORT%.
    echo.
    pause
    exit /b 1
)
echo.

:: ---------------------------------------------------------------------------
:: Start Server
:: ---------------------------------------------------------------------------
echo  ============================================================
echo   Starting BlueLock Crypto Tracking...
echo   URL: http://%SERVERHOST%:%SERVERPORT%
echo   Press Ctrl+C to stop the server.
echo  ============================================================
echo.

:: Open browser in background after server has had time to start
start "" cmd /c "timeout /t 4 /nobreak >nul && start "" "http://%SERVERHOST%:%SERVERPORT%""

:: Start FastAPI server using venv Python directly (no --reload, no watchfiles
:: dependency). main.py's __main__ block reads config.SERVER_HOST/SERVER_PORT
:: itself, so there's no port/host duplicated here.
cd backend
..\venv\Scripts\python.exe main.py

echo.
echo  Server stopped.
echo  Press any key to close this window.
pause >nul

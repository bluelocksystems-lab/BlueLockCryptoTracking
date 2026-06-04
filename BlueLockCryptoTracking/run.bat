@echo off
:: =============================================================================
:: BlueLock Crypto Tracking V1.3 — Windows Launcher
:: =============================================================================
:: This script:
::   1. Changes to the script directory
::   2. Verifies Python 3.10+ is installed
::   3. Creates a virtual environment (if missing)
::   4. Upgrades pip safely using python -m pip
::   5. Installs all required packages
::   6. Verifies installation succeeded
::   7. Creates the data directory if missing
::   8. Starts the FastAPI server
::   9. Opens the browser once the server is ready
:: =============================================================================

title BlueLock Crypto Tracking V1.3
color 0B
setlocal enabledelayedexpansion

echo.
echo  ============================================================
echo   BlueLock Crypto Tracking V1.3
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
:: Start Server
:: ---------------------------------------------------------------------------
echo  ============================================================
echo   Starting BlueLock Crypto Tracking...
echo   URL: http://127.0.0.1:8765
echo   Press Ctrl+C to stop the server.
echo  ============================================================
echo.

:: Open browser in background after server has had time to start
start "" cmd /c "timeout /t 4 /nobreak >nul && start "" "http://127.0.0.1:8765""

:: Start FastAPI server using venv Python directly (no --reload, no watchfiles dependency)
cd backend
..\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8765

echo.
echo  Server stopped.
echo  Press any key to close this window.
pause >nul

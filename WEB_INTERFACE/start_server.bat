@echo off
REM GuardLocker Startup Script for Windows

echo ============================================================
echo 🔒 GuardLocker Web Interface Launcher
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed!
    echo Please install Python 3.11 or higher from python.org
    pause
    exit /b 1
)

echo ✓ Python found
python --version

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Flask not found. Installing...
    pip install flask flask-cors
)

echo ✓ Flask is installed
echo.

REM Check if requirements.txt exists
if exist requirements.txt (
    echo 📦 Found requirements.txt
    set /p install="Do you want to install full dependencies? (y/N): "
    if /i "%install%"=="y" (
        echo Installing dependencies...
        pip install -r requirements.txt
    )
)

echo.
echo 🚀 Starting GuardLocker Web Server...
echo.
echo 📍 Server will be available at: http://localhost:5000
echo 🛑 Press Ctrl+C to stop the server
echo.
echo Opening in browser in 3 seconds...
timeout /t 3 /nobreak >nul

REM Open browser
start http://localhost:5000

echo.
echo ============================================================
echo.

REM Start the server
python web_server.py

pause
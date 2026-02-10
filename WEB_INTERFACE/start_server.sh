#!/bin/bash

# GuardLocker Startup Script
# This script starts the GuardLocker web server

echo "============================================================"
echo "🔒 GuardLocker Web Interface Launcher"
echo "============================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not found. Installing..."
    pip install flask flask-cors
fi

echo "✓ Flask is installed"
echo ""

# Check if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Found requirements.txt"
    read -p "Do you want to install full dependencies? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing dependencies..."
        pip install -r requirements.txt
    fi
fi

echo ""
echo "🚀 Starting GuardLocker Web Server..."
echo ""
echo "📍 Server will be available at: http://localhost:5000"
echo "🛑 Press Ctrl+C to stop the server"
echo ""
echo "Opening in browser in 3 seconds..."
sleep 1
echo "2..."
sleep 1
echo "1..."
sleep 1

# Try to open browser (different commands for different OS)
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5000 &
elif command -v open &> /dev/null; then
    open http://localhost:5000 &
elif command -v start &> /dev/null; then
    start http://localhost:5000 &
fi

echo ""
echo "============================================================"
echo ""

# Start the server
python3 web_server.py
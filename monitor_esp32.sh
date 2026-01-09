#!/bin/bash
# Serial Monitor Launcher untuk ESP32 di Raspberry Pi 5

echo "🔧 ESP32 Serial Monitor - Quick Launcher"
echo "========================================"
echo ""

# Check if main app is running
if pgrep -f "main_raspy.py" > /dev/null; then
    echo "⚠️  WARNING: main_raspy.py is running!"
    echo "   ESP32 serial port sedang digunakan oleh aplikasi utama"
    echo ""
    echo "Pilihan:"
    echo "1. Stop main app dan buka serial monitor"
    echo "2. Cancel (biarkan main app running)"
    echo ""
    read -p "Pilihan (1/2): " choice
    
    if [ "$choice" = "1" ]; then
        echo "🛑 Stopping main application..."
        pkill -f main_raspy.py
        sleep 2
        echo "✅ Main app stopped"
    else
        echo "❌ Cancelled. Main app tetap running."
        exit 0
    fi
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

# Check if serial_monitor.py exists
if [ ! -f "serial_monitor.py" ]; then
    echo "❌ serial_monitor.py not found!"
    echo "   Make sure you're in the Mobil_raspy directory"
    exit 1
fi

# Launch serial monitor
echo "🚀 Starting ESP32 Serial Monitor..."
echo ""
python3 serial_monitor.py

# Deactivate venv when done
if [ -f "venv/bin/activate" ]; then
    deactivate 2>/dev/null || true
fi

echo ""
echo "👋 Serial Monitor session ended"
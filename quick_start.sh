#!/bin/bash
# Quick Start Guide untuk Raspberry Pi 5
# Run this script setelah clone dari GitHub

echo "🚀 Quick Start - AI Voice Robot Raspberry Pi 5"
echo "=============================================="
echo ""

# Check if we're on Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    PI_MODEL=$(cat /proc/device-tree/model)
    echo "📍 Detected: $PI_MODEL"
    
    if [[ "$PI_MODEL" == *"Raspberry Pi 5"* ]]; then
        echo "✅ Raspberry Pi 5 confirmed!"
    else
        echo "⚠️  Warning: Not Raspberry Pi 5, but continuing..."
    fi
else
    echo "⚠️  Warning: Cannot detect Pi model"
fi

echo ""
echo "🔧 Setting executable permissions..."

# Set permissions for all scripts
chmod +x setup_raspy.sh
chmod +x run_raspy.sh  
chmod +x setup_gpio_uart.sh
chmod +x test_uart.sh
chmod +x monitor_esp32.sh

echo "✅ Permissions set"
echo ""

echo "📋 What to do next:"
echo "==================="
echo ""
echo "1. Run full setup (will take 10-15 minutes):"
echo "   ./setup_raspy.sh"
echo ""
echo "2. Connect ESP32 hardware:"
echo "   Option A: USB Cable (recommended)"  
echo "   Option B: GPIO UART (run ./setup_gpio_uart.sh)"
echo ""
echo "3. Upload ESP32 code:"
echo "   Use Arduino IDE to upload ESP32_Robot_RaspyPi5.ino"
echo ""
echo "4. Run the robot:"
echo "   ./run_raspy.sh"
echo ""
echo "🔧 Optional tools:"
echo "   ./monitor_esp32.sh    - Monitor ESP32 communication"
echo "   ./test_uart.sh        - Test GPIO UART (if using Option B)"
echo ""
echo "📖 For detailed instructions: cat README.md"
echo ""
echo "🆘 Need help? Check troubleshooting in README.md"
echo ""

read -p "Start full setup now? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting setup..."
    ./setup_raspy.sh
else
    echo "👍 Setup cancelled. Run ./setup_raspy.sh when ready."
fi
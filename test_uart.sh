#!/bin/bash
# Test GPIO UART Connection - Raspberry Pi 5

echo "🔧 GPIO UART Connection Test"
echo "============================="
echo ""

# Check if /dev/ttyS0 exists
if [ -e "/dev/ttyS0" ]; then
    echo "✅ /dev/ttyS0 exists"
else
    echo "❌ /dev/ttyS0 not found!"
    echo "   Run: ./setup_gpio_uart.sh"
    exit 1
fi

# Check permissions
echo "📋 /dev/ttyS0 permissions:"
ls -l /dev/ttyS0

echo ""
echo "🔍 Testing UART loopback (short TX to RX for test):"
echo "   Connect GPIO 14 (TX) to GPIO 15 (RX) temporarily"
echo "   Or test dengan ESP32 connected"
echo ""

read -p "Continue dengan test? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Test cancelled"
    exit 0
fi

# Test basic UART communication
echo "📡 Testing UART write/read..."

# Create simple Python test
cat > /tmp/uart_test.py << 'EOF'
#!/usr/bin/env python3
import serial
import time

try:
    # Open UART port
    ser = serial.Serial('/dev/ttyS0', 115200, timeout=2)
    print("✅ UART port opened successfully")
    
    # Send test string
    test_string = "UART_TEST_123"
    print(f"📤 Sending: {test_string}")
    ser.write((test_string + "\n").encode())
    ser.flush()
    
    # Try to read (will only work if ESP32 connected and echoing)
    time.sleep(0.5)
    if ser.in_waiting:
        response = ser.readline().decode().strip()
        print(f"📥 Received: {response}")
    else:
        print("📭 No response (normal jika ESP32 belum connected)")
    
    ser.close()
    print("✅ UART test completed")
    
except Exception as e:
    print(f"❌ UART test failed: {e}")
    print("   Check permissions: sudo usermod -a -G dialout $USER")
    print("   Then logout and login again")

EOF

python3 /tmp/uart_test.py
rm /tmp/uart_test.py

echo ""
echo "🔧 Next steps:"
echo "1. Connect ESP32 dengan wiring sesuai diagram"
echo "2. Upload ESP32 code dengan Serial.begin(115200)"  
echo "3. Test dengan: python3 serial_monitor.py"
echo "4. Jalankan aplikasi: ./run_raspy.sh"
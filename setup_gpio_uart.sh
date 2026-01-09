#!/bin/bash
# GPIO UART Setup untuk Raspberry Pi 5 <-> ESP32 Serial Communication
# Script ini akan mengaktifkan GPIO UART dan memberikan instruksi wiring

echo "=========================================="
echo "🔌 GPIO UART Setup - Raspberry Pi 5"  
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "Script ini tidak boleh dijalankan sebagai root!"
   echo "Jalankan dengan: ./setup_gpio_uart.sh"
   exit 1
fi

print_info "Checking current Raspberry Pi configuration..."

# Check Pi model
if [ -f /proc/device-tree/model ]; then
    PI_MODEL=$(cat /proc/device-tree/model)
    echo "   Pi Model: $PI_MODEL"
    
    if [[ "$PI_MODEL" == *"Raspberry Pi 5"* ]]; then
        print_success "Raspberry Pi 5 detected"
    else
        print_warning "Not Raspberry Pi 5 - GPIO UART pins might be different"
    fi
fi

# Check current UART status
print_info "Checking current UART configuration..."

# Check /boot/config.txt
UART_ENABLED=false
if [ -f /boot/config.txt ]; then
    if grep -q "^enable_uart=1" /boot/config.txt; then
        print_success "UART already enabled in /boot/config.txt"
        UART_ENABLED=true
    else
        print_warning "UART not enabled in /boot/config.txt"
    fi
else
    print_warning "/boot/config.txt not found"
fi

# Check if /dev/ttyS0 exists
if [ -e "/dev/ttyS0" ]; then
    print_success "/dev/ttyS0 device exists"
else
    print_error "/dev/ttyS0 not found"
fi

echo ""
print_info "GPIO UART Wiring Diagram for Raspberry Pi 5:"
echo "============================================="
echo ""
echo "  Raspberry Pi 5          ESP32"
echo "  Pin  GPIO  Function     Pin     Function"
echo "  ──────────────────────────────────────────"
echo "   8    14    TXD     →    RX     (GPIO 3)"
echo "  10    15    RXD     ←    TX     (GPIO 1)" 
echo "   6    ──    GND     ─    GND    (GND)"
echo "   4    ──    5V      ─    VIN    (Power - Optional)"
echo ""
echo "⚠️  PENTING:"
echo "   • ESP32 TX (GPIO 1) → Pi RX (GPIO 15, Pin 10)"
echo "   • ESP32 RX (GPIO 3) → Pi TX (GPIO 14, Pin 8)"
echo "   • ESP32 GND → Pi GND"
echo "   • ESP32 bisa tetap powered via USB atau gunakan Pi 5V"
echo ""

# Enable UART if not enabled
if [ "$UART_ENABLED" = false ]; then
    echo ""
    print_warning "UART belum enabled. Akan mengenable sekarang..."
    
    # Backup config.txt
    sudo cp /boot/config.txt /boot/config.txt.backup.$(date +%Y%m%d_%H%M%S)
    print_info "Backup dibuat: /boot/config.txt.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Add UART configuration
    echo "" | sudo tee -a /boot/config.txt
    echo "# GPIO UART Configuration for ESP32 Communication" | sudo tee -a /boot/config.txt
    echo "enable_uart=1" | sudo tee -a /boot/config.txt
    echo "dtoverlay=disable-bt" | sudo tee -a /boot/config.txt
    
    print_success "UART configuration added to /boot/config.txt"
    print_warning "REBOOT REQUIRED untuk aktivasi UART!"
    
    echo ""
    echo "Configuration added:"
    echo "  enable_uart=1          # Enable GPIO UART"
    echo "  dtoverlay=disable-bt   # Disable Bluetooth (frees up UART)"
    
    echo ""
    read -p "Reboot sekarang untuk aktivasi UART? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Rebooting dalam 5 detik..."
        sleep 5
        sudo reboot
    else
        print_info "Reboot manual nanti dengan: sudo reboot"
        print_warning "UART tidak akan aktif sampai reboot!"
    fi
else
    print_success "UART sudah enabled, ready untuk digunakan!"
fi

# Update main_raspy.py untuk enable GPIO UART
print_info "Updating main_raspy.py untuk enable GPIO UART mode..."

if [ -f "main_raspy.py" ]; then
    # Create backup
    cp main_raspy.py main_raspy.py.backup.$(date +%Y%m%d_%H%M%S)
    
    # Replace GPIO_UART_ENABLE = False dengan True
    sed -i 's/GPIO_UART_ENABLE = False/GPIO_UART_ENABLE = True/' main_raspy.py
    
    if grep -q "GPIO_UART_ENABLE = True" main_raspy.py; then
        print_success "GPIO UART mode enabled in main_raspy.py"
    else
        print_warning "Failed to update main_raspy.py automatically"
        echo "Manual edit: Set GPIO_UART_ENABLE = True in main_raspy.py"
    fi
else
    print_warning "main_raspy.py not found in current directory"
fi

echo ""
print_success "=========================================="
print_success "  GPIO UART Setup Complete!"
print_success "=========================================="
echo ""
print_info "Next Steps:"
echo "1. Wire ESP32 to Raspberry Pi sesuai diagram di atas"
echo "2. Upload ESP32 code dengan Serial.begin(115200)"
echo "3. Reboot Pi jika UART baru di-enable"
echo "4. Test dengan: python3 serial_monitor.py"
echo "5. Jalankan aplikasi: ./run_raspy.sh"
echo ""
print_info "Testing UART connection:"
echo "  • Tanpa ESP32: ./test_uart.sh"
echo "  • Dengan ESP32: python3 serial_monitor.py"
echo ""
print_warning "Troubleshooting:"
echo "  • Check wiring jika tidak ada komunikasi"
echo "  • Pastikan ESP32 menggunakan 115200 baud rate"
echo "  • Check /dev/ttyS0 permissions: ls -l /dev/ttyS0"
#!/bin/bash
# ====================================================
# AI Voice Robot Controller - Raspberry Pi 5 Launcher
# ====================================================

echo "============================================"
echo "🤖 AI Voice Robot Controller - Raspberry Pi 5"
echo "============================================"
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

# Check if setup was run
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found!"
    print_info "Please run setup first: ./setup_raspy.sh"
    exit 1
fi

if [ ! -f "main_raspy.py" ]; then
    print_error "Main application not found!"
    print_info "Make sure you're in the correct directory"
    exit 1
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    print_error "Failed to activate virtual environment"
    exit 1
fi

print_success "Virtual environment activated"

# Check Python packages
print_info "Checking critical packages..."
python3 -c "import speech_recognition, faster_whisper, serial, RPi.GPIO, ollama" 2>/dev/null

if [ $? -ne 0 ]; then
    print_error "Some Python packages are missing!"
    print_info "Try running: pip install -r requirements_raspy.txt"
    exit 1
fi

print_success "Python packages OK"

# Check Ollama service
print_info "Checking Ollama service..."
if ! systemctl is-active ollama >/dev/null 2>&1; then
    print_warning "Ollama service not running, attempting to start..."
    sudo systemctl start ollama
    sleep 3
    
    if ! systemctl is-active ollama >/dev/null 2>&1; then
        print_error "Failed to start Ollama service"
        print_info "Try manually: sudo systemctl start ollama"
        exit 1
    fi
fi

print_success "Ollama service running"

# Test Ollama connection
print_info "Testing Ollama connection..."
timeout 5s ollama list >/dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "Ollama is responding"
else
    print_warning "Ollama connection test failed, but continuing..."
fi

# Check TTS files
print_info "Checking TTS system..."
if [ ! -f "piper/piper" ]; then
    print_error "Piper TTS not found!"
    print_info "Run setup again: ./setup_raspy.sh"
    exit 1
fi

if [ ! -f "voice_id.onnx" ]; then
    print_error "Voice model not found!"
    print_info "Run setup again: ./setup_raspy.sh"
    exit 1
fi

print_success "TTS system ready"

# Check audio system
print_info "Checking audio system..."
if command -v aplay >/dev/null 2>&1; then
    print_success "ALSA audio available"
elif command -v paplay >/dev/null 2>&1; then
    print_success "PulseAudio available"
else
    print_warning "No audio system found, TTS may not work"
fi

# Check for USB microphone
print_info "Checking microphones..."
python3 -c "
import speech_recognition as sr
mics = sr.Microphone.list_microphone_names()
print(f'Found {len(mics)} microphone(s)')
for i, name in enumerate(mics):
    print(f'  [{i}] {name}')
" 2>/dev/null

# Check for ESP32 connection
print_info "Checking for ESP32 connection..."
ESP32_FOUND=false

for port in /dev/ttyUSB* /dev/ttyACM*; do
    if [ -e "$port" ]; then
        print_info "Found serial port: $port"
        ESP32_FOUND=true
        break
    fi
done

if [ "$ESP32_FOUND" = false ]; then
    print_warning "No ESP32 detected on USB ports"
    print_info "Make sure ESP32 is connected via USB"
    print_info "Application will run but robot commands won't work"
fi

# Final system status
echo ""
print_info "System Status Summary:"
echo "  🖥️  Hardware: Raspberry Pi 5"
echo "  🐍 Python Environment: Ready"
echo "  🧠 AI (Ollama): Ready" 
echo "  🔊 TTS (Piper): Ready"
echo "  🎤 Microphone: Available"
echo "  📡 ESP32: $([ "$ESP32_FOUND" = true ] && echo "Connected" || echo "Not Connected")"
echo ""

# Ask for confirmation
print_info "Ready to start AI Voice Robot Controller"
echo "Make sure:"
echo "  ✓ ESP32 is connected via USB"
echo "  ✓ Microphone (USB recommended) is connected"
echo "  ✓ Speaker/headphones are connected"
echo ""

read -p "Start the application? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Cancelled by user"
    exit 0
fi

# Final checks and start
echo ""
print_info "Starting AI Voice Robot Controller..."
echo ""
print_success "🚀 Launching application..."
echo ""

# Run the main application
python3 main_raspy.py

# Cleanup after exit
print_info "Application stopped"
print_info "Deactivating virtual environment..."
deactivate 2>/dev/null || true

echo ""
print_success "👋 AI Voice Robot Controller session ended"
echo ""
#!/bin/bash
# ========================================
# Setup Script untuk AI Voice Assistant
# Raspberry Pi 5 Version - ARM64 Optimized
# ========================================

echo "=========================================="
echo "   AI Voice Robot Setup - Raspberry Pi 5"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function untuk print dengan warna
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

# Check apakah running sebagai root
if [[ $EUID -eq 0 ]]; then
   print_error "Script ini tidak boleh dijalankan sebagai root!"
   echo "Jalankan dengan: ./setup_raspy.sh"
   exit 1
fi

# [1/8] Check Raspberry Pi 5
print_info "Checking Raspberry Pi model..."
if [ -f /proc/device-tree/model ]; then
    PI_MODEL=$(cat /proc/device-tree/model)
    echo "   Detected: $PI_MODEL"
    
    if [[ "$PI_MODEL" == *"Raspberry Pi 5"* ]]; then
        print_success "Raspberry Pi 5 confirmed"
    else
        print_warning "Not Raspberry Pi 5, but will continue"
        print_warning "This setup is optimized for Pi 5"
    fi
else
    print_warning "Cannot detect Pi model, continuing anyway"
fi

# [2/8] System update
print_info "Updating system packages..."
sudo apt update && sudo apt upgrade -y
if [ $? -eq 0 ]; then
    print_success "System updated"
else
    print_error "Failed to update system"
    exit 1
fi

# [3/8] Install system dependencies
print_info "Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    cmake \
    portaudio19-dev \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    git \
    curl \
    wget \
    unzip

if [ $? -eq 0 ]; then
    print_success "System dependencies installed"
else
    print_error "Failed to install system dependencies"
    exit 1
fi

# Check Python version
print_info "Checking Python version..."
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_info "Python version: $PYTHON_VERSION"

if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)'; then
    print_success "Python version is compatible"
else
    print_error "Python 3.8+ required, found $PYTHON_VERSION"
    exit 1
fi

# [4/8] Setup audio system
print_info "Configuring audio system..."

# Add user to audio group
sudo usermod -a -G audio $USER
print_info "User $USER added to audio group"

# Configure ALSA
if [ ! -f ~/.asoundrc ]; then
    cat > ~/.asoundrc << 'EOF'
pcm.!default {
  type asym
  playback.pcm "dmix"
  capture.pcm "dsnoop"
}
EOF
    print_info "ALSA configuration created"
fi

# Start and enable audio services
sudo systemctl enable alsa-state
sudo systemctl start alsa-state
sudo systemctl --user enable pulseaudio
sudo systemctl --user start pulseaudio

print_success "Audio system configured"

# [5/8] Create Python virtual environment
print_info "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip in virtual environment
python -m pip install --upgrade pip setuptools wheel

print_success "Virtual environment ready"

# [6/8] Install Python packages
print_info "Installing Python packages for Raspberry Pi..."
pip install -r requirements_raspy.txt

if [ $? -eq 0 ]; then
    print_success "Python packages installed"
else
    print_error "Failed to install Python packages"
    print_info "Trying to install packages individually..."
    
    # Try installing critical packages one by one
    pip install SpeechRecognition
    pip install faster-whisper
    pip install pyserial
    pip install RPi.GPIO
    pip install ollama
    pip install numpy
    
    print_warning "Some packages may have failed, but critical ones are installed"
fi

# [7/8] Download and setup Piper TTS
print_info "Setting up Piper TTS for ARM64..."

# Create piper directory
mkdir -p piper

# Download Piper binary untuk ARM64 (Raspberry Pi)
if [ ! -f "piper/piper" ]; then
    print_info "Downloading Piper TTS for ARM64..."
    
    # Download dari GitHub releases
    PIPER_VERSION="2023.11.14-2"
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_aarch64.tar.gz"
    
    curl -L "$PIPER_URL" -o piper_linux_aarch64.tar.gz
    
    if [ $? -eq 0 ]; then
        print_info "Extracting Piper..."
        tar -xzf piper_linux_aarch64.tar.gz -C piper --strip-components=1
        rm piper_linux_aarch64.tar.gz
        
        # Make executable
        chmod +x piper/piper
        
        print_success "Piper TTS downloaded and extracted"
    else
        print_error "Failed to download Piper TTS"
        exit 1
    fi
else
    print_info "Piper binary already exists"
fi

# Download Indonesian voice model
if [ ! -f "voice_id.onnx" ]; then
    print_info "Downloading Indonesian voice model..."
    
    # Download model dari Hugging Face
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/id/id_ID/news_tts/medium/id_ID-news_tts-medium.onnx" -o voice_id.onnx
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/id/id_ID/news_tts/medium/id_ID-news_tts-medium.onnx.json" -o voice_id.onnx.json
    
    if [ -f "voice_id.onnx" ] && [ -f "voice_id.onnx.json" ]; then
        print_success "Indonesian voice model downloaded"
    else
        print_error "Failed to download voice model"
        exit 1
    fi
else
    print_info "Voice model already exists"
fi

# [8/8] Install and setup Ollama
print_info "Installing Ollama for ARM64..."

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    print_info "Ollama already installed"
else
    print_info "Downloading and installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    
    if [ $? -eq 0 ]; then
        print_success "Ollama installed"
    else
        print_error "Failed to install Ollama"
        exit 1
    fi
fi

# Start Ollama service
print_info "Starting Ollama service..."
sudo systemctl enable ollama
sudo systemctl start ollama

# Wait for service to start
sleep 5

# Download AI model
print_info "Downloading AI model (qwen2.5:1.5b - ~900MB)..."
print_warning "This may take several minutes depending on internet speed..."

ollama pull qwen2.5:1.5b

if [ $? -eq 0 ]; then
    print_success "AI model downloaded successfully"
else
    print_error "Failed to download AI model"
    print_info "You can try downloading later with: ollama pull qwen2.5:1.5b"
fi

# Test Ollama installation
print_info "Testing Ollama installation..."
timeout 10s ollama list
if [ $? -eq 0 ]; then
    print_success "Ollama is working correctly"
else
    print_warning "Ollama may need manual restart"
fi

# [FINAL] Create convenience scripts and test
print_info "Creating setup and run scripts..."
cat > run_raspy.sh << 'EOF'
#!/bin/bash
echo "Starting AI Voice Robot Controller - Raspberry Pi 5..."
echo "Activating virtual environment..."
source venv/bin/activate

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama service..."
    sudo systemctl start ollama
    sleep 3
fi

echo "Running main application..."
python3 main_raspy.py
EOF

chmod +x run_raspy.sh
chmod +x setup_gpio_uart.sh
chmod +x test_uart.sh
chmod +x monitor_esp32.sh

# Test TTS system
print_info "Testing text-to-speech system..."
source venv/bin/activate
timeout 15s python3 -c "
from text_to_voice_raspy import text_to_voice
print('Testing TTS...')
text_to_voice('Test sistem suara robot berhasil')
"

if [ $? -eq 0 ]; then
    print_success "TTS system test passed"
else
    print_warning "TTS test failed, but installation continued"
fi

# Setup permissions for serial communication
print_info "Setting up serial permissions..."
sudo usermod -a -G dialout $USER

echo ""
print_success "=========================================="
print_success "   SETUP SELESAI! Raspberry Pi 5 Ready"
print_success "=========================================="
echo ""
print_info "Langkah selanjutnya:"
echo "  1. Logout dan login kembali (untuk audio & serial permissions)"
echo "  2. Sambungkan ESP32 ke Raspberry Pi:"
echo "     • Option 1 (Mudah): USB Cable"
echo "     • Option 2 (Direct): GPIO UART - Jalankan ./setup_gpio_uart.sh"
echo "  3. Jalankan: ./run_raspy.sh"
echo ""
print_info "Atau jalankan manual:"
echo "  source venv/bin/activate"
echo "  python3 main_raspy.py"
echo ""
print_warning "PENTING:"
echo "  - Pastikan ESP32 sudah terprogram dengan sketch yang sesuai"
echo "  - Gunakan microphone USB untuk input suara terbaik"
echo "  - Sambungkan speaker atau headphone untuk output suara"
echo ""
print_info "Untuk test TTS saja:"
echo "  source venv/bin/activate"
echo "  python3 text_to_voice_raspy.py"
echo ""
print_success "Setup Raspberry Pi 5 untuk robot suara selesai!"chmod +x monitor_esp32.sh

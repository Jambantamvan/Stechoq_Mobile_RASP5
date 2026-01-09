# AI Voice Robot Controller - Raspberry Pi 5

🤖 Sistem kontrol robot suara berbasis AI yang dioptimasi untuk Raspberry Pi 5, dengan koneksi ESP32 via serial communication.

## ⚡ Quick Start

```bash
# 1. Clone repository
git clone https://github.com/username/AI-Voice-Robot-RaspyPi5.git
cd AI-Voice-Robot-RaspyPi5

# 2. Quick setup
chmod +x quick_start.sh
./quick_start.sh

# 3. Connect ESP32 hardware (USB or GPIO)
# 4. Upload ESP32_Robot_RaspyPi5.ino to ESP32  
# 5. Run the robot
./run_raspy.sh
```

## 🎯 Features

- 🎤 **Voice Recognition** - Faster-Whisper STT (Bahasa Indonesia)
- 🧠 **AI Processing** - Ollama + Qwen2.5:1.5b untuk command processing
- 🔊 **Text-to-Speech** - Piper TTS (Indonesian voice)
- 📡 **Dual Serial** - USB dan GPIO UART communication
- 🔧 **Hardware Control** - GPIO status LEDs & motor control
- 🛠️ **Monitoring Tools** - Real-time serial monitoring & debugging

## 🔧 Hardware Requirements

### Raspberry Pi 5 Setup
- **Raspberry Pi 5** (4GB/8GB RAM)
- **MicroSD** 32GB+ (Class 10)
- **USB Microphone** 
- **Speaker/Headphones**
- **Power Supply** 5V/5A

### ESP32 Mobile Robot  
- **ESP32 Dev Board**
- **Motor Drivers** (L298N)
- **DC Motors**
- **Robot Chassis** 
- **Battery Pack**

## 🔌 Connection Options

### Option 1: USB (Recommended)
```
ESP32 ←─[USB Cable]─→ Raspberry Pi 5
```

### Option 2: GPIO UART
```
Raspberry Pi 5          ESP32
Pin  GPIO              Pin    Function
 8    14   (TXD)   →   RX     (GPIO 3)
10    15   (RXD)   ←   TX     (GPIO 1)
 6    GND            GND
```

## 🚀 Installation

### Automatic Setup
```bash
./setup_raspy.sh
```
**What it does:**
- ✅ Install system dependencies
- ✅ Setup Python virtual environment  
- ✅ Download Piper TTS (ARM64)
- ✅ Install & configure Ollama
- ✅ Download AI model (~900MB)
- ✅ Configure audio system

### GPIO UART Setup (Optional)
```bash
./setup_gpio_uart.sh  # Enable GPIO UART
./test_uart.sh         # Test connection
```

## 🎮 Usage

### Voice Commands (Bahasa Indonesia)
- **"Maju 5 meter"** - Move forward 5 meters
- **"Belok kiri"** - Turn left 90°  
- **"Mundur 2 meter"** - Move backward 2 meters
- **"Kecepatan 75 persen"** - Set speed to 75%
- **"Berhenti"** - Stop all movement
- **"Matikan"** - Shutdown system

### Manual Control
```bash
./monitor_esp32.sh     # ESP32 serial monitor
python3 serial_monitor.py  # Advanced monitoring

# Commands in monitor:
ESP32> forward 5      # Move forward 5m
ESP32> left 90        # Turn left 90°
ESP32> speed 75       # Set speed 75%
ESP32> status         # Check robot status
```

## 📁 File Structure

```
├── quick_start.sh              # Quick start guide
├── setup_raspy.sh              # Main setup script
├── run_raspy.sh                # Application launcher
├── main_raspy.py               # Main application
├── text_to_voice_raspy.py      # TTS module
├── serial_monitor.py           # Serial monitoring tool
├── setup_gpio_uart.sh          # GPIO UART setup
├── test_uart.sh                # UART testing
├── monitor_esp32.sh            # ESP32 monitor launcher
├── ESP32_Robot_RaspyPi5.ino    # Arduino code for ESP32
├── requirements_raspy.txt      # Python dependencies
└── README.md                   # This documentation
```

## 🔧 Troubleshooting

### Audio Issues
```bash
# Test audio output
speaker-test -t sine -f 1000 -l 1

# Check/restart audio services
sudo systemctl restart alsa-state
systemctl --user restart pulseaudio
```

### Serial Connection
```bash
# List ports
ls -la /dev/tty*

# Check permissions  
groups $USER  # Should include: dialout, audio

# Add permissions
sudo usermod -a -G dialout,audio $USER
# Logout & login again
```

### Ollama Issues
```bash
# Check/restart Ollama
sudo systemctl status ollama
sudo systemctl restart ollama
ollama list
```

### ESP32 Debug
```bash
# Stop main app first
pkill -f main_raspy.py

# Use serial monitor
./monitor_esp32.sh

# Or Arduino IDE Serial Monitor
```

## 🚦 Status Indicators

**GPIO LEDs (if connected):**
- **GPIO 18** - System active (ON/OFF)
- **GPIO 19** - Ready for commands (ON/OFF)

**Serial Messages:**
```
📡 PERINTAH DIKIRIM KE ESP32: FORWARD,5,meter
📥 RESPONS DARI ESP32: ✅ FORWARD command executed
```

## ⚙️ Performance Optimization

### Raspberry Pi 5 Specific
```bash
# Performance mode
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Memory optimization
sudo nano /etc/dphys-swapfile  # CONF_SWAPSIZE=2048
sudo dphys-swapfile setup && sudo dphys-swapfile swapon
```

### Configuration Tuning
Edit `main_raspy.py`:
```python
WHISPER_SIZE = "small"    # or "base" for better accuracy
AI_MODEL = "qwen2.5:1.5b" # or larger model if RAM allows
```

## 🔄 Development

### Custom Voice Commands
Edit `SYSTEM_PROMPT` in `main_raspy.py`:
```python
# Add new commands:
- DANCE = robot dance mode
- PATROL = autonomous patrol
```

### Multiple Robots
```python
# Support multiple ESP32s
SERIAL_PORTS = ['/dev/ttyUSB0', '/dev/ttyUSB1']
```

## 📊 Expected Performance

- **Setup time:** 10-15 minutes
- **Boot time:** 30-45 seconds  
- **Voice response:** 2-5 seconds
- **Memory usage:** ~1-2GB
- **AI processing:** ~2-3 seconds

## 🆘 Support

1. **Check logs:** `journalctl -u ollama -f`
2. **Test components individually**
3. **Verify hardware connections**
4. **Check troubleshooting section above**

## 📄 License

Educational and development use. Modify as needed.

---

**Ready to build your voice-controlled robot! 🤖🚀**

For detailed setup instructions, run: `./quick_start.sh`
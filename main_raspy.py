#!/usr/bin/env python3
"""
AI Voice Robot Controller - Raspberry Pi 5 Version
Optimized for Raspberry Pi 5 with ARM64 architecture
Serial communication with ESP32 mobile robot
"""

import os
import subprocess
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# Suppress ALSA/JACK error messages
from ctypes import *
try:
    ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
    def py_error_handler(filename, line, function, err, fmt):
        pass  # Ignore ALSA errors
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound = cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass  # If libasound not available, continue anyway

import speech_recognition as sr
from faster_whisper import WhisperModel
import ollama
import time
import serial
import serial.tools.list_ports
import re
import json
import platform
import wave
import struct
import RPi.GPIO as GPIO
import pyaudio
import numpy as np
from text_to_voice_raspy import text_to_voice

# --- KONFIGURASI RASPBERRY PI 5 ---
WHISPER_SIZE = "small"  # Optimal untuk Raspberry Pi 5 (balance antara speed & akurasi)
AI_MODEL = "qwen2.5:1.5b"  # Model yang cocok untuk resource Pi 5

# Serial untuk ESP32 - Raspberry Pi 5 detection
SERIAL_PORT = None  # Auto-detect: /dev/ttyUSB0, /dev/ttyACM0, /dev/ttyS0 atau manual set
SERIAL_BAUD = 115200
ser = None

# GPIO UART Configuration (untuk koneksi langsung)
GPIO_UART_PORT = '/dev/ttyS0'  # GPIO UART port (Primary UART)
GPIO_UART_ENABLE = False  # Set True untuk menggunakan GPIO UART instead of USB
UART_TX_PIN = 14  # GPIO 14 (TXD - Pin 8)
UART_RX_PIN = 15  # GPIO 15 (RXD - Pin 10)

# GPIO untuk status LED (optional)
LED_STATUS_PIN = 18  # GPIO 18 untuk status indicator
LED_READY_PIN = 23   # GPIO 23 untuk ready indicator (diubah dari 19 karena konflik I2S)

# ===== INMP441 I2S MICROPHONE CONFIGURATION =====
USE_I2S_MIC = True  # Set True untuk INMP441, False untuk USB microphone

# INMP441 Wiring ke Raspberry Pi 5:
# VDD  -> 3.3V (Pin 1)
# GND  -> GND (Pin 6)
# SD   -> GPIO 21 (Pin 40) - I2S Data
# WS   -> GPIO 19 (Pin 35) - I2S Word Select (LRCLK)
# SCK  -> GPIO 18 (Pin 12) - I2S Clock (BCLK)
# L/R  -> GND (untuk Left channel) atau 3.3V (untuk Right channel)

# Native sample rate untuk I2S soundcard (cek dengan: arecord -l)
I2S_NATIVE_RATE = 48000       # Native rate untuk GoogleVoiceHAT/I2S soundcard
I2S_SAMPLE_RATE = 16000       # Target sample rate untuk Whisper (akan di-resample)
I2S_CHANNELS = 2              # Stereo (required by GoogleVoiceHAT soundcard)  
I2S_CHUNK = 4096              # Buffer size (larger for stability)
I2S_FORMAT = pyaudio.paInt32  # INMP441 output 24-bit dalam 32-bit container
I2S_RECORD_SECONDS = 5        # Default recording duration

# Raspberry Pi 5 detection
IS_RASPBERRY_PI = True
PI_MODEL = "Unknown"

def detect_pi_model():
    """Deteksi model Raspberry Pi"""
    global PI_MODEL
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip()
            PI_MODEL = model
            print(f"🔍 Raspberry Pi terdeteksi: {model}")
            return "Pi 5" in model or "5" in model
    except:
        PI_MODEL = "Generic Linux"
        return False

# System Prompt untuk kontrol robot
SYSTEM_PROMPT = """
Kamu adalah asisten AI yang mengontrol robot mobil via Raspberry Pi 5. 
Ketika user memberikan perintah gerakan, kamu HARUS membalas dengan format JSON seperti ini:
{"command": "PERINTAH", "value": ANGKA, "unit": "SATUAN"}

Daftar PERINTAH yang tersedia:
- FORWARD = maju
- BACKWARD = mundur  
- LEFT = belok kiri
- RIGHT = belok kanan
- STOP = berhenti
- SPEED = atur kecepatan (value 0-100)
- STATUS = cek status robot

Contoh:
- User: "maju 5 meter" -> {"command": "FORWARD", "value": 5, "unit": "meter"}
- User: "mundur 2 meter" -> {"command": "BACKWARD", "value": 2, "unit": "meter"}
- User: "belok kiri" -> {"command": "LEFT", "value": 90, "unit": "degree"}
- User: "putar kanan" -> {"command": "RIGHT", "value": 90, "unit": "degree"}
- User: "berhenti" -> {"command": "STOP", "value": 0, "unit": "none"}
- User: "kecepatan 50 persen" -> {"command": "SPEED", "value": 50, "unit": "percent"}
- User: "maju terus" -> {"command": "FORWARD", "value": -1, "unit": "continuous"}
- User: "cek status" -> {"command": "STATUS", "value": 0, "unit": "none"}

Jika user bertanya hal lain (bukan perintah gerakan), jawab seperti biasa tanpa format JSON.
Jawab dalam Bahasa Indonesia yang singkat dan jelas.
Kamu berjalan di Raspberry Pi 5 yang terhubung ke ESP32 via serial communication (USB atau GPIO UART).
"""

def init_gpio():
    """Inisialisasi GPIO untuk status LED"""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LED_STATUS_PIN, GPIO.OUT)
        GPIO.setup(LED_READY_PIN, GPIO.OUT)
        GPIO.output(LED_STATUS_PIN, GPIO.LOW)
        GPIO.output(LED_READY_PIN, GPIO.LOW)
        print("✅ GPIO initialized for status LEDs")
        return True
    except Exception as e:
        print(f"⚠️ GPIO init failed: {e}")
        return False

def set_status_led(status=False, ready=False):
    """Set status LED"""
    try:
        GPIO.output(LED_STATUS_PIN, GPIO.HIGH if status else GPIO.LOW)
        GPIO.output(LED_READY_PIN, GPIO.HIGH if ready else GPIO.LOW)
    except:
        pass

def check_gpio_uart_available():
    """Check apakah GPIO UART tersedia dan enabled"""
    import os
    
    # Check apakah /dev/ttyS0 ada
    if not os.path.exists(GPIO_UART_PORT):
        print(f"⚠️ GPIO UART port {GPIO_UART_PORT} tidak ditemukan")
        return False
    
    # Check apakah UART sudah di-enable di config
    try:
        with open('/boot/config.txt', 'r') as f:
            config = f.read()
            if 'enable_uart=1' in config:
                print(f"✅ GPIO UART enabled di /boot/config.txt")
                return True
            else:
                print(f"⚠️ GPIO UART belum enabled. Tambahkan 'enable_uart=1' ke /boot/config.txt")
                return False
    except:
        print(f"⚠️ Tidak dapat mengecek /boot/config.txt")
        return False

def find_esp32_port_rpi():
    """Auto-detect ESP32 pada Raspberry Pi 5 (USB dan GPIO UART)"""
    
    # Jika GPIO UART mode enabled, cek dulu
    if GPIO_UART_ENABLE:
        if check_gpio_uart_available():
            print(f"🔌 Using GPIO UART: {GPIO_UART_PORT}")
            print(f"📡 ESP32 TX → GPIO {UART_RX_PIN} (Pi RX - Pin 10)")
            print(f"📡 ESP32 RX → GPIO {UART_TX_PIN} (Pi TX - Pin 8)")
            print(f"📡 ESP32 GND → Pi GND")
            return GPIO_UART_PORT
        else:
            print(f"❌ GPIO UART not available, falling back to USB detection")
    
    ports = serial.tools.list_ports.comports()
    
    # Priority ports untuk Raspberry Pi 5 (termasuk GPIO UART)
    priority_ports = [GPIO_UART_PORT, '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
    
    # Cek priority ports dulu
    for port_name in priority_ports:
        for port in ports:
            if port.device == port_name:
                print(f"🔍 Found ESP32 at priority port: {port.device}")
                return port.device
    
    # Kalau tidak ada di priority, cari berdasarkan description
    for port in ports:
        desc = port.description.lower() if port.description else ''
        mfr = port.manufacturer.lower() if port.manufacturer else ''
        
        # ESP32 keywords untuk Linux
        if any(x in desc for x in ['ch340', 'cp210', 'usb serial', 'uart', 'silicon labs', 'usb2.0-serial']):
            print(f"🔍 Found ESP32: {port.device} - {port.description}")
            return port.device
        if any(x in mfr for x in ['qinheng', 'silicon', 'ftdi', '1a86']):
            print(f"🔍 Found ESP32: {port.device} - {port.description}")
            return port.device
        
        # Generic USB serial ports
        if 'ttyUSB' in port.device or 'ttyACM' in port.device:
            print(f"🔍 Found USB Serial: {port.device} - {port.description}")
            return port.device
    
    # Tampilkan semua ports yang tersedia
    print("⚠️ ESP32 tidak terdeteksi otomatis. Port yang tersedia:")
    for port in ports:
        print(f"   {port.device}: {port.description}")
    
    # Gunakan port pertama jika ada
    if ports:
        print(f"🔧 Menggunakan port pertama: {ports[0].device}")
        return ports[0].device
    
    return None

def init_serial():
    """Inisialisasi koneksi serial ke ESP32"""
    global ser, SERIAL_PORT
    
    set_status_led(True, False)  # Status: connecting
    
    # Auto-detect port jika belum di-set
    if SERIAL_PORT is None:
        SERIAL_PORT = find_esp32_port_rpi()
    
    if SERIAL_PORT is None:
        print("❌ Tidak ada port serial yang ditemukan")
        set_status_led(False, False)
        return False
    
    try:
        # Konfigurasi serial untuk Raspberry Pi 5
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=SERIAL_BAUD,
            timeout=2,
            write_timeout=2,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        time.sleep(3)  # Tunggu ESP32 ready lebih lama di Pi
        
        # Flush buffer dan baca pesan startup dari ESP32
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print(f"✅ Serial connected: {SERIAL_PORT}")
        print(f"📊 Baud rate: {SERIAL_BAUD}")
        
        # Info koneksi berdasarkan jenis port
        if SERIAL_PORT == GPIO_UART_PORT:
            print(f"🔌 Connection: GPIO UART (Direct wiring)")
            print(f"📍 ESP32 TX → GPIO {UART_RX_PIN} (Pi RX - Pin 10)")
            print(f"📍 ESP32 RX → GPIO {UART_TX_PIN} (Pi TX - Pin 8)")
            print(f"📍 ESP32 GND → Pi GND (Pin 6/9/14)")
        else:
            print(f"🔌 Connection: USB Serial")
            
        print(f"ℹ️  Untuk monitoring serial: python3 serial_monitor.py")
        print(f"⚠️  Note: Stop aplikasi ini dulu sebelum buka Arduino IDE Serial Monitor")
        
        # Test koneksi dengan ping
        ser.write(b"STATUS,0,none\n")
        time.sleep(0.5)
        
        # Baca pesan startup dari ESP32
        startup_messages = []
        timeout_start = time.time()
        while (time.time() - timeout_start) < 3.0:
            if ser.in_waiting:
                try:
                    startup_msg = ser.readline().decode('utf-8', errors='ignore').strip()
                    if startup_msg:
                        startup_messages.append(startup_msg)
                        print(f"   ESP32: {startup_msg}")
                        timeout_start = time.time()  # Reset timeout
                except:
                    pass
            else:
                time.sleep(0.1)
        
        set_status_led(True, True)  # Status: connected and ready
        return True
        
    except Exception as e:
        print(f"⚠️ Serial tidak tersedia: {e}")
        print("   Robot akan berjalan tanpa kontrol hardware")
        set_status_led(False, False)
        return False

def send_to_robot(command_json):
    """Kirim perintah ke ESP32 via serial - Raspberry Pi optimized"""
    global ser
    if ser and ser.is_open:
        try:
            cmd_data = json.loads(command_json)
            
            command = cmd_data.get("command", "STOP")
            value = cmd_data.get("value", 0)
            unit = cmd_data.get("unit", "none")
            
            # Format perintah untuk ESP32: CMD,VALUE,UNIT
            serial_cmd = f"{command},{value},{unit}\n"
            
            # Flash status LED saat kirim command
            set_status_led(False, True)
            time.sleep(0.1)
            set_status_led(True, True)
            
            ser.write(serial_cmd.encode('utf-8'))
            ser.flush()  # Ensure data is sent
            
            print(f"\n{'='*50}")
            print(f"📡 PERINTAH DIKIRIM KE ESP32: {serial_cmd.strip()}")
            print(f"🔌 Port: {SERIAL_PORT}")
            print(f"⏰ Time: {time.strftime('%H:%M:%S')}")
            print(f"{'='*50}")
            
            # Baca response dari ESP32 dengan timeout lebih robust
            time.sleep(0.3)
            print("📥 RESPONS DARI ESP32:")
            print("-" * 50)
            
            response_count = 0
            timeout_start = time.time()
            max_timeout = 3.0  # 3 detik untuk response
            
            while (time.time() - timeout_start) < max_timeout:
                if ser.in_waiting:
                    try:
                        response = ser.readline().decode('utf-8', errors='ignore').strip()
                        if response:
                            print(f"   🤖 ESP32: {response}")
                            response_count += 1
                            timeout_start = time.time()  # Reset timeout
                            
                            # Flash LED untuk setiap response
                            set_status_led(False, False)
                            time.sleep(0.05)
                            set_status_led(True, True)
                    except Exception as decode_error:
                        print(f"   ⚠️ Decode error: {decode_error}")
                else:
                    time.sleep(0.05)
                    # Jika sudah dapat response, tunggu sebentar lagi
                    if response_count > 0 and (time.time() - timeout_start) > 1.0:
                        break
            
            if response_count == 0:
                print("   ⚠️ Tidak ada respons dari ESP32")
            print("-" * 50)
            
            return True
            
        except json.JSONDecodeError:
            print("⚠️ Response bukan format JSON (bukan perintah robot)")
            return False
        except Exception as e:
            print(f"❌ Serial error: {e}")
            set_status_led(False, False)
            # Try to reconnect
            try:
                if ser:
                    ser.close()
                time.sleep(1)
                init_serial()
            except:
                pass
            return False
    else:
        print("⚠️ Serial tidak terhubung - perintah tidak dikirim")
        set_status_led(False, False)
        return False

def extract_robot_command(ai_response):
    """Ekstrak JSON command dari response AI"""
    json_pattern = r'\{[^}]+\}'
    match = re.search(json_pattern, ai_response)
    if match:
        return match.group()
    return None

def speak(text):
    """TTS menggunakan Piper untuk Raspberry Pi"""
    text_to_voice(text)

def chat_with_ai(prompt):
    """Kirim ke Ollama - optimized untuk Raspberry Pi 5"""
    try:
        # Flash status LED saat processing AI
        set_status_led(True, False)
        
        response = ollama.chat(
            model=AI_MODEL, 
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt},
            ],
            options={
                'temperature': 0.7,
                'num_predict': 150,  # Limit response length for Pi 5
                'num_ctx': 1024     # Reduce context for better performance
            }
        )
        
        set_status_led(True, True)  # Ready again
        return response['message']['content']
        
    except Exception as e:
        print(f"Error AI: {e}")
        set_status_led(False, False)
        return "Maaf, koneksi AI bermasalah. Silakan coba lagi."

def find_usb_microphone():
    """Auto-detect USB microphone untuk Raspberry Pi"""
    try:
        mics = sr.Microphone.list_microphone_names()
        print(f"🎤 Microphones detected: {len(mics)}")
        
        for i, name in enumerate(mics):
            name_lower = name.lower()
            print(f"   [{i}] {name}")
            
            # Priority untuk USB mics yang umum di Raspberry Pi
            if any(keyword in name_lower for keyword in 
                   ['usb', 'webcam', 'logitech', 'c920', 'c270', 'blue yeti', 'samson']):
                print(f"🎤 USB Microphone selected: [{i}] {name}")
                return i
        
        # Fallback ke microphone index 1 jika ada (biasanya USB mic)
        if len(mics) > 1:
            print(f"🎤 Using microphone index 1: {mics[1]}")
            return 1
            
        # Ultimate fallback ke default
        print("🎤 Using default microphone (index 0)")
        return 0 if mics else None
        
    except Exception as e:
        print(f"⚠️ Microphone detection error: {e}")
        return None

def find_i2s_microphone():
    """Auto-detect INMP441 I2S microphone with fallback to PulseAudio"""
    try:
        p = pyaudio.PyAudio()
        i2s_device_index = None
        pulse_device_index = None
        default_device_index = None
        
        print("🎤 Mencari INMP441 I2S Microphone...")
        
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            dev_name = dev_info.get('name', '').lower()
            max_input_channels = dev_info.get('maxInputChannels', 0)
            
            print(f"   [{i}] {dev_info['name']} (Input Ch: {max_input_channels})")
            
            if max_input_channels > 0:
                # Priority 1: I2S device
                if any(keyword in dev_name for keyword in ['i2s', 'snd_rpi', 'bcm2835', 'simple-card', 'googlevoicehat']):
                    i2s_device_index = i
                    print(f"🎤 I2S Microphone found: [{i}] {dev_info['name']}")
                
                # Priority 2: PulseAudio (supports resampling)
                elif 'pulse' in dev_name and pulse_device_index is None:
                    pulse_device_index = i
                
                # Priority 3: Default device
                elif 'default' in dev_name and default_device_index is None:
                    default_device_index = i
        
        p.terminate()
        
        # Return dengan priority: I2S > PulseAudio > Default
        if i2s_device_index is not None:
            return i2s_device_index
        elif pulse_device_index is not None:
            print(f"💡 Fallback ke PulseAudio: [{pulse_device_index}]")
            return pulse_device_index
        elif default_device_index is not None:
            print(f"💡 Fallback ke Default device: [{default_device_index}]")
            return default_device_index
        
        return None
        
    except Exception as e:
        print(f"⚠️ I2S Microphone detection error: {e}")
        return None

def check_i2s_setup():
    """Check apakah I2S sudah dikonfigurasi dengan benar di Raspberry Pi"""
    try:
        # Check /boot/config.txt untuk I2S overlay
        config_paths = ['/boot/config.txt', '/boot/firmware/config.txt']
        i2s_enabled = False
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = f.read()
                    if 'dtparam=i2s=on' in config or 'dtoverlay=i2s-mems-mic' in config:
                        i2s_enabled = True
                        print(f"✅ I2S enabled di {config_path}")
                        break
        
        if not i2s_enabled:
            print("⚠️ I2S mungkin belum diaktifkan!")
            print("   Tambahkan ke /boot/config.txt:")
            print("   dtparam=i2s=on")
            print("   dtoverlay=googlevoicehat-soundcard")
            print("   (atau overlay I2S lainnya)")
            print("   Lalu reboot Raspberry Pi")
        
        return i2s_enabled
    except Exception as e:
        print(f"⚠️ Tidak dapat mengecek konfigurasi I2S: {e}")
        return False

def record_i2s_audio(duration=None):
    """
    Record audio dari INMP441 I2S microphone
    Uses native 48000Hz rate and resamples to 16000Hz for Whisper
    
    Args:
        duration: Durasi rekaman dalam detik. Jika None, gunakan default.
    
    Returns:
        Path ke file WAV temporary
    """
    if duration is None:
        duration = I2S_RECORD_SECONDS
    
    p = pyaudio.PyAudio()
    i2s_device = find_i2s_microphone()
    
    if i2s_device is None:
        print("❌ I2S Microphone tidak ditemukan!")
        print("💡 Mencoba menggunakan PulseAudio (device 'pulse' atau 'default')...")
        # Try using pulse or default device instead
        for fallback_idx in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(fallback_idx)
            if dev_info['maxInputChannels'] > 0 and 'pulse' in dev_info['name'].lower():
                i2s_device = fallback_idx
                print(f"✅ Fallback ke PulseAudio: [{i2s_device}] {dev_info['name']}")
                break
        
        if i2s_device is None:
            p.terminate()
            return None
    
    try:
        # Gunakan native sample rate dari device (48000 Hz untuk GoogleVoiceHAT)
        dev_info = p.get_device_info_by_index(i2s_device)
        native_rate = int(dev_info.get('defaultSampleRate', I2S_NATIVE_RATE))
        native_channels = min(int(dev_info.get('maxInputChannels', 2)), 2)
        
        print(f"📊 Using native rate: {native_rate}Hz, channels: {native_channels}")
        
        # Buka stream audio dengan native rate
        stream = p.open(
            format=I2S_FORMAT,
            channels=native_channels,
            rate=native_rate,
            input=True,
            input_device_index=i2s_device,
            frames_per_buffer=I2S_CHUNK
        )
        
        print(f"🎤 Recording dari I2S/Mic... ({duration} detik)")
        frames = []
        
        # Hitung jumlah chunk yang dibutuhkan berdasarkan native rate
        num_chunks = int(native_rate / I2S_CHUNK * duration)
        
        for i in range(num_chunks):
            try:
                data = stream.read(I2S_CHUNK, exception_on_overflow=False)
                frames.append(data)
            except Exception as e:
                print(f"⚠️ Read error: {e}")
                continue
        
        print("✅ Recording selesai")
        
        stream.stop_stream()
        stream.close()
        
    except Exception as e:
        print(f"❌ I2S Stream error: {e}")
        p.terminate()
        return None
    
    p.terminate()
    
    # Convert 32-bit stereo to 16-bit mono WAV dan resample untuk Whisper
    temp_file = "/tmp/temp_i2s_input.wav"
    
    try:
        # Parse raw 32-bit data dan convert ke 16-bit
        raw_data = b''.join(frames)
        
        # INMP441 mengirim data 24-bit dalam container 32-bit (left-justified)
        # Untuk stereo: L0 L1 L2 L3 R0 R1 R2 R3 (8 bytes per sample pair)
        samples = []
        bytes_per_sample = 4  # 32-bit = 4 bytes
        bytes_per_frame = bytes_per_sample * native_channels
        
        for i in range(0, len(raw_data), bytes_per_frame):
            if i + bytes_per_sample <= len(raw_data):
                # Ambil channel kiri saja (atau rata-rata jika stereo)
                val = struct.unpack('<i', raw_data[i:i+bytes_per_sample])[0]
                # Shift right 16 bit untuk mendapatkan 16-bit MSB
                val_16 = val >> 16
                # Clamp ke range 16-bit
                val_16 = max(-32768, min(32767, val_16))
                samples.append(val_16)
        
        # Resample dari native_rate ke I2S_SAMPLE_RATE (16000 Hz) untuk Whisper
        if native_rate != I2S_SAMPLE_RATE:
            print(f"🔄 Resampling {native_rate}Hz -> {I2S_SAMPLE_RATE}Hz...")
            samples_np = np.array(samples, dtype=np.float32)
            
            # Simple linear interpolation resampling
            resample_ratio = I2S_SAMPLE_RATE / native_rate
            new_length = int(len(samples_np) * resample_ratio)
            
            # Use numpy interpolation
            x_old = np.linspace(0, 1, len(samples_np))
            x_new = np.linspace(0, 1, new_length)
            samples_resampled = np.interp(x_new, x_old, samples_np)
            
            # Convert back to int16
            samples = [int(max(-32768, min(32767, s))) for s in samples_resampled]
            print(f"✅ Resampled: {len(samples_np)} -> {len(samples)} samples")
        
        # Buat WAV file 16-bit mono
        with wave.open(temp_file, 'wb') as wf:
            wf.setnchannels(1)  # Mono untuk Whisper
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(I2S_SAMPLE_RATE)  # 16000 Hz untuk Whisper
            
            # Pack samples sebagai 16-bit signed integers
            packed_data = struct.pack('<' + 'h' * len(samples), *samples)
            wf.writeframes(packed_data)
        
        print(f"✅ Audio disimpan: {temp_file} ({I2S_SAMPLE_RATE}Hz mono)")
        return temp_file
        
    except Exception as e:
        print(f"❌ Error menyimpan audio: {e}")
        import traceback
        traceback.print_exc()
        return None

def listen_and_transcribe_i2s():
    """
    Record audio dari INMP441 I2S mic dan transcribe dengan Whisper
    Optimized untuk Raspberry Pi 5
    """
    global stt_model
    
    # Flash LED saat listening
    set_status_led(True, False)
    
    print("\n🎤 Silakan Bicara... (INMP441 I2S Microphone)")
    
    # Record audio dari I2S mic
    temp_file = record_i2s_audio(duration=I2S_RECORD_SECONDS)
    
    if temp_file is None:
        print("❌ Gagal merekam audio dari I2S")
        set_status_led(False, False)
        return None
    
    print("⏳ Memproses audio dengan Whisper...")
    set_status_led(False, True)  # Processing
    
    try:
        # Transcribe dengan Whisper
        segments, info = stt_model.transcribe(
            temp_file,
            beam_size=1,      # Faster untuk Pi 5
            best_of=1,        # Faster untuk Pi 5
            language="id",    # Bahasa Indonesia
            vad_filter=True,  # Voice Activity Detection
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200
            )
        )
        
        # Gabungkan semua segment
        text_result = " ".join([segment.text for segment in segments]).strip()
        
        # Cleanup temp file
        try:
            os.remove(temp_file)
        except:
            pass
        
        set_status_led(True, True)  # Ready
        
        if not text_result:
            print("⚠️ Tidak ada suara terdeteksi")
            return None
        
        return text_result
        
    except Exception as e:
        print(f"❌ Whisper transcription error: {e}")
        set_status_led(False, False)
        
        # Cleanup temp file
        try:
            os.remove(temp_file)
        except:
            pass
        
        return None

# Initialize microphone once at startup
print("🎤 Detecting microphones...")
if USE_I2S_MIC:
    print("🎤 Mode: INMP441 I2S Microphone")
    check_i2s_setup()
    I2S_MIC_INDEX = find_i2s_microphone()
    MIC_INDEX = None  # Tidak digunakan untuk I2S
else:
    print("🎤 Mode: USB Microphone")
    MIC_INDEX = find_usb_microphone()
    I2S_MIC_INDEX = None

def listen_and_transcribe():
    """Record audio dan transcribe dengan Whisper - Raspberry Pi optimized"""
    global MIC_INDEX
    
    # Flash LED saat listening
    set_status_led(True, False)
    
    mic_kwargs = {}
    if MIC_INDEX is not None:
        mic_kwargs['device_index'] = MIC_INDEX
    
    try:
        with sr.Microphone(**mic_kwargs) as source:
            print("\n🎤 Silakan Bicara... (Mendengarkan)")
            
            # Adjust for ambient noise dengan timeout lebih pendek di Pi
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Set energy threshold yang lebih rendah untuk Pi
            recognizer.energy_threshold = 200
            recognizer.pause_threshold = 1.2
            recognizer.dynamic_energy_threshold = True
            
            # Record audio
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=8)
            
            print("⏳ Memproses audio...")
            set_status_led(False, True)  # Processing
            
            # Save temporary file
            temp_file = "/tmp/temp_input.wav"
            with open(temp_file, "wb") as f:
                f.write(audio.get_wav_data())
            
            # Transcribe dengan Whisper
            segments, _ = stt_model.transcribe(
                temp_file, 
                language="id",
                beam_size=1,  # Faster untuk Pi 5
                best_of=1     # Faster untuk Pi 5
            )
            
            text_result = " ".join([s.text for s in segments]).strip()
            
            # Cleanup temp file
            try:
                os.remove(temp_file)
            except:
                pass
            
            set_status_led(True, True)  # Ready
            
            if not text_result:
                print("⚠️ Tidak dapat mengenali suara, coba lagi...")
                return None
            
            return text_result
        
    except sr.WaitTimeoutError:
        print("⏱️ Timeout - tidak ada suara terdeteksi")
        set_status_led(True, True)
        return None
    except Exception as e:
        print(f"❌ Error Microphone: {e}")
        set_status_led(False, False)
        return None

def cleanup_gpio():
    """Cleanup GPIO saat exit"""
    try:
        GPIO.cleanup()
        print("✅ GPIO cleaned up")
    except:
        pass

def main():
    """Main function - Raspberry Pi 5 Voice Robot Controller"""
    print(f"\n{'='*60}")
    print("🤖 AI VOICE ROBOT CONTROLLER - RASPBERRY PI 5")
    print(f"{'='*60}")
    print(f"🔍 Hardware: {PI_MODEL}")
    print(f"🎤 Microphone: {'INMP441 I2S' if USE_I2S_MIC else 'USB Microphone'}")
    print("🎯 Target: ESP32 Mobile Robot via Serial")
    print("📡 Commands: maju, mundur, kiri, kanan, berhenti")
    print("📝 Examples: 'maju 5 meter', 'belok kiri', 'berhenti'")
    print(f"{'='*60}\n")
    
    # Initialize hardware
    gpio_ok = init_gpio()
    if gpio_ok:
        # Startup LED sequence
        for _ in range(3):
            set_status_led(True, False)
            time.sleep(0.2)
            set_status_led(False, True)
            time.sleep(0.2)
        set_status_led(False, False)
    
    # Initialize serial
    serial_ok = init_serial()
    
    if serial_ok:
        speak("Sistem robot Raspberry Pi siap. ESP32 terhubung. Silakan berikan perintah.")
    else:
        speak("Sistem robot siap, namun ESP32 belum terhubung. Silakan periksa koneksi serial.")
    
    try:
        while True:
            try:
                set_status_led(True, True)  # Ready state
                
                # Pilih metode recording berdasarkan konfigurasi microphone
                if USE_I2S_MIC:
                    user_text = listen_and_transcribe_i2s()
                else:
                    user_text = listen_and_transcribe()
                
                if user_text:
                    print(f"🗣️ Anda berkata: {user_text}")
                    
                    # Check shutdown commands
                    shutdown_keywords = ["matikan", "shutdown", "tutup sistem", "keluar"]
                    if any(keyword in user_text.lower() for keyword in shutdown_keywords):
                        send_to_robot('{"command": "STOP", "value": 0, "unit": "none"}')
                        speak("Baik, mematikan sistem robot Raspberry Pi.")
                        break
                    
                    # Process with AI
                    print("🤖 AI memproses perintah...")
                    ai_reply = chat_with_ai(user_text)
                    print(f"🤖 AI Response: {ai_reply}")
                    
                    # Check for robot command
                    robot_cmd = extract_robot_command(ai_reply)
                    if robot_cmd:
                        print(f"🎮 Robot command: {robot_cmd}")
                        cmd_success = send_to_robot(robot_cmd)
                        
                        if cmd_success:
                            try:
                                cmd_data = json.loads(robot_cmd)
                                cmd = cmd_data.get("command", "")
                                val = cmd_data.get("value", 0)
                                unit = cmd_data.get("unit", "")
                                
                                # Generate appropriate speech response
                                if cmd == "FORWARD":
                                    if val == -1:
                                        speak("Baik, robot maju terus")
                                    else:
                                        speak(f"Baik, robot maju {val} {unit}")
                                elif cmd == "BACKWARD":
                                    speak(f"Baik, robot mundur {val} {unit}")
                                elif cmd == "LEFT":
                                    speak("Baik, robot belok kiri")
                                elif cmd == "RIGHT":
                                    speak("Baik, robot belok kanan")
                                elif cmd == "STOP":
                                    speak("Baik, robot berhenti")
                                elif cmd == "SPEED":
                                    speak(f"Baik, kecepatan diatur {val} persen")
                                elif cmd == "STATUS":
                                    speak("Status robot sudah dikirim ke ESP32")
                                else:
                                    speak("Perintah berhasil dikirim ke robot")
                            except:
                                speak("Perintah telah dikirim ke ESP32")
                        else:
                            speak("Maaf, gagal mengirim perintah ke robot. Periksa koneksi ESP32.")
                    else:
                        # Regular conversation, not robot command
                        speak(ai_reply)
                
            except KeyboardInterrupt:
                print("\n\n👋 Menerima sinyal shutdown...")
                break
                
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        speak("Terjadi error sistem. Mematikan robot.")
    
    finally:
        # Cleanup
        print("\n🔧 Membersihkan sistem...")
        set_status_led(False, False)
        
        if ser and ser.is_open:
            try:
                print("📡 Mengirim perintah STOP ke ESP32...")
                send_to_robot('{"command": "STOP", "value": 0, "unit": "none"}')
                time.sleep(0.5)
                ser.close()
                print("✅ Serial connection closed")
            except:
                pass
        
        cleanup_gpio()
        print("👋 Sistem robot Raspberry Pi telah dimatikan")

if __name__ == "__main__":
    # Detect Pi model at startup
    is_pi5 = detect_pi_model()
    if not is_pi5:
        print("⚠️ Warning: Tidak terdeteksi sebagai Raspberry Pi 5")
        print("   Code ini dioptimasi untuk Pi 5, tapi akan tetap berjalan")
    
    # Load Whisper model
    print("🧠 Memuat Whisper model...")
    stt_model = WhisperModel(
        WHISPER_SIZE, 
        device="cpu", 
        compute_type="int8",  # Optimal untuk ARM64
        num_workers=2         # Limit workers untuk Pi 5
    )
    
    # Initialize speech recognizer
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.2
    recognizer.energy_threshold = 200
    recognizer.dynamic_energy_threshold = True
    
    print("✅ Sistem siap!")
    
    # Run main program
    main()
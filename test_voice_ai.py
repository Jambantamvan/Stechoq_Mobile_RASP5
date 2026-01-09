#!/usr/bin/env python3
"""
Test Voice to AI - Simple Terminal Test
========================================
Test INMP441 I2S Microphone -> Speech-to-Text -> AI Response

Wiring INMP441 ke Raspberry Pi 5:
---------------------------------
INMP441 Pin    | Raspberry Pi 5 Pin
---------------|-------------------
VDD            | Pin 1  (3.3V)
GND            | Pin 6  (Ground)
SD (Data)      | Pin 38 (GPIO 20)
WS (LRCLK)     | Pin 35 (GPIO 19)
SCK (BCLK)     | Pin 12 (GPIO 18)
L/R            | Pin 39 (Ground) - Left channel

Usage:
    python3 test_voice_ai.py
"""

import os
import sys
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# Suppress ALSA/JACK error messages
from ctypes import *
try:
    ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
    def py_error_handler(filename, line, function, err, fmt):
        pass
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound = cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass

import pyaudio
import wave
import struct
import numpy as np
import tempfile
import time

# Check dependencies
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️  faster-whisper tidak terinstall. Install dengan: pip install faster-whisper")

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️  ollama tidak terinstall. Install dengan: pip install ollama")

# ===== CONFIGURATION =====
RECORD_SECONDS = 5          # Durasi rekaman default
WHISPER_MODEL = "small"     # Model Whisper: tiny, base, small, medium, large
AI_MODEL = "qwen2.5:0.5b"   # Model Ollama (0.5b ringan untuk Raspberry Pi)

# Whisper Precision Settings (balanced for Raspberry Pi)
WHISPER_BEAM_SIZE = 3       # Lebih tinggi = lebih presisi (1-5, default: 1)
WHISPER_BEST_OF = 2         # Kandidat terbaik (1-3, default: 1)
WHISPER_PATIENCE = 1.0      # Beam search patience
WHISPER_TEMPERATURE = 0.0   # 0 = deterministic, lebih presisi

# Audio Configuration (untuk GoogleVoiceHAT/I2S soundcard)
NATIVE_RATE = 48000         # Native rate dari soundcard
TARGET_RATE = 16000         # Target rate untuk Whisper
CHANNELS = 2                # Stereo (required by soundcard)
CHUNK = 4096                # Buffer size
FORMAT = pyaudio.paInt32    # 32-bit format

class VoiceAITest:
    def __init__(self):
        self.whisper_model = None
        self.audio = None
        self.device_index = None
        
    def init_audio(self):
        """Initialize PyAudio dan find microphone"""
        print("\n🎤 Mencari microphone...")
        self.audio = pyaudio.PyAudio()
        
        # Cari device yang bisa digunakan
        for i in range(self.audio.get_device_count()):
            dev = self.audio.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0:
                name = dev['name'].lower()
                print(f"   [{i}] {dev['name']} (Channels: {dev['maxInputChannels']}, Rate: {dev['defaultSampleRate']})")
                
                # Prioritas: I2S > PulseAudio > Default
                if any(k in name for k in ['i2s', 'googlevoicehat', 'snd_rpi']):
                    self.device_index = i
                    print(f"   ✅ Selected: I2S device [{i}]")
                elif 'pulse' in name and self.device_index is None:
                    self.device_index = i
                elif 'default' in name and self.device_index is None:
                    self.device_index = i
        
        if self.device_index is None:
            # Fallback ke device pertama dengan input
            for i in range(self.audio.get_device_count()):
                dev = self.audio.get_device_info_by_index(i)
                if dev['maxInputChannels'] > 0:
                    self.device_index = i
                    break
        
        if self.device_index is not None:
            dev = self.audio.get_device_info_by_index(self.device_index)
            print(f"\n✅ Menggunakan: [{self.device_index}] {dev['name']}")
            return True
        else:
            print("❌ Tidak ada microphone yang ditemukan!")
            return False
    
    def init_whisper(self):
        """Initialize Whisper model"""
        if not WHISPER_AVAILABLE:
            return False
        
        print(f"\n🧠 Loading Whisper model '{WHISPER_MODEL}'...")
        print("   (Ini mungkin memakan waktu beberapa saat untuk pertama kali)")
        
        try:
            self.whisper_model = WhisperModel(
                WHISPER_MODEL,
                device="cpu",
                compute_type="int8"  # Optimized untuk Raspberry Pi
            )
            print("✅ Whisper model loaded!")
            return True
        except Exception as e:
            print(f"❌ Gagal load Whisper: {e}")
            return False
    
    def record_audio(self, duration=RECORD_SECONDS):
        """Record audio dari microphone"""
        dev = self.audio.get_device_info_by_index(self.device_index)
        sample_rate = int(dev['defaultSampleRate'])
        channels = min(int(dev['maxInputChannels']), 2)
        
        print(f"\n🎤 Recording... ({duration} detik)")
        print(f"   Rate: {sample_rate}Hz, Channels: {channels}")
        print("   Silakan bicara sekarang!")
        
        try:
            stream = self.audio.open(
                format=FORMAT,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=CHUNK
            )
            
            frames = []
            num_chunks = int(sample_rate / CHUNK * duration)
            
            for i in range(num_chunks):
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                    # Progress indicator
                    progress = int((i + 1) / num_chunks * 20)
                    print(f"\r   [{'█' * progress}{'░' * (20 - progress)}] {int((i+1)/num_chunks*100)}%", end='', flush=True)
                except Exception as e:
                    print(f"\n⚠️ Read error: {e}")
                    continue
            
            print()  # New line after progress
            stream.stop_stream()
            stream.close()
            
            print("✅ Recording selesai!")
            
            # Convert to WAV file
            return self._convert_to_wav(frames, sample_rate, channels)
            
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None
    
    def _convert_to_wav(self, frames, sample_rate, channels):
        """Convert raw audio to WAV file (16-bit mono, 16kHz for Whisper)"""
        print("🔄 Converting audio...")
        
        raw_data = b''.join(frames)
        
        # Parse stereo 32-bit data, extract LEFT channel only
        # INMP441 dengan L/R = GND mengirim data di LEFT channel
        samples_left = []
        bytes_per_frame = 4 * channels  # 4 bytes per sample * channels
        
        for i in range(0, len(raw_data), bytes_per_frame):
            if i + 4 <= len(raw_data):
                # Ambil LEFT channel saja (byte 0-3)
                left = struct.unpack('<i', raw_data[i:i+4])[0]
                samples_left.append(left)
        
        samples = samples_left
        print(f"   Using LEFT channel ({len(samples)} samples)")
        
        # Convert to numpy for processing
        arr = np.array(samples, dtype=np.float64)
        
        # Remove DC offset (penting untuk INMP441!)
        dc_offset = arr.mean()
        arr = arr - dc_offset
        print(f"   DC offset removed: {dc_offset:.0f}")
        
        # Check signal level
        signal_max = max(abs(arr.max()), abs(arr.min()))
        signal_std = arr.std()
        print(f"   Signal level - Max: {signal_max:.0f}, Std: {signal_std:.0f}")
        
        # DETEKSI NOISE: Jika std > 1 milyar, ini noise random bukan audio valid
        # Signal valid dari INMP441 biasanya std antara 1 juta - 100 juta
        if signal_std > 1000000000:  # > 1 milyar = noise random
            print("   ❌ NOISE TERDETEKSI! Signal adalah random noise, bukan audio.")
            print("   💡 Cek koneksi kabel, terutama pin SD (Pin 38)")
            return None  # Jangan proses noise
        
        if signal_std < 100000:
            print("   ⚠️ Signal sangat lemah! Coba bicara lebih keras atau cek wiring.")
        
        # Normalize ke 16-bit range
        if signal_max > 0:
            arr = arr / signal_max * 32000  # Sedikit headroom
        
        samples_16 = np.clip(arr, -32768, 32767).astype(np.int16)
        
        # Resample to 16kHz if needed
        if sample_rate != TARGET_RATE:
            print(f"   Resampling {sample_rate}Hz → {TARGET_RATE}Hz...")
            resample_ratio = TARGET_RATE / sample_rate
            new_length = int(len(samples_16) * resample_ratio)
            x_old = np.linspace(0, 1, len(samples_16))
            x_new = np.linspace(0, 1, new_length)
            samples_resampled = np.interp(x_new, x_old, samples_16.astype(np.float32))
            samples_16 = np.clip(samples_resampled, -32768, 32767).astype(np.int16)
        
        # Save to temp file
        temp_file = tempfile.mktemp(suffix='.wav')
        with wave.open(temp_file, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_RATE)
            wf.writeframes(samples_16.tobytes())
        
        # Also save a copy for debugging
        import shutil
        debug_file = "/tmp/last_recording.wav"
        shutil.copy(temp_file, debug_file)
        
        print(f"✅ Audio converted: {len(samples_16)} samples @ {TARGET_RATE}Hz")
        print(f"   Debug copy saved: {debug_file}")
        return temp_file
    
    def transcribe(self, audio_file):
        """Transcribe audio to text using Whisper"""
        if not self.whisper_model:
            return None
        
        print("\n📝 Transcribing dengan Whisper...")
        print(f"   (beam={WHISPER_BEAM_SIZE}, best_of={WHISPER_BEST_OF})")
        
        try:
            segments, info = self.whisper_model.transcribe(
                audio_file,
                beam_size=WHISPER_BEAM_SIZE,
                best_of=WHISPER_BEST_OF,
                patience=WHISPER_PATIENCE,
                temperature=WHISPER_TEMPERATURE,
                language="id",  # Bahasa Indonesia
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.4,              # Sensitivitas VAD (0.0-1.0)
                    min_silence_duration_ms=300,  # Lebih pendek = tangkap lebih banyak
                    speech_pad_ms=250,          # Padding sebelum/sesudah speech
                    min_speech_duration_ms=100  # Minimum durasi speech
                ),
                word_timestamps=False,  # False = lebih cepat
                condition_on_previous_text=True,  # Konteks antar segment
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.5  # Threshold untuk deteksi non-speech
            )
            
            text = " ".join([segment.text for segment in segments]).strip()
            
            # Cleanup temp file
            try:
                os.remove(audio_file)
            except:
                pass
            
            if text:
                print(f"✅ Hasil transkripsi: \"{text}\"")
                return text
            else:
                print("⚠️ Tidak ada suara terdeteksi")
                return None
                
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None
    
    def ask_ai(self, text):
        """Send text to Ollama AI and get response"""
        if not OLLAMA_AVAILABLE:
            print("⚠️ Ollama library tidak tersedia")
            return f"[Echo] Anda berkata: {text}"
        
        print(f"\n🤖 Mengirim ke AI ({AI_MODEL})...")
        
        try:
            response = ollama.chat(
                model=AI_MODEL,
                messages=[
                    {
                        'role': 'system',
                        'content': '''Kamu adalah asisten robot pengontrol gerakan. Tugasmu HANYA menginterpretasi perintah gerakan.

PERINTAH YANG VALID:
- MAJU [angka] meter/langkah
- MUNDUR [angka] meter/langkah  
- BELOK KANAN [angka] derajat (default 90)
- BELOK KIRI [angka] derajat (default 90)
- LURUS [angka] meter
- BERHENTI / STOP
- PUTAR BALIK (180 derajat)

FORMAT RESPONS:
Jika perintah valid, jawab: "OK, [aksi]. Perintah: [KODE]"
Kode: MAJU_X, MUNDUR_X, KANAN_X, KIRI_X, LURUS_X, STOP, PUTAR

Jika tidak valid/tidak jelas, jawab: "Maaf, perintah tidak dikenali. Contoh: Maju 5 meter, Belok kanan, Mundur 2 langkah"

Jawab SINGKAT dalam 1-2 kalimat saja.'''
                    },
                    {
                        'role': 'user',
                        'content': text
                    }
                ],
                options={
                    'temperature': 0.3,
                    'num_predict': 100
                }
            )
            
            ai_response = response['message']['content']
            return ai_response
            
        except Exception as e:
            print(f"⚠️ AI tidak tersedia: {e}")
            print("   Untuk mengaktifkan AI, install Ollama:")
            print("   curl -fsSL https://ollama.com/install.sh | sh")
            print(f"   ollama pull {AI_MODEL}")
            return f"[Echo tanpa AI] Anda berkata: \"{text}\""
    
    def parse_command(self, text):
        """Parse voice command untuk gerakan robot"""
        import re
        
        text_lower = text.lower().strip()
        
        # Ekstrak angka dari teks
        numbers = re.findall(r'\d+', text)
        distance = int(numbers[0]) if numbers else 1
        
        # Deteksi perintah
        command = None
        
        if any(word in text_lower for word in ['maju', 'kedepan', 'ke depan', 'forward']):
            command = f"MAJU_{distance}"
        elif any(word in text_lower for word in ['mundur', 'kebelakang', 'ke belakang', 'backward', 'back']):
            command = f"MUNDUR_{distance}"
        elif any(word in text_lower for word in ['kanan', 'right']):
            if 'belok' in text_lower or 'putar' in text_lower:
                command = f"KANAN_{distance if numbers else 90}"
            else:
                command = "KANAN_90"
        elif any(word in text_lower for word in ['kiri', 'left']):
            if 'belok' in text_lower or 'putar' in text_lower:
                command = f"KIRI_{distance if numbers else 90}"
            else:
                command = "KIRI_90"
        elif any(word in text_lower for word in ['lurus', 'straight']):
            command = f"LURUS_{distance}"
        elif any(word in text_lower for word in ['stop', 'berhenti', 'halt']):
            command = "STOP"
        elif any(word in text_lower for word in ['putar balik', 'balik', 'uturn', 'u-turn']):
            command = "PUTAR_180"
        
        return command
    
    def cleanup(self):
        """Cleanup resources"""
        if self.audio:
            self.audio.terminate()

def main():
    print("=" * 60)
    print("🤖 ROBOT VOICE COMMAND - INMP441 + Whisper + Ollama")
    print("=" * 60)
    print("""
┌────────────────────────────────────────────────────────────┐
│              PERINTAH YANG DIDUKUNG                        │
├────────────────────────────────────────────────────────────┤
│  🔹 "Maju [X] meter/langkah"      → Robot maju             │
│  🔹 "Mundur [X] meter/langkah"    → Robot mundur           │
│  🔹 "Belok kanan [X] derajat"     → Belok ke kanan         │
│  🔹 "Belok kiri [X] derajat"      → Belok ke kiri          │
│  🔹 "Lurus [X] meter"             → Jalan lurus            │
│  🔹 "Berhenti" / "Stop"           → Robot berhenti         │
│  🔹 "Putar balik"                 → Putar 180 derajat      │
└────────────────────────────────────────────────────────────┘

Wiring INMP441: VDD→Pin1, GND→Pin6, SD→Pin38, WS→Pin35, SCK→Pin12, L/R→Pin39
""")
    
    tester = VoiceAITest()
    
    try:
        # Initialize audio
        if not tester.init_audio():
            print("❌ Gagal inisialisasi audio!")
            return
        
        # Initialize Whisper
        if not tester.init_whisper():
            print("❌ Gagal inisialisasi Whisper!")
            return
        
        print("\n" + "=" * 60)
        print("✅ SISTEM SIAP!")
        print("=" * 60)
        print("\nTekan ENTER untuk mulai recording, atau 'q' untuk keluar.")
        print("Durasi recording: 5 detik per sesi.\n")
        
        while True:
            try:
                user_input = input("\n👉 Tekan ENTER untuk bicara (atau 'q' untuk keluar): ").strip().lower()
                
                if user_input == 'q':
                    print("\n👋 Sampai jumpa!")
                    break
                
                # Record audio
                audio_file = tester.record_audio(duration=5)
                if not audio_file:
                    print("❌ Gagal merekam audio")
                    continue
                
                # Transcribe to text
                text = tester.transcribe(audio_file)
                if not text:
                    print("⚠️ Tidak ada teks yang terdeteksi. Coba lagi.")
                    continue
                
                print("\n" + "-" * 40)
                print(f"👤 ANDA: {text}")
                print("-" * 40)
                
                # Parse command langsung dari teks
                command = tester.parse_command(text)
                if command:
                    print(f"📡 COMMAND DETECTED: {command}")
                else:
                    print("⚠️ Tidak ada perintah gerakan yang dikenali")
                
                # Get AI response
                ai_response = tester.ask_ai(text)
                if ai_response:
                    print("\n" + "-" * 40)
                    print(f"🤖 AI: {ai_response}")
                    print("-" * 40)
                
            except KeyboardInterrupt:
                print("\n\n👋 Dihentikan oleh user.")
                break
                
    finally:
        tester.cleanup()
        print("\n✅ Cleanup selesai.")

if __name__ == "__main__":
    main()

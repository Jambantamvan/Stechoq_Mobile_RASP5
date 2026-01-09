#!/usr/bin/env python3
"""
Text to Voice - Raspberry Pi 5 Version
Mengubah teks menjadi suara menggunakan Piper TTS
Optimized untuk ALSA audio system di Raspberry Pi 5
"""

import os
import subprocess
import sys
import platform
import time

# Konfigurasi path untuk Raspberry Pi 5
PIPER_BINARY = "./piper/piper"  # Akan di-download ke folder piper
VOICE_MODEL = "voice_id.onnx"   # Indonesian voice model
OUTPUT_FILE = "/tmp/robot_voice.wav"  # Gunakan /tmp untuk temporary files

def check_dependencies():
    """Check apakah semua file dependency tersedia"""
    missing = []
    
    if not os.path.exists(PIPER_BINARY):
        missing.append(f"Piper binary: {PIPER_BINARY}")
    
    if not os.path.exists(VOICE_MODEL):
        missing.append(f"Voice model: {VOICE_MODEL}")
    
    if missing:
        print("❌ Missing dependencies:")
        for item in missing:
            print(f"   - {item}")
        print("\n💡 Run setup first: ./setup_raspy.sh")
        return False
    
    return True

def check_audio_system():
    """Check dan setup audio system untuk Raspberry Pi"""
    try:
        # Check apakah ALSA mixer tersedia
        result = subprocess.run(['amixer', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ALSA audio system detected")
            
            # Set volume to reasonable level
            subprocess.run(['amixer', 'set', 'PCM', '80%'], 
                         capture_output=True, stderr=subprocess.DEVNULL)
            subprocess.run(['amixer', 'set', 'Master', '80%'], 
                         capture_output=True, stderr=subprocess.DEVNULL)
            return True
        else:
            print("⚠️ ALSA tidak ditemukan, akan mencoba PulseAudio")
            return False
    except FileNotFoundError:
        print("⚠️ ALSA utilities tidak terinstall")
        return False

def check_pulseaudio():
    """Check PulseAudio availability"""
    try:
        result = subprocess.run(['pulseaudio', '--check'], capture_output=True)
        if result.returncode == 0:
            print("✅ PulseAudio running")
            return True
        else:
            # Try to start PulseAudio
            print("🔧 Starting PulseAudio...")
            subprocess.run(['pulseaudio', '--start'], capture_output=True)
            time.sleep(1)
            result = subprocess.run(['pulseaudio', '--check'], capture_output=True)
            return result.returncode == 0
    except FileNotFoundError:
        print("⚠️ PulseAudio tidak terinstall")
        return False

def text_to_voice(text):
    """Konversi text ke suara dan mainkan di Raspberry Pi"""
    if not text or text.strip() == "":
        print("⚠️ Text kosong, tidak ada yang diucapkan")
        return False
    
    # Check dependencies first
    if not check_dependencies():
        return False
    
    # Bersihkan text untuk TTS
    clean_text = text.replace('"', '').replace("'", "").replace("\n", ". ")
    clean_text = clean_text.replace("  ", " ").strip()
    
    # Hapus file output lama
    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
        except:
            pass
    
    print(f"🔊 Mengkonversi teks ke suara: '{clean_text[:50]}{'...' if len(clean_text) > 50 else ''}'")
    
    # Check jika Piper binary tersedia
    if not os.path.exists(PIPER_BINARY):
        print(f"❌ Piper binary tidak ditemukan: {PIPER_BINARY}")
        print("   Jalankan setup_raspy.sh terlebih dahulu")
        return False
    
    if not os.path.exists(VOICE_MODEL):
        print(f"❌ Voice model tidak ditemukan: {VOICE_MODEL}")
        print("   Jalankan setup_raspy.sh terlebih dahulu")
        return False
    
    try:
        # Generate audio dengan Piper untuk Raspberry Pi
        # Gunakan echo dengan pipe ke Piper
        piper_cmd = f'echo "{clean_text}" | "{PIPER_BINARY}" --model "{VOICE_MODEL}" --output_file "{OUTPUT_FILE}"'
        
        result = subprocess.run(piper_cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ Piper TTS error: {result.stderr}")
            print(f"   Command: {piper_cmd}")
            return False
        
        if not os.path.exists(OUTPUT_FILE):
            print("❌ Output file tidak terbuat")
            return False
        
        print(f"✅ Audio berhasil dibuat: {OUTPUT_FILE}")
        
        # Mainkan audio
        return play_audio_rpi(OUTPUT_FILE)
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout: Piper TTS terlalu lama")
        return False
    except Exception as e:
        print(f"❌ Error TTS: {e}")
        return False

def play_audio_rpi(file_path):
    """Mainkan audio di Raspberry Pi dengan berbagai metode"""
    if not os.path.exists(file_path):
        print(f"❌ File audio tidak ditemukan: {file_path}")
        return False
    
    print("🔊 Memutar audio...")
    
    # Method 1: aplay (ALSA)
    try:
        result = subprocess.run(['aplay', file_path], 
                              capture_output=True, timeout=15)
        if result.returncode == 0:
            print("✅ Audio dimainkan dengan aplay")
            return True
        else:
            print(f"⚠️ aplay error: {result.stderr.decode()}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"⚠️ aplay tidak tersedia atau timeout: {e}")
    
    # Method 2: paplay (PulseAudio) 
    try:
        result = subprocess.run(['paplay', file_path], 
                              capture_output=True, timeout=15)
        if result.returncode == 0:
            print("✅ Audio dimainkan dengan paplay")
            return True
        else:
            print(f"⚠️ paplay error: {result.stderr.decode()}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"⚠️ paplay tidak tersedia atau timeout: {e}")
    
    # Method 3: mpg123 (jika tersedia)
    try:
        result = subprocess.run(['mpg123', file_path], 
                              capture_output=True, timeout=15)
        if result.returncode == 0:
            print("✅ Audio dimainkan dengan mpg123")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Method 4: mplayer (jika tersedia)
    try:
        result = subprocess.run(['mplayer', file_path], 
                              capture_output=True, timeout=15)
        if result.returncode == 0:
            print("✅ Audio dimainkan dengan mplayer")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Method 5: omxplayer untuk Raspberry Pi lama (fallback)
    try:
        result = subprocess.run(['omxplayer', file_path], 
                              capture_output=True, timeout=15)
        if result.returncode == 0:
            print("✅ Audio dimainkan dengan omxplayer")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("❌ Tidak dapat memutar audio dengan semua metode yang tersedia")
    print("   Pastikan audio system berjalan: sudo systemctl start alsa-state")
    print("   Atau install audio players: sudo apt install alsa-utils pulseaudio")
    return False

def test_audio_system():
    """Test audio system Raspberry Pi"""
    print("🔧 Testing audio system...")
    
    alsa_ok = check_audio_system()
    pulse_ok = check_pulseaudio()
    
    if not alsa_ok and not pulse_ok:
        print("❌ Tidak ada audio system yang berfungsi")
        print("   Install dengan: sudo apt install alsa-utils pulseaudio")
        return False
    
    # Test dengan beep jika tersedia
    try:
        subprocess.run(['speaker-test', '-t', 'sine', '-f', '1000', '-l', '1'], 
                      capture_output=True, timeout=3)
        print("✅ Audio hardware test berhasil")
    except:
        print("⚠️ Tidak dapat test audio hardware")
    
    return True

def setup_audio_permissions():
    """Setup audio permissions untuk user"""
    try:
        import pwd
        import grp
        
        username = pwd.getpwuid(os.getuid()).pw_name
        
        # Check jika user sudah di audio group
        audio_group = grp.getgrnam('audio')
        if username in [member for member in audio_group.gr_mem]:
            print("✅ User sudah di audio group")
        else:
            print(f"⚠️ User {username} tidak di audio group")
            print(f"   Jalankan: sudo usermod -a -G audio {username}")
            print("   Kemudian logout dan login kembali")
            
    except Exception as e:
        print(f"⚠️ Cannot check audio permissions: {e}")

def main():
    """Test TTS untuk Raspberry Pi 5"""
    print("=" * 60)
    print("🎙️  TEXT TO VOICE - Raspberry Pi 5")
    print("=" * 60)
    print()
    
    # Setup audio permissions
    setup_audio_permissions()
    
    # Test audio system
    if not test_audio_system():
        print("\n❌ Audio system tidak siap")
        print("Setup audio dengan:")
        print("   sudo apt install alsa-utils pulseaudio")
        print("   sudo systemctl enable alsa-state")
        print("   sudo usermod -a -G audio $USER")
        sys.exit(1)
    
    # Check Piper binary dan model
    if not check_dependencies():
        sys.exit(1)
    
    print("✅ Sistem TTS siap!")
    print("\nMasukkan teks yang ingin diubah menjadi suara.")
    print("Ketik 'quit', 'exit', atau 'keluar' untuk keluar.")
    print()
    
    # Test dengan sample text
    print("🧪 Testing dengan sample text...")
    test_success = text_to_voice("Halo, saya adalah robot yang berjalan di Raspberry Pi 5")
    
    if not test_success:
        print("❌ Test TTS gagal")
        sys.exit(1)
    
    print("\n✅ Test berhasil! Siap menerima input...")
    
    # Interactive mode
    while True:
        try:
            print("-" * 60)
            text = input("📝 Masukkan teks: ").strip()
            
            if not text:
                print("⚠️ Teks kosong, coba lagi.")
                continue
            
            if text.lower() in ['quit', 'exit', 'keluar', 'q']:
                print("👋 Terima kasih!")
                break
            
            success = text_to_voice(text)
            if success:
                print("✅ TTS berhasil")
            else:
                print("❌ TTS gagal")
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Terima kasih!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
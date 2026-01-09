#!/usr/bin/env python3
"""
Serial Monitor untuk ESP32 Robot - Raspberry Pi 5
Monitor komunikasi dan kirim perintah manual ke ESP32
"""

import serial
import serial.tools.list_ports
import threading
import time
import sys
import json
from datetime import datetime

class ESP32SerialMonitor:
    def __init__(self):
        self.ser = None
        self.port = None
        self.baud = 115200
        self.running = False
        self.monitor_thread = None
        
        print("========================================")
        print("🔧 ESP32 Serial Monitor - Raspberry Pi 5")
        print("========================================")
        print()

    def find_esp32_port(self):
        """Auto-detect ESP32 port pada Raspberry Pi (USB dan GPIO UART)"""
        ports = serial.tools.list_ports.comports()
        
        # Priority ports untuk Raspberry Pi (termasuk GPIO UART)
        priority_ports = ['/dev/ttyS0', '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
        
        print("🔍 Mencari ESP32...")
        
        # Cek GPIO UART dulu (/dev/ttyS0)
        import os
        if os.path.exists('/dev/ttyS0'):
            print("🔌 Found GPIO UART: /dev/ttyS0")
            print("📍 ESP32 TX → GPIO 15 (Pi RX - Pin 10)")
            print("📍 ESP32 RX → GPIO 14 (Pi TX - Pin 8)")
            return '/dev/ttyS0'
        
        # Cek priority ports untuk USB
        for port_name in priority_ports[1:]:  # Skip /dev/ttyS0 yang sudah dicek
            for port in ports:
                if port.device == port_name:
                    print(f"✅ Found ESP32 at USB port: {port.device}")
                    return port.device
        
        # Kalau tidak ada, tampilkan semua available ports
        print("📋 Available serial ports:")
        for port in ports:
            print(f"   {port.device}: {port.description}")
        
        if ports:
            return ports[0].device
        return None

    def connect(self, port=None):
        """Connect ke ESP32"""
        if port:
            self.port = port
        else:
            self.port = self.find_esp32_port()
        
        if not self.port:
            print("❌ No serial port found!")
            return False
        
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                timeout=1,
                write_timeout=1
            )
            
            time.sleep(2)  # Wait for ESP32 ready
            
            print(f"✅ Connected to ESP32 on {self.port}")
            print(f"📡 Baudrate: {self.baud}")
            print()
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect dari ESP32"""
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("🔌 Disconnected from ESP32")

    def monitor_serial(self):
        """Monitor thread untuk membaca data dari ESP32"""
        while self.running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting:
                    data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"[{timestamp}] ESP32: {data}")
            except Exception as e:
                if self.running:
                    print(f"❌ Monitor error: {e}")
                break
            
            time.sleep(0.01)

    def send_command(self, command, value=0, unit="none"):
        """Kirim perintah ke ESP32"""
        if not self.ser or not self.ser.is_open:
            print("❌ Not connected to ESP32")
            return False
        
        try:
            cmd_string = f"{command},{value},{unit}\n"
            self.ser.write(cmd_string.encode('utf-8'))
            self.ser.flush()
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] SENT: {cmd_string.strip()}")
            return True
            
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False

    def send_raw(self, raw_data):
        """Kirim raw data ke ESP32"""
        if not self.ser or not self.ser.is_open:
            print("❌ Not connected to ESP32")
            return False
        
        try:
            if not raw_data.endswith('\n'):
                raw_data += '\n'
            
            self.ser.write(raw_data.encode('utf-8'))
            self.ser.flush()
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] RAW SENT: {raw_data.strip()}")
            return True
            
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False

    def start_monitoring(self):
        """Start monitoring ESP32"""
        if not self.ser or not self.ser.is_open:
            print("❌ Not connected!")
            return False
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_serial, daemon=True)
        self.monitor_thread.start()
        
        print("📡 Monitoring started...")
        print("📝 Type commands or 'help' for command list")
        print("🚪 Type 'quit' or 'exit' to stop")
        print()
        
        return True

    def show_help(self):
        """Show available commands"""
        print()
        print("🔧 Available Commands:")
        print("═" * 50)
        print("Movement Commands:")
        print("  forward <distance>     - Maju (meter)")
        print("  backward <distance>    - Mundur (meter)")
        print("  left <degrees>         - Belok kiri (derajat)")
        print("  right <degrees>        - Belok kanan (derajat)")
        print("  stop                   - Berhenti")
        print()
        print("Speed Commands:")
        print("  speed <percent>        - Set kecepatan (0-100%)")
        print()
        print("System Commands:")
        print("  status                 - Cek status robot")
        print("  raw <data>             - Kirim raw data")
        print()
        print("Monitor Commands:")
        print("  clear                  - Clear screen")
        print("  help                   - Show this help")
        print("  quit/exit              - Exit monitor")
        print()
        print("Examples:")
        print("  forward 5              → FORWARD,5,meter")
        print("  left 90                → LEFT,90,degree")  
        print("  speed 75               → SPEED,75,percent")
        print("  raw STATUS,0,none      → Send custom command")
        print("═" * 50)
        print()

    def interactive_mode(self):
        """Interactive command mode"""
        if not self.start_monitoring():
            return
        
        self.show_help()
        
        try:
            while self.running:
                try:
                    user_input = input("ESP32> ").strip().lower()
                    
                    if not user_input:
                        continue
                    
                    if user_input in ['quit', 'exit', 'q']:
                        break
                    elif user_input == 'help':
                        self.show_help()
                    elif user_input == 'clear':
                        print("\033[H\033[J")  # Clear screen
                    elif user_input == 'status':
                        self.send_command("STATUS", 0, "none")
                    elif user_input == 'stop':
                        self.send_command("STOP", 0, "none")
                    elif user_input.startswith('forward '):
                        try:
                            distance = float(user_input.split()[1])
                            self.send_command("FORWARD", distance, "meter")
                        except:
                            print("❌ Usage: forward <distance>")
                    elif user_input.startswith('backward '):
                        try:
                            distance = float(user_input.split()[1])
                            self.send_command("BACKWARD", distance, "meter")
                        except:
                            print("❌ Usage: backward <distance>")
                    elif user_input.startswith('left '):
                        try:
                            degrees = float(user_input.split()[1])
                            self.send_command("LEFT", degrees, "degree")
                        except:
                            print("❌ Usage: left <degrees>")
                    elif user_input.startswith('right '):
                        try:
                            degrees = float(user_input.split()[1])
                            self.send_command("RIGHT", degrees, "degree")
                        except:
                            print("❌ Usage: right <degrees>")
                    elif user_input.startswith('speed '):
                        try:
                            speed = float(user_input.split()[1])
                            if 0 <= speed <= 100:
                                self.send_command("SPEED", speed, "percent")
                            else:
                                print("❌ Speed must be 0-100%")
                        except:
                            print("❌ Usage: speed <percent>")
                    elif user_input.startswith('raw '):
                        raw_data = user_input[4:]  # Remove 'raw '
                        self.send_raw(raw_data)
                    else:
                        print(f"❌ Unknown command: {user_input}")
                        print("💡 Type 'help' for available commands")
                
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
        
        except Exception as e:
            print(f"❌ Interactive mode error: {e}")
        
        finally:
            print("\n👋 Exiting serial monitor...")
            self.disconnect()

def main():
    monitor = ESP32SerialMonitor()
    
    try:
        # Command line arguments
        if len(sys.argv) > 1:
            port = sys.argv[1]
            print(f"🔗 Using specified port: {port}")
            if monitor.connect(port):
                monitor.interactive_mode()
        else:
            # Auto-detect port
            if monitor.connect():
                monitor.interactive_mode()
    
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        monitor.disconnect()

if __name__ == "__main__":
    print("🤖 ESP32 Serial Monitor for Raspberry Pi 5")
    print("📋 Usage: python3 serial_monitor.py [port]")
    print("🔧 Example: python3 serial_monitor.py /dev/ttyUSB0")
    print()
    
    main()
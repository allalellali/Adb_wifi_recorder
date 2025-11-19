#!/usr/bin/env python3

import subprocess
import threading
import time
import os
import sys
from datetime import datetime
import logging
import signal

class theway:
    def __init__(self, records_dir="~/records"):
        self.records_dir = os.path.expanduser(records_dir)
        self.is_recording = False
        self.phone_ip = None
        
        os.makedirs(self.records_dir, exist_ok=True)
        os.makedirs(f"{self.records_dir}/logs", exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{self.records_dir}/logs/recorder.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def get_phone_ip(self):
        while True:
            ip = input("Enter your phone's IP address : ").strip()
        
            if ip.count('.') == 3 and all(part.isdigit() and 0 <= int(part) <= 255 for part in ip.split('.')):
                self.phone_ip = ip
                print(f"IP address set to: {ip}")
                return ip
            else:
                print(" Invalid IP address format. Please try again.")

    def setup_wifi_adb_simple(self):
    
        try:
            if not self.phone_ip:
                self.get_phone_ip()
                
            print("Step 1: Checking current connections...")
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        
            if f'{self.phone_ip}:5555' in result.stdout and 'device' in result.stdout:
                print(f"Already connected via WiFi to {self.phone_ip}")
                return True
            
            if any('device' in line and self.phone_ip not in line for line in result.stdout.split('\n')):
                print("Device found via USB, setting up WiFi...")
                
                print("Step 2: Setting TCP mode...")
                result = subprocess.run(['adb', 'tcpip', '5555'], capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    print("Failed to set TCP mode")
                    return False
                
                print("TCP mode set successfully")
                time.sleep(3)
                
                print("Step 3: Connecting via WiFi...")
                result = subprocess.run(['adb', 'connect', f'{self.phone_ip}:5555'], 
                                      capture_output=True, text=True, timeout=30)
                
                if "connected" in result.stdout:
                    print("WiFi ADB connected ")
                    return True
                else:
                    print(f"WiFi connection failed: {result.stdout}")
                    return False
            else:
                print("No device found. Please connect via USB first.")
                return False
                
        except Exception as e:
            print(f"Setup failed: {e}")
            return False

    def check_connection(self):
    
        try:
            if not self.phone_ip:
                return False
                
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
            return f'{self.phone_ip}:5555' in result.stdout and "device" in result.stdout
        except:
            return False

    def simple_record_segment(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_filename = f"record_{timestamp}.mp4"
            
            print(f"Starting recording: {timestamp}")
            
            
            print("📱 Launching camera...")
            subprocess.run(['adb', 'shell', 'am', 'start', '-a', 'android.media.action.VIDEO_CAMERA'], 
                         timeout=15)
            time.sleep(5)
            

            print("Starting recording...")
            subprocess.run(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_CAMERA'], timeout=10)
            time.sleep(3)
            
            
            print("Recording for 29 minutes...")
            for i in range(1740): 
                if not self.is_recording:
                    break
                if i % 300 == 0: 
                    minutes = i // 60
                    print(f"Recording... {minutes}/29 minutes")
                time.sleep(1)
            
            
            print("Stopping recording...")
            subprocess.run(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_CAMERA'], timeout=10)
            time.sleep(5)
            
        
            subprocess.run(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_BACK'], timeout=5)
            subprocess.run(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_BACK'], timeout=5)
            time.sleep(3)
            
    
            print("Transferring video...")
            result = subprocess.run(['adb', 'shell', 'ls', '/sdcard/DCIM/Camera/*.mp4'], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.stdout and result.stdout.strip():
                
                video_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                if video_files:
                    latest_video = video_files[-1]
                    print(f"📹 Found video: {latest_video}")
                    
                    
                    transfer_result = subprocess.run(['adb', 'pull', latest_video, f"{self.records_dir}/{local_filename}"], 
                                                 timeout=120, capture_output=True, text=True)
                    
                    if transfer_result.returncode == 0:
                        
                        subprocess.run(['adb', 'shell', 'rm', latest_video], timeout=30)
                        print(f"Success: {local_filename}")
                        return True
                    else:
                        print(f"Transfer failed: {transfer_result.stderr}")
                        return False
            else:
                print("No video file found")
                return False
                
        except Exception as e:
            print(f"Recording failed: {e}")
            return False

    def continuous_recording(self):
        
        print("Starting 10hour continuous recording...")
        
        start_time = time.time()
        segment_count = 0
        successful_recordings = 0
        
        while self.is_recording and (time.time() - start_time) < 36000: 
            segment_count += 1
            elapsed = (time.time() - start_time) / 3600
            remaining = 10 - elapsed
            
            print(f"\n Segment {segment_count}")
            print(f"Elapsed: {elapsed:.1f}h, Remaining: {remaining:.1f}h")
            
            if self.simple_record_segment():
                successful_recordings += 1
                print(f"Segment {segment_count} completed")
            else:
                print(f"Segment {segment_count} failed")
            
            # Brief pause before next segment
            if self.is_recording:
                print(" Preparing next segment...")
                time.sleep(5)
        
        print("Recording completed!")
        print(f" Summary: {successful_recordings}/{segment_count} segments successful")

    def start_recording(self):
        
        print("Starting recording setup...")
        
        if not self.setup_wifi_adb_simple():
            return False
        
        self.is_recording = True
        
    
        record_thread = threading.Thread(target=self.continuous_recording)
        record_thread.daemon = True
        record_thread.start()
        
        return True

    def stop_recording(self):
    
        print("Stopping recording...")
        self.is_recording = False
        subprocess.run(['adb', 'shell', 'am', 'force-stop', 'com.sec.android.app.camera'], timeout=10)

    def signal_handler(self, signum, frame):
    
        print("\nShutting down...")
        self.stop_recording()
        sys.exit(0)

    def get_status(self):
        
        if os.path.exists(self.records_dir):
            videos = [f for f in os.listdir(self.records_dir) if f.endswith('.mp4')]
            return len(videos)
        return 0

    def list_recordings(self):
    
        if os.path.exists(self.records_dir):
            videos = [f for f in os.listdir(self.records_dir) if f.endswith('.mp4')]
            if videos:
                print(f"\nFound {len(videos)} recordings:")
                for i, video in enumerate(sorted(videos), 1):
                    size = os.path.getsize(os.path.join(self.records_dir, video)) / (1024*1024)
                    print(f"  {i}. {video} ({size:.1f} MB)")
            else:
                print("No recordings found")
        else:
            print("ecords directory not found")

def main():
    
    print("=" * 50)
    print("📱 WiFi Recorder")
    print("=" * 50)
    print("Please enter your phone's IP address ")
    print("=" * 50)
    
    
    try:
        subprocess.run(['adb', 'version'], capture_output=True, check=True)
    except:
        print("ADB not found. Install with: sudo apt install adb")
        return
    
    recorder = theway()
    
    while True:
        print("\nCommands: start, stop, status, list, ip, exit")
        cmd = input("recorder> ").strip().lower()
        
        if cmd == "start":
            if not recorder.is_recording:
                if recorder.start_recording():
                    print("Recording started successfully!")
                    print("Camera will start automatically")
                else:
                    print("Failed to start recording")
            else:
                print("Recording already running")
                
        elif cmd == "stop":
            recorder.stop_recording()
            print("Recording stopped")
            
        elif cmd == "status":
            count = recorder.get_status()
            print(f"Recorded videos: {count}")
            print(f"Location: {recorder.records_dir}")
            print(f"WiFi Connected: {recorder.check_connection()}")
            if recorder.phone_ip:
                print(f"Current IP: {recorder.phone_ip}")
            else:
                print("Current IP: Not set")
            
        elif cmd == "list":
            recorder.list_recordings()
            
        elif cmd == "ip":
        
            old_ip = recorder.phone_ip
            recorder.get_phone_ip()
            if old_ip != recorder.phone_ip:
                print("IP address changed. You may need to reconnect.")
            
        elif cmd in ["exit", "quit"]:
            recorder.stop_recording()
            print("Goodbye!")
            break
            
        else:
            print(" Unknown command")

if __name__ == "__main__":
    main()

#!/bin/bash
echo "================================================"
echo "Wall-E Bluetooth Speaker Integration Setup"
echo "================================================"

# Get the Wall-E project directory
WALLE_DIR="$HOME/walle-server/wall-e-control"

if [ ! -d "$WALLE_DIR" ]; then
    echo "❌ Wall-E project directory not found at $WALLE_DIR"
    exit 1
fi

cd "$WALLE_DIR"

echo "Setting up Bluetooth audio for Wall-E..."
echo "Project directory: $WALLE_DIR"

# Stop Wall-E service
echo "Stopping Wall-E service..."
sudo systemctl stop walle-control.service

# Update system packages
echo ""
echo "================================================"
echo "Installing Bluetooth packages..."
echo "================================================"
sudo apt-get update
sudo apt-get install -y bluetooth bluez bluez-tools pulseaudio pulseaudio-module-bluetooth
sudo apt-get install -y alsa-utils pavucontrol python3-numpy

# Enable and start Bluetooth
echo "Configuring Bluetooth services..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Add user to bluetooth group
sudo usermod -a -G bluetooth $USER

# Configure PulseAudio for Bluetooth
echo "Configuring PulseAudio..."
mkdir -p ~/.config/pulse

# Create PulseAudio config for Bluetooth
cat > ~/.config/pulse/default.pa << 'EOF'
#!/usr/bin/pulseaudio -nF
# Load default modules
.include /etc/pulse/default.pa

# Load Bluetooth modules
load-module module-bluetooth-policy
load-module module-bluetooth-discover
EOF

# Configure PulseAudio daemon
cat > ~/.config/pulse/daemon.conf << 'EOF'
# Enable auto-spawning
autospawn = yes
exit-idle-time = -1
EOF

# Enable PulseAudio user service
systemctl --user enable pulseaudio

echo ""
echo "================================================"
echo "Backing up original files..."
echo "================================================"

# Backup original audio system
if [ -f "modules/audio_system.py" ]; then
    cp modules/audio_system.py modules/audio_system.py.backup
    echo "✓ Backed up original audio_system.py"
fi

# Backup original app.py
if [ -f "app.py" ]; then
    cp app.py app.py.backup
    echo "✓ Backed up original app.py"
fi

# Backup original index.html
if [ -f "templates/index.html" ]; then
    cp templates/index.html templates/index.html.backup
    echo "✓ Backed up original index.html"
fi

echo ""
echo "================================================"
echo "Installing enhanced audio system..."
echo "================================================"

# Replace the audio system with the enhanced version
cat > modules/audio_system.py << 'AUDIO_EOF'
#!/usr/bin/env python3
"""
Enhanced Audio System Module for Wall-E with Bluetooth Support
"""

import pygame
import os
import subprocess
import threading
import time
import math
from typing import Dict, Optional, List, Callable

class BluetoothAudioManager:
    def __init__(self):
        self.connected_devices = {}
        self.default_speaker_mac = None
        self.load_config()
    
    def load_config(self):
        """Load Bluetooth configuration from file"""
        config_file = os.path.expanduser('~/.walle_bluetooth_config')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    for line in f:
                        if line.startswith('BLUETOOTH_SPEAKER_MAC='):
                            self.default_speaker_mac = line.split('=')[1].strip()
                            print(f"Loaded default Bluetooth speaker: {self.default_speaker_mac}")
            except Exception as e:
                print(f"Error loading Bluetooth config: {e}")
    
    def save_config(self):
        """Save Bluetooth configuration to file"""
        config_file = os.path.expanduser('~/.walle_bluetooth_config')
        try:
            with open(config_file, 'w') as f:
                if self.default_speaker_mac:
                    f.write(f"BLUETOOTH_SPEAKER_MAC={self.default_speaker_mac}\n")
        except Exception as e:
            print(f"Error saving Bluetooth config: {e}")
    
    def scan_devices(self, duration=15) -> List[Dict]:
        """Scan for available Bluetooth devices"""
        print("Scanning for Bluetooth devices...")
        devices = []
        
        try:
            # Start scan
            subprocess.run(['bluetoothctl', 'scan', 'on'], check=True, capture_output=True)
            time.sleep(duration)
            
            # Stop scan and get devices
            subprocess.run(['bluetoothctl', 'scan', 'off'], check=True, capture_output=True)
            
            # Get device list
            result = subprocess.run(['bluetoothctl', 'devices'], 
                                  check=True, capture_output=True, text=True)
            
            for line in result.stdout.split('\n'):
                if line.startswith('Device'):
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        mac = parts[1]
                        name = parts[2]
                        devices.append({'mac': mac, 'name': name})
            
        except Exception as e:
            print(f"Error scanning Bluetooth devices: {e}")
        
        return devices
    
    def connect_device(self, mac_address: str) -> bool:
        """Connect to a Bluetooth device"""
        try:
            print(f"Connecting to Bluetooth device: {mac_address}")
            
            # Trust the device
            subprocess.run(['bluetoothctl', 'trust', mac_address], 
                          check=True, capture_output=True)
            
            # Pair with the device
            subprocess.run(['bluetoothctl', 'pair', mac_address], 
                          check=True, capture_output=True)
            
            # Connect to the device
            result = subprocess.run(['bluetoothctl', 'connect', mac_address], 
                                  check=True, capture_output=True, text=True)
            
            time.sleep(3)  # Wait for connection to establish
            
            # Check if connected
            if self.is_device_connected(mac_address):
                self.connected_devices[mac_address] = True
                self.set_as_default_audio_output()
                print(f"✓ Connected to Bluetooth device: {mac_address}")
                return True
            else:
                print(f"✗ Failed to connect to: {mac_address}")
                return False
                
        except Exception as e:
            print(f"Error connecting to Bluetooth device: {e}")
            return False
    
    def disconnect_device(self, mac_address: str) -> bool:
        """Disconnect from a Bluetooth device"""
        try:
            subprocess.run(['bluetoothctl', 'disconnect', mac_address], 
                          check=True, capture_output=True)
            self.connected_devices[mac_address] = False
            print(f"Disconnected from: {mac_address}")
            return True
        except Exception as e:
            print(f"Error disconnecting from device: {e}")
            return False
    
    def is_device_connected(self, mac_address: str) -> bool:
        """Check if a Bluetooth device is connected"""
        try:
            result = subprocess.run(['bluetoothctl', 'info', mac_address], 
                                  check=True, capture_output=True, text=True)
            return 'Connected: yes' in result.stdout
        except:
            return False
    
    def set_as_default_audio_output(self):
        """Set Bluetooth device as default audio output"""
        try:
            # Get Bluetooth audio sink
            result = subprocess.run(['pacmd', 'list-sinks'], 
                                  capture_output=True, text=True)
            
            for line in result.stdout.split('\n'):
                if 'bluez' in line.lower() and 'index:' in line:
                    sink_index = line.split('index:')[1].split()[0]
                    subprocess.run(['pacmd', 'set-default-sink', sink_index])
                    print(f"Set Bluetooth sink {sink_index} as default")
                    break
        except Exception as e:
            print(f"Error setting default audio output: {e}")
    
    def auto_connect_default_speaker(self) -> bool:
        """Automatically connect to the default Bluetooth speaker"""
        if self.default_speaker_mac:
            return self.connect_device(self.default_speaker_mac)
        return False

class AudioSystem:
    def __init__(self, sounds_dir='sounds', static_sounds_dir='static/sounds', volume=0.7):
        """Initialize enhanced audio system with Bluetooth support"""
        self.sounds_dir = sounds_dir
        self.static_sounds_dir = static_sounds_dir
        self.volume = volume
        self.sounds = {}
        self.is_playing = False
        self.bluetooth_manager = BluetoothAudioManager()
        
        # Status callbacks
        self.connection_status_callback = None
        self.audio_status_callback = None
        
        # Initialize pygame mixer
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
            pygame.mixer.init()
            print("✓ Enhanced audio system initialized")
            self.available = True
        except Exception as e:
            print(f"✗ Audio system failed to initialize: {e}")
            self.available = False
            return
        
        # Load sound effects
        self._load_sounds()
        
        # Create default sounds if they don't exist
        self._create_default_sounds()
        
        # Auto-connect to default Bluetooth speaker
        self._auto_connect_bluetooth()
    
    def _auto_connect_bluetooth(self):
        """Automatically connect to Bluetooth speaker in background"""
        def connect_thread():
            time.sleep(2)
            if self.bluetooth_manager.auto_connect_default_speaker():
                if self.connection_status_callback:
                    self.connection_status_callback(True, "Bluetooth speaker connected")
        
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()
    
    def _load_sounds(self):
        """Load all sound files from both sound directories"""
        sound_dirs = [self.sounds_dir, self.static_sounds_dir]
        
        for sounds_dir in sound_dirs:
            if not os.path.exists(sounds_dir):
                os.makedirs(sounds_dir, exist_ok=True)
                print(f"Created sounds directory: {sounds_dir}")
                continue
            
            sound_files = [f for f in os.listdir(sounds_dir) 
                          if f.endswith(('.wav', '.mp3', '.ogg'))]
            
            for sound_file in sound_files:
                sound_name = os.path.splitext(sound_file)[0]
                sound_path = os.path.join(sounds_dir, sound_file)
                
                try:
                    sound = pygame.mixer.Sound(sound_path)
                    sound.set_volume(self.volume)
                    self.sounds[sound_name] = sound
                    print(f"Loaded sound: {sound_name}")
                except Exception as e:
                    print(f"Failed to load sound {sound_file}: {e}")
        
        print(f"Loaded {len(self.sounds)} sound(s)")
    
    def _create_default_sounds(self):
        """Create default Wall-E sounds using simple tones"""
        if not self.available:
            return
        
        sound_patterns = {
            'startup': [(220, 0.3), (440, 0.3), (660, 0.4), (880, 0.6), (660, 0.3)],
            'curious': [(330, 0.15), (550, 0.15), (440, 0.2), (660, 0.25), (550, 0.2)],
            'happy': [(523, 0.2), (659, 0.2), (784, 0.2), (880, 0.3), (1047, 0.4)],
            'worried': [(440, 0.3), (330, 0.4), (220, 0.5), (165, 0.6)],
            'beep': [(800, 0.15), (0, 0.05), (800, 0.15)],
            'error': [(200, 0.4), (150, 0.4), (100, 0.6)],
            'greeting': [(440, 0.25), (523, 0.25), (659, 0.3), (880, 0.4), (659, 0.2)],
            'excited': [(659, 0.1), (880, 0.1), (1047, 0.1), (1319, 0.2), (1047, 0.1)],
            'sleepy': [(220, 0.5), (165, 0.6), (110, 0.8)]
        }
        
        for sound_name, pattern in sound_patterns.items():
            if sound_name not in self.sounds:
                try:
                    sound = self._generate_tone_sequence(pattern)
                    if sound:
                        self.sounds[sound_name] = sound
                        print(f"Generated sound: {sound_name}")
                except Exception as e:
                    print(f"Failed to generate sound {sound_name}: {e}")
    
    def _generate_tone_sequence(self, pattern):
        """Generate a sequence of tones"""
        try:
            import numpy as np
            
            sample_rate = 44100
            total_duration = sum(duration for freq, duration in pattern)
            total_samples = int(sample_rate * total_duration)
            
            waveform = np.zeros(total_samples, dtype=np.float32)
            
            current_sample = 0
            for frequency, duration in pattern:
                samples = int(sample_rate * duration)
                
                if frequency > 0:
                    t = np.linspace(0, duration, samples, False)
                    wave = np.sin(2 * np.pi * frequency * t)
                    
                    # Add envelope for smoother sound
                    envelope = np.ones_like(wave)
                    fade_samples = min(samples // 20, 2200)
                    if fade_samples > 0:
                        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
                        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
                    
                    wave *= envelope
                else:
                    wave = np.zeros(samples)
                
                end_sample = current_sample + samples
                if end_sample <= total_samples:
                    waveform[current_sample:end_sample] = wave
                
                current_sample = end_sample
            
            # Convert to 16-bit integers and create stereo
            waveform_int = (waveform * 32767 * 0.3).astype(np.int16)
            stereo_waveform = np.zeros((total_samples, 2), dtype=np.int16)
            stereo_waveform[:, 0] = waveform_int
            stereo_waveform[:, 1] = waveform_int
            
            return pygame.sndarray.make_sound(stereo_waveform)
            
        except ImportError:
            print("NumPy not available, using simple tones")
            # Fallback to simple tone generation
            sample_rate = 22050
            total_duration = sum(duration for freq, duration in pattern)
            total_samples = int(sample_rate * total_duration)
            
            import array
            waveform = array.array('h', [0] * total_samples * 2)  # Stereo
            
            current_sample = 0
            for frequency, duration in pattern:
                samples = int(sample_rate * duration)
                
                if frequency > 0:
                    for i in range(samples):
                        sample_value = int(32767 * 0.3 * 
                                         math.sin(2 * math.pi * frequency * i / sample_rate))
                        if current_sample * 2 < len(waveform):
                            waveform[current_sample * 2] = sample_value
                            waveform[current_sample * 2 + 1] = sample_value
                        current_sample += 1
                else:
                    current_sample += samples
            
            return pygame.sndarray.make_sound(waveform)
        except Exception as e:
            print(f"Error generating tone: {e}")
            return None
    
    # Bluetooth management methods
    def scan_bluetooth_speakers(self) -> List[Dict]:
        """Scan for available Bluetooth speakers"""
        return self.bluetooth_manager.scan_devices()
    
    def connect_bluetooth_speaker(self, mac_address: str) -> bool:
        """Connect to a Bluetooth speaker"""
        success = self.bluetooth_manager.connect_device(mac_address)
        if success:
            self.bluetooth_manager.default_speaker_mac = mac_address
            self.bluetooth_manager.save_config()
            if self.connection_status_callback:
                self.connection_status_callback(True, f"Connected to {mac_address}")
        return success
    
    def disconnect_bluetooth_speaker(self, mac_address: str) -> bool:
        """Disconnect from a Bluetooth speaker"""
        success = self.bluetooth_manager.disconnect_device(mac_address)
        if success and self.connection_status_callback:
            self.connection_status_callback(False, f"Disconnected from {mac_address}")
        return success
    
    def get_bluetooth_status(self) -> Dict:
        """Get Bluetooth connection status"""
        status = {
            'default_speaker': self.bluetooth_manager.default_speaker_mac,
            'connected_devices': [],
            'is_connected': False
        }
        
        if self.bluetooth_manager.default_speaker_mac:
            is_connected = self.bluetooth_manager.is_device_connected(
                self.bluetooth_manager.default_speaker_mac)
            status['is_connected'] = is_connected
            if is_connected:
                status['connected_devices'].append(self.bluetooth_manager.default_speaker_mac)
        
        return status
    
    def test_bluetooth_audio(self) -> bool:
        """Test Bluetooth audio output"""
        try:
            self.play_sound('beep', blocking=True)
            return True
        except Exception as e:
            print(f"Bluetooth audio test failed: {e}")
            return False
    
    def play_sound(self, sound_name: str, blocking=False) -> bool:
        """Play a sound effect"""
        if not self.available:
            print(f"Audio not available, cannot play: {sound_name}")
            return False
        
        if sound_name not in self.sounds:
            print(f"Sound not found: {sound_name}")
            return False
        
        try:
            sound = self.sounds[sound_name]
            
            if blocking:
                self.is_playing = True
                channel = sound.play()
                if channel:
                    while channel.get_busy():
                        time.sleep(0.01)
                self.is_playing = False
            else:
                sound.play()
            
            print(f"Playing sound: {sound_name}")
            return True
            
        except Exception as e:
            print(f"Error playing sound {sound_name}: {e}")
            return False
    
    def speak_text(self, text: str, blocking=False):
        """Enhanced text-to-speech"""
        def speak_thread():
            try:
                subprocess.run(['espeak', text], check=True, capture_output=True)
            except:
                print(f"Text-to-speech not available for: {text}")
        
        if blocking:
            speak_thread()
        else:
            thread = threading.Thread(target=speak_thread, daemon=True)
            thread.start()
    
    def play_wall_e_emotion(self, emotion: str):
        """Play appropriate sounds for Wall-E emotions"""
        emotion_sounds = {
            'happy': ['happy'],
            'excited': ['excited', 'beep'],
            'curious': ['curious'],
            'worried': ['worried'],
            'sad': ['worried', 'sleepy'],
            'greeting': ['greeting'],
            'startup': ['startup'],
            'error': ['error'],
            'surprised': ['beep', 'curious'],
            'sleepy': ['sleepy'],
            'content': ['happy', 'sleepy']
        }
        
        if emotion in emotion_sounds:
            sounds_to_play = emotion_sounds[emotion]
            if len(sounds_to_play) == 1:
                self.play_sound(sounds_to_play[0])
            else:
                self.play_sequence(sounds_to_play, delay=0.3)
        else:
            print(f"Unknown emotion: {emotion}")
    
    def play_sequence(self, sound_names, delay=0.5):
        """Play a sequence of sounds with delays"""
        def play_sequence_thread():
            for sound_name in sound_names:
                self.play_sound(sound_name, blocking=True)
                if delay > 0:
                    time.sleep(delay)
        
        if self.available:
            thread = threading.Thread(target=play_sequence_thread, daemon=True)
            thread.start()
    
    def stop_all_sounds(self):
        """Stop all currently playing sounds"""
        if self.available:
            pygame.mixer.stop()
            self.is_playing = False
    
    def set_volume(self, volume: float):
        """Set master volume"""
        self.volume = max(0.0, min(1.0, volume))
        
        for sound in self.sounds.values():
            sound.set_volume(self.volume)
        
        # Also set system volume for Bluetooth
        try:
            volume_percent = int(self.volume * 100)
            subprocess.run(['amixer', 'set', 'Master', f'{volume_percent}%'], 
                          capture_output=True)
        except:
            pass
        
        print(f"Volume set to {self.volume:.1f}")
    
    def get_available_sounds(self):
        """Get list of available sound names"""
        return list(self.sounds.keys())
    
    def set_connection_status_callback(self, callback: Callable):
        """Set callback for Bluetooth connection status changes"""
        self.connection_status_callback = callback
    
    def set_audio_status_callback(self, callback: Callable):
        """Set callback for audio status updates"""
        self.audio_status_callback = callback
    
    def get_audio_info(self) -> Dict:
        """Get comprehensive audio system information"""
        return {
            'available': self.available,
            'volume': self.volume,
            'sounds_loaded': len(self.sounds),
            'sound_names': list(self.sounds.keys()),
            'bluetooth_status': self.get_bluetooth_status(),
            'is_playing': self.is_playing
        }
    
    def cleanup(self):
        """Clean up audio system"""
        if self.available:
            self.stop_all_sounds()
            pygame.mixer.quit()
            print("Audio system cleaned up")

# Backwards compatibility alias
EnhancedAudioSystem = AudioSystem
AUDIO_EOF

echo "✓ Enhanced audio system installed"

echo ""
echo "================================================"
echo "Adding Bluetooth API endpoints to app.py..."
echo "================================================"

# Add Bluetooth API endpoints to app.py
cat >> app.py << 'API_EOF'

# Bluetooth API endpoints
@app.route('/api/bluetooth/status')
def bluetooth_status():
    """Get Bluetooth connection status"""
    try:
        if audio and hasattr(audio, 'get_bluetooth_status'):
            status = audio.get_bluetooth_status()
            return jsonify({
                'success': True,
                'status': status
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Bluetooth not available'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/bluetooth/scan', methods=['POST'])
def bluetooth_scan():
    """Scan for Bluetooth devices"""
    try:
        if audio and hasattr(audio, 'scan_bluetooth_speakers'):
            devices = audio.scan_bluetooth_speakers()
            return jsonify({
                'success': True,
                'devices': devices,
                'message': f'Found {len(devices)} device(s)'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Bluetooth not available',
                'devices': []
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'devices': []
        }), 500

@app.route('/api/bluetooth/connect', methods=['POST'])
def bluetooth_connect():
    """Connect to a Bluetooth device"""
    try:
        if not audio or not hasattr(audio, 'connect_bluetooth_speaker'):
            return jsonify({
                'success': False,
                'message': 'Bluetooth not available'
            }), 500
        
        data = request.get_json()
        mac_address = data.get('mac_address')
        
        if not mac_address:
            return jsonify({
                'success': False,
                'message': 'MAC address required'
            }), 400
        
        success = audio.connect_bluetooth_speaker(mac_address)
        
        if success:
            socketio.emit('bluetooth_status_update', {
                'connected': True,
                'device': mac_address
            })
            
            return jsonify({
                'success': True,
                'message': f'Connected to {mac_address}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to connect to {mac_address}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/bluetooth/disconnect', methods=['POST'])
def bluetooth_disconnect():
    """Disconnect from a Bluetooth device"""
    try:
        if not audio or not hasattr(audio, 'disconnect_bluetooth_speaker'):
            return jsonify({
                'success': False,
                'message': 'Bluetooth not available'
            }), 500
        
        data = request.get_json()
        mac_address = data.get('mac_address')
        
        if not mac_address:
            return jsonify({
                'success': False,
                'message': 'MAC address required'
            }), 400
        
        success = audio.disconnect_bluetooth_speaker(mac_address)
        
        if success:
            socketio.emit('bluetooth_status_update', {
                'connected': False,
                'device': mac_address
            })
            
            return jsonify({
                'success': True,
                'message': f'Disconnected from {mac_address}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to disconnect from {mac_address}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/bluetooth/test', methods=['POST'])
def bluetooth_test():
    """Test Bluetooth audio output"""
    try:
        if audio and hasattr(audio, 'test_bluetooth_audio'):
            success = audio.test_bluetooth_audio()
            return jsonify({
                'success': success,
                'message': 'Audio test completed' if success else 'Audio test failed'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Bluetooth test not available'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/bluetooth/volume', methods=['POST'])
def bluetooth_volume():
    """Set Bluetooth audio volume"""
    try:
        if not audio:
            return jsonify({
                'success': False,
                'message': 'Audio system not available'
            }), 500
        
        data = request.get_json()
        volume = data.get('volume', 0.7)
        
        # Validate volume range
        volume = max(0.0, min(1.0, float(volume)))
        
        audio.set_volume(volume)
        
        socketio.emit('volume_update', {
            'volume': volume
        })
        
        return jsonify({
            'success': True,
            'volume': volume,
            'message': f'Volume set to {int(volume * 100)}%'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
API_EOF

echo "✓ Bluetooth API endpoints added to app.py"

echo ""
echo "================================================"
echo "Creating Bluetooth setup script..."
echo "================================================"

# Create a separate Bluetooth setup script for users
cat > setup_bluetooth_speaker.sh << 'SETUP_EOF'
#!/bin/bash
echo "================================================"
echo "Wall-E Bluetooth Speaker Quick Setup"
echo "================================================"

echo "This script will help you connect a Bluetooth speaker to Wall-E."
echo ""
echo "Before continuing, please:"
echo "1. Turn on your Bluetooth speaker"
echo "2. Put it in pairing/discoverable mode"
echo "3. Make sure it's close to the Raspberry Pi"
echo ""
read -p "Press Enter when ready to continue..."

echo ""
echo "Scanning for Bluetooth devices..."

# Start Bluetooth scan
sudo bluetoothctl scan on &
SCAN_PID=$!

# Show spinner during scan
echo -n "Scanning"
for i in {1..15}; do
    echo -n "."
    sleep 1
done
echo ""

# Stop scan
sudo kill $SCAN_PID 2>/dev/null
echo "scan off" | sudo bluetoothctl

echo ""
echo "Available Bluetooth devices:"
echo "devices" | sudo bluetoothctl | grep Device

echo ""
echo "Enter the MAC address of your Bluetooth speaker"
echo "(Format: XX:XX:XX:XX:XX:XX - example: 12:34:56:78:9A:BC)"
read -p "MAC Address: " SPEAKER_MAC

if [[ $SPEAKER_MAC =~ ^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$ ]]; then
    echo ""
    echo "Connecting to $SPEAKER_MAC..."
    
    # Trust, pair, and connect
    echo "trust $SPEAKER_MAC" | sudo bluetoothctl
    echo "pair $SPEAKER_MAC" | sudo bluetoothctl
    echo "connect $SPEAKER_MAC" | sudo bluetoothctl
    
    sleep 3
    
    # Check if connected
    if echo "info $SPEAKER_MAC" | sudo bluetoothctl | grep -q "Connected: yes"; then
        echo "✓ Successfully connected to Bluetooth speaker!"
        
        # Save configuration
        echo "BLUETOOTH_SPEAKER_MAC=$SPEAKER_MAC" > ~/.walle_bluetooth_config
        echo "✓ Configuration saved"
        
        # Set as default audio output
        pacmd set-default-sink $(pacmd list-sinks | grep -A1 "bluez" | grep "index:" | awk '{print $2}' | head -1) 2>/dev/null
        
        # Test audio
        echo ""
        echo "Testing audio..."
        speaker-test -t sine -f 1000 -l 1 -s 1 2>/dev/null &
        sleep 2
        pkill speaker-test
        
        echo ""
        echo "🎉 Bluetooth speaker setup complete!"
        echo ""
        echo "Your Wall-E will now use this speaker for audio output."
        echo "Restart the Wall-E service to apply changes:"
        echo "  sudo systemctl restart walle-control.service"
        echo ""
        echo "You can also manage Bluetooth speakers through the web interface at:"
        echo "  http://wall-e.local:5000"
        
    else
        echo "❌ Failed to connect to Bluetooth speaker"
        echo "Please try again or check if the speaker is in pairing mode"
    fi
else
    echo "❌ Invalid MAC address format"
    echo "Please run the script again with a valid MAC address"
fi
SETUP_EOF

chmod +x setup_bluetooth_speaker.sh
echo "✓ Created setup_bluetooth_speaker.sh"

echo ""
echo "================================================"
echo "Adding Bluetooth web interface..."
echo "================================================"

# Create a temporary file for the new HTML content
cat > /tmp/bluetooth_panel.html << 'HTML_EOF'
    <!-- Bluetooth Audio Control Panel -->
    <div class="control-panel bluetooth-panel">
        <div class="panel-title">🔊 Bluetooth Audio Control</div>
        
        <!-- Bluetooth Status -->
        <div class="bluetooth-status" id="bluetooth-status">
            <div>
                <span class="bluetooth-icon">📶</span>
                <span class="status-text" id="bluetooth-status-text">Checking connection...</span>
            </div>
            <button class="test-btn" onclick="testBluetoothAudio()" id="test-audio-btn">🔊 Test Audio</button>
        </div>

        <!-- Device Scanner -->
        <div style="text-align: center; margin-bottom: 20px;">
            <button class="scan-btn" onclick="scanBluetoothDevices()" id="scan-btn">
                🔍 Scan for Speakers
            </button>
        </div>

        <!-- Device List -->
        <div class="device-list" id="device-list">
            <div class="loading">No devices found. Click "Scan for Speakers" to search.</div>
        </div>

        <!-- Volume Control -->
        <div class="volume-control">
            <span>🔉</span>
            <input type="range" class="volume-slider" min="0" max="100" value="70" 
                   onchange="setBluetoothVolume(this.value)" id="volume-slider">
            <div class="volume-display" id="volume-display">70%</div>
            <span>🔊</span>
        </div>
    </div>
HTML_EOF

# Insert the Bluetooth panel before the emergency stop button
sed -i '/<button class="emergency-stop"/i\
' templates/index.html

# Read the bluetooth panel content and insert it
sed -i '/<button class="emergency-stop"/e cat /tmp/bluetooth_panel.html' templates/index.html

# Add Bluetooth CSS styles
sed -i '/<\/style>/i\
        /* Bluetooth Audio Control Styles */\
        .bluetooth-panel {\
            background: rgba(255, 255, 255, 0.1);\
            backdrop-filter: blur(10px);\
            border-radius: 15px;\
            padding: 25px;\
            border: 1px solid rgba(255, 255, 255, 0.2);\
            margin-bottom: 20px;\
        }\
\
        .bluetooth-status {\
            display: flex;\
            justify-content: space-between;\
            align-items: center;\
            margin-bottom: 20px;\
            padding: 15px;\
            background: rgba(0, 0, 0, 0.2);\
            border-radius: 10px;\
        }\
\
        .bluetooth-connected {\
            background: rgba(76, 175, 80, 0.2);\
            border: 1px solid #4CAF50;\
        }\
\
        .bluetooth-disconnected {\
            background: rgba(244, 67, 54, 0.2);\
            border: 1px solid #f44336;\
        }\
\
        .device-list {\
            max-height: 200px;\
            overflow-y: auto;\
            margin-bottom: 20px;\
        }\
\
        .device-item {\
            display: flex;\
            justify-content: space-between;\
            align-items: center;\
            padding: 10px;\
            margin-bottom: 10px;\
            background: rgba(255, 255, 255, 0.05);\
            border-radius: 8px;\
            border: 1px solid rgba(255, 255, 255, 0.1);\
        }\
\
        .device-item.connected {\
            background: rgba(76, 175, 80, 0.1);\
            border-color: #4CAF50;\
        }\
\
        .device-info {\
            flex-grow: 1;\
        }\
\
        .device-name {\
            font-weight: bold;\
            margin-bottom: 3px;\
        }\
\
        .device-mac {\
            font-size: 0.8em;\
            opacity: 0.7;\
            font-family: "Courier New", monospace;\
        }\
\
        .device-actions {\
            display: flex;\
            gap: 10px;\
        }\
\
        .scan-btn {\
            background: linear-gradient(45deg, #9C27B0, #7B1FA2);\
            border: none;\
            color: white;\
            padding: 12px 20px;\
            border-radius: 8px;\
            cursor: pointer;\
            font-weight: bold;\
            transition: all 0.3s ease;\
        }\
\
        .scan-btn:hover {\
            transform: translateY(-1px);\
            box-shadow: 0 3px 10px rgba(156, 39, 176, 0.3);\
        }\
\
        .scan-btn:disabled {\
            opacity: 0.5;\
            cursor: not-allowed;\
        }\
\
        .connect-btn {\
            background: linear-gradient(45deg, #4CAF50, #45a049);\
            border: none;\
            color: white;\
            padding: 8px 15px;\
            border-radius: 6px;\
            cursor: pointer;\
            font-size: 0.9em;\
            transition: all 0.3s ease;\
        }\
\
        .disconnect-btn {\
            background: linear-gradient(45deg, #f44336, #d32f2f);\
            border: none;\
            color: white;\
            padding: 8px 15px;\
            border-radius: 6px;\
            cursor: pointer;\
            font-size: 0.9em;\
            transition: all 0.3s ease;\
        }\
\
        .test-btn {\
            background: linear-gradient(45deg, #FF9800, #F57C00);\
            border: none;\
            color: white;\
            padding: 8px 15px;\
            border-radius: 6px;\
            cursor: pointer;\
            font-size: 0.9em;\
            transition: all 0.3s ease;\
        }\
\
        .volume-control {\
            display: flex;\
            align-items: center;\
            gap: 15px;\
            margin-top: 20px;\
        }\
\
        .volume-slider {\
            flex-grow: 1;\
            height: 8px;\
            border-radius: 5px;\
            background: #ddd;\
            outline: none;\
        }\
\
        .volume-display {\
            min-width: 50px;\
            text-align: center;\
            font-weight: bold;\
            color: #FFD700;\
        }\
\
        .loading {\
            text-align: center;\
            padding: 20px;\
            font-style: italic;\
            opacity: 0.7;\
        }\
\
        .bluetooth-icon {\
            font-size: 1.5em;\
            margin-right: 10px;\
        }\
\
        .status-text {\
            font-weight: bold;\
        }' templates/index.html

# Add Bluetooth JavaScript functions
cat > /tmp/bluetooth_js.js << 'JS_EOF'
        // Bluetooth control functions
        let bluetoothDevices = [];
        let currentVolume = 70;
        let isScanning = false;

        // Initialize Bluetooth interface
        function initializeBluetoothInterface() {
            updateBluetoothStatus();
            setInterval(updateBluetoothStatus, 30000);
        }

        // Update Bluetooth connection status
        function updateBluetoothStatus() {
            fetch('/api/bluetooth/status')
                .then(response => response.json())
                .then(data => {
                    const statusElement = document.getElementById('bluetooth-status');
                    const statusText = document.getElementById('bluetooth-status-text');
                    
                    if (data.success && data.status.is_connected) {
                        statusElement.className = 'bluetooth-status bluetooth-connected';
                        statusText.textContent = 'Connected to speaker';
                        if (data.status.default_speaker) {
                            statusText.textContent += ` (${data.status.default_speaker.substring(0, 8)}...)`;
                        }
                    } else {
                        statusElement.className = 'bluetooth-status bluetooth-disconnected';
                        statusText.textContent = 'No Bluetooth speaker connected';
                    }
                })
                .catch(error => {
                    console.error('Error checking Bluetooth status:', error);
                });
        }

        // Scan for Bluetooth devices
        function scanBluetoothDevices() {
            if (isScanning) return;
            
            isScanning = true;
            const scanBtn = document.getElementById('scan-btn');
            const deviceList = document.getElementById('device-list');
            
            scanBtn.disabled = true;
            scanBtn.textContent = '🔍 Scanning...';
            deviceList.innerHTML = '<div class="loading">Scanning for Bluetooth devices... This may take up to 15 seconds.</div>';
            
            fetch('/api/bluetooth/scan', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        bluetoothDevices = data.devices;
                        displayBluetoothDevices(data.devices);
                        addLogEntry(`Found ${data.devices.length} Bluetooth device(s)`);
                    } else {
                        deviceList.innerHTML = '<div class="loading">Failed to scan for devices. Check Bluetooth is enabled.</div>';
                        addLogEntry('Bluetooth scan failed: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Bluetooth scan error:', error);
                    deviceList.innerHTML = '<div class="loading">Network error during scan.</div>';
                    addLogEntry('Bluetooth scan network error', 'error');
                })
                .finally(() => {
                    isScanning = false;
                    scanBtn.disabled = false;
                    scanBtn.textContent = '🔍 Scan for Speakers';
                });
        }

        // Display found Bluetooth devices
        function displayBluetoothDevices(devices) {
            const deviceList = document.getElementById('device-list');
            
            if (devices.length === 0) {
                deviceList.innerHTML = '<div class="loading">No Bluetooth devices found. Make sure your speaker is in pairing mode.</div>';
                return;
            }
            
            deviceList.innerHTML = '';
            
            devices.forEach(device => {
                const deviceItem = document.createElement('div');
                deviceItem.className = 'device-item';
                
                deviceItem.innerHTML = `
                    <div class="device-info">
                        <div class="device-name">${device.name || 'Unknown Device'}</div>
                        <div class="device-mac">${device.mac}</div>
                    </div>
                    <div class="device-actions">
                        <button class="connect-btn" onclick="connectBluetoothDevice('${device.mac}')">
                            Connect
                        </button>
                    </div>
                `;
                
                deviceList.appendChild(deviceItem);
            });
        }

        // Connect to Bluetooth device
        function connectBluetoothDevice(macAddress) {
            const connectBtn = event.target;
            
            connectBtn.disabled = true;
            connectBtn.textContent = 'Connecting...';
            
            fetch('/api/bluetooth/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mac_address: macAddress })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        connectBtn.className = 'disconnect-btn';
                        connectBtn.textContent = 'Disconnect';
                        connectBtn.onclick = () => disconnectBluetoothDevice(macAddress);
                        
                        addLogEntry(`Connected to Bluetooth speaker: ${macAddress}`);
                        updateBluetoothStatus();
                        
                        // Auto-test audio after connection
                        setTimeout(() => testBluetoothAudio(), 2000);
                    } else {
                        connectBtn.disabled = false;
                        connectBtn.textContent = 'Connect';
                        addLogEntry(`Failed to connect to ${macAddress}: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    console.error('Connection error:', error);
                    connectBtn.disabled = false;
                    connectBtn.textContent = 'Connect';
                    addLogEntry(`Network error connecting to ${macAddress}`, 'error');
                });
        }

        // Disconnect from Bluetooth device
        function disconnectBluetoothDevice(macAddress) {
            const disconnectBtn = event.target;
            
            disconnectBtn.disabled = true;
            disconnectBtn.textContent = 'Disconnecting...';
            
            fetch('/api/bluetooth/disconnect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mac_address: macAddress })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        disconnectBtn.className = 'connect-btn';
                        disconnectBtn.textContent = 'Connect';
                        disconnectBtn.onclick = () => connectBluetoothDevice(macAddress);
                        
                        addLogEntry(`Disconnected from Bluetooth speaker: ${macAddress}`);
                        updateBluetoothStatus();
                    } else {
                        addLogEntry(`Failed to disconnect from ${macAddress}: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    console.error('Disconnection error:', error);
                    addLogEntry(`Network error disconnecting from ${macAddress}`, 'error');
                })
                .finally(() => {
                    disconnectBtn.disabled = false;
                });
        }

        // Test Bluetooth audio
        function testBluetoothAudio() {
            const testBtn = document.getElementById('test-audio-btn');
            
            testBtn.disabled = true;
            testBtn.textContent = '🔊 Testing...';
            
            fetch('/api/bluetooth/test', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addLogEntry('Bluetooth audio test successful');
                    } else {
                        addLogEntry('Bluetooth audio test failed: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Audio test error:', error);
                    addLogEntry('Audio test network error', 'error');
                })
                .finally(() => {
                    testBtn.disabled = false;
                    testBtn.textContent = '🔊 Test Audio';
                });
        }

        // Set Bluetooth volume
        function setBluetoothVolume(volume) {
            currentVolume = volume;
            document.getElementById('volume-display').textContent = volume + '%';
            
            fetch('/api/bluetooth/volume', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ volume: parseFloat(volume) / 100 })
            })
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        addLogEntry('Failed to set volume: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Volume control error:', error);
                });
        }
JS_EOF

# Insert the JavaScript before the closing script tag
sed -i '/<\/script>/e cat /tmp/bluetooth_js.js' templates/index.html

# Add the initialization call
sed -i '/document.addEventListener("DOMContentLoaded", function() {/a\
            initializeBluetoothInterface();' templates/index.html

# Clean up temporary files
rm -f /tmp/bluetooth_panel.html /tmp/bluetooth_js.js

echo "✓ Bluetooth web interface added to index.html"

echo ""
echo "================================================"
echo "Updating requirements.txt..."
echo "================================================"

# Add numpy to requirements if not present
if ! grep -q "numpy" requirements.txt; then
    echo "numpy==1.24.3" >> requirements.txt
    echo "✓ Added numpy to requirements.txt"
fi

echo ""
echo "================================================"
echo "Installing Python packages..."
echo "================================================"

# Activate virtual environment and install new packages
source walle-env/bin/activate
pip install --upgrade pip
pip install numpy==1.24.3

echo "✓ Python packages installed"

echo ""
echo "================================================"
echo "Starting Wall-E service..."
echo "================================================"

# Restart PulseAudio to ensure Bluetooth modules are loaded
pulseaudio -k
pulseaudio --start

# Start Wall-E service
sudo systemctl start walle-control.service

# Wait for startup
sleep 5

# Check service status
echo ""
echo "=== Wall-E Service Status ==="
sudo systemctl status walle-control.service --no-pager -l

echo ""
echo "================================================"
echo "Bluetooth Integration Complete! 🎉"
echo "================================================"

# Get IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ Bluetooth audio system has been successfully integrated into Wall-E!"
echo ""
echo "What's been added:"
echo "  ✓ Enhanced audio system with Bluetooth support"
echo "  ✓ Bluetooth management API endpoints"
echo "  ✓ Web interface for Bluetooth control"
echo "  ✓ Auto-reconnection functionality"
echo "  ✓ Volume control and audio testing"
echo ""
echo "How to connect a Bluetooth speaker:"
echo ""
echo "Option 1 - Use the Web Interface:"
echo "  1. Go to http://wall-e.local:5000 or http://$IP_ADDRESS:5000"
echo "  2. Look for the '🔊 Bluetooth Audio Control' panel"
echo "  3. Click 'Scan for Speakers'"
echo "  4. Connect to your speaker from the list"
echo ""
echo "Option 2 - Use the Setup Script:"
echo "  1. Put your Bluetooth speaker in pairing mode"
echo "  2. Run: ./setup_bluetooth_speaker.sh"
echo "  3. Follow the prompts"
echo ""
echo "Useful commands:"
echo "  Restart Wall-E:   sudo systemctl restart walle-control.service"
echo "  Check logs:       sudo journalctl -u walle-control.service -f"
echo "  Test Bluetooth:   ./setup_bluetooth_speaker.sh"
echo ""
echo "Your Wall-E now has professional-quality audio through Bluetooth! 🤖🔊"
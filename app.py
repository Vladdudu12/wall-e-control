#!/usr/bin/env python3
"""
Wall-E Control System - Flask Web Application
Author: Vladdudu12
Repository: https://github.com/Vladdudu12/wall-e-control

Main web server for controlling Wall-E robot via web interface.
Includes integrated Bluetooth audio support.
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import time
import threading
from datetime import datetime
import requests
import socket
import os
from threading import Thread

ESP32_CAM_IP = None  # Will be auto-discovered
ESP32_CAM_PORT = 80
CAMERA_SCAN_RANGE = "192.168.50"  # Adjust to your network range

# Wall-E modules
try:
    from modules.arduino_controller import ArduinoController
    from modules.audio_system import AudioSystem
    from modules.display_controller import EnhancedDisplayController
    from modules.battery_monitor import BatteryMonitor
except ImportError as e:
    print(f"Warning: Could not import module: {e}")
    print("Running in development mode without hardware")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'walle-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global Wall-E state
walle_state = {
    'mode': 'idle',
    'battery_level': 100,
    'sensors': {
        'front': 0,
        'left': 0,
        'right': 0
    },
    'servo_positions': {
        'head_pan': 90,
        'head_tilt': 90,
        'left_arm': 90,
        'right_arm': 90
    },
    'motors': {
        'left_speed': 0,
        'right_speed': 0
    },
    'is_charging': True,
    'solar_power': 1.2,
    'time_to_full': 2.5,
    'connected': False,
    'last_update': datetime.now().isoformat()
}

# Initialize hardware controllers
arduino = None
audio = None
display = None
battery = None


# ESP32-CAM Discovery and Connection Functions
def discover_esp32_cam():
    """Enhanced ESP32-CAM discovery for Wall-E Access Point network"""
    global ESP32_CAM_IP

    print("🔍 Scanning for ESP32-CAM on Wall-E Access Point...")

    # In AP mode, we know the network range
    network_base = "192.168.4"

    # Try common IP addresses first (faster discovery)
    common_ips = [
        "192.168.4.100",  # Most common DHCP assignment
        "192.168.4.101",
        "192.168.4.102",
        "192.168.4.103",
        "192.168.4.10",
        "192.168.4.20",
        "192.168.4.50"
    ]

    print("Testing common ESP32-CAM IP addresses...")
    for test_ip in common_ips:
        try:
            print(f"Testing {test_ip}...")
            response = requests.get(f"http://{test_ip}/status", timeout=3)

            if response.status_code == 200:
                data = response.json()
                # Enhanced detection - check for ESP32-CAM specific fields
                if ('camera' in data and 'Wall-E' in str(data)) or \
                        ('ESP32' in str(data)) or \
                        ('version' in data and 'Adaptive' in str(data)):
                    print(f"✅ Found ESP32-CAM at {test_ip}")
                    print(f"Camera details: {data}")
                    ESP32_CAM_IP = test_ip
                    return test_ip

        except Exception as e:
            # Silently continue to next IP
            continue

    # If not found in common IPs, scan full DHCP range
    print("Scanning full DHCP range 192.168.4.10-50...")
    dhcp_range = range(10, 51)  # 192.168.4.10 to 192.168.4.50

    for i in dhcp_range:
        try:
            test_ip = f"{network_base}.{i}"

            # Skip IPs we already tested
            if test_ip in common_ips:
                continue

            print(f"Testing {test_ip}...")

            response = requests.get(f"http://{test_ip}/status", timeout=2)

            if response.status_code == 200:
                data = response.json()
                # Check if it's our ESP32-CAM
                if ('camera' in data and 'Wall-E' in str(data)) or \
                        ('ESP32' in str(data)) or \
                        ('version' in data and 'Adaptive' in str(data)):
                    print(f"✅ Found ESP32-CAM at {test_ip}")
                    print(f"Camera details: {data}")
                    ESP32_CAM_IP = test_ip
                    return test_ip

        except:
            continue

    print("❌ ESP32-CAM not found on Wall-E network")
    return None


def check_camera_connection():
    """Enhanced camera connection check"""
    global ESP32_CAM_IP

    if not ESP32_CAM_IP:
        return False

    try:
        print(f"Testing camera connection to {ESP32_CAM_IP}...")
        response = requests.get(f"http://{ESP32_CAM_IP}/status", timeout=5)

        if response.status_code == 200:
            print(f"✅ Camera at {ESP32_CAM_IP} is responding")
            return True
        else:
            print(f"❌ Camera at {ESP32_CAM_IP} returned status {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print(f"❌ Camera connection timeout to {ESP32_CAM_IP}")
        return False
    except Exception as e:
        print(f"❌ Camera connection error to {ESP32_CAM_IP}: {e}")
        return False


def initialize_hardware():
    """Initialize all Wall-E hardware components"""
    global arduino, audio, display, battery

    try:
        # Initialize Arduino communication
        arduino = ArduinoController()
        walle_state['connected'] = arduino.is_connected()
        print("✓ Arduino controller initialized")

        os.makedirs("static/captures", exist_ok=True)

    except Exception as e:
        print(f"✗ Arduino controller failed: {e}")

    try:
        # Initialize audio system with Bluetooth support
        audio = AudioSystem()
        print("✓ Audio system initialized")

        # Set up Bluetooth status callbacks
        if hasattr(audio, 'set_connection_status_callback'):
            audio.set_connection_status_callback(bluetooth_status_callback)

    except Exception as e:
        print(f"✗ Audio system failed: {e}")

    try:
        # Initialize OLED display
        display = EnhancedDisplayController(rotation=270)
        print("✓ Display controller initialized")
    except Exception as e:
        print(f"✗ Display controller failed: {e}")

    try:
        # Initialize battery monitor
        battery = BatteryMonitor()
        print("✓ Battery monitor initialized")

        # Set up battery callbacks
        battery.set_low_battery_callback(low_battery_callback)
        battery.set_critical_battery_callback(critical_battery_callback)

    except Exception as e:
        print(f"✗ Battery monitor failed: {e}")

    try:
        # Create captures directory
        os.makedirs("static/captures", exist_ok=True)

        # Start camera discovery thread
        camera_thread = Thread(target=camera_monitor_thread, daemon=True)
        camera_thread.start()

        # Try initial discovery
        discover_esp32_cam()
        print("✓ Camera discovery initialized")

    except Exception as e:
        print(f"✗ Camera discovery failed: {e}")


def bluetooth_status_callback(connected, message):
    """Callback for Bluetooth connection status changes"""
    socketio.emit('bluetooth_status_update', {
        'connected': connected,
        'message': message
    })


def low_battery_callback(percentage):
    """Callback for low battery warning"""
    socketio.emit('battery_warning', {
        'level': 'low',
        'percentage': percentage,
        'message': f'Low battery: {percentage}%'
    })

    if audio:
        audio.play_wall_e_emotion('worried')


def critical_battery_callback(percentage):
    """Callback for critical battery warning"""
    socketio.emit('battery_warning', {
        'level': 'critical',
        'percentage': percentage,
        'message': f'Critical battery: {percentage}%! Please charge immediately.'
    })

    if audio:
        audio.play_wall_e_emotion('error')


# Main routes
@app.route('/')
def index():
    """Main Wall-E control interface"""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current Wall-E status"""
    # Update connection status
    if arduino:
        walle_state['connected'] = arduino.is_connected()

    # Add audio system info
    if audio and hasattr(audio, 'get_audio_info'):
        walle_state['audio_info'] = audio.get_audio_info()

    return jsonify(walle_state)


@app.route('/api/command', methods=['POST'])
def send_command():
    """Send command to Wall-E"""
    try:
        data = request.get_json()
        command = data.get('command')
        params = data.get('params', {})

        result = process_command(command, params)

        # Update state and broadcast to all clients
        walle_state['last_update'] = datetime.now().isoformat()
        socketio.emit('status_update', walle_state)

        return jsonify({
            'success': True,
            'result': result,
            'message': f"Command '{command}' executed successfully"
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': "Command execution failed"
        }), 500


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


# Audio control endpoints
@app.route('/api/audio/play', methods=['POST'])
def play_audio():
    """Play a specific sound"""
    try:
        data = request.get_json()
        sound_name = data.get('sound')

        if not sound_name:
            return jsonify({
                'success': False,
                'message': 'Sound name required'
            }), 400

        if audio:
            success = audio.play_sound(sound_name)
            return jsonify({
                'success': success,
                'message': f'Playing {sound_name}' if success else f'Failed to play {sound_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Audio system not available'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/audio/emotion', methods=['POST'])
def play_emotion():
    """Play Wall-E emotion sound"""
    try:
        data = request.get_json()
        emotion = data.get('emotion')

        if not emotion:
            return jsonify({
                'success': False,
                'message': 'Emotion required'
            }), 400

        if audio and hasattr(audio, 'play_wall_e_emotion'):
            audio.play_wall_e_emotion(emotion)
            return jsonify({
                'success': True,
                'message': f'Playing {emotion} emotion'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Audio system not available'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/audio/speak', methods=['POST'])
def speak_text():
    """Text-to-speech"""
    try:
        data = request.get_json()
        text = data.get('text')

        if not text:
            return jsonify({
                'success': False,
                'message': 'Text required'
            }), 400

        if audio and hasattr(audio, 'speak_text'):
            audio.speak_text(text)
            return jsonify({
                'success': True,
                'message': f'Speaking: {text}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Text-to-speech not available'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/audio/sounds')
def get_available_sounds():
    """Get list of available sounds"""
    try:
        if audio and hasattr(audio, 'get_available_sounds'):
            sounds = audio.get_available_sounds()
            return jsonify({
                'success': True,
                'sounds': sounds
            })
        else:
            return jsonify({
                'success': False,
                'sounds': [],
                'message': 'Audio system not available'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'sounds': [],
            'message': str(e)
        }), 500


@app.route('/api/network/ap_status')
def ap_status():
    """Get Access Point status"""
    try:
        import subprocess

        # Check if hostapd is running
        result = subprocess.run(['systemctl', 'is-active', 'hostapd'],
                                capture_output=True, text=True)
        hostapd_status = result.stdout.strip()

        # Check connected clients
        try:
            with open('/var/lib/dhcp/dhcpd.leases', 'r') as f:
                leases = f.read()
            client_count = leases.count('binding state active')
        except:
            client_count = 0

        # Get interface info
        result = subprocess.run(['ip', 'addr', 'show', 'wlan0'],
                                capture_output=True, text=True)
        wlan0_info = result.stdout

        return jsonify({
            'success': True,
            'ap_active': hostapd_status == 'active',
            'ssid': 'Wall-E-Robot',
            'ip': '192.168.4.1',
            'connected_clients': client_count,
            'interface_info': wlan0_info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/camera/status')
def camera_status():
    """Get camera connection status with enhanced discovery"""
    try:
        print("📷 Camera status requested...")

        if not ESP32_CAM_IP:
            print("No camera IP set, attempting discovery...")
            discover_esp32_cam()

        if ESP32_CAM_IP and check_camera_connection():
            try:
                # Get camera details
                response = requests.get(f"http://{ESP32_CAM_IP}/status", timeout=5)
                cam_data = response.json()

                print(f"✅ Camera connected at {ESP32_CAM_IP}")

                return jsonify({
                    'success': True,
                    'connected': True,
                    'ip': ESP32_CAM_IP,
                    'stream_url': f"http://{ESP32_CAM_IP}/stream",
                    'capture_url': f"http://{ESP32_CAM_IP}/capture",
                    'details': cam_data
                })

            except Exception as e:
                print(f"Error getting camera details: {e}")
                # Return basic connection info even if details fail
                return jsonify({
                    'success': True,
                    'connected': True,
                    'ip': ESP32_CAM_IP,
                    'stream_url': f"http://{ESP32_CAM_IP}/stream",
                    'capture_url': f"http://{ESP32_CAM_IP}/capture",
                    'details': {'error': str(e)}
                })
        else:
            print("❌ Camera not found or not responding")
            return jsonify({
                'success': False,
                'connected': False,
                'message': 'ESP32-CAM not found or not responding on Wall-E network'
            })

    except Exception as e:
        error_msg = str(e)
        print(f"Camera status error: {error_msg}")
        return jsonify({
            'success': False,
            'connected': False,
            'message': error_msg
        })


@app.route('/api/camera/discover', methods=['POST'])
def discover_camera():
    """Manually trigger camera discovery"""
    try:
        discovered_ip = discover_esp32_cam()

        if discovered_ip:
            return jsonify({
                'success': True,
                'ip': discovered_ip,
                'message': f'Camera found at {discovered_ip}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No ESP32-CAM found on network'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/camera/capture', methods=['POST'])
def capture_photo():
    """Capture a photo from ESP32-CAM"""
    try:
        if not ESP32_CAM_IP:
            return jsonify({
                'success': False,
                'message': 'Camera not connected'
            })

        # Trigger capture and get image
        response = requests.get(f"http://{ESP32_CAM_IP}/capture", timeout=10)

        if response.status_code == 200:
            # Save image with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"walle_capture_{timestamp}.jpg"

            # Create captures directory if it doesn't exist
            captures_dir = "static/captures"
            os.makedirs(captures_dir, exist_ok=True)

            filepath = os.path.join(captures_dir, filename)

            with open(filepath, 'wb') as f:
                f.write(response.content)

            return jsonify({
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'url': f'/static/captures/{filename}',
                'message': 'Photo captured successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to capture photo'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/camera/led', methods=['POST'])
def control_camera_led():
    """Control ESP32-CAM LED"""
    try:
        if not ESP32_CAM_IP:
            return jsonify({
                'success': False,
                'message': 'Camera not connected'
            })

        data = request.get_json()
        state = data.get('state', 'off')  # on/off

        response = requests.get(f"http://{ESP32_CAM_IP}/led?state={state}", timeout=10)

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'state': state,
                'message': f'LED turned {state}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to control LED'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/camera/settings', methods=['GET', 'POST'])
def camera_settings():
    """Get or update camera settings"""
    try:
        if not ESP32_CAM_IP:
            return jsonify({
                'success': False,
                'message': 'Camera not connected'
            })

        if request.method == 'GET':
            # Get current settings
            response = requests.get(f"http://{ESP32_CAM_IP}/settings", timeout=10)

            if response.status_code == 200:
                settings = response.json()
                return jsonify({
                    'success': True,
                    'settings': settings
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to get camera settings'
                })

        elif request.method == 'POST':
            # Update settings (if ESP32-CAM supports it)
            data = request.get_json()
            # This would require additional ESP32-CAM endpoints for setting changes
            return jsonify({
                'success': True,
                'message': 'Settings update feature coming soon'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/camera/debug')
def camera_debug():
    """Debug camera connection issues"""
    try:
        debug_info = {
            'current_camera_ip': ESP32_CAM_IP,
            'wall_e_ip': '192.168.4.1',
            'network_range': '192.168.4.x',
            'scan_results': []
        }

        # Test a few IPs to see what's responding
        test_ips = ["192.168.4.100", "192.168.4.101", "192.168.4.102"]

        for ip in test_ips:
            try:
                response = requests.get(f"http://{ip}/status", timeout=2)
                debug_info['scan_results'].append({
                    'ip': ip,
                    'status': 'responding',
                    'http_code': response.status_code,
                    'content': response.text[:200] if response.text else 'No content'
                })
            except Exception as e:
                debug_info['scan_results'].append({
                    'ip': ip,
                    'status': 'not_responding',
                    'error': str(e)
                })

        return jsonify({
            'success': True,
            'debug_info': debug_info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

# Background monitoring thread
def camera_monitor_thread():
    """Enhanced camera monitoring with better logging"""
    global ESP32_CAM_IP

    while True:
        try:
            # Try to discover camera if not found
            if not ESP32_CAM_IP:
                print("🔍 Periodic camera discovery...")
                discover_esp32_cam()

            # Check connection if IP is known
            if ESP32_CAM_IP:
                connected = check_camera_connection()

                # Broadcast camera status to web clients
                socketio.emit('camera_status_update', {
                    'connected': connected,
                    'ip': ESP32_CAM_IP if connected else None,
                    'stream_url': f"http://{ESP32_CAM_IP}/stream" if connected else None
                })

                # If disconnected, clear IP to trigger rediscovery
                if not connected:
                    print(f"❌ Lost connection to ESP32-CAM at {ESP32_CAM_IP}")
                    ESP32_CAM_IP = None
                else:
                    print(f"✅ Camera monitor: ESP32-CAM online at {ESP32_CAM_IP}")

        except Exception as e:
            print(f"Camera monitor error: {e}")

        time.sleep(30)  # Check every 30 seconds


def process_command(command, params):
    """Process Wall-E commands"""
    global walle_state

    if command == 'wake_up':
        walle_state['mode'] = 'greeting'
        if arduino:
            arduino.send_command('w')
        if audio:
            audio.play_wall_e_emotion('startup')
        return "Wall-E is waking up!"

    elif command == 'explore':
        walle_state['mode'] = 'exploring'
        if arduino:
            arduino.send_command('e')
        if audio:
            audio.play_wall_e_emotion('curious')
        return "Wall-E is exploring!"

    elif command == 'greeting':
        walle_state['mode'] = 'greeting'
        if arduino:
            arduino.send_command('g')
        if audio:
            audio.play_wall_e_emotion('greeting')
        return "Wall-E says hello!"

    elif command == 'stop':
        walle_state['mode'] = 'idle'
        walle_state['motors']['left_speed'] = 0
        walle_state['motors']['right_speed'] = 0
        if arduino:
            arduino.stop_all()
        if audio:
            audio.play_sound('beep')
        return "Wall-E stopped"

    elif command == 'move':
        direction = params.get('direction')
        walle_state['mode'] = 'moving'

        # Map directions to motor speeds
        speed = 150  # Default speed
        if direction == 'forward':
            walle_state['motors']['left_speed'] = speed
            walle_state['motors']['right_speed'] = speed
            if arduino:
                arduino.set_motor_speeds(speed, speed)
        elif direction == 'backward':
            walle_state['motors']['left_speed'] = -speed
            walle_state['motors']['right_speed'] = -speed
            if arduino:
                arduino.set_motor_speeds(-speed, -speed)
        elif direction == 'left':
            walle_state['motors']['left_speed'] = -speed // 2
            walle_state['motors']['right_speed'] = speed // 2
            if arduino:
                arduino.set_motor_speeds(-speed // 2, speed // 2)
        elif direction == 'right':
            walle_state['motors']['left_speed'] = speed // 2
            walle_state['motors']['right_speed'] = -speed // 2
            if arduino:
                arduino.set_motor_speeds(speed // 2, -speed // 2)

        return f"Moving {direction}"

    elif command == 'servo':
        servo = params.get('servo')
        angle = params.get('angle', 90)
        if arduino:
            arduino.set_servo(servo, angle)
        walle_state['servo_positions'][servo] = angle
        return f"Set {servo} to {angle}°"

    elif command == 'sound':
        sound = params.get('sound')
        if audio:
            if hasattr(audio, 'play_wall_e_emotion') and sound in ['happy', 'sad', 'curious', 'worried', 'excited',
                                                                   'greeting']:
                audio.play_wall_e_emotion(sound)
            else:
                audio.play_sound(sound)
        return f"Playing sound: {sound}"

    else:
        raise ValueError(f"Unknown command: {command}")


# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('status_update', walle_state)

    # Send initial Bluetooth status if available
    if audio and hasattr(audio, 'get_bluetooth_status'):
        bluetooth_status = audio.get_bluetooth_status()
        emit('bluetooth_status_update', bluetooth_status)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")


@socketio.on('manual_control')
def handle_manual_control(data):
    """Handle real-time manual control"""
    try:
        command = data.get('command')
        value = data.get('value', 0)

        if command == 'motor_control':
            left_speed = data.get('left_speed', 0)
            right_speed = data.get('right_speed', 0)

            if arduino:
                arduino.set_motor_speeds(left_speed, right_speed)

            walle_state['motors']['left_speed'] = left_speed
            walle_state['motors']['right_speed'] = right_speed

        elif command.startswith('servo_'):
            servo_name = command.replace('servo_', '')
            if arduino:
                arduino.set_servo(servo_name, value)
            walle_state['servo_positions'][servo_name] = value

        elif command == 'emergency_stop':
            walle_state['mode'] = 'idle'
            walle_state['motors']['left_speed'] = 0
            walle_state['motors']['right_speed'] = 0
            if arduino:
                arduino.stop_all()
            if audio:
                audio.play_wall_e_emotion('worried')

        # Broadcast update to all clients
        emit('status_update', walle_state, broadcast=True)

    except Exception as e:
        emit('error', {'message': str(e)})


def sensor_update_thread():
    """Background thread to update sensor readings"""
    while True:
        try:
            if arduino and arduino.is_connected():
                # Get sensor readings from Arduino
                sensors = arduino.get_sensor_readings()
                walle_state['sensors'].update(sensors)
                walle_state['connected'] = True
            else:
                walle_state['connected'] = False

            # Update battery level
            if battery:
                battery_status = battery.get_battery_status()
                walle_state['battery_level'] = battery_status['percentage']
                walle_state['battery_voltage'] = battery_status['voltage']
                walle_state['battery_status'] = battery_status['status']

            # Update display
            if display and display.available:
                display.update_status(walle_state)

            # Broadcast to all connected clients
            walle_state['last_update'] = datetime.now().isoformat()
            socketio.emit('status_update', walle_state)

        except Exception as e:
            print(f"Sensor update error: {e}")

        time.sleep(0.5)  # Update every 500ms


def play_startup_sequence():
    """Play Wall-E startup sequence"""
    time.sleep(2)  # Wait for system to stabilize

    if audio:
        audio.play_wall_e_emotion('startup')

    if display and display.available:
        display.show_message("WALL-E", "ONLINE", duration=3)


def cleanup_on_exit():
    """Clean up resources on exit"""
    print("Cleaning up Wall-E resources...")

    if arduino:
        arduino.close()

    if audio and hasattr(audio, 'cleanup'):
        audio.cleanup()

    if display and hasattr(display, 'cleanup'):
        display.cleanup()

    if battery and hasattr(battery, 'cleanup'):
        battery.cleanup()


if __name__ == '__main__':
    print("=== Wall-E Control System Starting ===")
    print("Repository: https://github.com/Vladdudu12/wall-e-control")
    print(f"Access at: http://wall-e.local:5000")
    print("=" * 40)

    # Initialize hardware
    initialize_hardware()

    # Start background threads
    sensor_thread = threading.Thread(target=sensor_update_thread, daemon=True)
    sensor_thread.start()

    # Play startup sequence
    startup_thread = threading.Thread(target=play_startup_sequence, daemon=True)
    startup_thread.start()

    # Start web server
    try:
        socketio.run(app,
                     host='0.0.0.0',  # Allow external connections
                     port=5000,
                     debug=False,  # Set to True for development
                     allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\nShutting down Wall-E control system...")
        cleanup_on_exit()
        print("Wall-E offline. Goodbye!")
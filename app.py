#!/usr/bin/env python3
"""
Wall-E Control System - Flask Web Application
Author: Vladdudu12
Repository: https://github.com/Vladdudu12/wall-e-control

Main web server for controlling Wall-E robot via web interface.
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import time
import threading
from datetime import datetime

# Wall-E modules (we'll create these)
try:
    from modules.arduino_controller import ArduinoController
    from modules.audio_system import AudioSystem
    from modules.display_controller import DisplayController
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
    'connected': False,
    'last_update': datetime.now().isoformat()
}

# Initialize hardware controllers
arduino = None
audio = None
display = None
battery = None

def initialize_hardware():
    """Initialize all Wall-E hardware components"""
    global arduino, audio, display, battery
    
    try:
        # Initialize Arduino communication
        arduino = ArduinoController()
        print("✓ Arduino controller initialized")
    except Exception as e:
        print(f"✗ Arduino controller failed: {e}")
    
    try:
        # Initialize audio system
        audio = AudioSystem()
        print("✓ Audio system initialized")
    except Exception as e:
        print(f"✗ Audio system failed: {e}")
    
    try:
        # Initialize OLED display
        display = DisplayController()
        print("✓ Display controller initialized")
    except Exception as e:
        print(f"✗ Display controller failed: {e}")
    
    try:
        # Initialize battery monitor
        battery = BatteryMonitor()
        print("✓ Battery monitor initialized")
    except Exception as e:
        print(f"✗ Battery monitor failed: {e}")

@app.route('/')
def index():
    """Main Wall-E control interface"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current Wall-E status"""
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

def process_command(command, params):
    """Process Wall-E commands"""
    global walle_state
    
    if command == 'wake_up':
        walle_state['mode'] = 'greeting'
        if arduino:
            arduino.send_command('w')
        if audio:
            audio.play_sound('startup')
        return "Wall-E is waking up!"
    
    elif command == 'explore':
        walle_state['mode'] = 'exploring'
        if arduino:
            arduino.send_command('e')
        if audio:
            audio.play_sound('curious')
        return "Wall-E is exploring!"
    
    elif command == 'stop':
        walle_state['mode'] = 'idle'
        if arduino:
            arduino.send_command('s')
        return "Wall-E stopped"
    
    elif command == 'move':
        direction = params.get('direction')
        if arduino:
            arduino.send_command(direction.upper())
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
                walle_state['battery_level'] = battery.get_battery_percentage()
            
            # Update display
            if display:
                display.update_status(walle_state)
            
            # Broadcast to all connected clients
            walle_state['last_update'] = datetime.now().isoformat()
            socketio.emit('status_update', walle_state)
            
        except Exception as e:
            print(f"Sensor update error: {e}")
        
        time.sleep(0.5)  # Update every 500ms

def play_startup_sequence():
    """Play Wall-E startup sequence"""
    if audio:
        time.sleep(1)
        audio.play_sound('startup')
    
    if display:
        display.show_message("WALL-E", "ONLINE")

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
                    debug=False,     # Set to True for development
                    allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\nShutting down Wall-E control system...")
        if arduino:
            arduino.close()
        print("Wall-E offline. Goodbye!")
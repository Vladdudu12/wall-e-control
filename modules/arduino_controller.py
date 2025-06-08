#!/usr/bin/env python3
"""
Arduino Controller Module for Wall-E
Handles serial communication with Arduino for motor, servo, and sensor control
"""

import serial
import time
import json
import threading
from typing import Dict, Optional, Tuple

class ArduinoController:
    def __init__(self, port='/dev/ttyACM0', baudrate=9600, timeout=2):
        """
        Initialize Arduino controller
        
        Args:
            port: Serial port (usually /dev/ttyACM0 or /dev/ttyUSB0)
            baudrate: Communication speed (must match Arduino)
            timeout: Serial timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None
        self.connected = False
        self.last_sensor_reading = {'front': 0, 'left': 0, 'right': 0}
        self.response_buffer = []
        
        # Try to connect
        self.connect()
        
        # Start background thread for reading responses
        if self.connected:
            self.read_thread = threading.Thread(target=self._read_responses, daemon=True)
            self.read_thread.start()
    
    def connect(self) -> bool:
        """
        Establish serial connection with Arduino
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Try common Arduino ports
            ports_to_try = ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyACM1']
            
            for port in ports_to_try:
                try:
                    print(f"Trying to connect to Arduino on {port}...")
                    self.serial_connection = serial.Serial(
                        port=port,
                        baudrate=self.baudrate,
                        timeout=self.timeout
                    )
                    time.sleep(2)  # Wait for Arduino to reset
                    
                    # Test connection
                    self.serial_connection.write(b'r\n')  # Send reset command
                    time.sleep(0.5)
                    
                    self.port = port
                    self.connected = True
                    print(f"✓ Arduino connected on {port}")
                    return True
                    
                except serial.SerialException:
                    continue
            
            print("✗ Could not connect to Arduino on any port")
            return False
            
        except Exception as e:
            print(f"✗ Arduino connection error: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.connected = False
        print("Arduino disconnected")
    
    def is_connected(self) -> bool:
        """Check if Arduino is connected"""
        return self.connected and self.serial_connection and self.serial_connection.is_open
    
    def send_command(self, command: str) -> bool:
        """
        Send command to Arduino
        
        Args:
            command: Single character command
            
        Returns:
            bool: True if sent successfully
        """
        if not self.is_connected():
            print("Arduino not connected")
            return False
        
        try:
            command_str = f"{command}\n"
            self.serial_connection.write(command_str.encode())
            print(f"Sent to Arduino: {command}")
            return True
            
        except Exception as e:
            print(f"Error sending command: {e}")
            self.connected = False
            return False
    
    def set_servo(self, servo_name: str, angle: int) -> bool:
        """
        Set servo position
        
        Args:
            servo_name: Name of servo (head_pan, head_tilt, left_arm, right_arm)
            angle: Angle in degrees (0-180)
            
        Returns:
            bool: True if sent successfully
        """
        if not self.is_connected():
            return False
        
        # Map servo names to channels
        servo_map = {
            'head_pan': 0,
            'head_tilt': 1,
            'left_arm': 2,
            'right_arm': 3
        }
        
        if servo_name not in servo_map:
            print(f"Unknown servo: {servo_name}")
            return False
        
        channel = servo_map[servo_name]
        angle = max(0, min(180, angle))  # Clamp to valid range
        
        try:
            # Send servo command: "SERVO,channel,angle"
            command = f"SERVO,{channel},{angle}\n"
            self.serial_connection.write(command.encode())
            print(f"Set {servo_name} (ch{channel}) to {angle}°")
            return True
            
        except Exception as e:
            print(f"Error setting servo: {e}")
            return False
    
    def set_motor_speeds(self, left_speed: int, right_speed: int) -> bool:
        """
        Set motor speeds
        
        Args:
            left_speed: Left motor speed (-255 to 255)
            right_speed: Right motor speed (-255 to 255)
            
        Returns:
            bool: True if sent successfully
        """
        if not self.is_connected():
            return False
        
        # Clamp speeds to valid range
        left_speed = max(-255, min(255, left_speed))
        right_speed = max(-255, min(255, right_speed))
        
        try:
            command = f"MOTOR,{left_speed},{right_speed}\n"
            self.serial_connection.write(command.encode())
            print(f"Set motors: L={left_speed}, R={right_speed}")
            return True
            
        except Exception as e:
            print(f"Error setting motors: {e}")
            return False
    
    def get_sensor_readings(self) -> Dict[str, float]:
        """
        Get latest sensor readings
        
        Returns:
            dict: Sensor distances in cm
        """
        if not self.is_connected():
            return {'front': 0, 'left': 0, 'right': 0}
        
        try:
            # Request sensor reading
            self.serial_connection.write(b"SENSORS\n")
            return self.last_sensor_reading.copy()
            
        except Exception as e:
            print(f"Error reading sensors: {e}")
            return {'front': 0, 'left': 0, 'right': 0}
    
    def _read_responses(self):
        """Background thread to read Arduino responses"""
        while self.connected and self.is_connected():
            try:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode().strip()
                    if line:
                        self._parse_response(line)
                        
            except Exception as e:
                print(f"Error reading Arduino response: {e}")
                self.connected = False
                break
            
            time.sleep(0.1)
    
    def _parse_response(self, response: str):
        """Parse responses from Arduino"""
        try:
            if response.startswith("SENSORS:"):
                # Parse sensor data: "SENSORS:front,left,right"
                data_part = response.split(":", 1)[1]
                values = data_part.split(",")
                
                if len(values) >= 3:
                    self.last_sensor_reading = {
                        'front': float(values[0]),
                        'left': float(values[1]),
                        'right': float(values[2])
                    }
                    
            elif response.startswith("STATUS:"):
                # Parse status updates
                print(f"Arduino status: {response}")
                
            elif response.startswith("ERROR:"):
                # Handle errors
                print(f"Arduino error: {response}")
                
            else:
                # General Arduino output
                print(f"Arduino: {response}")
                
        except Exception as e:
            print(f"Error parsing Arduino response: {e}")
    
    def reset_arduino(self) -> bool:
        """Reset Arduino to neutral state"""
        return self.send_command('r')
    
    def stop_all(self) -> bool:
        """Emergency stop - stop all motors and return to neutral"""
        return self.send_command('x')
    
    def close(self):
        """Clean shutdown"""
        if self.is_connected():
            self.stop_all()
            time.sleep(0.5)
        self.disconnect()

# Test function for standalone testing
def test_arduino_controller():
    """Test the Arduino controller functionality"""
    print("Testing Arduino Controller...")
    
    controller = ArduinoController()
    
    if not controller.is_connected():
        print("Could not connect to Arduino for testing")
        return
    
    print("Testing basic commands...")
    controller.send_command('w')  # Wake up
    time.sleep(2)
    
    print("Testing servo control...")
    controller.set_servo('head_pan', 45)
    time.sleep(1)
    controller.set_servo('head_pan', 135)
    time.sleep(1)
    controller.set_servo('head_pan', 90)
    
    print("Testing motor control...")
    controller.set_motor_speeds(100, 100)
    time.sleep(1)
    controller.set_motor_speeds(0, 0)
    
    print("Testing sensor readings...")
    for i in range(5):
        sensors = controller.get_sensor_readings()
        print(f"Sensors: {sensors}")
        time.sleep(1)
    
    controller.close()
    print("Arduino controller test complete")

if __name__ == "__main__":
    test_arduino_controller()
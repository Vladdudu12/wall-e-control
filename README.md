# Wall-E Robot Control System

A comprehensive web-based control system for Wall-E robot built with Raspberry Pi and Arduino.

## Features
- 🎮 Web-based remote control interface
- 🤖 Real-time servo and motor control
- 📊 Live sensor monitoring
- 🔊 Audio feedback system
- 📱 Mobile-friendly responsive design
- 🔋 Battery level monitoring

## Hardware Requirements
- Raspberry Pi Zero 2W
- Arduino Uno Rev. 3
- PCA9685 PWM Driver
- L298N Motor Driver
- 3x HC-SR04 Ultrasonic Sensors
- 12x SG90 Micro Servos
- 2x DC Motors
- OLED Display
- Speakers + Amplifier

## Installation
### 1. Clone the repository:
```bash
cd ~/walle-server
git clone https://github.com/Vladdudu12/wall-e-control.git
```
### 2. Set up Python virtual environment:
```bash
bashcd wall-e-control
python3 -m venv ../walle-env
source ../walle-env/bin/activate
pip install -r requirements.txt
```
### 3. Make startup script executable:
```bash
bashchmod +x start_walle.sh
```
### 4. Run Wall-E Control System:
```bash
bash./start_walle.sh
```
### 5. Access web interface at: http://wall-e.local:5000

## Usage

- Use the web interface to control Wall-E remotely
- WASD keys for movement
- Sliders for servo control
- Real-time sensor monitoring
- Audio feedback for actions

## Author
Vladdudu12 - https://github.com/Vladdudu12
## License
MIT License

### 6. modules/__init__.py
```python
# Wall-E Control System Modules
# This file makes the modules directory a Python package
"""
Wall-E Robot Control System Modules

This package contains all the hardware interface modules for the Wall-E robot:
- arduino_controller: Serial communication with Arduino
- audio_system: Sound and audio management
- display_controller: OLED display control
- battery_monitor: Battery level monitoring
"""

__version__ = "1.0.0"
__author__ = "Vladdudu12"
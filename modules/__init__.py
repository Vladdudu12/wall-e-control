#!/usr/bin/env python3
"""
Wall-E Control System Modules

This package contains all the hardware interface modules for the Wall-E robot:
- arduino_controller: Serial communication with Arduino
- audio_system: Sound and audio management  
- display_controller: OLED display control
- battery_monitor: Battery level monitoring

Author: Vladdudu12
Repository: https://github.com/Vladdudu12/wall-e-control
"""

__version__ = "1.0.0"
__author__ = "Vladdudu12"
__all__ = [
    "arduino_controller",
    "audio_system", 
    "display_controller",
    "battery_monitor"
]
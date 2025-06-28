#!/usr/bin/env python3
"""
Enhanced Display Controller with Solar Charging Mode
Adds solar panel interface to existing Wall-E display
"""

import time
import math
from datetime import datetime
from typing import Dict, Optional

try:
    import board
    import busio
    import adafruit_ssd1306
    from PIL import Image, ImageDraw, ImageFont

    I2C_AVAILABLE = True
except ImportError as e:
    print(f"Display libraries not available: {e}")
    I2C_AVAILABLE = False


class EnhancedDisplayController:
    def __init__(self, width=128, height=64, address=0x3C, auto_detect=True):
        """Initialize enhanced display controller with solar capabilities"""
        self.width = width
        self.height = height
        self.address = address
        self.display = None
        self.available = False
        self.last_battery_level = 100
        self.animation_frame = 0
        self.display_mode = 'normal'  # 'normal', 'solar', 'battery'

        if not I2C_AVAILABLE:
            print("✗ Display controller: Required libraries not installed")
            return

        if self._initialize_display(address, width, height):
            return

        if auto_detect:
            print(f"Display not found at 0x{address:02X}, trying auto-detection...")
            self._auto_detect_display()

    def _auto_detect_display(self):
        """Auto-detect display configuration"""
        addresses_to_try = [0x3C, 0x3D, 0x78, 0x7A, 0x3E, 0x3F]
        sizes_to_try = [(128, 64), (128, 32), (64, 48)]

        for addr in addresses_to_try:
            for width, height in sizes_to_try:
                if self._initialize_display(addr, width, height):
                    print(f"✓ Display auto-detected: 0x{addr:02X}, {width}x{height}")
                    return

        print("✗ No OLED display detected during auto-detection")

    def _initialize_display(self, address, width, height):
        """Try to initialize display with specific parameters"""
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.display = adafruit_ssd1306.SSD1306_I2C(width, height, i2c, addr=address)
            self.display.fill(0)
            self.display.show()

            self.address = address
            self.width = width
            self.height = height
            self.available = True

            print(f"✓ OLED display initialized at 0x{address:02X} ({width}x{height})")
            self.show_startup_message()
            return True

        except Exception as e:
            return False

    def show_startup_message(self):
        """Display Wall-E startup message"""
        if not self.available:
            return

        try:
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            try:
                if self.height >= 64:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                else:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font = small_font = ImageFont.load_default()

            if self.height >= 64:
                draw.text((10, 5), "WALL-E", font=font, fill=255)
                draw.text((10, 25), "Control System", font=small_font, fill=255)
                draw.text((10, 40), "Solar Ready", font=small_font, fill=255)
                draw.text((10, 52), datetime.now().strftime("%H:%M"), font=small_font, fill=255)
            else:
                draw.text((5, 2), "WALL-E", font=font, fill=255)
                draw.text((5, 18), "Solar Ready", font=small_font, fill=255)

            self.display.image(image)
            self.display.show()

        except Exception as e:
            print(f"Error showing startup message: {e}")

    # Solar Display Methods
    def draw_sun(self, draw, x, y, size=16, frame=0):
        """Draw animated sun with rotating rays"""
        # Sun circle
        draw.ellipse([(x - size // 2, y - size // 2), (x + size // 2, y + size // 2)], outline=255, fill=0)

        # Rotating sun rays
        num_rays = 8
        ray_length = size // 2 + 4

        for i in range(num_rays):
            angle = (i * 45 + frame * 5) * math.pi / 180

            inner_x = x + int((size // 2 + 2) * math.cos(angle))
            inner_y = y + int((size // 2 + 2) * math.sin(angle))
            outer_x = x + int((size // 2 + ray_length) * math.cos(angle))
            outer_y = y + int((size // 2 + ray_length) * math.sin(angle))

            draw.line([(inner_x, inner_y), (outer_x, outer_y)], fill=255, width=1)

    def draw_charge_bars(self, draw, x, y, width, height, battery_level, num_bars=12):
        """Draw charge bars like the original solar panel - empties from TOP"""
        bar_height = height // num_bars
        bar_spacing = 1
        actual_bar_height = max(1, bar_height - bar_spacing)

        # Calculate how many bars should be filled (from top to bottom)
        bars_to_fill = int((battery_level / 100.0) * num_bars)

        for i in range(num_bars):
            bar_y = y + i * bar_height

            # Draw bar outline (all bars always have outlines)
            draw.rectangle([(x, bar_y), (x + width, bar_y + actual_bar_height)],
                           outline=255, fill=0)

            # Fill bars from top down
            # Bar index 0 = top bar, should be filled when battery > (11/12)*100 = 91.67%
            # Bar index 11 = bottom bar, should be filled when battery > (0/12)*100 = 0%
            bar_threshold = ((num_bars - 1 - i) / num_bars) * 100

            if battery_level > bar_threshold:
                if i < bars_to_fill:
                    # Full bar
                    draw.rectangle([(x + 1, bar_y + 1), (x + width - 1, bar_y + actual_bar_height - 1)],
                                   fill=255)
                elif i == bars_to_fill:
                    # Partial bar (current draining bar from top)
                    remaining_in_segment = battery_level - bar_threshold
                    segment_size = 100.0 / num_bars
                    partial_fill = remaining_in_segment / segment_size
                    fill_width = int((width - 2) * partial_fill)
                    if fill_width > 0:
                        draw.rectangle([(x + 1, bar_y + 1), (x + 1 + fill_width, bar_y + actual_bar_height - 1)],
                                       fill=255)

    def draw_energy_particles(self, draw, frame):
        """Draw energy flow particles from sun to charge bars"""
        for i in range(3):
            particle_x = 30 + ((frame + i * 25) % 60)
            particle_y = 25 + int(3 * math.sin((frame + i * 30) * 0.1))

            # Energy particle
            if particle_x < 90:  # Only show particles traveling to bars
                draw.rectangle([(particle_x, particle_y), (particle_x + 1, particle_y + 1)], fill=255)

    def show_solar_panel_mode(self, battery_level: int = 85, solar_power: float = 1.2,
                              is_charging: bool = True, time_to_full: float = 2.5):
        """
        Show solar panel charging interface (like the original image)

        Args:
            battery_level: Battery percentage (0-100)
            solar_power: Solar power in watts
            is_charging: Whether currently charging
            time_to_full: Hours to full charge
        """
        if not self.available:
            return

        try:
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 7)
                tiny_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 6)
            except:
                font = small_font = tiny_font = ImageFont.load_default()

            # Title
            draw.text((10, 0), "SOLAR CHARGE PANEL", font=tiny_font, fill=255)

            # Sun icon (left side)
            sun_x, sun_y = 25, 30
            self.draw_sun(draw, sun_x, sun_y, size=14, frame=self.animation_frame)

            # Energy flow particles if charging
            if is_charging:
                self.draw_energy_particles(draw, self.animation_frame)

            # Charge bars (right side) - recreating the original look
            bars_start_x = 65
            bars_start_y = 12
            bar_width = 55
            bars_height = 35

            self.draw_charge_bars(draw, bars_start_x, bars_start_y, bar_width, bars_height, battery_level, 12)

            # Status information at bottom
            status_y = 50

            # Battery percentage (prominent)
            draw.text((5, status_y), f"{battery_level}%", font=font, fill=255)

            # Solar power
            draw.text((35, status_y), f"{solar_power:.1f}W", font=small_font, fill=255)

            # Status indicator
            if is_charging:
                if self.animation_frame % 20 < 10:  # Blinking
                    draw.text((65, status_y), "CHRG", font=small_font, fill=255)
                draw.text((95, status_y), f"{time_to_full:.1f}H", font=small_font, fill=255)
            else:
                draw.text((65, status_y), "IDLE", font=small_font, fill=255)

            # Wall-E indicator
            draw.text((5, 58), "WALL-E", font=tiny_font, fill=255)
            draw.text((95, 58), datetime.now().strftime("%H:%M"), font=tiny_font, fill=255)

            self.display.image(image)
            self.display.show()

            # Increment animation frame
            self.animation_frame += 1
            if self.animation_frame > 360:
                self.animation_frame = 0

        except Exception as e:
            print(f"Error showing solar panel mode: {e}")

    def update_status(self, walle_state: Dict):
        """
        Enhanced status update with mode switching
        """
        if not self.available:
            return

        battery_level = walle_state.get('battery_level', 100)
        is_charging = walle_state.get('is_charging', False)
        solar_power = walle_state.get('solar_power', 0.0)

        # Auto-switch to solar mode if solar power detected or charging
        if solar_power > 0.1 or is_charging:
            self.display_mode = 'solar'
        elif battery_level < 25:
            self.display_mode = 'battery'
        else:
            self.display_mode = 'normal'

        if self.display_mode == 'solar':
            time_to_full = walle_state.get('time_to_full', 0.0)
            self.show_solar_panel_mode(battery_level, solar_power, is_charging, time_to_full)
        elif self.display_mode == 'battery':
            self.show_battery_focus(battery_level, walle_state.get('battery_voltage', 0.0), is_charging)
        else:
            self._show_normal_status(walle_state)

        self.last_battery_level = battery_level

    def _show_normal_status(self, walle_state: Dict):
        """Show normal Wall-E status display"""
        try:
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
            except:
                font = small_font = ImageFont.load_default()

            # Header
            draw.text((0, 0), "WALL-E Status", font=font, fill=255)
            draw.line([(0, 12), (self.width, 12)], fill=255)

            # Mode and connection
            mode = walle_state.get('mode', 'Unknown').title()
            connected = walle_state.get('connected', False)
            status_text = "ONLINE" if connected else "OFFLINE"

            draw.text((0, 14), f"Mode: {mode}", font=small_font, fill=255)
            draw.text((0, 24), f"Status: {status_text}", font=small_font, fill=255)

            # Battery
            battery_level = walle_state.get('battery_level', 100)
            draw.text((0, 34), f"Battery: {battery_level}%", font=small_font, fill=255)

            # Battery bar
            bar_x, bar_y = 70, 36
            bar_width, bar_height = 52, 6

            draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
                           outline=255, fill=0)

            fill_width = int((battery_level / 100.0) * (bar_width - 2))
            if fill_width > 0:
                draw.rectangle([(bar_x + 1, bar_y + 1),
                                (bar_x + 1 + fill_width, bar_y + bar_height - 1)],
                               fill=255)

            # Sensors
            sensors = walle_state.get('sensors', {})
            front = sensors.get('front', 0)
            left = sensors.get('left', 0)
            right = sensors.get('right', 0)

            draw.text((0, 44), f"Sensors: F:{front:.0f} L:{left:.0f} R:{right:.0f}",
                      font=small_font, fill=255)

            # Time
            current_time = datetime.now().strftime("%H:%M:%S")
            draw.text((0, 54), current_time, font=small_font, fill=255)

            self.display.image(image)
            self.display.show()

        except Exception as e:
            print(f"Error showing normal status: {e}")

    def show_battery_focus(self, battery_level: int, voltage: float = 0.0, charging: bool = False):
        """Show focused battery display (from previous version)"""
        if not self.available:
            return

        try:
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            try:
                big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                big_font = font = small_font = ImageFont.load_default()

            # Title
            draw.text((5, 0), "WALL-E BATTERY", font=font, fill=255)

            # Large percentage
            percentage_text = f"{battery_level}%"
            bbox = draw.textbbox((0, 0), percentage_text, font=big_font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, 15), percentage_text, font=big_font, fill=255)

            # Battery bar
            bar_x, bar_y = 10, 42
            bar_width, bar_height = self.width - 20, 12

            # Battery outline
            draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
                           outline=255, fill=0)

            # Battery terminal
            terminal_width = 3
            draw.rectangle([(bar_x + bar_width, bar_y + 3),
                            (bar_x + bar_width + terminal_width, bar_y + bar_height - 3)],
                           fill=255)

            # Battery fill
            fill_width = int((battery_level / 100.0) * (bar_width - 2))
            if fill_width > 0:
                draw.rectangle([(bar_x + 1, bar_y + 1),
                                (bar_x + 1 + fill_width, bar_y + bar_height - 1)],
                               fill=255)

            # Status line
            status_y = bar_y + bar_height + 3
            if voltage > 0:
                draw.text((5, status_y), f"{voltage:.1f}V", font=small_font, fill=255)

            if charging:
                draw.text((self.width - 25, status_y), "CHG", font=small_font, fill=255)

            self.display.image(image)
            self.display.show()

        except Exception as e:
            print(f"Error showing battery focus: {e}")

    def set_display_mode(self, mode: str):
        """
        Manually set display mode

        Args:
            mode: 'normal', 'solar', 'battery'
        """
        if mode in ['normal', 'solar', 'battery']:
            self.display_mode = mode
            print(f"Display mode set to: {mode}")
        else:
            print(f"Invalid display mode: {mode}")

    def show_solar_animation_sequence(self, battery_level: int = 75, duration: int = 60):
        """Show animated solar charging sequence"""
        if not self.available:
            return

        for frame in range(duration):
            self.animation_frame = frame

            # Simulate changing values during animation
            current_battery = min(100, battery_level + (frame * 0.5))
            solar_power = 1.0 + 0.5 * math.sin(frame * 0.1)
            time_to_full = max(0.1, (100 - current_battery) / 10)

            self.show_solar_panel_mode(int(current_battery), solar_power, True, time_to_full)
            time.sleep(0.05)  # 20fps

    def show_message(self, title: str, message: str, duration: Optional[float] = None):
        """Show a custom message on the display"""
        if not self.available:
            return

        try:
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                message_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                title_font = message_font = ImageFont.load_default()

            # Center the title
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.width - title_width) // 2

            draw.text((title_x, 10), title, font=title_font, fill=255)

            # Center the message
            message_bbox = draw.textbbox((0, 0), message, font=message_font)
            message_width = message_bbox[2] - message_bbox[0]
            message_x = (self.width - message_width) // 2

            draw.text((message_x, 35), message, font=message_font, fill=255)

            self.display.image(image)
            self.display.show()

            if duration:
                time.sleep(duration)
                self.clear_display()

        except Exception as e:
            print(f"Error showing message: {e}")

    def clear_display(self):
        """Clear the display"""
        if self.available:
            self.display.fill(0)
            self.display.show()

    def get_display_info(self) -> Dict:
        """Get display information"""
        return {
            'available': self.available,
            'width': self.width,
            'height': self.height,
            'address': hex(self.address) if self.available else None,
            'mode': self.display_mode,
            'animation_frame': self.animation_frame
        }

    def cleanup(self):
        """Clean up display resources"""
        if self.available:
            self.clear_display()
            print("Enhanced display controller cleaned up")


# Test function
def test_enhanced_solar_display():
    """Test the enhanced display with solar functionality"""
    print("Testing Enhanced Solar Display Controller...")

    display = EnhancedDisplayController(auto_detect=True)

    if not display.available:
        print("Display not available for testing")
        return

    print("Display info:", display.get_display_info())

    # Test startup
    time.sleep(2)

    print("Testing solar panel mode...")
    for i in range(20):
        battery_level = 60 + i
        solar_power = 1.0 + 0.5 * math.sin(i * 0.3)
        time_to_full = (100 - battery_level) / 15

        display.show_solar_panel_mode(battery_level, solar_power, True, time_to_full)
        time.sleep(0.2)

    print("Testing mode switching...")
    # Test normal mode
    display.set_display_mode('normal')
    test_state = {
        'mode': 'exploring',
        'battery_level': 85,
        'connected': True,
        'sensors': {'front': 25, 'left': 30, 'right': 20}
    }
    display.update_status(test_state)
    time.sleep(3)

    # Test solar mode
    display.set_display_mode('solar')
    test_state_solar = {
        'mode': 'charging',
        'battery_level': 75,
        'is_charging': True,
        'solar_power': 1.2,
        'time_to_full': 2.5
    }
    display.update_status(test_state_solar)
    time.sleep(3)

    # Test battery mode
    display.set_display_mode('battery')
    test_state_battery = {
        'battery_level': 20,
        'battery_voltage': 11.1,
        'is_charging': False
    }
    display.update_status(test_state_battery)
    time.sleep(3)

    print("Testing solar animation sequence...")
    display.show_solar_animation_sequence(battery_level=70, duration=30)

    display.cleanup()
    print("Enhanced solar display test complete!")


if __name__ == "__main__":
    test_enhanced_solar_display()
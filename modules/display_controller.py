#!/usr/bin/env python3
"""
Enhanced Display Controller Module for Wall-E
Handles OLED display for status information and battery monitoring
Now with better battery display and auto-detection
"""

import time
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
    print("Install with: pip install RPi.GPIO adafruit-blinka adafruit-circuitpython-ssd1306 pillow")
    I2C_AVAILABLE = False


class DisplayController:
    def __init__(self, width=128, height=64, address=0x3C, auto_detect=True):
        """
        Initialize OLED display controller with auto-detection

        Args:
            width: Display width in pixels
            height: Display height in pixels
            address: I2C address of the display
            auto_detect: Try to auto-detect display if default fails
        """
        self.width = width
        self.height = height
        self.address = address
        self.display = None
        self.available = False
        self.last_battery_level = 100

        if not I2C_AVAILABLE:
            print("✗ Display controller: Required libraries not installed")
            return

        # Try to initialize with given address first
        if self._initialize_display(address, width, height):
            return

        # If auto-detect is enabled and initial attempt failed, try other common addresses
        if auto_detect:
            print(f"Display not found at 0x{address:02X}, trying auto-detection...")
            self._auto_detect_display()

    def _auto_detect_display(self):
        """Auto-detect display configuration"""
        # Common addresses for generic displays
        addresses_to_try = [0x3C, 0x3D, 0x78, 0x7A, 0x3E, 0x3F]
        sizes_to_try = [(128, 64), (128, 32), (64, 48)]

        print("Auto-detecting OLED display...")

        for addr in addresses_to_try:
            for width, height in sizes_to_try:
                if self._initialize_display(addr, width, height):
                    print(f"✓ Display auto-detected: 0x{addr:02X}, {width}x{height}")
                    return

        print("✗ No OLED display detected during auto-detection")

    def _initialize_display(self, address, width, height):
        """Try to initialize display with specific parameters"""
        try:
            # Initialize I2C
            i2c = busio.I2C(board.SCL, board.SDA)

            # Initialize display
            self.display = adafruit_ssd1306.SSD1306_I2C(width, height, i2c, addr=address)

            # Test display
            self.display.fill(0)
            self.display.show()

            # Update configuration
            self.address = address
            self.width = width
            self.height = height
            self.available = True

            print(f"✓ OLED display initialized at 0x{address:02X} ({width}x{height})")

            # Show startup message
            self.show_startup_message()

            return True

        except Exception as e:
            return False

    def show_startup_message(self):
        """Display Wall-E startup message"""
        if not self.available:
            return

        try:
            # Create image
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            # Try to load fonts, fallback to default
            try:
                if self.height >= 64:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                else:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()

            # Draw Wall-E logo/text
            if self.height >= 64:
                draw.text((10, 5), "WALL-E", font=font, fill=255)
                draw.text((10, 25), "Control System", font=small_font, fill=255)
                draw.text((10, 40), "Online", font=small_font, fill=255)
                draw.text((10, 52), datetime.now().strftime("%H:%M"), font=small_font, fill=255)
            else:
                # Compact layout for smaller displays
                draw.text((5, 2), "WALL-E", font=font, fill=255)
                draw.text((5, 18), "Online", font=small_font, fill=255)

            # Display the image
            self.display.image(image)
            self.display.show()

        except Exception as e:
            print(f"Error showing startup message: {e}")

    def show_battery_focus(self, battery_level: int, voltage: float = 0.0, charging: bool = False):
        """
        Display focused battery information with large visual elements

        Args:
            battery_level: Battery percentage (0-100)
            voltage: Battery voltage
            charging: Whether battery is charging
        """
        if not self.available:
            return

        try:
            # Create image
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            # Load fonts
            try:
                if self.height >= 64:
                    big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                else:
                    big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
            except:
                big_font = font = small_font = ImageFont.load_default()

            if self.height >= 64:
                # Large display layout
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

            else:
                # Compact display layout
                draw.text((2, 0), "WALL-E BAT", font=font, fill=255)
                draw.text((2, 12), f"{battery_level}%", font=font, fill=255)

                # Compact battery bar
                bar_x, bar_y = 2, 22
                bar_width, bar_height = self.width - 6, 8

                draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
                               outline=255, fill=0)

                fill_width = int((battery_level / 100.0) * (bar_width - 2))
                if fill_width > 0:
                    draw.rectangle([(bar_x + 1, bar_y + 1),
                                    (bar_x + 1 + fill_width, bar_y + bar_height - 1)],
                                   fill=255)

            # Display the image
            self.display.image(image)
            self.display.show()

            self.last_battery_level = battery_level

        except Exception as e:
            print(f"Error showing battery display: {e}")

    def update_status(self, walle_state: Dict):
        """
        Update display with current Wall-E status
        Enhanced to show battery prominently when low

        Args:
            walle_state: Dictionary containing Wall-E status information
        """
        if not self.available:
            return

        try:
            battery_level = walle_state.get('battery_level', 100)
            voltage = walle_state.get('battery_voltage', 0.0)
            charging = walle_state.get('is_charging', False)

            # Show battery-focused display if battery is low or changed significantly
            if (battery_level < 25 or
                    abs(battery_level - self.last_battery_level) > 10):
                self.show_battery_focus(battery_level, voltage, charging)
                return

            # Create image
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            # Load fonts
            try:
                if self.height >= 64:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
                else:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
            except:
                font = small_font = ImageFont.load_default()

            if self.height >= 64:
                # Full status display
                draw.text((0, 0), "WALL-E Status", font=font, fill=255)
                draw.line([(0, 12), (self.width, 12)], fill=255)

                # Mode and connection
                mode = walle_state.get('mode', 'Unknown').title()
                connected = walle_state.get('connected', False)
                status_text = "ONLINE" if connected else "OFFLINE"

                draw.text((0, 14), f"Mode: {mode}", font=small_font, fill=255)
                draw.text((0, 24), f"Status: {status_text}", font=small_font, fill=255)

                # Battery with enhanced visual bar
                draw.text((0, 34), f"Battery: {battery_level}%", font=small_font, fill=255)

                # Enhanced battery bar
                bar_x, bar_y = 70, 36
                bar_width, bar_height = 52, 6

                draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
                               outline=255, fill=0)

                # Battery terminal
                draw.rectangle([(bar_x + bar_width, bar_y + 1), (bar_x + bar_width + 2, bar_y + bar_height - 1)],
                               fill=255)

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

            else:
                # Compact display for smaller screens
                draw.text((0, 0), "WALL-E", font=font, fill=255)

                mode = walle_state.get('mode', 'Unknown')[:4].upper()  # Truncate mode
                draw.text((0, 10), f"M:{mode}", font=small_font, fill=255)

                draw.text((0, 20), f"Bat: {battery_level}%", font=small_font, fill=255)

                connected = walle_state.get('connected', False)
                status = "ON" if connected else "OFF"
                draw.text((60, 20), status, font=small_font, fill=255)

            # Display the image
            self.display.image(image)
            self.display.show()

            self.last_battery_level = battery_level

        except Exception as e:
            print(f"Error updating display: {e}")

    def show_low_battery_warning(self, battery_level: int):
        """Show flashing low battery warning"""
        if not self.available:
            return

        try:
            for i in range(3):  # Flash 3 times
                # Warning screen
                image = Image.new("1", (self.width, self.height))
                draw = ImageDraw.Draw(image)

                try:
                    if self.height >= 64:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                    else:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
                        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
                except:
                    font = small_font = ImageFont.load_default()

                # Warning text
                if self.height >= 64:
                    draw.text((15, 10), "LOW BATTERY!", font=font, fill=255)
                    draw.text((35, 30), f"{battery_level}%", font=font, fill=255)
                    draw.text((20, 50), "CHARGE NOW", font=small_font, fill=255)
                else:
                    draw.text((5, 5), "LOW BATTERY!", font=small_font, fill=255)
                    draw.text((15, 20), f"{battery_level}%", font=font, fill=255)

                self.display.image(image)
                self.display.show()
                time.sleep(0.5)

                # Clear
                self.display.fill(0)
                self.display.show()
                time.sleep(0.3)

        except Exception as e:
            print(f"Error showing battery warning: {e}")

    def show_message(self, title: str, message: str, duration: Optional[float] = None):
        """
        Show a custom message on the display

        Args:
            title: Message title
            message: Message content
            duration: How long to show message (None = indefinite)
        """
        if not self.available:
            return

        try:
            # Create image
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            # Load fonts
            try:
                if self.height >= 64:
                    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                    message_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                else:
                    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
                    message_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
            except:
                title_font = message_font = ImageFont.load_default()

            # Center the title
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.width - title_width) // 2

            y_offset = 10 if self.height >= 64 else 5
            draw.text((title_x, y_offset), title, font=title_font, fill=255)

            # Center the message
            message_bbox = draw.textbbox((0, 0), message, font=message_font)
            message_width = message_bbox[2] - message_bbox[0]
            message_x = (self.width - message_width) // 2

            message_y = y_offset + 20 if self.height >= 64 else y_offset + 12
            draw.text((message_x, message_y), message, font=message_font, fill=255)

            # Display the image
            self.display.image(image)
            self.display.show()

            # Auto-clear after duration
            if duration:
                time.sleep(duration)
                self.clear_display()

        except Exception as e:
            print(f"Error showing message: {e}")

    def show_sensor_data(self, sensors: Dict[str, float]):
        """
        Display sensor readings in a visual format

        Args:
            sensors: Dictionary with sensor readings
        """
        if not self.available:
            return

        try:
            # Create image
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            # Load font
            try:
                if self.height >= 64:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                else:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
            except:
                font = ImageFont.load_default()

            # Title
            draw.text((35, 0), "SENSORS", font=font, fill=255)
            draw.line([(0, 12), (self.width, 12)], fill=255)

            # Front sensor (top)
            front = sensors.get('front', 0)
            front_text = f"{front:.1f}cm" if front > 0 else "--"
            draw.text((50, 15), f"F: {front_text}", font=font, fill=255)

            # Left sensor (left side)
            left = sensors.get('left', 0)
            left_text = f"{left:.1f}cm" if left > 0 else "--"
            draw.text((5, 35), f"L: {left_text}", font=font, fill=255)

            # Right sensor (right side)
            right = sensors.get('right', 0)
            right_text = f"{right:.1f}cm" if right > 0 else "--"
            draw.text((80, 35), f"R: {right_text}", font=font, fill=255)

            # Draw Wall-E representation
            center_x, center_y = 64, 40

            # Draw Wall-E body (rectangle)
            draw.rectangle([(center_x - 8, center_y - 5), (center_x + 8, center_y + 5)], outline=255, fill=0)

            # Draw sensor detection zones
            max_range = 50  # cm
            scale = 0.3  # pixels per cm

            # Front sensor zone
            if front > 0 and front < max_range:
                zone_length = int(front * scale)
                draw.line([(center_x, center_y - 5), (center_x, center_y - 5 - zone_length)], fill=255)
                draw.line([(center_x - 2, center_y - 5 - zone_length), (center_x + 2, center_y - 5 - zone_length)],
                          fill=255)

            # Left sensor zone
            if left > 0 and left < max_range:
                zone_length = int(left * scale)
                draw.line([(center_x - 8, center_y), (center_x - 8 - zone_length, center_y)], fill=255)
                draw.line([(center_x - 8 - zone_length, center_y - 2), (center_x - 8 - zone_length, center_y + 2)],
                          fill=255)

            # Right sensor zone
            if right > 0 and right < max_range:
                zone_length = int(right * scale)
                draw.line([(center_x + 8, center_y), (center_x + 8 + zone_length, center_y)], fill=255)
                draw.line([(center_x + 8 + zone_length, center_y - 2), (center_x + 8 + zone_length, center_y + 2)],
                          fill=255)

            # Display the image
            self.display.image(image)
            self.display.show()

        except Exception as e:
            print(f"Error showing sensor data: {e}")

    def show_animation(self, frames: int = 5):
        """
        Show a simple animation (Wall-E eyes blinking)

        Args:
            frames: Number of animation frames
        """
        if not self.available:
            return

        try:
            for frame in range(frames):
                # Create image
                image = Image.new("1", (self.width, self.height))
                draw = ImageDraw.Draw(image)

                # Draw Wall-E face
                center_x, center_y = self.width // 2, self.height // 2

                # Eyes (circles that blink)
                eye_size = 15 if self.height >= 64 else 10
                eye_offset = 20 if self.height >= 64 else 15

                if frame % 4 == 0:  # Blink frame
                    # Draw closed eyes (lines)
                    draw.line([(center_x - eye_offset - eye_size // 2, center_y),
                               (center_x - eye_offset + eye_size // 2, center_y)], fill=255, width=2)
                    draw.line([(center_x + eye_offset - eye_size // 2, center_y),
                               (center_x + eye_offset + eye_size // 2, center_y)], fill=255, width=2)
                else:
                    # Draw open eyes (circles)
                    draw.ellipse([(center_x - eye_offset - eye_size // 2, center_y - eye_size // 2),
                                  (center_x - eye_offset + eye_size // 2, center_y + eye_size // 2)], outline=255,
                                 fill=0)
                    draw.ellipse([(center_x + eye_offset - eye_size // 2, center_y - eye_size // 2),
                                  (center_x + eye_offset + eye_size // 2, center_y + eye_size // 2)], outline=255,
                                 fill=0)

                    # Eye pupils
                    pupil_size = 4 if self.height >= 64 else 3
                    draw.ellipse([(center_x - eye_offset - pupil_size // 2, center_y - pupil_size // 2),
                                  (center_x - eye_offset + pupil_size // 2, center_y + pupil_size // 2)], fill=255)
                    draw.ellipse([(center_x + eye_offset - pupil_size // 2, center_y - pupil_size // 2),
                                  (center_x + eye_offset + pupil_size // 2, center_y + pupil_size // 2)], fill=255)

                # Display the frame
                self.display.image(image)
                self.display.show()
                time.sleep(0.3)

        except Exception as e:
            print(f"Error showing animation: {e}")

    def clear_display(self):
        """Clear the display"""
        if not self.available:
            return

        try:
            self.display.fill(0)
            self.display.show()
        except Exception as e:
            print(f"Error clearing display: {e}")

    def set_brightness(self, brightness: float):
        """
        Set display brightness (if supported)

        Args:
            brightness: Brightness level (0.0 to 1.0)
        """
        # Note: SSD1306 doesn't support brightness control
        # This is a placeholder for future display types
        pass

    def get_display_info(self) -> Dict:
        """Get display information"""
        return {
            'available': self.available,
            'width': self.width,
            'height': self.height,
            'address': hex(self.address) if self.available else None,
            'last_battery_level': self.last_battery_level
        }

    def cleanup(self):
        """Clean up display resources"""
        if self.available:
            self.clear_display()
            print("Display controller cleaned up")


# Test function
def test_display_controller():
    """Test the display controller functionality with enhanced features"""
    print("Testing Enhanced Display Controller...")

    display = DisplayController(auto_detect=True)

    if not display.available:
        print("Display not available for testing")
        return

    print("Display info:", display.get_display_info())

    # Test startup message
    time.sleep(2)

    # Test battery focus display
    print("Testing battery focus display...")
    for battery_level in [100, 75, 50, 25, 15, 5]:
        voltage = 12.6 - (1.0 * (100 - battery_level) / 100)  # Simulate voltage drop
        display.show_battery_focus(battery_level, voltage, charging=(battery_level < 50))
        time.sleep(2)

    # Test low battery warning
    print("Testing low battery warning...")
    display.show_low_battery_warning(5)

    # Test custom message
    print("Testing custom message...")
    display.show_message("WALL-E", "TESTING", duration=2)

    # Test status update
    print("Testing status update...")
    test_state = {
        'mode': 'exploring',
        'battery_level': 85,
        'battery_voltage': 12.1,
        'connected': True,
        'sensors': {'front': 25.5, 'left': 0, 'right': 15.2}
    }
    display.update_status(test_state)
    time.sleep(3)

    # Test sensor display
    print("Testing sensor display...")
    test_sensors = {'front': 30.0, 'left': 45.5, 'right': 0}
    display.show_sensor_data(test_sensors)
    time.sleep(3)

    # Test animation
    print("Testing animation...")
    display.show_animation(frames=6)

    # Clear display
    display.clear_display()
    display.cleanup()
    print("Enhanced display controller test complete")


if __name__ == "__main__":
    test_display_controller()
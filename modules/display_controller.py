#!/usr/bin/env python3
"""
Enhanced Display Controller with Vertical Solar Charging Mode
Complete version with vertical solar panel interface
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
    def __init__(self, width=128, height=64, address=0x3C, auto_detect=True, rotation=0):
        """Initialize enhanced display controller with vertical solar capabilities"""
        self.width = width
        self.height = height
        self.address = address
        self.display = None
        self.available = False
        self.last_battery_level = 100
        self.animation_frame = 0
        self.display_mode = 'solar'  # Default to solar mode

        self.rotation = rotation
        if rotation in [90, 270]:
            self.width = height  # 64 pixels wide
            self.height = width  # 128 pixels tall
        else:
            self.width = width  # 128 pixels wide
            self.height = height  # 64 pixels tall

        if not I2C_AVAILABLE:
            print("✗ Display controller: Required libraries not installed")
            return

        if self._initialize_display(address, width, height):
            return

        if auto_detect:
            print(f"Display not found at 0x{address:02X}, trying auto-detection...")
            self._auto_detect_display()

    def rotate_image_if_needed(self, image):
        """Rotate image based on rotation setting"""
        if self.rotation == 90:
            return image.transpose(Image.ROTATE_90)
        elif self.rotation == 180:
            return image.transpose(Image.ROTATE_180)
        elif self.rotation == 270:
            return image.transpose(Image.ROTATE_270)
        return image

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
                draw.text((10, 40), "Vertical Solar", font=small_font, fill=255)
                draw.text((10, 52), datetime.now().strftime("%H:%M"), font=small_font, fill=255)
            else:
                draw.text((5, 2), "WALL-E", font=font, fill=255)
                draw.text((5, 18), "Vertical Solar", font=small_font, fill=255)

            self.display.image(image)
            self.display.show()

        except Exception as e:
            print(f"Error showing startup message: {e}")

    def safe_rectangle(self, draw, coords, **kwargs):
        """Draw rectangle with safe coordinates"""
        x1, y1, x2, y2 = coords

        # Ensure coordinates are in bounds and properly ordered
        x1 = max(0, min(x1, self.width - 1))
        y1 = max(0, min(y1, self.height - 1))
        x2 = max(0, min(x2, self.width - 1))
        y2 = max(0, min(y2, self.height - 1))

        # Ensure x2 >= x1 and y2 >= y1
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1

        # Only draw if we have valid coordinates
        if x2 > x1 and y2 > y1:
            draw.rectangle([(x1, y1), (x2, y2)], **kwargs)

    def safe_line(self, draw, coords, **kwargs):
        """Draw line with safe coordinates"""
        x1, y1, x2, y2 = coords

        # Clamp coordinates to display bounds
        x1 = max(0, min(x1, self.width - 1))
        y1 = max(0, min(y1, self.height - 1))
        x2 = max(0, min(x2, self.width - 1))
        y2 = max(0, min(y2, self.height - 1))

        draw.line([(x1, y1), (x2, y2)], **kwargs)

    def draw_sun(self, draw, x, y, size=16, frame=0):
        """Draw animated sun with rotating rays"""
        try:
            # Clamp sun position to display bounds
            x = max(size, min(x, self.width - size))
            y = max(size, min(y, self.height - size))

            # Sun circle - use safe coordinates
            sun_radius = size // 2
            self.safe_rectangle(draw,
                                (x - sun_radius, y - sun_radius, x + sun_radius, y + sun_radius),
                                outline=255, fill=0)

            # Rotating sun rays
            num_rays = 8
            ray_length = size // 2 + 3

            for i in range(num_rays):
                angle = (i * 45 + frame * 3) * math.pi / 180

                inner_radius = size // 2 + 1
                outer_radius = size // 2 + ray_length

                inner_x = x + int(inner_radius * math.cos(angle))
                inner_y = y + int(inner_radius * math.sin(angle))
                outer_x = x + int(outer_radius * math.cos(angle))
                outer_y = y + int(outer_radius * math.sin(angle))

                self.safe_line(draw, (inner_x, inner_y, outer_x, outer_y), fill=255, width=1)

        except Exception as e:
            print(f"Error drawing sun: {e}")

    def draw_vertical_charge_bars(self, draw, x, y, width, height, battery_level, num_bars=12):
        """Draw VERTICAL charge bars - stack vertically, empty from TOP"""
        try:
            bar_spacing = 2  # Increased spacing between bars
            available_height = height - (bar_spacing * (num_bars - 1))
            bar_height = max(2, available_height // num_bars)  # Minimum 2 pixels high

            # Calculate how many bars should be filled
            bars_to_fill = int((battery_level / 100.0) * num_bars)

            for i in range(num_bars):
                bar_y = y + i * (bar_height + bar_spacing)

                # Skip if bar would be outside display
                if bar_y + bar_height >= self.height - 10:  # Leave room for bottom text
                    continue

                # Draw bar outline (all bars always have outlines)
                self.safe_rectangle(draw,
                                    (x, bar_y, x + width, bar_y + bar_height),
                                    outline=255, fill=0)

                # Fill bars from top down (like fuel gauge emptying from top)
                # Top bar (i=0) empties first when battery decreases
                # Bottom bar (i=11) is last to empty
                bar_threshold = ((num_bars - 1 - i) / num_bars) * 100

                if battery_level > bar_threshold:
                    if i < bars_to_fill:
                        # Full bar
                        self.safe_rectangle(draw,
                                            (x + 1, bar_y + 1, x + width - 1, bar_y + bar_height - 1),
                                            fill=255)
                    elif i == bars_to_fill:
                        # Partial bar (currently draining from top)
                        remaining_in_segment = battery_level - bar_threshold
                        segment_size = 100.0 / num_bars
                        if segment_size > 0:
                            partial_fill = remaining_in_segment / segment_size
                            fill_width = max(1, int((width - 2) * partial_fill))

                            self.safe_rectangle(draw,
                                                (x + 1, bar_y + 1, x + 1 + fill_width, bar_y + bar_height - 1),
                                                fill=255)

        except Exception as e:
            print(f"Error drawing vertical charge bars: {e}")

    def draw_vertical_energy_particles(self, draw, frame):
        """Draw energy particles flowing vertically downward from sun to charge bars"""
        try:
            for i in range(3):
                # Particles flow vertically downward
                particle_x = 15 + int(3 * math.sin((frame + i * 20) * 0.1))  # Slight horizontal wiggle
                particle_y = 38 + ((frame + i * 15) % 25)  # Flow downward

                # Only show particles in the flow zone (from sun to bars)
                if particle_y < 50 and 10 < particle_x < 35:
                    # Clamp particle position
                    particle_x = max(0, min(particle_x, self.width - 2))
                    particle_y = max(0, min(particle_y, self.height - 2))

                    self.safe_rectangle(draw,
                                        (particle_x, particle_y, particle_x + 1, particle_y + 1),
                                        fill=255)

        except Exception as e:
            print(f"Error drawing vertical energy particles: {e}")

    def show_solar_panel_mode(self, battery_level: int = 85, solar_power: float = 1.2,
                              is_charging: bool = True, time_to_full: float = 2.5):
        """
        Show VERTICAL solar panel charging interface (portrait layout)

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

            # === VERTICAL LAYOUT ===

            # Title at top left
            draw.text((2, 0), "SOLAR", font=small_font, fill=255)
            draw.text((2, 10), "PANEL", font=tiny_font, fill=255)

            # Sun icon (top left, smaller for vertical layout)
            sun_x, sun_y = 15, 28
            self.draw_sun(draw, sun_x, sun_y, size=10, frame=self.animation_frame)

            # Energy flow particles (vertical flow downward)
            if is_charging:
                self.draw_vertical_energy_particles(draw, self.animation_frame)

            # VERTICAL charge bars (main centerpiece - running down the middle)
            bars_start_x = 45  # Center position
            bars_start_y = 15  # Start high
            bar_width = 8      # Narrow bars for vertical layout
            bars_height = 35   # Tall for vertical layout

            self.draw_vertical_charge_bars(draw, bars_start_x, bars_start_y, bar_width, bars_height, battery_level, 12)

            # Right side - status information (stacked vertically)
            status_x = 65

            # Battery percentage (large, prominent)
            draw.text((status_x, 12), f"{battery_level}%", font=font, fill=255)

            # Solar power (middle right)
            draw.text((status_x, 24), f"{solar_power:.1f}W", font=small_font, fill=255)

            # Charging status (bottom right)
            if is_charging:
                if self.animation_frame % 20 < 10:  # Blinking indicator
                    draw.text((status_x, 36), "CHG", font=small_font, fill=255)
                draw.text((status_x, 46), f"{time_to_full:.1f}H", font=tiny_font, fill=255)
            else:
                draw.text((status_x, 36), "IDLE", font=small_font, fill=255)

            # Bottom status line
            bottom_y = self.height - 8
            draw.text((2, bottom_y), "WALL-E", font=tiny_font, fill=255)
            draw.text((85, bottom_y), datetime.now().strftime("%H:%M"), font=tiny_font, fill=255)

            rotated_image = self.rotate_image_if_needed(image)
            self.display.image(rotated_image)
            self.display.show()

            # Increment animation frame
            self.animation_frame += 1
            if self.animation_frame > 360:
                self.animation_frame = 0

        except Exception as e:
            print(f"Error showing vertical solar panel mode: {e}")

    def update_status(self, walle_state: Dict):
        """
        Enhanced status update with vertical solar mode as default
        """
        if not self.available:
            return

        try:
            battery_level = walle_state.get('battery_level', 100)
            is_charging = walle_state.get('is_charging', False)
            solar_power = walle_state.get('solar_power', 0.0)

            # Solar mode is now the default mode
            self.display_mode = 'solar'

            # Only switch to other modes in special cases
            if battery_level < 15:  # Only switch to battery mode when critically low
                self.display_mode = 'battery'
            # Solar mode for everything else (default)

            if self.display_mode == 'solar':
                time_to_full = walle_state.get('time_to_full', 0.0)
                self.show_solar_panel_mode(battery_level, solar_power, is_charging, time_to_full)
            elif self.display_mode == 'battery':
                self.show_battery_focus(battery_level, walle_state.get('battery_voltage', 0.0), is_charging)
            else:
                self._show_normal_status(walle_state)

            self.last_battery_level = battery_level

        except Exception as e:
            print(f"Error updating status: {e}")

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

            self.safe_rectangle(draw, (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
                                outline=255, fill=0)

            fill_width = int((battery_level / 100.0) * (bar_width - 2))
            if fill_width > 0:
                self.safe_rectangle(draw,
                                    (bar_x + 1, bar_y + 1, bar_x + 1 + fill_width, bar_y + bar_height - 1),
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
        """Show focused battery display"""
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
            self.safe_rectangle(draw, (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
                                outline=255, fill=0)

            # Battery terminal
            terminal_width = 3
            self.safe_rectangle(draw, (bar_x + bar_width, bar_y + 3,
                                       bar_x + bar_width + terminal_width, bar_y + bar_height - 3),
                                fill=255)

            # Battery fill
            fill_width = int((battery_level / 100.0) * (bar_width - 2))
            if fill_width > 0:
                self.safe_rectangle(draw,
                                    (bar_x + 1, bar_y + 1, bar_x + 1 + fill_width, bar_y + bar_height - 1),
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
        """Show animated vertical solar charging sequence"""
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


# Backward compatibility alias
DisplayController = EnhancedDisplayController


# Test function
def test_vertical_solar_display():
    """Test the vertical solar display functionality"""
    print("Testing Vertical Solar Display Controller...")

    display = DisplayController(auto_detect=True)

    if not display.available:
        print("Display not available for testing")
        return

    print("Display info:", display.get_display_info())

    # Test startup
    time.sleep(2)

    print("Testing vertical solar panel mode...")
    # Test different battery levels to see vertical bars empty from top
    test_levels = [100, 90, 75, 50, 25, 15, 8, 0]

    for battery_level in test_levels:
        print(f"  Battery level: {battery_level}% - Watch TOP bars empty first!")
        display.show_solar_panel_mode(
            battery_level=battery_level,
            solar_power=1.2,
            is_charging=True,
            time_to_full=2.0
        )
        time.sleep(2)

    print("Testing charging animation...")
    for i in range(30):
        battery = 50 + i
        display.show_solar_panel_mode(
            battery_level=battery,
            solar_power=1.5,
            is_charging=True,
            time_to_full=1.5
        )
        time.sleep(0.1)

    display.cleanup()
    print("Vertical solar display test complete!")


if __name__ == "__main__":
    test_vertical_solar_display()
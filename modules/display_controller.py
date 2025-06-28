#!/usr/bin/env python3
"""
Fixed Solar Display Controller - Prevents coordinate errors
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


class DisplayController:
    def __init__(self, width=128, height=64, address=0x3C, auto_detect=True):
        """Initialize display controller"""
        self.width = width
        self.height = height
        self.address = address
        self.display = None
        self.available = False
        self.last_battery_level = 100
        self.animation_frame = 0
        self.display_mode = 'normal'

        if not I2C_AVAILABLE:
            print("✗ Display controller: Required libraries not installed")
            return

        if self._initialize_display(address, width, height):
            return

        if auto_detect:
            self._auto_detect_display()

    def _auto_detect_display(self):
        """Auto-detect display configuration"""
        addresses_to_try = [0x3C, 0x3D]
        sizes_to_try = [(128, 64), (128, 32)]

        for addr in addresses_to_try:
            for width, height in sizes_to_try:
                if self._initialize_display(addr, width, height):
                    print(f"✓ Display auto-detected: 0x{addr:02X}, {width}x{height}")
                    return

    def _initialize_display(self, address, width, height):
        """Initialize display with specific parameters"""
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
        """Display startup message"""
        if not self.available:
            return

        try:
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                font = small_font = ImageFont.load_default()

            draw.text((10, 5), "WALL-E", font=font, fill=255)
            draw.text((10, 25), "Solar Ready", font=small_font, fill=255)
            draw.text((10, 40), "Display Online", font=small_font, fill=255)

            self.display.image(image)
            self.display.show()

        except Exception as e:
            print(f"Error in startup message: {e}")

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

    def draw_sun(self, draw, x, y, size=12):
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

            # Sun rays
            num_rays = 8
            ray_length = size // 2 + 3

            for i in range(num_rays):
                angle = (i * 45 + self.animation_frame * 3) * math.pi / 180

                # Calculate ray positions
                inner_radius = size // 2 + 1
                outer_radius = size // 2 + ray_length

                inner_x = x + int(inner_radius * math.cos(angle))
                inner_y = y + int(inner_radius * math.sin(angle))
                outer_x = x + int(outer_radius * math.cos(angle))
                outer_y = y + int(outer_radius * math.sin(angle))

                # Draw ray using safe line
                self.safe_line(draw, (inner_x, inner_y, outer_x, outer_y), fill=255, width=1)

        except Exception as e:
            print(f"Error drawing sun: {e}")

    def draw_solar_bars(self, draw, x, y, width, height, battery_level, num_bars=12):
        """Draw solar charge bars that empty from top"""
        try:
            # Ensure valid dimensions
            if width <= 0 or height <= 0 or num_bars <= 0:
                return

            bar_height = max(1, height // num_bars)
            bar_spacing = 1
            actual_bar_height = max(1, bar_height - bar_spacing)

            # Clamp battery level
            battery_level = max(0, min(100, battery_level))

            for i in range(num_bars):
                bar_y = y + i * bar_height

                # Skip if bar would be outside display
                if bar_y >= self.height or bar_y + actual_bar_height >= self.height:
                    continue

                # Draw bar outline
                self.safe_rectangle(draw,
                                    (x, bar_y, x + width, bar_y + actual_bar_height),
                                    outline=255, fill=0)

                # Calculate if this bar should be filled
                # Top bar (i=0) empties first, bottom bar (i=11) empties last
                bar_threshold_max = ((num_bars - i) / num_bars) * 100
                bar_threshold_min = ((num_bars - i - 1) / num_bars) * 100

                if battery_level >= bar_threshold_max:
                    # Full bar
                    self.safe_rectangle(draw,
                                        (x + 1, bar_y + 1, x + width - 1, bar_y + actual_bar_height - 1),
                                        fill=255)
                elif battery_level > bar_threshold_min:
                    # Partial bar
                    segment_range = bar_threshold_max - bar_threshold_min
                    if segment_range > 0:
                        fill_ratio = (battery_level - bar_threshold_min) / segment_range
                        fill_width = max(1, int((width - 2) * fill_ratio))

                        self.safe_rectangle(draw,
                                            (x + 1, bar_y + 1, x + 1 + fill_width, bar_y + actual_bar_height - 1),
                                            fill=255)

        except Exception as e:
            print(f"Error drawing solar bars: {e}")

    def show_solar_panel_mode(self, battery_level=85, solar_power=1.2, is_charging=True, time_to_full=2.5):
        """Show solar panel charging interface"""
        if not self.available:
            return

        try:
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            # Load fonts safely
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 7)
            except:
                font = small_font = ImageFont.load_default()

            # Title
            draw.text((8, 0), "SOLAR CHARGE PANEL", font=small_font, fill=255)

            # Sun (left side)
            sun_x, sun_y = 20, 28
            self.draw_sun(draw, sun_x, sun_y, size=12)

            # Energy particles (if charging)
            if is_charging:
                for i in range(2):
                    particle_x = 32 + ((self.animation_frame + i * 20) % 35)
                    particle_y = 26 + int(2 * math.sin((self.animation_frame + i * 15) * 0.1))

                    # Clamp particle position
                    particle_x = max(0, min(particle_x, self.width - 2))
                    particle_y = max(0, min(particle_y, self.height - 2))

                    self.safe_rectangle(draw,
                                        (particle_x, particle_y, particle_x + 1, particle_y + 1),
                                        fill=255)

            # Solar charge bars (right side)
            bars_x = 70
            bars_y = 12
            bars_width = 50
            bars_height = 30

            # Ensure bars fit in display
            if bars_x + bars_width > self.width:
                bars_width = self.width - bars_x - 2
            if bars_y + bars_height > self.height - 15:
                bars_height = self.height - bars_y - 15

            self.draw_solar_bars(draw, bars_x, bars_y, bars_width, bars_height, battery_level)

            # Status line at bottom
            status_y = self.height - 12

            # Battery percentage
            draw.text((2, status_y), f"{battery_level}%", font=font, fill=255)

            # Solar power
            draw.text((30, status_y), f"{solar_power:.1f}W", font=small_font, fill=255)

            # Charging status
            if is_charging:
                if self.animation_frame % 30 < 15:  # Blinking indicator
                    draw.text((65, status_y), "CHG", font=small_font, fill=255)
                draw.text((90, status_y), f"{time_to_full:.1f}H", font=small_font, fill=255)
            else:
                draw.text((65, status_y), "IDLE", font=small_font, fill=255)

            self.display.image(image)
            self.display.show()

            # Increment animation
            self.animation_frame += 1
            if self.animation_frame >= 360:
                self.animation_frame = 0

        except Exception as e:
            print(f"Error in solar panel mode: {e}")

    def update_status(self, walle_state: Dict):
        """Update display based on Wall-E state"""
        if not self.available:
            return

        try:
            battery_level = walle_state.get('battery_level', 100)
            is_charging = walle_state.get('is_charging', False)
            solar_power = walle_state.get('solar_power', 0.0)

            # Auto-switch modes based on data
            if solar_power > 0.1 or is_charging:
                self.display_mode = 'solar'
                time_to_full = walle_state.get('time_to_full', 0.0)
                self.show_solar_panel_mode(battery_level, solar_power, is_charging, time_to_full)
            else:
                self.display_mode = 'normal'
                self._show_normal_status(walle_state)

        except Exception as e:
            print(f"Error updating status: {e}")

    def _show_normal_status(self, walle_state: Dict):
        """Show normal Wall-E status"""
        try:
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font = small_font = ImageFont.load_default()

            # Header
            draw.text((0, 0), "WALL-E Status", font=font, fill=255)
            draw.line([(0, 14), (128, 14)], fill=255)

            # Mode
            mode = walle_state.get('mode', 'Unknown').upper()
            draw.text((0, 16), f"Mode: {mode}", font=small_font, fill=255)

            # Battery with bar
            battery = walle_state.get('battery_level', 0)
            draw.text((0, 28), f"Battery: {battery}%", font=small_font, fill=255)

            # Safe battery bar
            bar_x, bar_y = 70, 30
            bar_width, bar_height = 50, 8

            self.safe_rectangle(draw, (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
                                outline=255, fill=0)

            fill_width = int((battery / 100.0) * (bar_width - 2))
            if fill_width > 0:
                self.safe_rectangle(draw,
                                    (bar_x + 1, bar_y + 1, bar_x + 1 + fill_width, bar_y + bar_height - 1),
                                    fill=255)

            # Connection status
            connected = walle_state.get('connected', False)
            status_text = "CONNECTED" if connected else "DISCONNECTED"
            draw.text((0, 40), f"Arduino: {status_text}", font=small_font, fill=255)

            # Time
            current_time = datetime.now().strftime("%H:%M:%S")
            draw.text((0, 52), current_time, font=small_font, fill=255)

            self.display.image(image)
            self.display.show()

        except Exception as e:
            print(f"Error in normal status: {e}")

    def set_display_mode(self, mode: str):
        """Set display mode manually"""
        if mode in ['normal', 'solar', 'battery']:
            self.display_mode = mode
            print(f"Display mode set to: {mode}")

    def clear_display(self):
        """Clear display"""
        if self.available:
            self.display.fill(0)
            self.display.show()

    def cleanup(self):
        """Clean up resources"""
        if self.available:
            self.clear_display()


# Test function
def test_fixed_solar_display():
    """Test the fixed solar display"""
    print("Testing Fixed Solar Display...")

    display = DisplayController()
    if not display.available:
        print("Display not available")
        return

    print("Testing solar mode with different battery levels...")

    # Test various battery levels
    test_levels = [100, 90, 75, 50, 25, 10, 0]

    for battery_level in test_levels:
        print(f"Testing battery level: {battery_level}%")
        display.show_solar_panel_mode(
            battery_level=battery_level,
            solar_power=1.2,
            is_charging=True,
            time_to_full=2.0
        )
        time.sleep(2)

    display.cleanup()
    print("Fixed solar display test complete!")


if __name__ == "__main__":
    test_fixed_solar_display()
#!/usr/bin/env python3
"""
Fixed Enhanced Display Controller with Proper Portrait Mode Support
Complete version with vertical solar panel interface that works correctly in portrait mode
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
        # Physical display dimensions (never change these)
        self.physical_width = width
        self.physical_height = height

        self.address = address
        self.display = None
        self.available = False
        self.last_battery_level = 100
        self.animation_frame = 0
        self.display_mode = 'solar'  # Default to solar mode

        # Set logical dimensions based on rotation
        self.rotation = rotation
        if rotation in [90, 270]:
            # Portrait mode - logical dimensions are swapped
            self.logical_width = height  # 64 pixels wide (logical)
            self.logical_height = width  # 128 pixels tall (logical)
        else:
            # Landscape mode - logical dimensions match physical
            self.logical_width = width  # 128 pixels wide
            self.logical_height = height  # 64 pixels tall

        if not I2C_AVAILABLE:
            print("✗ Display controller: Required libraries not installed")
            return

        if self._initialize_display(address, width, height):
            return

        if auto_detect:
            print(f"Display not found at 0x{address:02X}, trying auto-detection...")
            self._auto_detect_display()

    def rotate_image_for_display(self, image):
        """
        Rotate image for the physical display.
        Always creates image in PHYSICAL dimensions first, then rotates if needed.
        """
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
            self.physical_width = width
            self.physical_height = height
            self.available = True

            print(f"✓ OLED display initialized at 0x{address:02X} ({width}x{height})")
            print(f"  Rotation: {self.rotation}°")
            print(f"  Logical size: {self.logical_width}x{self.logical_height}")
            self.show_startup_message()
            return True

        except Exception as e:
            return False

    def show_startup_message(self):
        """Display Wall-E startup message"""
        if not self.available:
            return

        try:
            # Always create image in PHYSICAL dimensions
            image = Image.new("1", (self.physical_width, self.physical_height))
            draw = ImageDraw.Draw(image)

            try:
                if self.physical_height >= 64:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                else:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font = small_font = ImageFont.load_default()

            # Draw startup message for the physical display layout
            if self.rotation in [90, 270]:
                # Portrait mode startup layout
                draw.text((10, 5), "WALL-E", font=font, fill=255)
                draw.text((10, 25), "Portrait Mode", font=small_font, fill=255)
                draw.text((10, 40), f"Rotation: {self.rotation}°", font=small_font, fill=255)
            else:
                # Landscape mode startup layout
                if self.physical_height >= 64:
                    draw.text((10, 5), "WALL-E", font=font, fill=255)
                    draw.text((10, 25), "Control System", font=small_font, fill=255)
                    draw.text((10, 40), "Vertical Solar", font=small_font, fill=255)
                    draw.text((10, 52), datetime.now().strftime("%H:%M"), font=small_font, fill=255)
                else:
                    draw.text((5, 2), "WALL-E", font=font, fill=255)
                    draw.text((5, 18), "Vertical Solar", font=small_font, fill=255)

            # Rotate if needed and display
            rotated_image = self.rotate_image_for_display(image)
            self.display.image(rotated_image)
            self.display.show()

        except Exception as e:
            print(f"Error showing startup message: {e}")

    def safe_rectangle(self, draw, coords, **kwargs):
        """Draw rectangle with safe coordinates using LOGICAL dimensions"""
        x1, y1, x2, y2 = coords

        # Clamp to logical display bounds
        x1 = max(0, min(x1, self.logical_width - 1))
        y1 = max(0, min(y1, self.logical_height - 1))
        x2 = max(0, min(x2, self.logical_width - 1))
        y2 = max(0, min(y2, self.logical_height - 1))

        # Ensure x2 >= x1 and y2 >= y1
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1

        # Only draw if we have valid coordinates
        if x2 > x1 and y2 > y1:
            draw.rectangle([(x1, y1), (x2, y2)], **kwargs)

    def safe_line(self, draw, coords, **kwargs):
        """Draw line with safe coordinates using LOGICAL dimensions"""
        x1, y1, x2, y2 = coords

        # Clamp coordinates to logical bounds
        x1 = max(0, min(x1, self.logical_width - 1))
        y1 = max(0, min(y1, self.logical_height - 1))
        x2 = max(0, min(x2, self.logical_width - 1))
        y2 = max(0, min(y2, self.logical_height - 1))

        draw.line([(x1, y1), (x2, y2)], **kwargs)

    def draw_sun(self, draw, x, y, size=16, frame=0):
        """Draw animated sun with rotating rays"""
        try:
            # Clamp sun position to logical bounds
            x = max(size, min(x, self.logical_width - size))
            y = max(size, min(y, self.logical_height - size))

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
        """Draw VERTICAL charge bars - stack vertically, fill from bottom up"""
        try:
            bar_spacing = 2
            available_height = height - (bar_spacing * (num_bars - 1))
            bar_height = max(2, available_height // num_bars)

            # Calculate how many bars should be filled
            bars_to_fill = int((battery_level / 100.0) * num_bars)

            for i in range(num_bars):
                bar_y = y + i * (bar_height + bar_spacing)

                # Skip if bar would be outside logical display
                if bar_y + bar_height >= self.logical_height - 10:
                    continue

                # Draw bar outline (all bars always have outlines)
                self.safe_rectangle(draw,
                                    (x, bar_y, x + width, bar_y + bar_height),
                                    outline=255, fill=0)

                # Fill bars from bottom up (like fuel gauge filling from bottom)
                # Bottom bar (highest index) fills first
                bar_from_bottom = num_bars - 1 - i
                if bar_from_bottom < bars_to_fill:
                    # Full bar
                    self.safe_rectangle(draw,
                                        (x + 1, bar_y + 1, x + width - 1, bar_y + bar_height - 1),
                                        fill=255)
                elif bar_from_bottom == bars_to_fill:
                    # Partial bar (currently filling)
                    fill_percentage = (battery_level % (100.0 / num_bars)) / (100.0 / num_bars)
                    if fill_percentage > 0:
                        fill_width = max(1, int((width - 2) * fill_percentage))
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
                particle_x = 15 + int(3 * math.sin((frame + i * 20) * 0.1))
                particle_y = 25 + ((frame + i * 15) % 30)

                # Only show particles in the flow zone
                if particle_y < 55 and 10 < particle_x < 35:
                    # Clamp particle position to logical bounds
                    particle_x = max(0, min(particle_x, self.logical_width - 2))
                    particle_y = max(0, min(particle_y, self.logical_height - 2))

                    self.safe_rectangle(draw,
                                        (particle_x, particle_y, particle_x + 1, particle_y + 1),
                                        fill=255)

        except Exception as e:
            print(f"Error drawing vertical energy particles: {e}")

    def show_solar_panel_mode(self, battery_level: int = 85, solar_power: float = 1.2,
                              is_charging: bool = True, time_to_full: float = 2.5):
        """
        Show solar panel charging interface optimized for portrait mode

        Args:
            battery_level: Battery percentage (0-100)
            solar_power: Solar power in watts
            is_charging: Whether currently charging
            time_to_full: Hours to full charge
        """
        if not self.available:
            return

        try:
            # Create image in LOGICAL dimensions first
            image = Image.new("1", (self.logical_width, self.logical_height))
            draw = ImageDraw.Draw(image)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 7)
                tiny_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 6)
            except:
                font = small_font = tiny_font = ImageFont.load_default()

            if self.rotation in [90, 270]:
                # === PORTRAIT LAYOUT (64x128 logical) ===

                # Title at top
                draw.text((2, 0), "SOLAR", font=small_font, fill=255)
                draw.text((2, 10), "PANEL", font=tiny_font, fill=255)

                # Sun icon (top left, smaller for portrait)
                sun_x, sun_y = 15, 25
                self.draw_sun(draw, sun_x, sun_y, size=8, frame=self.animation_frame)

                # Energy flow particles (vertical flow downward)
                if is_charging:
                    self.draw_vertical_energy_particles(draw, self.animation_frame)

                # VERTICAL charge bars (center of display)
                bars_start_x = 25
                bars_start_y = 35
                bar_width = 12
                bars_height = 80  # Much taller for portrait mode

                self.draw_vertical_charge_bars(draw, bars_start_x, bars_start_y, bar_width, bars_height, battery_level, 16)

                # Right side status (stacked vertically)
                status_x = 42

                # Battery percentage
                draw.text((status_x, 40), f"{battery_level}%", font=font, fill=255)

                # Solar power
                draw.text((status_x, 55), f"{solar_power:.1f}W", font=small_font, fill=255)

                # Charging status
                if is_charging:
                    if self.animation_frame % 20 < 10:  # Blinking
                        draw.text((status_x, 70), "CHG", font=small_font, fill=255)
                    draw.text((status_x, 85), f"{time_to_full:.1f}H", font=tiny_font, fill=255)
                else:
                    draw.text((status_x, 70), "IDLE", font=small_font, fill=255)

                # Bottom status
                draw.text((2, self.logical_height - 8), "WALL-E", font=tiny_font, fill=255)
                draw.text((35, self.logical_height - 8), datetime.now().strftime("%H:%M"), font=tiny_font, fill=255)

            else:
                # === LANDSCAPE LAYOUT (128x64 logical) ===

                # Title at top left
                draw.text((2, 0), "SOLAR PANEL", font=small_font, fill=255)

                # Sun icon (top left)
                sun_x, sun_y = 20, 25
                self.draw_sun(draw, sun_x, sun_y, size=12, frame=self.animation_frame)

                # Energy flow particles
                if is_charging:
                    self.draw_vertical_energy_particles(draw, self.animation_frame)

                # Vertical charge bars for landscape
                bars_start_x = 45
                bars_start_y = 15
                bar_width = 8
                bars_height = 35

                self.draw_vertical_charge_bars(draw, bars_start_x, bars_start_y, bar_width, bars_height, battery_level, 12)

                # Right side status
                status_x = 65
                draw.text((status_x, 12), f"{battery_level}%", font=font, fill=255)
                draw.text((status_x, 24), f"{solar_power:.1f}W", font=small_font, fill=255)

                if is_charging:
                    if self.animation_frame % 20 < 10:
                        draw.text((status_x, 36), "CHG", font=small_font, fill=255)
                    draw.text((status_x, 46), f"{time_to_full:.1f}H", font=tiny_font, fill=255)
                else:
                    draw.text((status_x, 36), "IDLE", font=small_font, fill=255)

                # Bottom status
                draw.text((2, self.logical_height - 8), "WALL-E", font=tiny_font, fill=255)
                draw.text((85, self.logical_height - 8), datetime.now().strftime("%H:%M"), font=tiny_font, fill=255)

            # Convert logical image to physical display
            if self.rotation in [90, 270]:
                # For portrait mode, we need to create a physical-sized image and rotate the logical one
                physical_image = Image.new("1", (self.physical_width, self.physical_height))

                # The logical image (64x128) needs to be placed/rotated to fit physical (128x64)
                if self.rotation == 90:
                    rotated_logical = image.transpose(Image.ROTATE_270)  # Counter-rotate for display
                else:  # rotation == 270
                    rotated_logical = image.transpose(Image.ROTATE_90)  # Counter-rotate for display

                physical_image.paste(rotated_logical, (0, 0))
                final_image = physical_image
            else:
                final_image = image

            self.display.image(final_image)
            self.display.show()

            # Increment animation frame
            self.animation_frame += 1
            if self.animation_frame > 360:
                self.animation_frame = 0

        except Exception as e:
            print(f"Error showing solar panel mode: {e}")

    def update_status(self, walle_state: Dict):
        """Enhanced status update with solar mode as default"""
        if not self.available:
            return

        try:
            battery_level = walle_state.get('battery_level', 100)
            is_charging = walle_state.get('is_charging', False)
            solar_power = walle_state.get('solar_power', 0.0)

            # Solar mode is default
            self.display_mode = 'solar'

            # Only switch to other modes in special cases
            if battery_level < 15:
                self.display_mode = 'battery'

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

    def show_battery_focus(self, battery_level: int, voltage: float = 0.0, charging: bool = False):
        """Show focused battery display"""
        if not self.available:
            return

        try:
            # Create image in logical dimensions
            image = Image.new("1", (self.logical_width, self.logical_height))
            draw = ImageDraw.Draw(image)

            try:
                big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                big_font = font = small_font = ImageFont.load_default()

            # Adapt layout for orientation
            if self.rotation in [90, 270]:
                # Portrait battery layout
                draw.text((5, 5), "WALL-E", font=font, fill=255)
                draw.text((5, 20), "BATTERY", font=font, fill=255)

                # Large percentage (centered)
                percentage_text = f"{battery_level}%"
                bbox = draw.textbbox((0, 0), percentage_text, font=big_font)
                text_width = bbox[2] - bbox[0]
                x = (self.logical_width - text_width) // 2
                draw.text((x, 40), percentage_text, font=big_font, fill=255)

                # Vertical battery bar
                bar_x, bar_y = 10, 70
                bar_width, bar_height = self.logical_width - 20, 30

                # Battery outline
                self.safe_rectangle(draw, (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
                                    outline=255, fill=0)

                # Battery fill
                fill_height = int((battery_level / 100.0) * (bar_height - 2))
                if fill_height > 0:
                    self.safe_rectangle(draw,
                                        (bar_x + 1, bar_y + bar_height - 1 - fill_height,
                                         bar_x + bar_width - 1, bar_y + bar_height - 1),
                                        fill=255)

                # Status
                if voltage > 0:
                    draw.text((5, self.logical_height - 20), f"{voltage:.1f}V", font=small_font, fill=255)
                if charging:
                    draw.text((self.logical_width - 25, self.logical_height - 20), "CHG", font=small_font, fill=255)

            else:
                # Landscape battery layout (original)
                draw.text((5, 0), "WALL-E BATTERY", font=font, fill=255)

                percentage_text = f"{battery_level}%"
                bbox = draw.textbbox((0, 0), percentage_text, font=big_font)
                text_width = bbox[2] - bbox[0]
                x = (self.logical_width - text_width) // 2
                draw.text((x, 15), percentage_text, font=big_font, fill=255)

                # Horizontal battery bar
                bar_x, bar_y = 10, 42
                bar_width, bar_height = self.logical_width - 20, 12

                self.safe_rectangle(draw, (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
                                    outline=255, fill=0)

                fill_width = int((battery_level / 100.0) * (bar_width - 2))
                if fill_width > 0:
                    self.safe_rectangle(draw,
                                        (bar_x + 1, bar_y + 1, bar_x + 1 + fill_width, bar_y + bar_height - 1),
                                        fill=255)

                # Status
                if voltage > 0:
                    draw.text((5, self.logical_height - 10), f"{voltage:.1f}V", font=small_font, fill=255)
                if charging:
                    draw.text((self.logical_width - 25, self.logical_height - 10), "CHG", font=small_font, fill=255)

            # Handle rotation for display
            if self.rotation in [90, 270]:
                physical_image = Image.new("1", (self.physical_width, self.physical_height))
                if self.rotation == 90:
                    rotated_logical = image.transpose(Image.ROTATE_270)
                else:
                    rotated_logical = image.transpose(Image.ROTATE_90)
                physical_image.paste(rotated_logical, (0, 0))
                final_image = physical_image
            else:
                final_image = image

            self.display.image(final_image)
            self.display.show()

        except Exception as e:
            print(f"Error showing battery focus: {e}")

    def _show_normal_status(self, walle_state: Dict):
        """Show normal Wall-E status display"""
        try:
            image = Image.new("1", (self.logical_width, self.logical_height))
            draw = ImageDraw.Draw(image)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
            except:
                font = small_font = ImageFont.load_default()

            # Header
            draw.text((0, 0), "WALL-E Status", font=font, fill=255)
            draw.line([(0, 12), (self.logical_width, 12)], fill=255)

            # Content - adapt for orientation
            mode = walle_state.get('mode', 'Unknown').title()
            connected = walle_state.get('connected', False)
            status_text = "ONLINE" if connected else "OFFLINE"
            battery_level = walle_state.get('battery_level', 100)

            if self.rotation in [90, 270]:
                # Portrait layout - stack vertically
                draw.text((0, 14), f"Mode:", font=small_font, fill=255)
                draw.text((0, 24), mode, font=small_font, fill=255)
                draw.text((0, 34), f"Status:", font=small_font, fill=255)
                draw.text((0, 44), status_text, font=small_font, fill=255)
                draw.text((0, 54), f"Battery:", font=small_font, fill=255)
                draw.text((0, 64), f"{battery_level}%", font=small_font, fill=255)

                # Vertical battery bar
                bar_x, bar_y = 10, 80
                bar_width, bar_height = self.logical_width - 20, 20

                self.safe_rectangle(draw, (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
                                    outline=255, fill=0)

                fill_height = int((battery_level / 100.0) * (bar_height - 2))
                if fill_height > 0:
                    self.safe_rectangle(draw,
                                        (bar_x + 1, bar_y + bar_height - 1 - fill_height,
                                         bar_x + bar_width - 1, bar_y + bar_height - 1),
                                        fill=255)

                # Time at bottom
                current_time = datetime.now().strftime("%H:%M:%S")
                draw.text((0, self.logical_height - 10), current_time, font=small_font, fill=255)
            else:
                # Landscape layout (original)
                draw.text((0, 14), f"Mode: {mode}", font=small_font, fill=255)
                draw.text((0, 24), f"Status: {status_text}", font=small_font, fill=255)
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

                # Sensors and time
                sensors = walle_state.get('sensors', {})
                front = sensors.get('front', 0)
                left = sensors.get('left', 0)
                right = sensors.get('right', 0)

                draw.text((0, 44), f"Sensors: F:{front:.0f} L:{left:.0f} R:{right:.0f}",
                          font=small_font, fill=255)

                current_time = datetime.now().strftime("%H:%M:%S")
                draw.text((0, 54), current_time, font=small_font, fill=255)

            # Handle rotation for display
            if self.rotation in [90, 270]:
                physical_image = Image.new("1", (self.physical_width, self.physical_height))
                if self.rotation == 90:
                    rotated_logical = image.transpose(Image.ROTATE_270)
                else:
                    rotated_logical = image.transpose(Image.ROTATE_90)
                physical_image.paste(rotated_logical, (0, 0))
                final_image = physical_image
            else:
                final_image = image

            self.display.image(final_image)
            self.display.show()

        except Exception as e:
            print(f"Error showing normal status: {e}")

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
                # Create image in logical dimensions
                image = Image.new("1", (self.logical_width, self.logical_height))
                draw = ImageDraw.Draw(image)

                try:
                    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                    message_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                except:
                    title_font = message_font = ImageFont.load_default()

                # Center the title
                title_bbox = draw.textbbox((0, 0), title, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
                title_x = (self.logical_width - title_width) // 2

                draw.text((title_x, 10), title, font=title_font, fill=255)

                # Center the message
                message_bbox = draw.textbbox((0, 0), message, font=message_font)
                message_width = message_bbox[2] - message_bbox[0]
                message_x = (self.logical_width - message_width) // 2

                y_pos = 35 if self.rotation not in [90, 270] else 50
                draw.text((message_x, y_pos), message, font=message_font, fill=255)

                # Handle rotation for display
                if self.rotation in [90, 270]:
                    physical_image = Image.new("1", (self.physical_width, self.physical_height))
                    if self.rotation == 90:
                        rotated_logical = image.transpose(Image.ROTATE_270)
                    else:
                        rotated_logical = image.transpose(Image.ROTATE_90)
                    physical_image.paste(rotated_logical, (0, 0))
                    final_image = physical_image
                else:
                    final_image = image

                self.display.image(final_image)
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
                'physical_width': self.physical_width,
                'physical_height': self.physical_height,
                'logical_width': self.logical_width,
                'logical_height': self.logical_height,
                'rotation': self.rotation,
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
    def test_portrait_display(self):
        """Test the portrait display functionality"""
        print("Testing Portrait Display Controller...")

        # Test both orientations
        for rotation in [0, 90]:
            print(f"\n=== Testing rotation {rotation}° ===")

            display = DisplayController(auto_detect=True, rotation=rotation)

            if not display.available:
                print("Display not available for testing")
                continue

            print("Display info:", display.get_display_info())

            # Test startup
            time.sleep(2)

            print("Testing solar panel mode...")
            # Test different battery levels
            test_levels = [100, 75, 50, 25, 10]

            for battery_level in test_levels:
                print(f"  Battery level: {battery_level}%")
                display.show_solar_panel_mode(
                    battery_level=battery_level,
                    solar_power=1.2,
                    is_charging=True,
                    time_to_full=2.0
                )
                time.sleep(1.5)

            print("Testing battery focus mode...")
            display.show_battery_focus(battery_level=75, voltage=12.1, charging=True)
            time.sleep(2)

            print("Testing normal status mode...")
            test_state = {
                'mode': 'solar_charging',
                'connected': True,
                'battery_level': 85,
                'sensors': {'front': 25, 'left': 30, 'right': 20}
            }
            display._show_normal_status(test_state)
            time.sleep(2)

            print("Testing message display...")
            display.show_message("Test", "Portrait Mode", duration=2)

            display.cleanup()

        print("Portrait display test complete!")

    if __name__ == "__main__":
        test_portrait_display()
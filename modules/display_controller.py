#!/usr/bin/env python3
"""
Display Controller Module for Wall-E
Handles OLED display for status information and battery monitoring
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
    I2C_AVAILABLE = False

class DisplayController:
    def __init__(self, width=128, height=64, address=0x3C):
        """
        Initialize OLED display controller
        
        Args:
            width: Display width in pixels
            height: Display height in pixels  
            address: I2C address of the display
        """
        self.width = width
        self.height = height
        self.address = address
        self.display = None
        self.available = False
        
        if not I2C_AVAILABLE:
            print("✗ Display controller: Required libraries not installed")
            return
        
        try:
            # Initialize I2C
            i2c = busio.I2C(board.SCL, board.SDA)
            
            # Initialize display
            self.display = adafruit_ssd1306.SSD1306_I2C(width, height, i2c, addr=address)
            
            # Clear display
            self.display.fill(0)
            self.display.show()
            
            self.available = True
            print("✓ OLED display initialized")
            
            # Show startup message
            self.show_startup_message()
            
        except Exception as e:
            print(f"✗ OLED display initialization failed: {e}")
            self.available = False
    
    def show_startup_message(self):
        """Display Wall-E startup message"""
        if not self.available:
            return
        
        try:
            # Create image
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)
            
            # Try to load a font, fallback to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Draw Wall-E logo/text
            draw.text((10, 5), "WALL-E", font=font, fill=255)
            draw.text((10, 25), "Control System", font=small_font, fill=255)
            draw.text((10, 40), "Online", font=small_font, fill=255)
            draw.text((10, 52), datetime.now().strftime("%H:%M"), font=small_font, fill=255)
            
            # Display the image
            self.display.image(image)
            self.display.show()
            
        except Exception as e:
            print(f"Error showing startup message: {e}")
    
    def update_status(self, walle_state: Dict):
        """
        Update display with current Wall-E status
        
        Args:
            walle_state: Dictionary containing Wall-E status information
        """
        if not self.available:
            return
        
        try:
            # Create image
            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)
            
            # Load fonts
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Draw header
            draw.text((0, 0), "WALL-E Status", font=font, fill=255)
            draw.line([(0, 14), (128, 14)], fill=255)
            
            # Mode
            mode = walle_state.get('mode', 'Unknown').upper()
            draw.text((0, 16), f"Mode: {mode}", font=small_font, fill=255)
            
            # Battery level with visual indicator
            battery = walle_state.get('battery_level', 0)
            draw.text((0, 28), f"Battery: {battery}%", font=small_font, fill=255)
            
            # Battery bar
            bar_x = 70
            bar_y = 30
            bar_width = 50
            bar_height = 8
            
            # Battery outline
            draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)], outline=255, fill=0)
            
            # Battery fill
            fill_width = int((battery / 100.0) * (bar_width - 2))
            if fill_width > 0:
                draw.rectangle([(bar_x + 1, bar_y + 1), (bar_x + 1 + fill_width, bar_y + bar_height - 1)], fill=255)
            
            # Connection status
            connected = walle_state.get('connected', False)
            status_text = "CONNECTED" if connected else "DISCONNECTED"
            draw.text((0, 40), f"Arduino: {status_text}", font=small_font, fill=255)
            
            # Sensor readings
            sensors = walle_state.get('sensors', {})
            front = sensors.get('front', 0)
            
            if front > 0:
                draw.text((0, 52), f"Front: {front:.1f}cm", font=small_font, fill=255)
            else:
                draw.text((0, 52), "Front: --", font=small_font, fill=255)
            
            # Time
            current_time = datetime.now().strftime("%H:%M:%S")
            draw.text((85, 52), current_time, font=small_font, fill=255)
            
            # Display the image
            self.display.image(image)
            self.display.show()
            
        except Exception as e:
            print(f"Error updating display: {e}")
    
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
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                message_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                title_font = ImageFont.load_default()
                message_font = ImageFont.load_default()
            
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
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font = ImageFont.load_default()
            
            # Title
            draw.text((35, 0), "SENSORS", font=font, fill=255)
            draw.line([(0, 12), (128, 12)], fill=255)
            
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
            draw.rectangle([(center_x-8, center_y-5), (center_x+8, center_y+5)], outline=255, fill=0)
            
            # Draw sensor detection zones
            max_range = 50  # cm
            scale = 0.3  # pixels per cm
            
            # Front sensor zone
            if front > 0 and front < max_range:
                zone_length = int(front * scale)
                draw.line([(center_x, center_y-5), (center_x, center_y-5-zone_length)], fill=255)
                draw.line([(center_x-2, center_y-5-zone_length), (center_x+2, center_y-5-zone_length)], fill=255)
            
            # Left sensor zone
            if left > 0 and left < max_range:
                zone_length = int(left * scale)
                draw.line([(center_x-8, center_y), (center_x-8-zone_length, center_y)], fill=255)
                draw.line([(center_x-8-zone_length, center_y-2), (center_x-8-zone_length, center_y+2)], fill=255)
            
            # Right sensor zone
            if right > 0 and right < max_range:
                zone_length = int(right * scale)
                draw.line([(center_x+8, center_y), (center_x+8+zone_length, center_y)], fill=255)
                draw.line([(center_x+8+zone_length, center_y-2), (center_x+8+zone_length, center_y+2)], fill=255)
            
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
                center_x, center_y = 64, 32
                
                # Eyes (circles that blink)
                eye_size = 15
                eye_offset = 20
                
                if frame % 4 == 0:  # Blink frame
                    # Draw closed eyes (lines)
                    draw.line([(center_x - eye_offset - eye_size//2, center_y), 
                              (center_x - eye_offset + eye_size//2, center_y)], fill=255, width=2)
                    draw.line([(center_x + eye_offset - eye_size//2, center_y), 
                              (center_x + eye_offset + eye_size//2, center_y)], fill=255, width=2)
                else:
                    # Draw open eyes (circles)
                    draw.ellipse([(center_x - eye_offset - eye_size//2, center_y - eye_size//2),
                                 (center_x - eye_offset + eye_size//2, center_y + eye_size//2)], outline=255, fill=0)
                    draw.ellipse([(center_x + eye_offset - eye_size//2, center_y - eye_size//2),
                                 (center_x + eye_offset + eye_size//2, center_y + eye_size//2)], outline=255, fill=0)
                    
                    # Eye pupils
                    pupil_size = 4
                    draw.ellipse([(center_x - eye_offset - pupil_size//2, center_y - pupil_size//2),
                                 (center_x - eye_offset + pupil_size//2, center_y + pupil_size//2)], fill=255)
                    draw.ellipse([(center_x + eye_offset - pupil_size//2, center_y - pupil_size//2),
                                 (center_x + eye_offset + pupil_size//2, center_y + pupil_size//2)], fill=255)
                
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
            'address': hex(self.address) if self.available else None
        }
    
    def cleanup(self):
        """Clean up display resources"""
        if self.available:
            self.clear_display()
            print("Display controller cleaned up")

# Test function
def test_display_controller():
    """Test the display controller functionality"""
    print("Testing Display Controller...")
    
    display = DisplayController()
    
    if not display.available:
        print("Display not available for testing")
        return
    
    print("Display info:", display.get_display_info())
    
    # Test startup message
    time.sleep(2)
    
    # Test custom message
    print("Testing custom message...")
    display.show_message("WALL-E", "TESTING", duration=2)
    
    # Test status update
    print("Testing status update...")
    test_state = {
        'mode': 'exploring',
        'battery_level': 85,
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
    display.show_animation(frames=8)
    
    # Clear display
    display.clear_display()
    display.cleanup()
    print("Display controller test complete")

if __name__ == "__main__":
    test_display_controller()
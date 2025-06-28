#!/usr/bin/env python3
"""
OLED Display Setup and Troubleshooting - Pure Python
No shell scripts needed!
"""

import subprocess
import sys
import time
import os


def install_packages():
    """Install required packages using pip"""
    packages = [
        'adafruit-circuitpython-ssd1306',
        'pillow',
        'adafruit-circuitpython-busdevice'
    ]

    print("Installing required Python packages...")
    for package in packages:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                           check=True, capture_output=True)
            print(f"✓ Installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")


def check_i2c_devices():
    """Check for I2C devices using Python"""
    print("\nScanning for I2C devices...")

    try:
        # Try to detect I2C devices
        result = subprocess.run(['i2cdetect', '-y', '1'],
                                capture_output=True, text=True, check=True)
        print("I2C Bus 1 scan:")
        print(result.stdout)

        # Parse output to find device addresses
        devices = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        for line in lines:
            parts = line.split()[1:]  # Skip row number
            for i, part in enumerate(parts):
                if part != '--' and len(part) == 2:
                    address = int(part, 16)
                    devices.append(address)
                    print(f"Found device at address: 0x{address:02X}")

        return devices

    except subprocess.CalledProcessError:
        print("i2cdetect not available. Installing i2c-tools...")
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'i2c-tools'], check=True)
            return check_i2c_devices()  # Retry
        except:
            print("Could not install i2c-tools. Manual I2C check needed.")
            return [0x3C, 0x3D]  # Default addresses to try


def test_display_configurations():
    """Test different display configurations"""
    print("\nTesting OLED display configurations...")

    # Import after installation
    try:
        import board
        import busio
        import adafruit_ssd1306
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        print(f"Import error: {e}")
        install_packages()
        # Try importing again
        import board
        import busio
        import adafruit_ssd1306
        from PIL import Image, ImageDraw, ImageFont

    # Test configurations
    addresses = [0x3C, 0x3D]
    sizes = [(128, 64), (128, 32), (64, 48)]

    for addr in addresses:
        for width, height in sizes:
            try:
                print(f"Testing address 0x{addr:02X} with size {width}x{height}...")

                # Initialize I2C and display
                i2c = busio.I2C(board.SCL, board.SDA)
                display = adafruit_ssd1306.SSD1306_I2C(width, height, i2c, addr=addr)

                # Test basic functionality
                display.fill(0)
                display.show()

                # Create test image
                image = Image.new("1", (width, height))
                draw = ImageDraw.Draw(image)

                # Draw test content
                draw.text((0, 0), "WALL-E", fill=255)
                draw.text((0, 12), "Display Test", fill=255)
                draw.text((0, 24), f"0x{addr:02X}", fill=255)
                draw.text((0, 36), f"{width}x{height}", fill=255)

                display.image(image)
                display.show()

                print(f"✓ SUCCESS! Working configuration found:")
                print(f"  Address: 0x{addr:02X}")
                print(f"  Size: {width}x{height}")

                # Test battery display
                test_battery_display(display, width, height)

                return addr, width, height

            except Exception as e:
                print(f"  Failed: {e}")
                continue

    print("✗ No working display configuration found")
    return None, None, None


def test_battery_display(display, width, height):
    """Test battery display functionality"""
    print("Testing battery display...")

    try:
        from PIL import Image, ImageDraw, ImageFont

        # Test different battery levels
        for battery_level in [100, 75, 50, 25, 10]:
            image = Image.new("1", (width, height))
            draw = ImageDraw.Draw(image)

            # Title
            draw.text((5, 0), "WALL-E BATTERY", fill=255)

            # Battery percentage
            draw.text((5, 15), f"Level: {battery_level}%", fill=255)

            # Battery bar
            bar_x, bar_y = 10, 35
            bar_width = width - 20
            bar_height = 15

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

            # Voltage simulation
            voltage = 12.6 - (2.0 * (100 - battery_level) / 100)
            draw.text((5, 55), f"Voltage: {voltage:.1f}V", fill=255)

            display.image(image)
            display.show()

            print(f"  Showing {battery_level}% battery level")
            time.sleep(1.5)

        # Low battery warning test
        print("Testing low battery warning...")
        for i in range(3):
            # Warning screen
            image = Image.new("1", (width, height))
            draw = ImageDraw.Draw(image)

            draw.text((10, 10), "LOW BATTERY!", fill=255)
            draw.text((20, 30), "5%", fill=255)
            draw.text((10, 50), "CHARGE NOW!", fill=255)

            display.image(image)
            display.show()
            time.sleep(0.5)

            # Clear
            display.fill(0)
            display.show()
            time.sleep(0.3)

        print("✓ Battery display test completed successfully!")

    except Exception as e:
        print(f"Battery display test failed: {e}")


def enable_i2c():
    """Enable I2C interface"""
    print("Checking I2C configuration...")

    config_file = '/boot/config.txt'
    backup_file = '/boot/config.txt.backup'

    try:
        # Read current config
        with open(config_file, 'r') as f:
            config = f.read()

        # Check if I2C is already enabled
        if 'dtparam=i2c_arm=on' in config:
            print("✓ I2C already enabled in config")
            return True

        print("I2C not enabled. Enabling...")

        # Backup original config
        if not os.path.exists(backup_file):
            subprocess.run(['sudo', 'cp', config_file, backup_file], check=True)
            print("✓ Config backup created")

        # Add I2C configuration
        with open('/tmp/i2c_config', 'w') as f:
            f.write(config)
            if not config.endswith('\n'):
                f.write('\n')
            f.write('dtparam=i2c_arm=on\n')

        # Apply configuration
        subprocess.run(['sudo', 'cp', '/tmp/i2c_config', config_file], check=True)
        subprocess.run(['sudo', 'rm', '/tmp/i2c_config'], check=True)

        print("✓ I2C enabled in config")
        print("⚠️  Please reboot your Raspberry Pi for changes to take effect")
        return False

    except Exception as e:
        print(f"✗ Failed to enable I2C: {e}")
        print("Please enable I2C manually using: sudo raspi-config")
        return False


def main():
    """Main setup and test function"""
    print("=" * 50)
    print("WALL-E OLED Display Setup and Test")
    print("=" * 50)

    # Step 1: Enable I2C if needed
    i2c_enabled = enable_i2c()
    if not i2c_enabled:
        print("\nPlease reboot and run this script again.")
        return

    # Step 2: Install required packages
    install_packages()

    # Step 3: Scan for I2C devices
    devices = check_i2c_devices()
    if not devices:
        print("\n⚠️  No I2C devices found. Please check your wiring:")
        print("OLED Display -> Raspberry Pi")
        print("VCC/VDD     -> 3.3V (Pin 1 or 17)")
        print("GND         -> Ground (Pin 6, 9, 14, 20, 25, 30, 34, 39)")
        print("SDA         -> GPIO 2 (Pin 3)")
        print("SCL         -> GPIO 3 (Pin 5)")
        return

    # Step 4: Test display configurations
    addr, width, height = test_display_configurations()

    if addr is not None:
        print("\n" + "=" * 50)
        print("SUCCESS! Your display is working!")
        print("=" * 50)
        print(f"Configuration found:")
        print(f"  Address: 0x{addr:02X}")
        print(f"  Size: {width}x{height}")
        print("")
        print("Your Wall-E system will now automatically use this display!")
        print("The improved display controller includes:")
        print("  ✓ Battery level with visual bar")
        print("  ✓ Low battery warnings")
        print("  ✓ Status information")
        print("  ✓ Auto-detection")
        print("")
        print("Restart your Wall-E service to see the display in action:")
        print("  sudo systemctl restart walle-control.service")
    else:
        print("\n" + "=" * 50)
        print("Display not working - Troubleshooting")
        print("=" * 50)
        print("Possible issues:")
        print("1. Wrong wiring - double-check connections")
        print("2. Power supply - make sure you're using 3.3V, NOT 5V")
        print("3. Faulty display - try a different OLED module")
        print("4. Wrong display type - this script is for SSD1306 displays")
        print("")
        print("Manual testing commands:")
        print("  i2cdetect -y 1  # Should show device addresses")
        print("  sudo raspi-config  # Enable I2C in Interface Options")


if __name__ == "__main__":
    main()
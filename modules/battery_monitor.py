#!/usr/bin/env python3
"""
Battery Monitor Module for Wall-E
Monitors 12V LiPO battery voltage and provides battery level information
"""

import time
import threading
from typing import Dict, Optional, Callable

try:
    import board
    import busio
    import adafruit_ads1x15.ads1015 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    ADC_AVAILABLE = True
except ImportError:
    print("ADC libraries not available, using voltage divider simulation")
    ADC_AVAILABLE = False

class BatteryMonitor:
    def __init__(self, voltage_pin=None, min_voltage=9.6, max_voltage=12.6, 
                 voltage_divider_ratio=3.0, update_interval=5.0):
        """
        Initialize battery monitor
        
        Args:
            voltage_pin: GPIO pin for voltage reading (if using ADC)
            min_voltage: Minimum battery voltage (empty)
            max_voltage: Maximum battery voltage (full)
            voltage_divider_ratio: Voltage divider ratio (12V -> 4V for Pi)
            update_interval: How often to update readings (seconds)
        """
        self.voltage_pin = voltage_pin
        self.min_voltage = min_voltage
        self.max_voltage = max_voltage
        self.voltage_divider_ratio = voltage_divider_ratio
        self.update_interval = update_interval
        
        # Current readings
        self.current_voltage = 0.0
        self.battery_percentage = 100
        self.is_charging = False
        self.low_battery_warning = False
        
        # Callbacks
        self.low_battery_callback = None
        self.critical_battery_callback = None
        
        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.adc = None
        self.analog_in = None
        
        # Initialize ADC if available
        self._initialize_adc()
        
        # Start monitoring
        self.start_monitoring()
        
        print("✓ Battery monitor initialized")
    
    def _initialize_adc(self):
        """Initialize ADC for voltage reading"""
        if not ADC_AVAILABLE:
            print("Using simulated battery readings (ADC not available)")
            return
        
        try:
            # Create I2C bus
            i2c = busio.I2C(board.SCL, board.SDA)
            
            # Create ADC object
            self.adc = ADS.ADS1015(i2c)
            
            # Create analog input channel
            self.analog_in = AnalogIn(self.adc, ADS.P0)  # Using channel 0
            
            print("✓ ADC initialized for battery monitoring")
            
        except Exception as e:
            print(f"✗ ADC initialization failed: {e}")
            self.adc = None
            self.analog_in = None
    
    def read_voltage(self) -> float:
        """
        Read current battery voltage
        
        Returns:
            float: Battery voltage in volts
        """
        if self.analog_in:
            try:
                # Read voltage from ADC
                adc_voltage = self.analog_in.voltage
                
                # Convert back to battery voltage using voltage divider ratio
                battery_voltage = adc_voltage * self.voltage_divider_ratio
                
                return battery_voltage
                
            except Exception as e:
                print(f"Error reading voltage: {e}")
                return 0.0
        else:
            # Simulate battery voltage (for testing without ADC)
            # Slowly decrease over time
            base_voltage = 12.0
            time_factor = (time.time() % 3600) / 3600  # 1 hour cycle
            simulated_voltage = base_voltage - (time_factor * 2.0)  # 12V to 10V over 1 hour
            return max(9.5, simulated_voltage)
    
    def voltage_to_percentage(self, voltage: float) -> int:
        """
        Convert voltage to battery percentage
        
        Args:
            voltage: Battery voltage
            
        Returns:
            int: Battery percentage (0-100)
        """
        if voltage <= self.min_voltage:
            return 0
        elif voltage >= self.max_voltage:
            return 100
        else:
            # Linear interpolation
            percentage = ((voltage - self.min_voltage) / 
                         (self.max_voltage - self.min_voltage)) * 100
            return int(percentage)
    
    def get_battery_percentage(self) -> int:
        """Get current battery percentage"""
        return self.battery_percentage
    
    def get_battery_voltage(self) -> float:
        """Get current battery voltage"""
        return self.current_voltage
    
    def get_battery_status(self) -> Dict:
        """
        Get complete battery status
        
        Returns:
            dict: Battery status information
        """
        return {
            'voltage': self.current_voltage,
            'percentage': self.battery_percentage,
            'is_charging': self.is_charging,
            'low_battery_warning': self.low_battery_warning,
            'status': self._get_status_text(),
            'estimated_runtime': self._estimate_runtime()
        }
    
    def _get_status_text(self) -> str:
        """Get battery status as text"""
        if self.battery_percentage > 75:
            return "Excellent"
        elif self.battery_percentage > 50:
            return "Good"
        elif self.battery_percentage > 25:
            return "Fair"
        elif self.battery_percentage > 10:
            return "Low"
        else:
            return "Critical"
    
    def _estimate_runtime(self) -> Optional[float]:
        """
        Estimate remaining runtime in hours
        
        Returns:
            float: Estimated hours remaining, or None if unknown
        """
        if self.battery_percentage <= 5:
            return 0.0
        
        # Rough estimation based on typical Wall-E power consumption
        # This would need calibration based on actual usage
        base_runtime = 2.0  # hours at 100%
        estimated_runtime = (self.battery_percentage / 100.0) * base_runtime
        
        return estimated_runtime
    
    def _update_battery_readings(self):
        """Update battery readings and check for warnings"""
        # Read current voltage
        self.current_voltage = self.read_voltage()
        
        # Calculate percentage
        old_percentage = self.battery_percentage
        self.battery_percentage = self.voltage_to_percentage(self.current_voltage)
        
        # Detect charging (voltage increasing)
        if self.battery_percentage > old_percentage + 2:  # 2% threshold to avoid noise
            self.is_charging = True
        elif self.battery_percentage < old_percentage - 1:
            self.is_charging = False
        
        # Check for low battery warning
        if self.battery_percentage <= 20 and not self.low_battery_warning:
            self.low_battery_warning = True
            if self.low_battery_callback:
                self.low_battery_callback(self.battery_percentage)
        elif self.battery_percentage > 25:
            self.low_battery_warning = False
        
        # Check for critical battery
        if self.battery_percentage <= 5:
            if self.critical_battery_callback:
                self.critical_battery_callback(self.battery_percentage)
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                self._update_battery_readings()
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"Battery monitoring error: {e}")
                time.sleep(self.update_interval)
    
    def start_monitoring(self):
        """Start battery monitoring in background thread"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            print("Battery monitoring started")
    
    def stop_monitoring(self):
        """Stop battery monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        print("Battery monitoring stopped")
    
    def set_low_battery_callback(self, callback: Callable[[int], None]):
        """
        Set callback for low battery warning
        
        Args:
            callback: Function to call with battery percentage
        """
        self.low_battery_callback = callback
    
    def set_critical_battery_callback(self, callback: Callable[[int], None]):
        """
        Set callback for critical battery warning
        
        Args:
            callback: Function to call with battery percentage
        """
        self.critical_battery_callback = callback
    
    def calibrate_voltage_range(self, samples=10, sample_interval=1.0):
        """
        Calibrate voltage range by taking multiple samples
        
        Args:
            samples: Number of samples to take
            sample_interval: Time between samples
        """
        print("Calibrating battery voltage range...")
        print("Make sure battery is at known charge level")
        
        voltages = []
        for i in range(samples):
            voltage = self.read_voltage()
            voltages.append(voltage)
            print(f"Sample {i+1}: {voltage:.2f}V")
            time.sleep(sample_interval)
        
        avg_voltage = sum(voltages) / len(voltages)
        print(f"Average voltage: {avg_voltage:.2f}V")
        
        # You can manually set this as max or min voltage
        print(f"Current range: {self.min_voltage}V - {self.max_voltage}V")
        print("Update min_voltage and max_voltage based on your battery specifications")
        
        return avg_voltage
    
    def get_voltage_history(self, duration=60) -> list:
        """
        Get voltage readings over a period of time
        
        Args:
            duration: Duration in seconds
            
        Returns:
            list: List of voltage readings with timestamps
        """
        history = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            voltage = self.read_voltage()
            timestamp = time.time()
            history.append({'time': timestamp, 'voltage': voltage})
            time.sleep(1.0)
        
        return history
    
    def cleanup(self):
        """Clean up battery monitor"""
        self.stop_monitoring()
        print("Battery monitor cleaned up")

# Test function
def test_battery_monitor():
    """Test the battery monitor functionality"""
    print("Testing Battery Monitor...")
    
    def low_battery_alert(percentage):
        print(f"⚠️  LOW BATTERY ALERT: {percentage}%")
    
    def critical_battery_alert(percentage):
        print(f"🚨 CRITICAL BATTERY: {percentage}%")
    
    # Initialize monitor
    monitor = BatteryMonitor()
    monitor.set_low_battery_callback(low_battery_alert)
    monitor.set_critical_battery_callback(critical_battery_alert)
    
    # Test readings for 30 seconds
    print("Monitoring battery for 30 seconds...")
    start_time = time.time()
    
    while time.time() - start_time < 30:
        status = monitor.get_battery_status()
        print(f"Battery: {status['percentage']}% ({status['voltage']:.2f}V) - {status['status']}")
        
        if status['estimated_runtime'] is not None:
            print(f"Estimated runtime: {status['estimated_runtime']:.1f} hours")
        
        time.sleep(5)
    
    # Test calibration
    print("\nTesting voltage calibration...")
    avg_voltage = monitor.calibrate_voltage_range(samples=5, sample_interval=0.5)
    
    monitor.cleanup()
    print("Battery monitor test complete")

if __name__ == "__main__":
    test_battery_monitor()
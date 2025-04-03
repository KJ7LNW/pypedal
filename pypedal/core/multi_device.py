"""
Multi-device pedal event handling functionality
"""
import select
import click
from typing import List, Tuple, Dict
from .device import DeviceHandler
from .config import Config
from .pedal import Button
from .history import History

class MultiDeviceHandler:
    """Manages multiple pedal devices with offset button numbering"""
    
    def __init__(self, devices: List[Tuple[str, List[int]]], config: Config):
        """
        Initialize handlers for multiple devices
        
        Args:
            devices: List of (device_path, button_numbers) tuples
            config: Configuration for button patterns
        """
        self.handlers: List[DeviceHandler] = []
        self.device_fds: Dict[int, DeviceHandler] = {}
        self.config = config
        self.history = History()  # Shared history for all devices
        
        # First open all devices to get file descriptors
        device_files = []
        next_button = 1  # Counter for unique button numbers
        
        for device_path, buttons in devices:
            # Get key codes from config
            device_key_codes = config.devices.get(device_path)
            if not device_key_codes:
                raise ValueError(f"No key codes configured for device {device_path}")
                
            # Map system key codes to sequential button numbers
            key_codes = {}
            for system_key_code in device_key_codes:
                key_codes[system_key_code] = Button(next_button)
                next_button += 1
            
            # Pass shared history and key_codes to handler
            handler = DeviceHandler(device_path, key_codes=key_codes, config=config, history=self.history)
            self.handlers.append(handler)
            
            # Open device and store file descriptor mapping
            dev = open(device_path, 'rb', buffering=0)
            device_files.append(dev)
            self.device_fds[dev.fileno()] = handler
            
        # Close devices after getting FDs
        for dev in device_files:
            dev.close()
            
    def read_events(self) -> None:
        """Read events from all devices using select()"""
        try:
            # Open all device files
            device_files = []
            for handler in self.handlers:
                dev = open(handler.device_path, 'rb', buffering=0)
                device_files.append(dev)
                
            while device_files:
                try:
                    # Monitor all device FDs
                    ready, _, _ = select.select(device_files, [], [], 0.1)
                    
                    if not ready:
                        continue
                        
                    for dev in ready:
                        # Get corresponding handler
                        handler = self.device_fds[dev.fileno()]
                        
                        try:
                            # Read and process event
                            event = dev.read(DeviceHandler.EVENT_SIZE)
                            handler.process_event(event)
                        except (OSError, IOError):
                            # Handle device disconnection
                            click.secho(f"Device {handler.device_path} disconnected", fg="red", err=True)
                            device_files.remove(dev)
                            dev.close()
                            
                except Exception as e:
                    click.secho(f"Error reading from devices: {str(e)}", fg="red", err=True)
                    # Clean up remaining devices
                    for dev in device_files:
                        try:
                            dev.close()
                        except:
                            pass
                    device_files.clear()
                    return
                            
        except Exception as e:
            click.secho(f"Error reading from devices: {str(e)}", fg="red", err=True)
            raise
        finally:
            # Clean up
            for dev in device_files:
                try:
                    dev.close()
                except:
                    pass
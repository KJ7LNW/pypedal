"""
Multi-device pedal event handling functionality
"""
import click
from typing import List, Tuple, Dict
from evdev import InputDevice
from select import select
from .device import DeviceHandler
from .config import Config
from .pedal import Button, PedalState
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
        self.device_map: Dict[str, DeviceHandler] = {}
        self.device_key_codes: Dict[str, Dict[int, Button]] = {}
        self.device_shared: Dict[str, bool] = {}
        self.config = config
        self.history = History()

        # First collect all buttons for shared state
        next_button = 1
        all_buttons = []

        for device_path, buttons in devices:
            # Get key codes and shared flag from config
            device_config = config.devices.get(device_path)
            if not device_config:
                raise ValueError(f"No key codes configured for device {device_path}")

            device_key_codes, shared = device_config

            # Map system key codes to sequential button numbers
            key_codes = {}
            for system_key_code in device_key_codes:
                button = Button(next_button)
                key_codes[system_key_code] = button
                all_buttons.append(button)
                next_button += 1

            # Keep key_codes and shared flag for handler creation after state init
            self.device_key_codes[device_path] = key_codes
            self.device_shared[device_path] = shared

        # Create shared state with all buttons
        self.pedal_state = PedalState(all_buttons)

        # Now create handlers with shared state
        for device_path, _buttons in devices:
            # Pass shared history, state, key_codes and shared flag to each device handler
            handler = DeviceHandler(
                device_path,
                key_codes=self.device_key_codes[device_path],
                config=config,
                history=self.history,
                pedal_state=self.pedal_state,
                shared=self.device_shared[device_path]
            )
            self.handlers.append(handler)
            self.device_map[device_path] = handler
            
    def read_events(self) -> None:
        """Read events from all devices using select()"""
        try:
            devices = {}
            for handler in self.handlers:
                dev = InputDevice(handler.device_path)
                if not handler.shared:
                    dev.grab()
                devices[dev.fd] = (dev, handler)

            while devices:
                try:
                    fds = list(devices.keys())
                    ready, _, _ = select(fds, [], [], 0.1)

                    if not ready:
                        continue

                    for fd in ready:
                        dev, handler = devices[fd]

                        try:
                            event = dev.read_one()
                            if event is not None:
                                handler.process_event(event)
                        except (OSError, IOError):
                            click.secho(f"Device {handler.device_path} disconnected", fg="red", err=True)
                            dev.close()
                            del devices[fd]

                except Exception as e:
                    click.secho(f"Error reading from devices: {str(e)}", fg="red", err=True)
                    for dev, _ in devices.values():
                        try:
                            dev.close()
                        except:
                            pass
                    devices.clear()
                    return

        except Exception as e:
            click.secho(f"Error reading from devices: {str(e)}", fg="red", err=True)
            raise
        finally:
            for dev, _ in devices.values():
                try:
                    dev.close()
                except:
                    pass
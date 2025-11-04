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

    def __init__(self, config: Config):
        """
        Initialize handlers for multiple devices

        Args:
            config: Configuration for button patterns and devices
        """
        self.handlers: List[DeviceHandler] = []
        self.device_map: Dict[str, DeviceHandler] = {}
        self.config = config
        self.history = History()

        all_buttons = []
        seen_buttons = set()
        for device_config in config.devices:
            for button in device_config.get_buttons():
                if button not in seen_buttons:
                    all_buttons.append(button)
                    seen_buttons.add(button)

        self.pedal_state = PedalState(all_buttons)

        for device_config in config.devices:
            handler = DeviceHandler(
                device_config.path,
                key_codes=device_config.get_key_code_map(),
                buttons=device_config.get_buttons(),
                config=config,
                history=self.history,
                pedal_state=self.pedal_state,
                shared=device_config.shared
            )
            self.handlers.append(handler)
            self.device_map[device_config.path] = handler
            
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
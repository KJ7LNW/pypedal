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

    def open_devices(self) -> Dict:
        """
        Open and grab all configured devices

        Returns:
            Dictionary mapping file descriptors to (device, handler) tuples
        """
        devices = {}
        for handler in self.handlers:
            dev = InputDevice(handler.device_path)
            if not handler.shared:
                dev.grab()
            devices[dev.fd] = (dev, handler)
        return devices

    def close_devices(self, devices: Dict) -> None:
        """
        Close all devices in the provided dictionary

        Args:
            devices: Dictionary mapping file descriptors to (device, handler) tuples
        """
        for dev, _ in devices.values():
            try:
                dev.close()
            except:
                pass

    def process_one_cycle(self, devices: Dict) -> bool:
        """
        Process one select cycle, handling ready events

        Args:
            devices: Dictionary mapping file descriptors to (device, handler) tuples

        Returns:
            True if processing should continue, False if devices dict is empty
        """
        if not devices:
            return False

        continue_processing = False

        try:
            fds = list(devices.keys())
            ready, _, _ = select(fds, [], [], 0.1)

            if ready:
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

            continue_processing = len(devices) > 0

        except Exception as e:
            click.secho(f"Error reading from devices: {str(e)}", fg="red", err=True)
            self.close_devices(devices)
            devices.clear()
            continue_processing = False

        return continue_processing

    def read_events(self) -> None:
        """Read events from all devices using select()"""
        devices = {}
        try:
            devices = self.open_devices()
            while self.process_one_cycle(devices):
                pass
        except Exception as e:
            click.secho(f"Error reading from devices: {str(e)}", fg="red", err=True)
            raise
        finally:
            self.close_devices(devices)
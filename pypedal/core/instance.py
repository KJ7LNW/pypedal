"""
Instance management for multiple configuration files
"""
import os
import time
import click
from dataclasses import dataclass
from typing import Dict, List, TYPE_CHECKING
from select import select
from .config import Config
from .multi_device import MultiDeviceHandler

if TYPE_CHECKING:
    from .device import DeviceHandler

@dataclass
class Instance:
    """
    Runtime container for a single configuration instance

    Each instance represents one configuration file with its associated runtime:
    - config: Configuration data including config.config_file
    - handler: Multi-device event handler
    - devices: Dictionary mapping file descriptors to handlers for select()
    """
    config: Config
    handler: MultiDeviceHandler
    devices: Dict[int, 'DeviceHandler']

class InstanceManager:
    """Manages multiple configuration instances in a single runtime"""

    def __init__(self, quiet: bool = False, debug: bool = False, repeat_rate: float = 0.1):
        """
        Initialize instance manager

        Args:
            quiet: Suppress additional output
            debug: Show debug information
            repeat_rate: Repeat rate in seconds for patterns marked with repeat
        """
        self.instances: List[Instance] = []
        self.quiet = quiet
        self.debug = debug
        self.repeat_rate = repeat_rate

    def add_config_file(self, config_file: str) -> Instance:
        """
        Add a new configuration file as an instance

        Args:
            config_file: Path to configuration file

        Returns:
            Created Instance object
        """
        config = Config(config_file)

        if not config.devices:
            raise click.UsageError(f"No devices configured in {config_file}. Add device configs like: dev: /path/to/device [1,2,3]")

        handler = MultiDeviceHandler(config)

        instance = Instance(
            config=config,
            handler=handler,
            devices={}
        )

        self.instances.append(instance)

        if self.debug:
            click.echo(f"\nConfiguration file: {config_file}")
            click.echo("Configuration structure:")
            config.dump_structure()

        return instance

    def attempt_reconnection(self) -> None:
        """
        Check for reconnection of previously disconnected devices

        Polls device paths that were disconnected and attempts to reopen
        them if the path exists again
        """
        for instance in self.instances:
            for handler in instance.handler.handlers:
                if handler.attempt_reconnection():
                    if handler.fd is not None:
                        instance.devices[handler.fd] = handler
                        click.secho(f"Device {handler.device_path} reconnected", fg="green", err=True)

    def reload_if_changed(self) -> None:
        """
        Check all configuration files for modifications and reload if changed

        Reloads entire instance if its configuration file has been modified
        """
        for i, instance in enumerate(self.instances):
            if instance.config.reload_if_changed():
                click.secho(f"Configuration reloaded from {instance.config.config_file}", fg="green", err=True)

                self.close_instance_devices(instance)

                instance.handler = MultiDeviceHandler(instance.config)
                instance.devices = {}

                self.open_instance_devices(instance)

    def open_instance_devices(self, instance: Instance) -> None:
        """
        Open and grab all devices for a specific instance

        Args:
            instance: Instance whose devices to open
        """
        for handler in instance.handler.handlers:
            try:
                handler.open()
                if handler.fd is not None:
                    instance.devices[handler.fd] = handler
            except (FileNotFoundError, OSError, IOError, PermissionError):
                # Device does not exist yet, reconnection polling will activate when available
                pass

    def open_all_devices(self) -> None:
        """Open and grab all devices for all instances"""
        for instance in self.instances:
            self.open_instance_devices(instance)

    def close_instance_devices(self, instance: Instance) -> None:
        """
        Close all devices for a specific instance

        Args:
            instance: Instance whose devices to close
        """
        for handler in instance.handler.handlers:
            handler.close()
        instance.devices.clear()

    def close_all_devices(self) -> None:
        """Close all devices for all instances"""
        for instance in self.instances:
            self.close_instance_devices(instance)

    def calculate_select_timeout(self) -> float:
        """
        Calculate dynamic select timeout based on history state

        Timeout values:
        - 1.0 seconds when all histories empty (idle state, low CPU usage)
        - repeat_rate when any repeat pattern matches current history
        - 0.1 seconds otherwise (default polling rate)

        Returns:
            Timeout value in seconds for select() call
        """
        all_empty = True
        for instance in self.instances:
            if instance.handler.history.entries:
                all_empty = False
                break

        timeout = 0.1

        if all_empty:
            timeout = 1.0
        else:
            has_repeat = False
            for instance in self.instances:
                for handler in instance.handler.handlers:
                    repeat_patterns = handler.find_repeat_patterns()
                    if repeat_patterns:
                        has_repeat = True
                        break
                if has_repeat:
                    break

            if has_repeat:
                timeout = self.repeat_rate
            else:
                timeout = 0.1

        return timeout

    def process_one_cycle(self) -> bool:
        """
        Process one select cycle across all instances

        Polls all device file descriptors and processes ready events

        Returns:
            True if processing should continue, False if all devices closed
        """
        continue_processing = False

        try:
            self.attempt_reconnection()
            self.reload_if_changed()

            all_devices = {}
            for instance in self.instances:
                all_devices.update(instance.devices)

            if all_devices:
                fds = list(all_devices.keys())
                timeout = self.calculate_select_timeout()
                ready, _, _ = select(fds, [], [], timeout)

                if ready:
                    for fd in ready:
                        handler = all_devices[fd]

                        try:
                            event = handler.device.read_one()
                            if event is not None:
                                handler.process_event(event)
                        except (OSError, IOError):
                            click.secho(f"Device {handler.device_path} disconnected", fg="red", err=True)
                            handler.close()

                            for instance in self.instances:
                                if fd in instance.devices:
                                    del instance.devices[fd]
                                    break

                # Check and fire repeats every cycle (timer-based, not timeout-based)
                for instance in self.instances:
                    for handler in instance.handler.handlers:
                        handler.check_and_fire_repeats(self.repeat_rate)
            else:
                time.sleep(0.1)

            continue_processing = True

        except Exception as e:
            click.secho(f"Error reading from devices: {str(e)}", fg="red", err=True)
            self.close_all_devices()
            continue_processing = False

        return continue_processing

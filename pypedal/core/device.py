"""
Pedal device event handling functionality
"""
import struct
import select
import subprocess
import click
from typing import Tuple, BinaryIO, Optional
from .pedal import PedalState, ButtonEvent, Button
from .history import History
from .config import Config

# Event type mappings
EV_TYPES = {
    0: "EV_SYN",  # Synchronization event
    1: "EV_KEY",  # Key/Button event
    4: "EV_MSC"   # Miscellaneous event
}

# Key code mappings for the pedal device buttons
KEY_CODES = {
    256: Button(1),  # Left pedal button
    257: Button(2),  # Middle pedal button
    258: Button(3)   # Right pedal button
}

class DeviceHandler:
    """Handles reading and processing pedal device events"""
    EVENT_SIZE = 24  # struct input_event size
    EVENT_FORMAT = 'llHHI'  # struct input_event format

    def __init__(self, device_path: str, config: Optional[Config] = None, quiet: bool = False):
        self.device_path = device_path
        self.config = config
        self.quiet = quiet
        self.pedal_state = PedalState()
        self.history = History()

    def process_event(self, event_data: bytes) -> None:
        """Process a single event from the pedal device"""
        if not event_data:
            return

        (tv_sec, tv_usec, type_, code, value) = struct.unpack(self.EVENT_FORMAT, event_data)

        # Skip non-key events
        if type_ != 1:  # Not a key event
            return

        button = KEY_CODES.get(code)
        if button is None:
            click.echo(f"Unknown button code: {code}", err=True)
            return

        event = ButtonEvent.BUTTON_DOWN if value == 1 else ButtonEvent.BUTTON_UP

        # Update button state
        self.pedal_state.update(button, event)

        # Add to history and display event immediately
        entry = self.history.add_entry(button, event, self.pedal_state.get_state())
        if not self.quiet:
            click.echo(str(entry))

        # Check for matching patterns and execute commands
        if self.config:
            command, entries_to_consume = self.config.get_matching_command(self.history.entries, self.pedal_state.get_state())
            if command:
                try:
                    if not self.quiet:
                        click.echo(f"    Executing: {command}")
                    subprocess.run(command, shell=True, check=True)
                    # Consume matched entries to prevent re-triggering
                    if entries_to_consume:
                        self.history.entries = self.history.entries[entries_to_consume:]
                except subprocess.CalledProcessError as e:
                    click.echo(f"    Error executing command: {e}", err=True)

    def read_events(self) -> None:
        """Read and process events from the pedal device"""
        try:
            with open(self.device_path, 'rb', buffering=0) as dev:
                while True:
                    # Use select to implement a timeout and check for interrupts
                    ready, _, _ = select.select([dev], [], [], 0.1)
                    if not ready:
                        continue

                    event = dev.read(self.EVENT_SIZE)
                    self.process_event(event)

        except FileNotFoundError:
            raise
        except PermissionError:
            raise
        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)
            raise

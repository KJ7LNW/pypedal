"""
Device event handling functionality
"""
import struct
import select
import subprocess
import click
from typing import Tuple, BinaryIO, Optional
from .button import ButtonState, History
from .config import Config

# Event type mappings
EV_TYPES = {
    0: "EV_SYN",  # Synchronization event
    1: "EV_KEY",  # Key/Button event
    4: "EV_MSC"   # Miscellaneous event
}

# Key code mappings for the footpedal - using numeric identifiers
KEY_CODES = {
    256: "1",  # Left pedal
    257: "2",  # Middle pedal
    258: "3"   # Right pedal
}

class DeviceHandler:
    """Handles reading and processing device events"""
    EVENT_SIZE = 24  # struct input_event size
    EVENT_FORMAT = 'llHHI'  # struct input_event format

    def __init__(self, device_path: str, config: Optional[Config] = None, quiet: bool = False, history_timeout: float = 1.0):
        self.device_path = device_path
        self.config = config
        self.quiet = quiet
        self.button_state = ButtonState()
        self.history = History(timeout=history_timeout)

    def process_event(self, event_data: bytes) -> None:
        """Process a single event from the device"""
        if not event_data:
            return

        (tv_sec, tv_usec, type_, code, value) = struct.unpack(self.EVENT_FORMAT, event_data)

        # Skip non-key events
        if type_ != 1:  # Not a key event
            return

        button = KEY_CODES.get(code, f"Unknown({code})")
        state = "pressed" if value == 1 else "released"

        # Update button state
        self.button_state.update(button, value == 1)

        # Add to history and display event immediately
        entry = self.history.add_entry(button, state, self.button_state.get_state())
        click.echo(str(entry))

        # Clean up old entries for released buttons
        self.history.cleanup_old_entries(self.button_state.get_state())

        # Check for matching patterns and execute commands
        if self.config:
            command, entries_to_consume = self.config.get_matching_command(self.history.entries)
            if command:
                try:
                    click.echo(f"    Executing: {command}")
                    subprocess.run(command, shell=True, check=True)
                    # Consume matched entries to prevent re-triggering
                    if entries_to_consume:
                        self.history.entries = self.history.entries[entries_to_consume:]
                except subprocess.CalledProcessError as e:
                    click.echo(f"    Error executing command: {e}", err=True)

    def read_events(self) -> None:
        """Read and process events from the device"""
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

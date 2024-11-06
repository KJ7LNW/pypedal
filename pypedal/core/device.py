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

    def __init__(self, device_path: str, config: Optional[Config] = None, quiet: bool = False):
        self.device_path = device_path
        self.config = config
        self.quiet = quiet
        self.button_state = ButtonState()
        self.history = History()

    def process_event(self, event_data: bytes) -> None:
        """Process a single event from the device"""
        if not event_data:
            return

        (tv_sec, tv_usec, type_, code, value) = struct.unpack(self.EVENT_FORMAT, event_data)

        # Skip synchronization events (type 0) to reduce noise
        if type_ == 0:
            return

        type_name = EV_TYPES.get(type_, f"Unknown({type_})")

        if type_ == 1:  # Key events
            button = KEY_CODES.get(code, f"Unknown({code})")
            state = "pressed" if value == 1 else "released"

            # Update button state
            self.button_state.update(button, value == 1)

            # Add to history
            self.history.add_entry(button, state, self.button_state.get_state())

            # Check for matching patterns and execute commands
            if self.config:
                command, entries_to_consume = self.config.get_matching_command(self.history.entries)
                if command:
                    try:
                        subprocess.run(command, shell=True, check=True)
                        # Consume matched entries to prevent re-triggering
                        if entries_to_consume:
                            self.history.entries = self.history.entries[entries_to_consume:]
                    except subprocess.CalledProcessError as e:
                        click.echo(f"Error executing command: {e}", err=True)

            # Display updated history
            self.history.display_all()
        else:
            if not self.quiet:
                click.echo(f"Event: {type_name}, code={code}, value={value}")

    def read_events(self) -> None:
        """Read and process events from the device"""
        if not self.quiet:
            click.echo(f"Reading events from: {self.device_path}")
            if self.config:
                click.echo("Configuration loaded")
            click.echo("Press Ctrl+C to stop")
            click.echo("\nHistory (B1/B2/B3: + = pressed, - = released):")
            click.echo("-" * 60)

        try:
            with open(self.device_path, 'rb') as dev:
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

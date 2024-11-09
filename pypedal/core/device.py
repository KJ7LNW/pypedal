"""
Pedal device event handling functionality
"""
import struct
import select
import subprocess
import click
from typing import Tuple, BinaryIO, Optional, List
from .pedal import PedalState, ButtonEvent, Button
from .history import History
from .config import Config, ButtonEventPattern

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

    def __init__(self, device_path: str, config: Config = None, quiet: bool = False):
        self.device_path = device_path
        self.config = config
        self.quiet = quiet
        self.pedal_state = PedalState()
        self.history = History()

    def find_matching_patterns(self) -> List[ButtonEventPattern]:
        """Compare current history with configured patterns and return matching prefixes"""
        if not self.config or not self.history.entries:
            return []

        matching_patterns = []
        current_time = self.history.entries[-1].timestamp
        current_states = self.pedal_state.get_state()

        for pattern in self.config.patterns:
            history_len = len(self.history.entries)
            pattern_len = min(len(pattern.sequence), history_len)
            matches = True

            for i in range(pattern_len):
                pattern_element = pattern.sequence[i]
                history_entry = self.history.entries[i]

                if not pattern_element.matches(history_entry):
                    matches = False
                    break

                if i > 0:
                    time_diff = (history_entry.timestamp - self.history.entries[0].timestamp).total_seconds()
                    if time_diff > pattern.time_constraint:
                        matches = False
                        break

            if matches:
                matching_patterns.append(pattern)

        return matching_patterns

    def process_event(self, event_data: bytes) -> None:
        """Process a single event from the pedal device"""
        if not event_data:
            return

        (tv_sec, tv_usec, type, code, value) = struct.unpack(self.EVENT_FORMAT, event_data)

        # Skip non-key events
        if type != 1:  # Not a key event
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

        # display history
        self.history.display_all()

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

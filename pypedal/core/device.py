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
        """
        Find patterns that match the current button event sequence to determine which command to execute.
        
        A pattern matches when:
        1. Length matches history - ensures complete patterns only, preventing partial matches
           e.g. "1v,2" won't match just on "1v" press
        
        2. Time constraints met - for patterns requiring quick button combinations
           e.g. if "1v,2 < 0.5" requires button 2 within 0.5s of holding 1
        
        3. Button sequence matches exactly - both numbers and press/release types
           e.g. "1v,2v" needs button 1 held while 2 pressed
           e.g. "2v,2^" needs button 2 pressed then released
        
        4. Usage limits not exceeded - critical for single vs multi-button patterns
           - Single button "1" sets max_use=0 to prevent combining with others
           - Multi-button "1v,2" allows reuse (max_use=None) for combinations
        """
        if not self.config or not self.history.entries:
            return []

        matching_patterns = []
        history = self.history.entries
        history_len = len(history)

        # Check each history entry against pattern sequences
        for i in range(history_len):
            if i > 0:
                time_diff = (history[i].timestamp - history[0].timestamp).total_seconds()

            # Check each pattern
            for pattern in self.config.patterns:
                # Must match complete patterns only, not partial sequences
                if len(pattern.sequence) != history_len:
                    continue

                # Time between button presses must be within constraint
                # Critical for patterns requiring quick combinations
                if i > 0 and time_diff > pattern.time_constraint:
                    continue

                # Check all history entries up to current index
                matches = True
                for j in range(i + 1):
                    # Button numbers and press/release types must match exactly
                    # e.g. "1v,2v" needs button 1 held while 2 pressed
                    if not pattern.sequence[j].matches(history[j]):
                        matches = False
                        break

                    # Check usage limits to handle single vs multi-button patterns
                    # max_use=0 prevents single buttons combining with longer sequences
                    # max_use=None allows multi-button combinations
                    if pattern.sequence[j].max_use is not None and history[j].used > pattern.sequence[j].max_use:
                        matches = False
                        break

                # Only complete matches trigger commands (last iteration)
                if matches and i == history_len - 1:
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

        # Update internal button state tracking
        self.pedal_state.update(button, event)

        # Record event in history for pattern matching
        entry = self.history.add_entry(button, event, self.pedal_state.get_state())
        if not self.quiet:
            click.echo(str(entry))

        # Display current history
        self.history.display_all()

        # Find matching patterns
        matching_patterns = self.find_matching_patterns()

        if not self.quiet:
            click.echo("\nMatching patterns:")
            for pattern in matching_patterns:
                click.echo(f"  - {pattern}")
            click.echo("")

        # Execute matching patterns
        if (len(matching_patterns)):
            cmd = matching_patterns[0].command
            if not self.quiet:
                click.echo(f"  - run: {cmd}")
            subprocess.run(cmd, shell=True, check=True)

            # Mark history entries as used to prevent reuse
            self.history.set_used()

        # Clean up history after command execution
        self.history.pop_released(self.pedal_state.get_state())

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

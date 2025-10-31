"""
Pedal device event handling functionality
"""
import subprocess
import click
from typing import Optional, List, Dict
from evdev import InputDevice, ecodes
from .pedal import PedalState, ButtonEvent, Button
from .history import History
from .config import Config, ButtonEventPattern

class DeviceHandler:
    """Handles reading and processing pedal device events"""

    def __init__(self, device_path: str, key_codes: Dict[int, Button], config: Config = None,
                 quiet: bool = False, history: History = None, pedal_state: PedalState = None,
                 shared: bool = False):
        """
        Initialize device handler

        Args:
            device_path: Path to input device
            key_codes: Mapping of system key codes to button numbers
            config: Button pattern configuration
            quiet: Suppress output
            history: Shared history for pattern matching
            pedal_state: Shared state for button tracking
            shared: Allow other programs to see device events
        """
        self.device_path = device_path
        self.key_codes = key_codes
        self.config = config
        self.quiet = quiet
        self.shared = shared

        # Use provided shared state or create new one
        if pedal_state is not None:
            self.pedal_state = pedal_state
        else:
            self.pedal_state = PedalState(buttons=list(key_codes.values()))
        # Use provided history or create new one
        self.history = history if history is not None else History()

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

    def process_event(self, event) -> None:
        """
        Process a single event from the pedal device

        Args:
            event: evdev.InputEvent object
        """
        if event is None:
            return

        # Skip non-key events
        if event.type != ecodes.EV_KEY:
            return

        button = self.key_codes.get(event.code)
        if button is None:
            click.secho(f"  Error: Unknown button code: {event.code}", fg="red", err=True)
            return

        button_event = ButtonEvent.BUTTON_DOWN if event.value == 1 else ButtonEvent.BUTTON_UP

        # Update internal button state tracking
        self.pedal_state.update(button, button_event)

        # Record event in history for pattern matching
        entry = self.history.add_entry(button, button_event, self.pedal_state.get_state())

        # Display current history
        if not self.quiet:
            self.history.display_all()

        # Find and execute matching patterns
        matching_patterns = self.find_matching_patterns()
        if matching_patterns:
            pattern = matching_patterns[0]
            if not self.quiet:
                click.secho("  Patterns run:", bold=True)
                click.secho(f"   - {pattern.sequence_str()}: {click.style(pattern.command, fg='yellow', bold=True)}", fg="cyan")

            # Execute the command
            subprocess.run(pattern.command, shell=True, check=True)

            # Mark history entries as used to prevent reuse
            self.history.set_used()

        # Clean up history after command execution
        self.history.pop_released(self.pedal_state.get_state())

    def read_events(self) -> None:
        """Read and process events from the pedal device"""
        try:
            with InputDevice(self.device_path) as device:
                if not self.shared:
                    device.grab()

                while True:
                    event = device.read_one()
                    if event is not None:
                        self.process_event(event)

        except FileNotFoundError:
            raise
        except PermissionError:
            raise
        except Exception as e:
            click.secho(f"  Error: {str(e)}", fg="red", err=True)
            raise

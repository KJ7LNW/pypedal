"""
Pedal device event handling functionality
"""
import os
import subprocess
import time
import click
from typing import Optional, List, Dict
from evdev import InputDevice, ecodes
from .pedal import PedalState, ButtonEvent, Button
from .history import History
from .config import Config, ButtonEventPattern

class DeviceHandler:
    """Handles reading and processing pedal device events"""

    def __init__(self, device_path: str, key_codes: Dict, buttons: List[Button],
                 config: Config = None, quiet: bool = False, history: History = None,
                 pedal_state: PedalState = None, shared: bool = False):
        """
        Initialize device handler

        Args:
            device_path: Path to input device
            key_codes: Mapping of (type,code,value) tuples to (button,auto_release) tuples
            buttons: List of Button objects for this device
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
        self.device: Optional[InputDevice] = None
        self.last_repeat_time: Optional[float] = None

        if pedal_state is not None:
            self.pedal_state = pedal_state
        else:
            self.pedal_state = PedalState(buttons=buttons)

        self.history = history if history is not None else History()

    def open(self) -> None:
        """
        Open device and grab if not shared

        Creates InputDevice and grabs it exclusively unless shared mode enabled
        """
        if self.device is not None:
            return

        self.device = InputDevice(self.device_path)
        if not self.shared:
            self.device.grab()

    def close(self) -> None:
        """
        Close device and clear reference

        Releases device resources and sets device to None
        """
        if self.device is None:
            return

        try:
            self.device.close()
        except:
            pass
        self.device = None

    @property
    def fd(self) -> Optional[int]:
        """
        Get file descriptor for select()

        Returns:
            File descriptor if device is open, None otherwise
        """
        return self.device.fd if self.device is not None else None

    @property
    def is_connected(self) -> bool:
        """
        Check if device is currently connected

        Returns:
            True if device is open, False otherwise
        """
        return self.device is not None

    def attempt_reconnection(self) -> bool:
        """
        Attempt to reconnect to disconnected device

        Returns:
            True if reconnection successful, False otherwise
        """
        if self.is_connected:
            return False

        if not os.path.exists(self.device_path):
            return False

        try:
            self.open()
            return True
        except (OSError, IOError, PermissionError):
            return False

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

    def find_repeat_patterns(self) -> List[ButtonEventPattern]:
        """
        Find repeat patterns matching current history, ignoring max_use constraints

        Repeat patterns can fire continuously without consuming history entries.
        This differs from find_matching_patterns() which respects max_use limits
        to prevent single-button patterns from combining with longer sequences.

        Returns:
            List of repeat-enabled patterns matching current history state
        """
        if not self.config or not self.history.entries:
            return []

        matching = []
        history = self.history.entries
        history_len = len(history)

        for pattern in self.config.patterns:
            if not pattern.repeat:
                continue

            if len(pattern.sequence) != history_len:
                continue

            if history_len > 1:
                time_diff = (history[-1].timestamp - history[0].timestamp).total_seconds()
                if time_diff > pattern.time_constraint:
                    continue

            matches = True
            for j in range(history_len):
                if not pattern.sequence[j].matches(history[j]):
                    matches = False
                    break

            if matches:
                matching.append(pattern)

        return matching

    def check_and_fire_repeats(self, repeat_rate: float) -> None:
        """
        Check timer and fire repeat patterns if interval elapsed

        Uses monotonic time as single source of truth for repeat timing.
        Timer is independent of select() behavior, ensuring consistent
        intervals without jitter from spurious events.

        First repeat fires after 2x interval to prevent rapid double-fire.
        Subsequent repeats fire at normal interval.

        Args:
            repeat_rate: Seconds between repeat fires

        Fires when:
        - Repeat patterns match current history AND
        - Timer interval has elapsed (2x for first repeat, 1x for subsequent)
        """
        repeat_patterns = self.find_repeat_patterns()

        if not repeat_patterns:
            self.last_repeat_time = None
            return

        now = time.monotonic()
        should_fire = False
        required_interval = repeat_rate

        if self.last_repeat_time is None:
            should_fire = False
        elif self.last_repeat_time < 0:
            required_interval = repeat_rate * 2
            elapsed = now - abs(self.last_repeat_time)
            if elapsed >= required_interval:
                should_fire = True
        elif (now - self.last_repeat_time) >= repeat_rate:
            should_fire = True
        else:
            should_fire = False

        if not should_fire:
            return

        self.last_repeat_time = now

        instance_label = None
        if self.config and self.config.config_file:
            instance_label = os.path.basename(self.config.config_file)

        for pattern in repeat_patterns:
            if not self.quiet:
                header = "  Repeat pattern:"
                if instance_label:
                    header = f"  Repeat pattern [{instance_label}]:"
                click.secho(header, bold=True)
                click.secho(f"   - {pattern.sequence_str()}: {click.style(pattern.command, fg='yellow', bold=True)}", fg="cyan")

            try:
                subprocess.run(pattern.command, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                if not self.quiet:
                    click.secho(f"  Warning: Repeat command failed (exit code {e.returncode})", fg="yellow", err=True)

    def process_event(self, event) -> None:
        """
        Process a single event from the pedal device

        Args:
            event: evdev.InputEvent object
        """
        if event is None:
            return

        # Look up button using (type, code, value) tuple
        key = (event.type, event.code, event.value)
        mapping = self.key_codes.get(key)
        if mapping is None:
            return

        button, auto_release = mapping

        if auto_release:
            self.pedal_state.update(button, ButtonEvent.BUTTON_DOWN)
            self.history.add_entry(button, ButtonEvent.BUTTON_DOWN, self.pedal_state.get_state())
            self.pedal_state.update(button, ButtonEvent.BUTTON_UP)
            self.history.add_entry(button, ButtonEvent.BUTTON_UP, self.pedal_state.get_state())
        elif event.value == 1:
            button_event = ButtonEvent.BUTTON_DOWN
            self.pedal_state.update(button, button_event)
            self.history.add_entry(button, button_event, self.pedal_state.get_state())
        elif event.value == 0:
            button_event = ButtonEvent.BUTTON_UP
            self.pedal_state.update(button, button_event)
            self.history.add_entry(button, button_event, self.pedal_state.get_state())
        else:
            click.secho(f"  Warning: Unexpected event value {event.value} for button {button}", fg="yellow", err=True)
            return

        # Derive instance label from config
        instance_label = None
        if self.config and self.config.config_file:
            instance_label = os.path.basename(self.config.config_file)

        # Display current history
        if not self.quiet:
            self.history.display_all(instance_label)

        # Find and execute matching patterns
        matching_patterns = self.find_matching_patterns()
        if matching_patterns:
            pattern = matching_patterns[0]
            if not self.quiet:
                header = "  Patterns run:"
                if instance_label:
                    header = f"  Patterns run [{instance_label}]:"
                click.secho(header, bold=True)
                click.secho(f"   - {pattern.sequence_str()}: {click.style(pattern.command, fg='yellow', bold=True)}", fg="cyan")

            # Execute the command
            subprocess.run(pattern.command, shell=True, check=True)

            # Mark history entries as used to prevent reuse, unless pattern repeats
            # Repeat patterns skip incrementing used counter to allow continuous matching
            if not pattern.repeat:
                self.history.set_used()
            else:
                self.last_repeat_time = -time.monotonic()

        # Clean up history after command execution
        self.history.pop_released(self.pedal_state.get_state())

        # Reset repeat timer when history is cleared
        if not self.history.entries:
            self.last_repeat_time = None

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

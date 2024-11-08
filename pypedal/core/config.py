"""
Configuration and command pattern handling for pedal device
"""
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from .pedal import HistoryEntry, ButtonEvent, Button
from pprint import pprint

@dataclass
class ButtonEventPatternElement:
    """Represents a single button event element in a sequence"""
    button: Button
    event: ButtonEvent

    def __str__(self) -> str:
        return f"{self.button}{'v' if self.event == ButtonEvent.BUTTON_DOWN else '^'}"

    def __repr__(self) -> str:
        return str(self)

    def matches(self, history_entry: HistoryEntry) -> bool:
        """Check if this element matches a history entry"""
        return (history_entry.button == self.button and 
                history_entry.event == self.event)

@dataclass
class ButtonEventPattern:
    """Represents a sequence of pedal button events with timing and command info"""
    sequence: List[ButtonEventPatternElement]
    time_constraint: float = float('inf')
    command: str = ""
    line_number: int = 0

    def __str__(self) -> str:
        pattern = ",".join(str(element) for element in self.sequence)
        if self.time_constraint != float('inf'):
            pattern += f" < {self.time_constraint}"
        pattern += f": {self.command}"
        return pattern

    def __repr__(self) -> str:
        return str(self)

    def matches_history(self, history: List[HistoryEntry], current_time: datetime, pressed_buttons: Dict[Button, ButtonEvent]) -> Tuple[bool, Optional[int]]:
        """
        Check if this pattern matches the recent history and current pressed button state.
        Returns (matches, match_length) where match_length is the number of history entries to consume.
        """
        if not history or len(history) < len(self.sequence):
            return False, None

        # Skip this pattern if any currently pressed buttons are not used in this pattern
        pattern_buttons = set(element.button for element in self.sequence)
        if any(button for button, state in pressed_buttons.items() if state == ButtonEvent.BUTTON_DOWN and button not in pattern_buttons):
            return False, None

        # Try to find a match starting at each possible position
        for i in range(len(history) - len(self.sequence) + 1):
            matches = True
            first_timestamp = history[i].timestamp

            # Check each event in the sequence
            for j, element in enumerate(self.sequence):
                if not element.matches(history[i + j]):
                    matches = False
                    break

                # Check time constraint
                time_diff = (history[i + j].timestamp - first_timestamp).total_seconds()
                if time_diff > self.time_constraint:
                    matches = False
                    break

            if matches:
                # Check if the last event is within the time constraint
                last_event_time = history[i + len(self.sequence) - 1].timestamp
                if (current_time - last_event_time).total_seconds() > self.time_constraint:
                    continue

                # Return the number of history entries that matched
                return True, len(self.sequence)

        return False, None

class Config:
    """Handles configuration file parsing and storage for the pedal device"""
    def __init__(self, config_file: str = None):
        self.patterns: List[ButtonEventPattern] = []
        if config_file and os.path.exists(config_file):
            self.load(config_file)

    def __str__(self) -> str:
        return "\n".join(str(pattern) for pattern in self.patterns)

    def __repr__(self) -> str:
        return str(self)

    def load_line(self, line: str, line_number: int = 0) -> None:
        """Load a single configuration line"""
        # Split pattern and command
        match = re.match(r'^([^:]+):(.*)$', line)
        if not match:
            return

        pattern_str = match.group(1).strip()
        command = match.group(2).split('#')[0].strip()

        # Match pattern for timing constraint
        timing_match = re.match(r'^(.*?)(?:\s*<\s*([0-9.]+))?$', pattern_str)
        if not timing_match:
            return

        sequence_str = timing_match.group(1).strip()
        time_constraint = float(timing_match.group(2)) if timing_match.group(2) else float('inf')

        # Parse sequence parts
        sequence = []
        parts = sequence_str.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Handle explicit v/^ notation for button press/release
            if part.endswith('v') or part.endswith('^'):
                button = Button(int(part[:-1]))
                event = part[-1]
                event_type = ButtonEvent.BUTTON_DOWN if event == 'v' else ButtonEvent.BUTTON_UP
                sequence.append(ButtonEventPatternElement(button, event_type))
            else:
                # Implicit press/release for single button
                button = Button(int(part))
                sequence.append(ButtonEventPatternElement(button, ButtonEvent.BUTTON_DOWN))
                sequence.append(ButtonEventPatternElement(button, ButtonEvent.BUTTON_UP))

        if sequence:
            self.patterns.append(ButtonEventPattern(sequence, time_constraint, command, line_number))

    def load(self, config_file: str) -> None:
        """Load configuration from file"""
        with open(config_file, 'r') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    self.load_line(line, line_number)

    def get_matching_command(self, history: List[HistoryEntry], pressed_buttons: Dict[Button, ButtonEvent]) -> Tuple[Optional[str], Optional[int]]:
        """
        Get command for the best matching pattern in history.
        Returns (command, entries_to_consume) where entries_to_consume is the number
        of history entries that should be consumed after executing the command.
        """
        current_time = datetime.now()
        
        # Sort patterns by line number (ascending)
        sorted_patterns = sorted(
            self.patterns,
            key=lambda p: p.line_number
        )
        
        best_match = None
        best_match_length = 0
        
        for pattern in sorted_patterns:
            matches, match_length = pattern.matches_history(history, current_time, pressed_buttons)
            if matches and match_length > best_match_length:
                best_match = pattern
                best_match_length = match_length
        
        if best_match:
            return best_match.command, best_match_length
        
        return None, None

    def dump_structure(self) -> None:
        """Display the in-memory structure of the configuration"""
        pprint(self.patterns)

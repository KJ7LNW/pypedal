"""
Configuration and command pattern handling for pedal device
"""
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from .pedal import ButtonEvent, Button
from .history import HistoryEntry
from pprint import pprint

@dataclass
class ButtonEventPatternElement:
    """
    Represents a single button event element in a sequence
    
    max_use controls how many times this element can be used in pattern matching:
    - None: unlimited uses, typical for explicit v/^ patterns like "1v,2"
    - 0: single-use only, used for implicit patterns like "1" to prevent combining
    """
    button: Button
    event: ButtonEvent
    max_use: int = None

    def __str__(self) -> str:
        return f"{self.button}{'v' if self.event == ButtonEvent.BUTTON_DOWN else '^'}"

    def __repr__(self) -> str:
        return str(self)

    def matches(self, history_entry: HistoryEntry) -> bool:
        """
        Check if this element matches a history entry
        Verifies both button number and event type (DOWN/UP) match
        """
        return (history_entry.button == self.button and 
                history_entry.event == self.event)

@dataclass
class ButtonEventPattern:
    """
    Represents a sequence of pedal button events with timing and command info
    
    Handles three types of patterns:
    1. Explicit multi-button (1v,2): Requires holding specific buttons
    2. Implicit single-button (1): Press and release triggers command
    3. Press-release pairs (2v,2^): Explicit press and release sequence
    """
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

    def find_matching_patterns(self, history: List[HistoryEntry], current_time: datetime, pressed_buttons: Dict[Button, ButtonEvent]) -> List[ButtonEventPattern]:
        """
        Find all patterns that match the current history as a full or partial prefix.
        
        Matches patterns against history considering:
        1. Button numbers and event types match
        2. Time constraints between events are met
        3. Usage limits (max_use) are not exceeded
        """
        if not history:
            return []

        matching_patterns = []
        for pattern in self.patterns:
            history_len = len(history)
            pattern_len = min(len(pattern.sequence), history_len)
            matches = True

            for i in range(pattern_len):
                pattern_element = pattern.sequence[i]
                history_entry = history[i]

                # Check both button number and event type match
                if not pattern_element.matches(history_entry):
                    matches = False
                    break

                # Verify time constraints between events
                if i > 0:
                    time_diff = (history_entry.timestamp - history[0].timestamp).total_seconds()
                    if time_diff > pattern.time_constraint:
                        matches = False
                        break

            if matches:
                matching_patterns.append(pattern)

        return matching_patterns

    def load_line(self, line: str, line_number: int = 0) -> None:
        """
        Load a single configuration line
        
        Handles pattern formats:
        1. "1v,2: command" - Explicit multi-button sequence
        2. "1: command" - Implicit single button press-release, where max_use must be 0
        3. "2v,2^: command" - Explicit press-release sequence
        """
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
                # Implicit press/release for single button, so cannot
                # be used with any other combinations (max_use=0)
                button = Button(int(part))
                sequence.append(ButtonEventPatternElement(button, ButtonEvent.BUTTON_DOWN,
                                                          max_use=0))
                sequence.append(ButtonEventPatternElement(button, ButtonEvent.BUTTON_UP,
                                                          max_use=0))

        if sequence:
            self.patterns.append(ButtonEventPattern(sequence, time_constraint, command, line_number))

    def load(self, config_file: str) -> None:
        """Load configuration from file"""
        with open(config_file, 'r') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    self.load_line(line, line_number)

    def dump_structure(self) -> None:
        """Display the in-memory structure of the configuration"""
        pprint(self.patterns)

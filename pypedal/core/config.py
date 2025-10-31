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
        pattern = self.sequence_str()
        if self.time_constraint != float('inf'):
            pattern += f" < {self.time_constraint}"
        pattern += f": {self.command}"
        return pattern

    def __repr__(self) -> str:
        return str(self)
    
    def sequence_str(self):
        return ",".join(str(element) for element in self.sequence)

class Config:
    """Handles configuration file parsing and storage for the pedal device"""
    def __init__(self, config_file: str = None):
        self.patterns: List[ButtonEventPattern] = []
        self.devices: Dict[str, Tuple[List[int], bool]] = {}  # Maps device paths to (key codes, shared flag)
        if config_file and os.path.exists(config_file):
            self.load(config_file)

    def __str__(self) -> str:
        return "\n".join(str(pattern) for pattern in self.patterns)

    def __repr__(self) -> str:
        return str(self)

    def load_device_config(self, line: str) -> bool:
        """Parse device configuration line if present"""
        dev_match = re.match(r'^dev:\s*([^\s]+)\s*\[([\d,\s]+)\](?:\s*\[shared\])?', line)
        if dev_match:
            device_path = dev_match.group(1)
            key_codes = [int(code.strip()) for code in dev_match.group(2).split(',')]
            shared = bool(re.search(r'\[shared\]', line))
            self.devices[device_path] = (key_codes, shared)
            return True
        return False

    def load_line(self, line: str, line_number: int = 0) -> None:
        """
        Load a single configuration line
        
        Handles formats:
        1. "dev: /dev/input/eventX [code1,code2,...]" - Device configuration
        2. "1v,2: command" - Explicit multi-button sequence
        3. "1: command" - Implicit single button press-release
        4. "2v,2^: command" - Explicit press-release sequence
        """

        # Try to parse as device config first
        if self.load_device_config(line):
            return

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
        print("Devices:")
        pprint(self.devices)
        print("\nPatterns:")
        pprint(self.patterns)

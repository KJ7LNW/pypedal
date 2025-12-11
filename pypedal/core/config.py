"""
Configuration and command pattern handling for pedal device
"""
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from evdev import ecodes
from .pedal import ButtonEvent, Button
from .history import HistoryEntry
from pprint import pprint

@dataclass
class EventMapping:
    """Maps input event type/code/value to button number"""
    event_type: int
    event_code: int
    event_value: int
    button: Button
    auto_release: bool = False

@dataclass
class DeviceConfig:
    """Device configuration with all settings"""
    path: str
    mappings: List[EventMapping]
    shared: bool = False

    def get_key_code_map(self) -> Dict[Tuple[int, int, int], Tuple[Button, bool]]:
        """
        Build lookup dictionary for event processing

        Returns:
            Dictionary mapping (event_type, event_code, event_value) to (button, auto_release)
        """
        key_codes = {}
        for mapping in self.mappings:
            key = (mapping.event_type, mapping.event_code, mapping.event_value)
            key_codes[key] = (mapping.button, mapping.auto_release)
        return key_codes

    def get_buttons(self) -> List[Button]:
        """
        Extract unique buttons from mappings

        Returns:
            List of unique Button objects configured for this device
        """
        seen = set()
        buttons = []
        for mapping in self.mappings:
            if mapping.button not in seen:
                buttons.append(mapping.button)
                seen.add(mapping.button)
        return buttons

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
    repeat: bool = False

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
        self.config_file: str = config_file
        self.mtime: float = 0.0
        self.patterns: List[ButtonEventPattern] = []
        self.devices: List[DeviceConfig] = []
        if config_file and os.path.exists(config_file):
            self.load(config_file)

    def __str__(self) -> str:
        return "\n".join(str(pattern) for pattern in self.patterns)

    def __repr__(self) -> str:
        return str(self)

    def get_next_button_number(self) -> int:
        """
        Calculate next available button number from configured devices

        Returns:
            Next available button number (1 if no devices configured)
        """
        next_button = 1
        for device_config in self.devices:
            for button in device_config.get_buttons():
                if button >= next_button:
                    next_button = button + 1
        return next_button

    def load_device_config(self, line: str, next_button: int) -> Tuple[bool, int]:
        """
        Parse device configuration line if present

        Args:
            line: Configuration line to parse
            next_button: Next available button number

        Returns:
            Tuple of (success, next_button) where success indicates if line was parsed
        """
        dev_match = re.match(r'^dev:\s*([^\s]+)\s*\[([^\]]+)\](?:\s*\[shared\])?', line)
        if not dev_match:
            return False, next_button

        device_path = dev_match.group(1)
        mappings_str = dev_match.group(2)
        shared = bool(re.search(r'\[shared\]', line))

        mappings = []

        for part in mappings_str.split(','):
            part = part.strip()
            if not part:
                continue

            type_code_match = re.match(r'^(\w+|\d+)/(\w+|\d+)=(-?\d+)$', part)
            if type_code_match:
                type_str = type_code_match.group(1)
                code_str = type_code_match.group(2)
                value = int(type_code_match.group(3))

                if type_str.isdigit():
                    event_type = int(type_str)
                else:
                    event_type = getattr(ecodes, type_str, None)
                    if event_type is None:
                        continue

                if code_str.isdigit():
                    event_code = int(code_str)
                else:
                    event_code = getattr(ecodes, code_str, None)
                    if event_code is None:
                        continue

                mappings.append(EventMapping(
                    event_type=event_type,
                    event_code=event_code,
                    event_value=value,
                    button=Button(next_button),
                    auto_release=True
                ))
                next_button += 1
            else:
                key_code = int(part)
                button = Button(next_button)

                mappings.append(EventMapping(
                    event_type=ecodes.EV_KEY,
                    event_code=key_code,
                    event_value=1,
                    button=button,
                    auto_release=False
                ))
                mappings.append(EventMapping(
                    event_type=ecodes.EV_KEY,
                    event_code=key_code,
                    event_value=0,
                    button=button,
                    auto_release=False
                ))
                next_button += 1

        self.devices.append(DeviceConfig(
            path=device_path,
            mappings=mappings,
            shared=shared
        ))
        return True, next_button

    def load_line(self, line: str, line_number: int = 0) -> None:
        """
        Load a single configuration line

        Handles formats:
        1. "dev: /dev/input/eventX [code1,code2,...]" - Device configuration
        2. "1v,2: command" - Explicit multi-button sequence
        3. "1: command" - Implicit single button press-release
        4. "2v,2^: command" - Explicit press-release sequence
        """
        parsed, _ = self.load_device_config(line, self.get_next_button_number())
        if parsed:
            return

        # Split pattern and command
        match = re.match(r'^([^:]+):(.*)$', line)
        if not match:
            return

        pattern_str = match.group(1).strip()
        command = match.group(2).split('#')[0].strip()

        # Extract repeat modifier before parsing timing constraint
        repeat = False
        repeat_match = re.search(r'\s+repeat\s*$', pattern_str)
        if repeat_match:
            repeat = True
            pattern_str = pattern_str[:repeat_match.start()].strip()

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
            self.patterns.append(ButtonEventPattern(sequence, time_constraint, command, line_number, repeat))

    def load(self, config_file: str) -> None:
        """Load configuration from file"""
        self.config_file = config_file
        self.mtime = os.stat(config_file).st_mtime

        with open(config_file, 'r') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    self.load_line(line, line_number)

    def reload_if_changed(self) -> bool:
        """
        Check if configuration file has been modified and reload if changed

        Returns:
            True if file was reloaded, False if unchanged
        """
        if not self.config_file or not os.path.exists(self.config_file):
            return False

        current_mtime = os.stat(self.config_file).st_mtime
        if current_mtime != self.mtime:
            self.patterns.clear()
            self.devices.clear()
            self.load(self.config_file)
            return True

        return False

    def dump_structure(self) -> None:
        """Display the in-memory structure of the configuration"""
        print("Devices:")
        pprint(self.devices)
        print("\nPatterns:")
        pprint(self.patterns)

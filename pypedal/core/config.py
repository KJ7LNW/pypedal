"""
Configuration and command pattern handling
"""
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from .button import HistoryEntry
from pprint import pprint

@dataclass
class ButtonEvent:
    """Represents a single button event in a sequence"""
    button: str
    event: str  # "v" for press, "^" for release

    def __str__(self) -> str:
        return f"{self.button}{self.event}"

    def matches(self, history_entry: HistoryEntry) -> bool:
        """Check if this button event matches a history entry"""
        event_type = "pressed" if self.event == "v" else "released"
        return (history_entry.button == self.button and 
                history_entry.event == event_type)

@dataclass
class CommandPattern:
    """Represents a parsed command pattern"""
    sequence: List[ButtonEvent]
    time_constraint: Optional[float] = None
    command: str = ""
    line_number: int = 0  # Track original line number for priority

    @property
    def specificity(self) -> int:
        """Calculate pattern specificity for sorting"""
        return -self.line_number

    @classmethod
    def parse(cls, pattern: str, command: str, line_number: int = 0) -> Optional['CommandPattern']:
        """Parse a command pattern string"""
        # Remove comments and whitespace
        pattern = pattern.split('#')[0].strip()
        command = command.strip()
        
        # Handle shorthand notation N < time
        time_match = re.match(r'^(\d+)\s*<\s*([\d.]+)$', pattern)
        if time_match:
            button, time = time_match.groups()
            return cls(
                sequence=[
                    ButtonEvent(button, "v"),
                    ButtonEvent(button, "^")
                ],
                time_constraint=float(time),
                command=command,
                line_number=line_number
            )
        
        # Handle shorthand notation N
        if pattern.isdigit():
            return cls(
                sequence=[
                    ButtonEvent(pattern, "v"),
                    ButtonEvent(pattern, "^")
                ],
                command=command,
                line_number=line_number
            )
        
        # Handle single event Nv or N^
        single_match = re.match(r'^(\d+)(v|\^)$', pattern)
        if single_match:
            button, event = single_match.groups()
            return cls(
                sequence=[ButtonEvent(button, event)],
                command=command,
                line_number=line_number
            )
        
        # Handle sequence with optional time constraint and mixed v/^ notation
        # Format: 1,2,3,2,1 or 1,2,3,2,1 < 0.5 or 1v,2,3^
        sequence_match = re.match(r'^([\d,v^]+)(?:\s*<\s*([\d.]+))?$', pattern)
        if sequence_match:
            buttons_str, time = sequence_match.groups()
            parts = buttons_str.split(',')
            
            sequence = []
            for part in parts:
                if part.endswith('v') or part.endswith('^'):
                    button = part[:-1]
                    event = part[-1]
                    sequence.append(ButtonEvent(button, event))
                else:
                    # implicit press/release
                    button = part
                    sequence.append(ButtonEvent(button, "v"))
                    sequence.append(ButtonEvent(button, "^"))

            return cls(
                sequence=sequence,
                time_constraint=float(time) if time else None,
                command=command,
                line_number=line_number
            )
            
        return None

    def matches_history(self, history: List[HistoryEntry], current_time: datetime, pressed_buttons: Dict[str, bool]) -> Tuple[bool, Optional[int]]:
        """
        Check if this pattern matches the recent history and current pressed button state.
        Returns (matches, match_length) where match_length is the number of history entries to consume.
        """
        if not history or len(history) < len(self.sequence):
            return False, None

        # Skip this pattern if any currently pressed buttons are not used in this pattern
        pattern_buttons = set(event.button for event in self.sequence)
        if any(button for button, is_pressed in pressed_buttons.items() if is_pressed and button not in pattern_buttons):
            return False, None

        # Try to find a match starting at each possible position
        for i in range(len(history) - len(self.sequence) + 1):
            matches = True
            first_timestamp = history[i].timestamp

            # Check each event in the sequence
            for j, button_event in enumerate(self.sequence):
                if not button_event.matches(history[i + j]):
                    matches = False
                    break

                # Check time constraint if specified
                if self.time_constraint is not None:
                    time_diff = (history[i + j].timestamp - first_timestamp).total_seconds()
                    if time_diff > self.time_constraint:
                        matches = False
                        break

            if matches:
                # Check if the last event is within the time constraint
                if self.time_constraint is not None:
                    last_event_time = history[i + len(self.sequence) - 1].timestamp
                    if (current_time - last_event_time).total_seconds() > self.time_constraint:
                        continue

                # Return the number of history entries that matched
                return True, len(self.sequence)

        return False, None

class Config:
    """Handles configuration file parsing and storage"""
    def __init__(self, config_file: str = None):
        self.patterns: List[CommandPattern] = []
        if config_file and os.path.exists(config_file):
            self.load(config_file)

    def load(self, config_file: str) -> None:
        """Load configuration from file"""
        with open(config_file, 'r') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Split on first colon and strip whitespace
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        pattern_str = parts[0].strip()
                        command = parts[1].split('#')[0].strip()
                        pattern = CommandPattern.parse(pattern_str, command, line_number)
                        if pattern:
                            self.patterns.append(pattern)

    def get_matching_command(self, history: List[HistoryEntry], pressed_buttons: Dict[str, bool]) -> Tuple[Optional[str], Optional[int]]:
        """
        Get command for the best matching pattern in history.
        Returns (command, entries_to_consume) where entries_to_consume is the number
        of history entries that should be consumed after executing the command.
        """
        current_time = datetime.now()
        
        # Sort patterns by specificity (descending) and line number (ascending)
        sorted_patterns = sorted(
            self.patterns,
            key=lambda p: (-p.specificity, p.line_number)
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

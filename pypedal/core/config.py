"""
Configuration and command pattern handling
"""
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime
from .button import HistoryEntry

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

    @classmethod
    def parse(cls, pattern: str, command: str) -> Optional['CommandPattern']:
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
                command=command
            )
        
        # Handle shorthand notation N
        if pattern.isdigit():
            return cls(
                sequence=[
                    ButtonEvent(pattern, "v"),
                    ButtonEvent(pattern, "^")
                ],
                command=command
            )
        
        # Handle single event Nv or N^
        single_match = re.match(r'^(\d+)(v|\^)$', pattern)
        if single_match:
            button, event = single_match.groups()
            return cls(
                sequence=[ButtonEvent(button, event)],
                command=command
            )
        
        # Handle sequence with optional time constraint
        # Format: 1,2,3,2,1 or 1,2,3,2,1 < 0.5
        sequence_match = re.match(r'^([\d,]+)(?:\s*<\s*([\d.]+))?$', pattern)
        if sequence_match:
            buttons_str, time = sequence_match.groups()
            # Default to press events for sequence
            sequence = [ButtonEvent(b.strip(), "v") for b in buttons_str.split(',')]
            return cls(
                sequence=sequence,
                time_constraint=float(time) if time else None,
                command=command
            )
            
        return None

    def matches_history(self, history: List[HistoryEntry], current_time: datetime) -> bool:
        """Check if this pattern matches the recent history"""
        if not history or len(history) < len(self.sequence):
            return False

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
                return True

        return False

class Config:
    """Handles configuration file parsing and storage"""
    def __init__(self, config_file: str = None):
        self.patterns: List[CommandPattern] = []
        if config_file and os.path.exists(config_file):
            self.load(config_file)

    def load(self, config_file: str) -> None:
        """Load configuration from file"""
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Split on first colon and strip whitespace
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        pattern_str = parts[0].strip()
                        command = parts[1].split('#')[0].strip()
                        pattern = CommandPattern.parse(pattern_str, command)
                        if pattern:
                            self.patterns.append(pattern)

    def get_matching_command(self, history: List[HistoryEntry]) -> Optional[str]:
        """Get command for the first matching pattern in history"""
        current_time = datetime.now()
        for pattern in self.patterns:
            if pattern.matches_history(history, current_time):
                return pattern.command
        return None

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
    line_number: int = 0  # Track original line number for priority

    @property
    def specificity(self) -> int:
        """Calculate pattern specificity for sorting"""
        score = 0
        # Patterns with explicit v/^ are more specific
        score += sum(1 for event in self.sequence if event.event in ('v', '^'))
        # Longer sequences are more specific
        score += len(self.sequence) * 10
        # Time constraints add specificity
        if self.time_constraint is not None:
            score += 5
            # More restrictive time constraints are more specific
            if self.time_constraint < 0.2:
                score += 3
            elif self.time_constraint < 0.5:
                score += 2
            elif self.time_constraint < 1.0:
                score += 1
        return score

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
            # Parse sequence with potential v/^ notation
            sequence = []
            parts = buttons_str.split(',')
            for part in parts:
                if part.endswith('v') or part.endswith('^'):
                    button = part[:-1]
                    event = part[-1]
                else:
                    button = part
                    event = "v"  # Default to press for implicit events
                sequence.append(ButtonEvent(button, event))
            
            return cls(
                sequence=sequence,
                time_constraint=float(time) if time else None,
                command=command,
                line_number=line_number
            )
            
        return None

    def matches_history(self, history: List[HistoryEntry], current_time: datetime) -> Tuple[bool, Optional[int]]:
        """
        Check if this pattern matches the recent history.
        Returns (matches, match_length) where match_length is the number of history entries to consume.
        """
        if not history or len(history) < len(self.sequence):
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

    def get_matching_command(self, history: List[HistoryEntry]) -> Tuple[Optional[str], Optional[int]]:
        """
        Get command for the first matching pattern in history.
        Returns (command, entries_to_consume) where entries_to_consume is the number
        of history entries that should be consumed after executing the command.
        """
        current_time = datetime.now()
        
        # Sort patterns by specificity (descending) and line number (ascending)
        sorted_patterns = sorted(
            self.patterns,
            key=lambda p: (-p.specificity, p.line_number)
        )
        
        for pattern in sorted_patterns:
            matches, match_length = pattern.matches_history(history, current_time)
            if matches:
                return pattern.command, match_length
        
        return None, None

"""
Button state and history tracking functionality
"""
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime, timedelta
import click
from enum import Enum

class ButtonEvent(Enum):
    """Button event types"""
    BUTTON_DOWN = True  # Maps to value == 1 from device events
    BUTTON_UP = False    # Maps to value == 0 from device events

@dataclass
class ButtonState:
    """Tracks the state of all buttons"""
    states: Dict[str, ButtonEvent] = None

    def __init__(self):
        self.states = {"1": ButtonEvent.BUTTON_UP, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}

    def update(self, button: str, event: ButtonEvent) -> None:
        """Update the state of a button"""
        self.states[button] = event

    def get_state(self) -> Dict[str, ButtonEvent]:
        """Get current state of all buttons"""
        return self.states.copy()

    def __str__(self) -> str:
        """String representation of button states"""
        return " ".join(f"B{b}:{'+' if s == ButtonEvent.BUTTON_DOWN else '-'}" for b, s in self.states.items())

@dataclass
class HistoryEntry:
    """Represents a single event in history"""
    timestamp: datetime
    button: str
    event: ButtonEvent
    button_states: Dict[str, ButtonEvent]

    def __str__(self) -> str:
        """String representation of history entry"""
        states = " ".join(f"B{b}:{'+' if s == ButtonEvent.BUTTON_DOWN else '-'}" for b, s in self.button_states.items())
        event_str = "pressed" if self.event == ButtonEvent.BUTTON_DOWN else "released"
        return f"{self.timestamp.strftime('%H:%M:%S.%f')[:-3]} B{self.button} {event_str:8} | {states}"

class History:
    """Maintains history of button events"""
    def __init__(self, timeout: float = 1.0):
        self.entries: List[HistoryEntry] = []
        self.timeout = timeout  # Timeout in seconds

    def add_entry(self, button: str, event: ButtonEvent, button_states: Dict[str, ButtonEvent], timestamp: datetime = None) -> HistoryEntry:
        """Add a new entry to history"""
        entry = HistoryEntry(
            timestamp=timestamp or datetime.now(),
            button=button,
            event=event,
            button_states=button_states.copy()
        )
        self.entries.append(entry)
        return entry

    def cleanup_old_entries(self, current_button_states: Dict[str, ButtonEvent]) -> None:
        """Remove old entries for released buttons"""
        current_time = datetime.now()
        timeout_delta = timedelta(seconds=self.timeout)

        # Keep entries that are either:
        # 1. For buttons that are currently pressed
        # 2. For buttons that were released less than timeout seconds ago
        self.entries = [
            entry for entry in self.entries
            if current_button_states[entry.button] == ButtonEvent.BUTTON_DOWN or  # Button is currently pressed
               (current_time - entry.timestamp) <= timeout_delta  # Entry is within timeout
        ]

    def consume_latest_matches(self) -> None:
        """Remove entries that have been matched to prevent re-triggering"""
        if len(self.entries) > 10:  # Keep last 10 entries for matching
            self.entries = self.entries[-10:]

    def display_all(self) -> None:
        """Display all history entries"""
        for entry in self.entries:
            click.echo(str(entry))

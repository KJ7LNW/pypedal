"""
Button state and history tracking functionality
"""
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime
import click

@dataclass
class ButtonState:
    """Tracks the state of all buttons"""
    states: Dict[str, bool] = None

    def __init__(self):
        self.states = {"1": False, "2": False, "3": False}

    def update(self, button: str, pressed: bool) -> None:
        """Update the state of a button"""
        self.states[button] = pressed

    def get_state(self) -> Dict[str, bool]:
        """Get current state of all buttons"""
        return self.states.copy()

    def __str__(self) -> str:
        """String representation of button states"""
        return " ".join(f"B{b}:{'+' if s else '-'}" for b, s in self.states.items())

@dataclass
class HistoryEntry:
    """Represents a single event in history"""
    timestamp: datetime
    button: str
    event: str  # "pressed" or "released"
    button_states: Dict[str, bool]

    def __str__(self) -> str:
        """String representation of history entry"""
        states = " ".join(f"B{b}:{'+' if s else '-'}" for b, s in self.button_states.items())
        return f"{self.timestamp.strftime('%H:%M:%S.%f')[:-3]} B{self.button} {self.event:8} | {states}"

class History:
    """Maintains history of button events"""
    def __init__(self):
        self.entries: List[HistoryEntry] = []

    def add_entry(self, button: str, event: str, button_states: Dict[str, bool]) -> HistoryEntry:
        """Add a new entry to history"""
        entry = HistoryEntry(
            timestamp=datetime.now(),
            button=button,
            event=event,
            button_states=button_states.copy()
        )
        self.entries.append(entry)
        return entry

    def consume_latest_matches(self) -> None:
        """Remove entries that have been matched to prevent re-triggering"""
        if len(self.entries) > 10:  # Keep last 10 entries for matching
            self.entries = self.entries[-10:]

    def display_all(self) -> None:
        """Display all history entries with indentation"""
        click.clear()
        click.echo("History (B1/B2/B3: + = pressed, - = released):")
        click.echo("-" * 60)
        for i, entry in enumerate(self.entries, 1):
            click.echo(f"    {i:3d}. {entry}")
        click.echo("-" * 60)
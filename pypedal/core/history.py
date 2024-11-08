"""
History tracking functionality for pedal events
"""
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime
import click
from .pedal import Button, ButtonEvent

@dataclass
class HistoryEntry:
    """Represents a single event in history"""
    timestamp: datetime
    button: Button
    event: ButtonEvent
    button_states: Dict[Button, ButtonEvent]

    def __str__(self) -> str:
        """String representation of history entry"""
        states = " ".join(f"B{b}:{'+' if s == ButtonEvent.BUTTON_DOWN else '-'}" for b, s in self.button_states.items())
        event_str = "pressed" if self.event == ButtonEvent.BUTTON_DOWN else "released"
        return f"{self.timestamp.strftime('%H:%M:%S.%f')[:-3]} B{self.button} {event_str:8} | {states}"

class History:
    """Maintains history of button events"""
    def __init__(self):
        self.entries: List[HistoryEntry] = []

    def add_entry(self, button: Button, event: ButtonEvent, button_states: Dict[Button, ButtonEvent], timestamp: datetime = None) -> HistoryEntry:
        """Add a new entry to history"""
        entry = HistoryEntry(
            timestamp=timestamp or datetime.now(),
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
        """Display all history entries"""
        click.echo("\nHistory:")
        for entry in self.entries:
            click.echo("  " + str(entry))
        click.echo("")

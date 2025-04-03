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
    """
    Represents a single event in history
    
    Tracks:
    - When the event occurred (timestamp)
    - Which button was involved (button)
    - Type of event (press/release)
    - State of all buttons at time of event
    - How many times this event used in pattern matching
    """
    timestamp: datetime
    button: Button
    event: ButtonEvent
    button_states: Dict[Button, ButtonEvent]
    used: int = 0

    def __str__(self) -> str:
        """
        String representation of history entry
        Format: "HH:MM:SS.mmm B1 pressed  | B1:+ B2:- B3:- B4:-... (used:0)"
        Where:
        - + means pressed, - means released
        - Shows all available buttons
        """
        state_parts = []
        # Show all buttons in button_states
        for button in sorted(self.button_states.keys()):
            state = self.button_states.get(button, ButtonEvent.BUTTON_UP)
            state_symbol = '+' if state == ButtonEvent.BUTTON_DOWN else '-'
            state_parts.append(f"B{button}:{state_symbol}")
        states = " ".join(state_parts)

        event_str = "pressed " if self.event == ButtonEvent.BUTTON_DOWN else "released"
        event_color = "green" if self.event == ButtonEvent.BUTTON_DOWN else "red"
        button_str = f"B{self.button}"
        used_str = f"(used:{str(self.used)})"
        return f"{self.timestamp.strftime('%H:%M:%S.%f')[:-3]} {button_str} {click.style(event_str, fg=event_color):8} | {states} {used_str}"

class History:
    """
    Maintains history of button events
    
    Key responsibilities:
    1. Track button press/release events
    2. Maintain current state of all buttons
    3. Track usage of events in pattern matching
    4. Clean up history when buttons released
    """
    def __init__(self):
        self.entries: List[HistoryEntry] = []
        self.all_buttons: List[Button] = []

    def add_entry(self, button: Button, event: ButtonEvent, button_states: Dict[Button, ButtonEvent], timestamp: datetime = None) -> HistoryEntry:
        """
        Add a new entry to history
        Records button event with current state of all buttons
        """
        # Track all available buttons
        for b in button_states:
            if b not in self.all_buttons:
                self.all_buttons.append(b)

        entry = HistoryEntry(
            timestamp=timestamp or datetime.now(),
            button=button,
            event=event,
            button_states=button_states.copy()
        )
        self.entries.append(entry)
        return entry

    def pop_released(self, current_states: Dict[Button, ButtonEvent]) -> None:
        """
        Remove all released buttons until a pressed button is found, like a stack.
        
        This cleanup ensures:
        1. History only contains active button sequences
        2. Single button patterns clear after release
        3. Multi-button patterns maintain while buttons held
        """
        # Start from most recent entry
        for i in reversed(range(len(self.entries))):
            entry = self.entries[i]

            # Check if this button is pressed in current state
            if current_states.get(entry.button) == ButtonEvent.BUTTON_DOWN:
                # Keep this entry and all before it
                self.entries = self.entries[:i+1]
                break
        else:
            # No pressed buttons found, clear all entries
            self.entries.clear()

    def set_used(self) -> None:
        """
        Mark all entries as used
        
        Increments used counter for pattern matching:
        - Tracks against max_use limits
        - Critical for single-button patterns (when config.pattern.sequence[].max_use=0)
        - Allows multi-button pattern reuse (config.pattern.sequence[].max_use=None)
        """
        for i in range(len(self.entries)):
            self.entries[i].used += 1

    def display_all(self) -> None:
        """Display all history entries"""
        if self.entries:
            click.secho("\n  History:", bold=True)
            for entry in self.entries:
                click.echo("   - " + str(entry))

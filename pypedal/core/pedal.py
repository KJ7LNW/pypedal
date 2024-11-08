"""
Pedal state tracking functionality
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

# Define the Button type
class Button(int):
    pass

class ButtonEvent(Enum):
    """Button event types"""
    BUTTON_DOWN = True  # Maps to value == 1 from device events
    BUTTON_UP = False    # Maps to value == 0 from device events

@dataclass
class PedalState:
    """Tracks the state of all buttons on the pedal"""
    states: Dict[Button, ButtonEvent] = None

    def __init__(self):
        self.states = {Button(1): ButtonEvent.BUTTON_UP, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}

    def update(self, button: Button, event: ButtonEvent) -> None:
        """Update the state of a button"""
        self.states[button] = event

    def get_state(self) -> Dict[Button, ButtonEvent]:
        """Get current state of all buttons"""
        return self.states.copy()

    def __str__(self) -> str:
        """String representation of button states"""
        return " ".join(f"B{b}:{'+' if s == ButtonEvent.BUTTON_DOWN else '-'}" for b, s in self.states.items())

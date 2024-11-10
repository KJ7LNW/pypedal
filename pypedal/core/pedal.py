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
    """
    Button event types
    
    Maps directly to device event values:
    - BUTTON_DOWN = True matches value == 1 from device
    - BUTTON_UP = False matches value == 0 from device
    """
    BUTTON_DOWN = True  # Maps to value == 1 from device events
    BUTTON_UP = False   # Maps to value == 0 from device events

@dataclass
class PedalState:
    """
    Tracks the state of all buttons on the pedal
    
    Maintains a simple pressed/released state for each button.
    This state is used to:
    1. Track which buttons are currently held down
    2. Provide current state snapshot for history entries
    3. Help determine when to clean up history (all buttons released)
    """
    states: Dict[Button, ButtonEvent] = None

    def __init__(self):
        """Initialize all buttons to released state"""
        self.states = {Button(1): ButtonEvent.BUTTON_UP, 
                      Button(2): ButtonEvent.BUTTON_UP, 
                      Button(3): ButtonEvent.BUTTON_UP}

    def update(self, button: Button, event: ButtonEvent) -> None:
        """
        Update the state of a button
        
        Simply tracks press/release state - history tracking is handled separately.
        This separation ensures state tracking remains simple and reliable.
        """
        self.states[button] = event

    def get_state(self) -> Dict[Button, ButtonEvent]:
        """
        Get current state of all buttons
        
        Returns a copy to prevent external modifications.
        Used by history entries to snapshot button states at time of event.
        """
        return self.states.copy()

    def __str__(self) -> str:
        """
        String representation of button states
        Format: "B1:+ B2:- B3:-" where + is pressed, - is released
        """
        return " ".join(f"B{b}:{'+' if s == ButtonEvent.BUTTON_DOWN else '-'}" 
                       for b, s in self.states.items())

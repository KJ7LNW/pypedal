"""
Test button state and history tracking
"""
from datetime import datetime
from pypedal.core.pedal import PedalState, ButtonEvent
from pypedal.core.history import HistoryEntry, History
from pypedal.core.device import Button

def test_button_state():
    """Test button state tracking"""
    state = PedalState()

    # Test initial state
    assert all(s == ButtonEvent.BUTTON_UP for s in state.states.values())

    # Test updating state
    state.update(Button(1), ButtonEvent.BUTTON_DOWN)
    assert state.states[Button(1)] == ButtonEvent.BUTTON_DOWN
    assert state.states[Button(2)] == ButtonEvent.BUTTON_UP
    assert state.states[Button(3)] == ButtonEvent.BUTTON_UP

def test_history_entry():
    """Test history entry creation"""
    now = datetime.now()
    button_states = {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}
    entry = HistoryEntry(now, Button(1), ButtonEvent.BUTTON_DOWN, button_states)

    assert entry.timestamp == now
    assert entry.button == Button(1)
    assert entry.event == ButtonEvent.BUTTON_DOWN
    assert entry.button_states == button_states

def test_history_basic():
    """Test basic history functionality"""
    history = History()
    button_states = {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}
    entry = history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, button_states)

    assert len(history.entries) == 1
    assert history.entries[0] == entry

def test_history_sequence():
    """Test history sequence tracking"""
    history = History()
    states = {Button(1): ButtonEvent.BUTTON_UP, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}

    # Add sequence: B1 press, B2 press, B2 release
    states[Button(1)] = ButtonEvent.BUTTON_DOWN
    history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, states)

    states[Button(2)] = ButtonEvent.BUTTON_DOWN
    history.add_entry(Button(2), ButtonEvent.BUTTON_DOWN, states)

    states[Button(2)] = ButtonEvent.BUTTON_UP
    history.add_entry(Button(2), ButtonEvent.BUTTON_UP, states)

    assert len(history.entries) == 3
    assert history.entries[0].button == Button(1)
    assert history.entries[0].event == ButtonEvent.BUTTON_DOWN
    assert history.entries[1].button == Button(2)
    assert history.entries[1].event == ButtonEvent.BUTTON_DOWN
    assert history.entries[2].button == Button(2)
    assert history.entries[2].event == ButtonEvent.BUTTON_UP

def test_history_cleanup():
    """Test history cleanup when buttons are released"""
    history = History()
    states = {Button(1): ButtonEvent.BUTTON_UP, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}

    # Press B1
    states[Button(1)] = ButtonEvent.BUTTON_DOWN
    history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, states.copy())

    # Press B2
    states[Button(2)] = ButtonEvent.BUTTON_DOWN
    history.add_entry(Button(2), ButtonEvent.BUTTON_DOWN, states.copy())

    # Release B2
    states[Button(2)] = ButtonEvent.BUTTON_UP
    history.add_entry(Button(2), ButtonEvent.BUTTON_UP, states.copy())

    # Should keep B1, still pressed
    history.pop_released(states)
    assert len(history.entries) == 1

    # Release B1
    states[Button(1)] = ButtonEvent.BUTTON_UP
    history.add_entry(Button(1), ButtonEvent.BUTTON_UP, states.copy())

    # Should clear all entries since no buttons pressed
    history.pop_released(states)
    assert len(history.entries) == 0

def test_history_state_tracking():
    """Test that history tracks button states correctly"""
    history = History()
    states = {Button(1): ButtonEvent.BUTTON_UP, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}

    # Press B1
    states[Button(1)] = ButtonEvent.BUTTON_DOWN
    history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, states.copy())

    # Press B2
    states[Button(2)] = ButtonEvent.BUTTON_DOWN
    history.add_entry(Button(2), ButtonEvent.BUTTON_DOWN, states.copy())

    # Release B1
    states[Button(1)] = ButtonEvent.BUTTON_UP
    history.add_entry(Button(1), ButtonEvent.BUTTON_UP, states.copy())

    # Verify states at each point
    assert history.entries[0].button_states[Button(1)] == ButtonEvent.BUTTON_DOWN
    assert history.entries[0].button_states[Button(2)] == ButtonEvent.BUTTON_UP

    assert history.entries[1].button_states[Button(1)] == ButtonEvent.BUTTON_DOWN
    assert history.entries[1].button_states[Button(2)] == ButtonEvent.BUTTON_DOWN

    assert history.entries[2].button_states[Button(1)] == ButtonEvent.BUTTON_UP
    assert history.entries[2].button_states[Button(2)] == ButtonEvent.BUTTON_DOWN

def test_history_display():
    """Test history display formatting"""
    history = History()
    states = {Button(1): ButtonEvent.BUTTON_UP, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}
    history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, states)
    history.display_all()  # Just verify it doesn't error

"""
Tests for button state and history tracking
"""
from datetime import datetime
from pypedal.core.button import ButtonState, HistoryEntry, History

def test_button_state():
    """Test button state tracking"""
    state = ButtonState()
    
    # Test initial state
    assert not any(state.states.values())
    
    # Test updating state
    state.update("1", True)
    assert state.states["1"]
    assert not state.states["2"]
    assert not state.states["3"]
    
    # Test state copy
    state_copy = state.get_state()
    state_copy["1"] = False
    assert state.states["1"]  # Original unchanged

def test_history_entry():
    """Test history entry creation and string representation"""
    button_states = {"1": True, "2": False, "3": False}
    entry = HistoryEntry(
        timestamp=datetime.now(),
        button="1",
        event="pressed",
        button_states=button_states
    )
    
    # Test string representation contains key information
    str_rep = str(entry)
    assert "B1" in str_rep
    assert "pressed" in str_rep
    assert "+" in str_rep  # Pressed state
    assert "-" in str_rep  # Released state

def test_history():
    """Test history tracking"""
    history = History()
    button_states = {"1": False, "2": False, "3": False}
    
    # Test adding entries
    entry1 = history.add_entry("1", "pressed", button_states)
    assert len(history.entries) == 1
    assert history.entries[0] == entry1
    
    # Test history consumption
    for i in range(15):  # Add more than 10 entries
        history.add_entry(str(i % 3 + 1), "pressed", button_states)
    history.consume_latest_matches()
    assert len(history.entries) == 10  # Should keep only last 10

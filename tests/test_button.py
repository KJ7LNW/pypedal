"""
Tests for button state and history tracking
"""
from datetime import datetime, timedelta
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

def test_history_basic():
    """Test basic history tracking"""
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

def test_history_sequence():
    """Test history with button sequences"""
    history = History()
    button_states = {"1": False, "2": False, "3": False}
    base_time = datetime.now()
    
    # Create a sequence: 1 press -> 2 press -> 3 press -> 2 press -> 1 press
    sequence = ["1", "2", "3", "2", "1"]
    for i, button in enumerate(sequence):
        history.add_entry(
            button,
            "pressed",
            button_states.copy(),
            timestamp=base_time + timedelta(seconds=0.1 * i)
        )
    
    # Verify sequence is recorded correctly
    assert len(history.entries) == 5
    for i, entry in enumerate(history.entries):
        assert entry.button == sequence[i]
        assert entry.event == "pressed"
        assert entry.timestamp == base_time + timedelta(seconds=0.1 * i)

def test_history_timing():
    """Test history with timing constraints"""
    history = History()
    button_states = {"1": False, "2": False, "3": False}
    base_time = datetime.now()
    
    # Add entries with specific timing
    history.add_entry("1", "pressed", button_states.copy(), timestamp=base_time)
    history.add_entry("2", "pressed", button_states.copy(), timestamp=base_time + timedelta(seconds=0.1))
    history.add_entry("3", "pressed", button_states.copy(), timestamp=base_time + timedelta(seconds=0.2))
    
    # Verify timing is preserved
    assert (history.entries[1].timestamp - history.entries[0].timestamp).total_seconds() == 0.1
    assert (history.entries[2].timestamp - history.entries[1].timestamp).total_seconds() == 0.1

def test_history_consumption():
    """Test history entry consumption"""
    history = History()
    button_states = {"1": False, "2": False, "3": False}
    base_time = datetime.now()
    
    # Add sequence of entries
    for i in range(5):
        history.add_entry(
            str(i % 3 + 1),
            "pressed",
            button_states.copy(),
            timestamp=base_time + timedelta(seconds=0.1 * i)
        )
    
    # Verify initial length
    assert len(history.entries) == 5
    
    # Consume first 3 entries
    history.entries = history.entries[3:]
    assert len(history.entries) == 2
    assert history.entries[0].button == "1"  # Entry 4
    assert history.entries[1].button == "2"  # Entry 5

def test_history_state_tracking():
    """Test history tracks button states correctly"""
    history = History()
    button_states = {"1": False, "2": False, "3": False}
    
    # Press button 1
    button_states["1"] = True
    history.add_entry("1", "pressed", button_states.copy())
    assert history.entries[-1].button_states["1"] == True
    
    # Press button 2
    button_states["2"] = True
    history.add_entry("2", "pressed", button_states.copy())
    assert history.entries[-1].button_states["1"] == True
    assert history.entries[-1].button_states["2"] == True
    
    # Release button 1
    button_states["1"] = False
    history.add_entry("1", "released", button_states.copy())
    assert history.entries[-1].button_states["1"] == False
    assert history.entries[-1].button_states["2"] == True

def test_history_display():
    """Test history display formatting"""
    history = History()
    button_states = {"1": False, "2": False, "3": False}
    
    # Add some entries
    button_states["1"] = True
    history.add_entry("1", "pressed", button_states.copy())
    button_states["2"] = True
    history.add_entry("2", "pressed", button_states.copy())
    button_states["1"] = False
    history.add_entry("1", "released", button_states.copy())
    
    # Call display_all() to verify it doesn't raise any errors
    # Note: We can't easily test the actual output since it uses click.echo
    history.display_all()

def test_history_timeout():
    """Test history entry timeout for released buttons"""
    history = History(timeout=0.5)  # 500ms timeout
    button_states = {"1": False, "2": False, "3": False}
    base_time = datetime.now()
    
    # Add some entries with different timestamps
    history.add_entry("1", "pressed", {"1": True, "2": False, "3": False}, base_time - timedelta(seconds=1))
    history.add_entry("1", "released", {"1": False, "2": False, "3": False}, base_time - timedelta(seconds=0.8))
    history.add_entry("2", "pressed", {"1": False, "2": True, "3": False}, base_time - timedelta(seconds=0.3))
    history.add_entry("2", "released", {"1": False, "2": False, "3": False}, base_time - timedelta(seconds=0.2))
    
    # Clean up old entries
    history.cleanup_old_entries(button_states)
    
    # Only entries within timeout should remain
    assert len(history.entries) == 2
    assert history.entries[0].button == "2"
    assert history.entries[0].event == "pressed"
    assert history.entries[1].button == "2"
    assert history.entries[1].event == "released"

def test_history_timeout_pressed_buttons():
    """Test that history entries for pressed buttons are not timed out"""
    history = History(timeout=0.5)  # 500ms timeout
    button_states = {"1": True, "2": False, "3": False}  # Button 1 is pressed
    base_time = datetime.now()
    
    # Add old entries for button 1 (which is still pressed)
    history.add_entry("1", "pressed", {"1": True, "2": False, "3": False}, base_time - timedelta(seconds=1))
    history.add_entry("2", "pressed", {"1": True, "2": True, "3": False}, base_time - timedelta(seconds=0.8))
    history.add_entry("2", "released", {"1": True, "2": False, "3": False}, base_time - timedelta(seconds=0.7))
    
    # Clean up old entries
    history.cleanup_old_entries(button_states)
    
    # Button 1 entries should remain because it's still pressed
    # Button 2 entries should be removed because they're old and button is released
    assert len(history.entries) == 1
    assert history.entries[0].button == "1"
    assert history.entries[0].event == "pressed"

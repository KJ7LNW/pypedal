"""
Tests for button state and history tracking
"""
from datetime import datetime, timedelta
from pypedal.core.button import ButtonState, HistoryEntry, History, ButtonEvent

def test_button_state():
    """Test button state tracking"""
    state = ButtonState()
    
    # Test initial state
    assert all(s == ButtonEvent.BUTTON_UP for s in state.states.values())
    
    # Test updating state
    state.update("1", ButtonEvent.BUTTON_DOWN)
    assert state.states["1"] == ButtonEvent.BUTTON_DOWN
    assert state.states["2"] == ButtonEvent.BUTTON_UP
    assert state.states["3"] == ButtonEvent.BUTTON_UP
    
    # Test state copy
    state_copy = state.get_state()
    state_copy["1"] = ButtonEvent.BUTTON_UP
    assert state.states["1"] == ButtonEvent.BUTTON_DOWN  # Original unchanged

def test_history_entry():
    """Test history entry creation and string representation"""
    button_states = {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}
    entry = HistoryEntry(
        timestamp=datetime.now(),
        button="1",
        event=ButtonEvent.BUTTON_DOWN,
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
    button_states = {"1": ButtonEvent.BUTTON_UP, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}
    
    # Test adding entries
    entry1 = history.add_entry("1", ButtonEvent.BUTTON_DOWN, button_states)
    assert len(history.entries) == 1
    assert history.entries[0] == entry1
    
    # Test history consumption
    for i in range(15):  # Add more than 10 entries
        history.add_entry(str(i % 3 + 1), ButtonEvent.BUTTON_DOWN, button_states)
    history.consume_latest_matches()
    assert len(history.entries) == 10  # Should keep only last 10

def test_history_sequence():
    """Test history with button sequences"""
    history = History()
    button_states = {"1": ButtonEvent.BUTTON_UP, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}
    base_time = datetime.now()
    
    # Create a sequence: 1 press -> 2 press -> 3 press -> 2 press -> 1 press
    sequence = ["1", "2", "3", "2", "1"]
    for i, button in enumerate(sequence):
        history.add_entry(
            button,
            ButtonEvent.BUTTON_DOWN,
            button_states.copy(),
            timestamp=base_time + timedelta(seconds=0.1 * i)
        )
    
    # Verify sequence is recorded correctly
    assert len(history.entries) == 5
    for i, entry in enumerate(history.entries):
        assert entry.button == sequence[i]
        assert entry.event == ButtonEvent.BUTTON_DOWN
        assert entry.timestamp == base_time + timedelta(seconds=0.1 * i)

def test_history_consumption():
    """Test history entry consumption"""
    history = History()
    button_states = {"1": ButtonEvent.BUTTON_UP, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}
    base_time = datetime.now()
    
    # Add sequence of entries
    for i in range(5):
        history.add_entry(
            str(i % 3 + 1),
            ButtonEvent.BUTTON_DOWN,
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
    button_states = {"1": ButtonEvent.BUTTON_UP, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}
    
    # Press button 1
    button_states["1"] = ButtonEvent.BUTTON_DOWN
    history.add_entry("1", ButtonEvent.BUTTON_DOWN, button_states.copy())
    assert history.entries[-1].button_states["1"] == ButtonEvent.BUTTON_DOWN
    
    # Press button 2
    button_states["2"] = ButtonEvent.BUTTON_DOWN
    history.add_entry("2", ButtonEvent.BUTTON_DOWN, button_states.copy())
    assert history.entries[-1].button_states["1"] == ButtonEvent.BUTTON_DOWN
    assert history.entries[-1].button_states["2"] == ButtonEvent.BUTTON_DOWN
    
    # Release button 1
    button_states["1"] = ButtonEvent.BUTTON_UP
    history.add_entry("1", ButtonEvent.BUTTON_UP, button_states.copy())
    assert history.entries[-1].button_states["1"] == ButtonEvent.BUTTON_UP
    assert history.entries[-1].button_states["2"] == ButtonEvent.BUTTON_DOWN

def test_history_display():
    """Test history display formatting"""
    history = History()
    button_states = {"1": ButtonEvent.BUTTON_UP, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}
    
    # Add some entries
    button_states["1"] = ButtonEvent.BUTTON_DOWN
    history.add_entry("1", ButtonEvent.BUTTON_DOWN, button_states.copy())
    button_states["2"] = ButtonEvent.BUTTON_DOWN
    history.add_entry("2", ButtonEvent.BUTTON_DOWN, button_states.copy())
    button_states["1"] = ButtonEvent.BUTTON_UP
    history.add_entry("1", ButtonEvent.BUTTON_UP, button_states.copy())
    
    # Call display_all() to verify it doesn't raise any errors
    # Note: We can't easily test the actual output since it uses click.echo
    history.display_all()

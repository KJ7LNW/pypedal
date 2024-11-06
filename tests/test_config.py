"""
Tests for configuration and command pattern handling
"""
import os
from datetime import datetime, timedelta
from pypedal.core.config import CommandPattern, Config, ButtonEvent
from pypedal.core.button import HistoryEntry

def get_test_file_path(filename: str) -> str:
    """Get path to a test data file"""
    return os.path.join(os.path.dirname(__file__), 'test_data', filename)

def test_basic_patterns():
    """Test basic button press/release patterns"""
    config = Config(get_test_file_path('basic.conf'))
    base_time = datetime.now()
    button_states = {"1": False, "2": False, "3": False}
    
    # Test button 1 press
    history = [HistoryEntry(base_time, "1", "pressed", button_states)]
    command, entries = config.get_matching_command(history)
    assert command == "echo button 1 pressed"
    assert entries == 1
    
    # Test button 1 release
    history = [HistoryEntry(base_time, "1", "released", button_states)]
    command, entries = config.get_matching_command(history)
    assert command == "echo button 1 released"
    assert entries == 1

def test_sequence_patterns():
    """Test sequence patterns with different lengths"""
    config = Config(get_test_file_path('sequences.conf'))
    base_time = datetime.now()
    button_states = {"1": False, "2": False, "3": False}
    
    # Test that longer sequence takes priority
    history = [
        HistoryEntry(base_time, "1", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.1), "2", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.2), "3", "pressed", button_states),
    ]
    command, entries = config.get_matching_command(history)
    assert command == "echo medium sequence"  # Not "echo short sequence"
    assert entries == 3
    
    # Test full 5-button sequence
    history = [
        HistoryEntry(base_time, "1", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.1), "2", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.2), "3", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.3), "2", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.4), "1", "pressed", button_states),
    ]
    command, entries = config.get_matching_command(history)
    assert command == "echo long sequence"
    assert entries == 5

def test_timing_constraints():
    """Test patterns with timing constraints"""
    config = Config(get_test_file_path('timing.conf'))
    base_time = datetime.now()
    button_states = {"1": False, "2": False, "3": False}
    
    # Test fast sequence (under 0.2s)
    fast_history = [
        HistoryEntry(base_time, "1", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.1), "2", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.15), "3", "pressed", button_states),
    ]
    command, entries = config.get_matching_command(fast_history)
    assert command == "echo very fast sequence"
    assert entries == 3
    
    # Test medium sequence (under 0.5s)
    medium_history = [
        HistoryEntry(base_time, "1", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.3), "2", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.4), "3", "pressed", button_states),
    ]
    command, entries = config.get_matching_command(medium_history)
    assert command == "echo moderately fast sequence"
    assert entries == 3
    
    # Test slow sequence (too slow for fast/medium patterns)
    slow_history = [
        HistoryEntry(base_time, "1", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.6), "2", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.8), "3", "pressed", button_states),
    ]
    command, entries = config.get_matching_command(slow_history)
    assert command == "echo slow sequence"
    assert entries == 3

def test_edge_cases():
    """Test edge cases and potential conflicts"""
    config = Config(get_test_file_path('edge_cases.conf'))
    base_time = datetime.now()
    button_states = {"1": False, "2": False, "3": False}
    
    # Test whitespace handling
    history = [HistoryEntry(base_time, "1", "pressed", button_states)]
    command, entries = config.get_matching_command(history)
    assert command == "echo explicit press"  # Not shorthand version
    
    # Test equivalent patterns
    history = [
        HistoryEntry(base_time, "2", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.1), "2", "pressed", button_states),
    ]
    command, entries = config.get_matching_command(history)
    assert command == "echo double press explicit"
    assert entries == 2
    
    # Test mixed notation
    history = [
        HistoryEntry(base_time, "1", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.1), "2", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.2), "3", "released", button_states),
    ]
    command, entries = config.get_matching_command(history)
    assert command == "echo mixed notation"
    assert entries == 3

def test_pattern_priority():
    """Test pattern matching priority"""
    config = Config(get_test_file_path('sequences.conf'))
    base_time = datetime.now()
    button_states = {"1": False, "2": False, "3": False}
    
    # Create history that could match multiple patterns
    history = [
        HistoryEntry(base_time, "2", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.1), "3", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.2), "1", "pressed", button_states),
    ]
    
    # Should match the longer pattern
    command, entries = config.get_matching_command(history)
    assert command == "echo overlap 2"  # Not "echo overlap 1"
    assert entries == 3

def test_same_button_sequences():
    """Test sequences with repeated buttons"""
    config = Config(get_test_file_path('sequences.conf'))
    base_time = datetime.now()
    button_states = {"1": False, "2": False, "3": False}
    
    # Test double press
    history = [
        HistoryEntry(base_time, "1", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.1), "1", "pressed", button_states),
    ]
    command, entries = config.get_matching_command(history)
    assert command == "echo double press"
    assert entries == 2
    
    # Test triple press
    history = [
        HistoryEntry(base_time, "1", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.1), "1", "pressed", button_states),
        HistoryEntry(base_time + timedelta(seconds=0.2), "1", "pressed", button_states),
    ]
    command, entries = config.get_matching_command(history)
    assert command == "echo triple press"
    assert entries == 3

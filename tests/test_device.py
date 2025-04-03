import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from pypedal.core.device import DeviceHandler, Button
from pypedal.core.history import HistoryEntry
from pypedal.core.pedal import ButtonEvent
from pypedal.core.config import Config, ButtonEventPattern, ButtonEventPatternElement

def create_event(type_, code, value):
    """Create a mock event"""
    return (0).to_bytes(8, 'little') + \
           (0).to_bytes(8, 'little') + \
           type_.to_bytes(2, 'little') + \
           code.to_bytes(2, 'little') + \
           value.to_bytes(4, 'little')

def test_device_handler_initialization():
    key_codes = {
        256: Button(1),  # Left pedal button
        257: Button(2),  # Middle pedal button
        258: Button(3)   # Right pedal button
    }
    handler = DeviceHandler('/dev/null', key_codes=key_codes)
    assert handler.device_path == '/dev/null'
    assert handler.config is None
    assert handler.quiet is False
    assert handler.key_codes == key_codes

def test_process_event():
    key_codes = {
        256: Button(1),  # Left pedal button
        257: Button(2),  # Middle pedal button
        258: Button(3)   # Right pedal button
    }
    handler = DeviceHandler('/dev/null', key_codes=key_codes, quiet=True)

    # Create a mock event (button 1 press)
    event = create_event(1, 256, 1)

    handler.process_event(event)

    assert handler.pedal_state.get_state() == {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}
    assert len(handler.history.entries) == 1
    assert handler.history.entries[0].button == Button(1)
    assert handler.history.entries[0].event == ButtonEvent.BUTTON_DOWN

def test_read_events():
    key_codes = {
        256: Button(1),  # Left pedal button
        257: Button(2),  # Middle pedal button
        258: Button(3)   # Right pedal button
    }
    handler = DeviceHandler('/dev/null', key_codes=key_codes, quiet=True)

    # Mock the open function to return a file-like object
    mock_file = Mock()
    mock_file.read.side_effect = [
        create_event(1, 256, 1),  # Button 1 press
        create_event(1, 256, 0),  # Button 1 release
        KeyboardInterrupt,  # Simulate Ctrl+C to stop the loop
    ]

    # Add __enter__ and __exit__ methods to mock_file
    mock_file.__enter__ = Mock(return_value=mock_file)
    mock_file.__exit__ = Mock(return_value=None)

    with patch('builtins.open', return_value=mock_file), \
         patch('select.select', return_value=([mock_file], [], [])):
        try:
            handler.read_events()
        except KeyboardInterrupt:
            pass  # Expected behavior, do nothing

    # History should be empty since all buttons are released
    assert len(handler.history.entries) == 0
    # and state should reflect the last event
    assert handler.pedal_state.get_state()[Button(1)] == ButtonEvent.BUTTON_UP

def test_find_matching_patterns_empty():
    """Test find_matching_patterns with empty history or config"""
    key_codes = {
        256: Button(1),  # Left pedal button
        257: Button(2),  # Middle pedal button
        258: Button(3)   # Right pedal button
    }
    handler = DeviceHandler('/dev/null', key_codes=key_codes)
    assert handler.find_matching_patterns() == []

    handler.config = Config()
    assert handler.find_matching_patterns() == []

def test_find_matching_patterns_timing():
    """Test find_matching_patterns with timing constraints"""
    key_codes = {
        256: Button(1),  # Left pedal button
        257: Button(2),  # Middle pedal button
        258: Button(3)   # Right pedal button
    }
    handler = DeviceHandler('/dev/null', key_codes=key_codes)
    handler.config = Config()

    # Create a pattern with 1 second time constraint
    pattern = ButtonEventPattern(
        sequence=[
            ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_DOWN),
            ButtonEventPatternElement(Button(2), ButtonEvent.BUTTON_DOWN)
        ],
        time_constraint=1.0,
        command="test"
    )
    handler.config.patterns = [pattern]

    # Add events with 2 second gap
    now = datetime.now()
    handler.history.add_entry(
        Button(1),
        ButtonEvent.BUTTON_DOWN,
        {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP},
        now
    )
    handler.history.add_entry(
        Button(2),
        ButtonEvent.BUTTON_DOWN,
        {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_DOWN},
        now + timedelta(seconds=2)
    )

    # Should not match due to timing
    matches = handler.find_matching_patterns()
    assert len(matches) == 0

def test_find_matching_patterns_full():
    """Test find_matching_patterns with full pattern matches"""
    key_codes = {
        256: Button(1),  # Left pedal button
        257: Button(2),  # Middle pedal button
        258: Button(3)   # Right pedal button
    }
    handler = DeviceHandler('/dev/null', key_codes=key_codes)
    handler.config = Config()

    # Create a pattern: Button1 down, Button2 down
    pattern = ButtonEventPattern(
        sequence=[
            ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_DOWN),
            ButtonEventPatternElement(Button(2), ButtonEvent.BUTTON_DOWN)
        ],
        time_constraint=1.0,
        command="test"
    )
    handler.config.patterns = [pattern]

    # Add matching sequence within time constraint
    now = datetime.now()
    handler.history.add_entry(
        Button(1),
        ButtonEvent.BUTTON_DOWN,
        {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP},
        now
    )
    handler.history.add_entry(
        Button(2),
        ButtonEvent.BUTTON_DOWN,
        {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_DOWN},
        now + timedelta(seconds=0.5)
    )

    # Should match fully
    matches = handler.find_matching_patterns()
    assert len(matches) == 1
    assert matches[0] == pattern

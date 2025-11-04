import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from pypedal.core.device import DeviceHandler, Button
from pypedal.core.history import HistoryEntry
from pypedal.core.pedal import ButtonEvent
from pypedal.core.config import Config, ButtonEventPattern, ButtonEventPatternElement

def create_event(type_, code, value):
    """Create a mock InputEvent object"""
    from unittest.mock import MagicMock
    event = MagicMock()
    event.type = type_
    event.code = code
    event.value = value
    return event

def test_device_handler_initialization():
    key_codes = {
        (1, 256, 1): (Button(1), False),
        (1, 256, 0): (Button(1), False),
        (1, 257, 1): (Button(2), False),
        (1, 257, 0): (Button(2), False),
        (1, 258, 1): (Button(3), False),
        (1, 258, 0): (Button(3), False)
    }
    buttons = [Button(1), Button(2), Button(3)]
    handler = DeviceHandler('/dev/null', key_codes=key_codes, buttons=buttons)
    assert handler.device_path == '/dev/null'
    assert handler.config is None
    assert handler.quiet is False
    assert handler.key_codes == key_codes

def test_process_event():
    key_codes = {
        (1, 256, 1): (Button(1), False),
        (1, 256, 0): (Button(1), False),
        (1, 257, 1): (Button(2), False),
        (1, 257, 0): (Button(2), False),
        (1, 258, 1): (Button(3), False),
        (1, 258, 0): (Button(3), False)
    }
    buttons = [Button(1), Button(2), Button(3)]
    handler = DeviceHandler('/dev/null', key_codes=key_codes, buttons=buttons, quiet=True)

    # Create a mock event (button 1 press)
    event = create_event(1, 256, 1)

    handler.process_event(event)

    assert handler.pedal_state.get_state() == {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}
    assert len(handler.history.entries) == 1
    assert handler.history.entries[0].button == Button(1)
    assert handler.history.entries[0].event == ButtonEvent.BUTTON_DOWN

def test_read_events():
    key_codes = {
        (1, 256, 1): (Button(1), False),
        (1, 256, 0): (Button(1), False),
        (1, 257, 1): (Button(2), False),
        (1, 257, 0): (Button(2), False),
        (1, 258, 1): (Button(3), False),
        (1, 258, 0): (Button(3), False)
    }
    buttons = [Button(1), Button(2), Button(3)]
    handler = DeviceHandler('/dev/null', key_codes=key_codes, buttons=buttons, quiet=True)

    mock_device = Mock()
    mock_device.read_one.side_effect = [
        create_event(1, 256, 1),
        create_event(1, 256, 0),
        KeyboardInterrupt,
    ]
    mock_device.__enter__ = Mock(return_value=mock_device)
    mock_device.__exit__ = Mock(return_value=None)

    with patch('pypedal.core.device.InputDevice', return_value=mock_device):
        try:
            handler.read_events()
        except KeyboardInterrupt:
            pass

    assert len(handler.history.entries) == 0
    assert handler.pedal_state.get_state()[Button(1)] == ButtonEvent.BUTTON_UP

def test_find_matching_patterns_empty():
    """Test find_matching_patterns with empty history or config"""
    key_codes = {
        (1, 256, 1): (Button(1), False),
        (1, 256, 0): (Button(1), False),
        (1, 257, 1): (Button(2), False),
        (1, 257, 0): (Button(2), False),
        (1, 258, 1): (Button(3), False),
        (1, 258, 0): (Button(3), False)
    }
    buttons = [Button(1), Button(2), Button(3)]
    handler = DeviceHandler('/dev/null', key_codes=key_codes, buttons=buttons)
    assert handler.find_matching_patterns() == []

    handler.config = Config()
    assert handler.find_matching_patterns() == []

def test_find_matching_patterns_timing():
    """Test find_matching_patterns with timing constraints"""
    key_codes = {
        (1, 256, 1): (Button(1), False),
        (1, 256, 0): (Button(1), False),
        (1, 257, 1): (Button(2), False),
        (1, 257, 0): (Button(2), False),
        (1, 258, 1): (Button(3), False),
        (1, 258, 0): (Button(3), False)
    }
    buttons = [Button(1), Button(2), Button(3)]
    handler = DeviceHandler('/dev/null', key_codes=key_codes, buttons=buttons)
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
        (1, 256, 1): (Button(1), False),
        (1, 256, 0): (Button(1), False),
        (1, 257, 1): (Button(2), False),
        (1, 257, 0): (Button(2), False),
        (1, 258, 1): (Button(3), False),
        (1, 258, 0): (Button(3), False)
    }
    buttons = [Button(1), Button(2), Button(3)]
    handler = DeviceHandler('/dev/null', key_codes=key_codes, buttons=buttons)
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

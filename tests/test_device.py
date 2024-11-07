import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from pypedal.core.device import DeviceHandler
from pypedal.core.button import HistoryEntry

def create_event(type_, code, value):
    """Create a mock event"""
    return (0).to_bytes(8, 'little') + \
           (0).to_bytes(8, 'little') + \
           type_.to_bytes(2, 'little') + \
           code.to_bytes(2, 'little') + \
           value.to_bytes(4, 'little')

def test_device_handler_initialization():
    handler = DeviceHandler('/dev/null')
    assert handler.device_path == '/dev/null'
    assert handler.config is None
    assert handler.quiet is False

def test_process_event():
    mock_config = Mock()
    mock_config.get_matching_command.return_value = (None, None)  # Return a tuple
    handler = DeviceHandler('/dev/null', config=mock_config, quiet=True)

    # Create a mock event (button 1 press)
    event = create_event(1, 256, 1)

    handler.process_event(event)

    assert handler.button_state.get_state() == {"1": True, "2": False, "3": False}
    assert len(handler.history.entries) == 1
    assert handler.history.entries[0].button == "1"
    assert handler.history.entries[0].event == "pressed"

def test_process_event_with_command():
    mock_config = Mock()
    mock_config.get_matching_command.return_value = ("test command", 1)
    handler = DeviceHandler('/dev/null', config=mock_config, quiet=True)

    # Create a mock event (button 1 press)
    event = create_event(1, 256, 1)

    with patch('subprocess.run') as mock_run:
        handler.process_event(event)

    mock_run.assert_called_once_with("test command", shell=True, check=True)

def test_command_execution_with_history_consumption():
    """Test that history is consumed after command execution"""
    mock_config = Mock()

    # Configure mock to return command only after seeing both button 1 and 2
    def mock_get_matching_command(history, pressed_buttons):
        if len(history) >= 2:
            if (history[0].button == "1" and history[0].event == "pressed" and
                history[1].button == "2" and history[1].event == "pressed"):
                return "test command", 2
        return None, None

    mock_config.get_matching_command.side_effect = mock_get_matching_command

    handler = DeviceHandler('/dev/null', config=mock_config, quiet=True)

    # Add some events
    press_event1 = create_event(1, 256, 1)  # Button 1 press
    press_event2 = create_event(1, 257, 1)  # Button 2 press
    press_event3 = create_event(1, 258, 1)  # Button 3 press

    with patch('subprocess.run') as mock_run:
        # Process events
        handler.process_event(press_event1)
        handler.process_event(press_event2)
        handler.process_event(press_event3)

        # Check that the command was executed
        mock_run.assert_called_once_with("test command", shell=True, check=True)

        # Check that history was consumed
        assert len(handler.history.entries) == 1
        assert handler.history.entries[0].button == "3"

def test_read_events():
    mock_config = Mock()
    mock_config.get_matching_command.return_value = (None, None)  # Return a tuple
    handler = DeviceHandler('/dev/null', config=mock_config, quiet=True)

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

    assert len(handler.history.entries) == 2
    assert handler.history.entries[0].button == "1"
    assert handler.history.entries[0].event == "pressed"
    assert handler.history.entries[1].button == "1"
    assert handler.history.entries[1].event == "released"

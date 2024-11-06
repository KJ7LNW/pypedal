"""
Tests for device event handling
"""
import struct
from unittest.mock import Mock, patch
from pypedal.core.device import DeviceHandler, EV_TYPES, KEY_CODES

def create_event(type_: int, code: int, value: int) -> bytes:
    """Create a mock event byte string"""
    # Create event with dummy timestamp (0, 0)
    return struct.pack('llHHI', 0, 0, type_, code, value)

def test_process_key_event():
    """Test processing of key events"""
    handler = DeviceHandler('/dev/null', quiet=True)
    
    # Test button press event
    press_event = create_event(1, 256, 1)  # Type 1 (EV_KEY), code 256 (button 1), value 1 (press)
    handler.process_event(press_event)
    
    # Verify button state was updated
    assert handler.button_state.states["1"] == True
    assert len(handler.history.entries) == 1
    assert handler.history.entries[0].button == "1"
    assert handler.history.entries[0].event == "pressed"
    
    # Test button release event
    release_event = create_event(1, 256, 0)  # Type 1 (EV_KEY), code 256 (button 1), value 0 (release)
    handler.process_event(release_event)
    
    # Verify button state was updated
    assert handler.button_state.states["1"] == False
    assert len(handler.history.entries) == 2
    assert handler.history.entries[1].button == "1"
    assert handler.history.entries[1].event == "released"

def test_process_sync_event():
    """Test processing of sync events"""
    handler = DeviceHandler('/dev/null', quiet=True)
    
    # Test sync event (type 0)
    sync_event = create_event(0, 0, 0)
    handler.process_event(sync_event)
    
    # Verify sync events are ignored
    assert len(handler.history.entries) == 0

def test_process_unknown_event():
    """Test processing of unknown event types"""
    handler = DeviceHandler('/dev/null', quiet=True)
    
    # Test unknown event type
    unknown_event = create_event(99, 0, 0)
    handler.process_event(unknown_event)
    
    # Verify unknown events don't affect state
    assert len(handler.history.entries) == 0

def test_command_execution():
    """Test command execution when patterns match"""
    mock_config = Mock()
    mock_config.get_matching_command.return_value = "echo test"
    
    handler = DeviceHandler('/dev/null', config=mock_config, quiet=True)
    
    # Create and process a button press event
    press_event = create_event(1, 256, 1)
    
    with patch('subprocess.run') as mock_run:
        handler.process_event(press_event)
        
        # Verify command was executed
        mock_config.get_matching_command.assert_called_once()
        mock_run.assert_called_once_with("echo test", shell=True, check=True)

def test_event_type_mappings():
    """Test event type mappings"""
    assert EV_TYPES[0] == "EV_SYN"
    assert EV_TYPES[1] == "EV_KEY"
    assert EV_TYPES[4] == "EV_MSC"

def test_key_code_mappings():
    """Test key code mappings"""
    assert KEY_CODES[256] == "1"  # Left pedal
    assert KEY_CODES[257] == "2"  # Middle pedal
    assert KEY_CODES[258] == "3"  # Right pedal

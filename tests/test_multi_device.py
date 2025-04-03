"""
Tests for multi-device pedal event handling
"""
import os
from tests.test_device import create_event
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from pypedal.core.multi_device import MultiDeviceHandler
from pypedal.core.config import Config, ButtonEventPattern, ButtonEventPatternElement
from pypedal.core.pedal import Button, ButtonEvent

def test_multi_device_init():
    """Test MultiDeviceHandler initialization"""
    config = Config()
    devices = [
        ("/dev/input/event0", [1, 2, 3]),
        ("/dev/input/event1", [4, 5, 6])
    ]
    
    mock_dev1 = MagicMock()
    mock_dev2 = MagicMock()
    mock_dev1.fileno.return_value = 1
    mock_dev2.fileno.return_value = 2
    
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = [mock_dev1, mock_dev2]
        handler = MultiDeviceHandler(devices, config)
        assert len(handler.handlers) == 2
        assert len(handler.device_fds) == 2
        
        # Verify FDs are mapped correctly
        assert handler.device_fds[1] == handler.handlers[0]
        assert handler.device_fds[2] == handler.handlers[1]

def test_multi_device_read_events():
    """Test reading events from multiple devices"""
    config = Config()
    devices = [
        ("/dev/input/event0", [1, 2, 3]),
        ("/dev/input/event1", [4, 5, 6])
    ]
    
    mock_dev1 = MagicMock()
    mock_dev2 = MagicMock()
    
    # Setup mock devices
    mock_dev1.fileno.return_value = 1
    mock_dev2.fileno.return_value = 2
    mock_dev1.read.return_value = b"test_event"
    
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = [mock_dev1, mock_dev2] * 2  # Need two sets for init and read_events
        
        with patch("select.select") as mock_select:
            # First select() returns device, second returns empty to exit loop
            mock_select.side_effect = [([mock_dev1], [], [])]
            
            handler = MultiDeviceHandler(devices, config)
            handler.handlers[0].process_event = MagicMock()
            
            # Test event reading
            handler.read_events()
            
            # Verify event was processed
            handler.handlers[0].process_event.assert_called_once_with(b"test_event")
            mock_dev1.close.assert_called()

def test_device_disconnection():
    """Test handling of device disconnection"""
    config = Config()
    devices = [
        ("/dev/input/event0", [1, 2, 3]),
        ("/dev/input/event1", [4, 5, 6])
    ]
    
    mock_dev1 = MagicMock()
    mock_dev2 = MagicMock()
    
    # Setup mock devices
    mock_dev1.fileno.return_value = 1
    mock_dev2.fileno.return_value = 2
    mock_dev1.read.side_effect = OSError("Device disconnected")
    
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = [mock_dev1, mock_dev2] * 2  # Need two sets for init and read_events
        
        with patch("select.select") as mock_select:
            # Return device that will raise OSError
            mock_select.side_effect = [([mock_dev1], [], [])]
            
            handler = MultiDeviceHandler(devices, config)
            
            # Test disconnection handling
            handler.read_events()
            
            # Verify device was closed after disconnection
            mock_dev1.close.assert_called()
            mock_dev2.close.assert_called()

def test_shared_history_across_devices():
    """Test that button history is shared across devices for pattern matching"""
    config = Config()
    
    # Add patterns for individual and combined device buttons
    # Pattern for device 1
    dev1_pattern = ButtonEventPattern(
        sequence=[
            ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_DOWN, 0),
            ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_UP, 0)
        ],
        command="echo device1"
    )
    
    # Pattern for device 2
    dev2_pattern = ButtonEventPattern(
        sequence=[
            ButtonEventPatternElement(Button(4), ButtonEvent.BUTTON_DOWN, 0),
            ButtonEventPatternElement(Button(4), ButtonEvent.BUTTON_UP, 0)
        ],
        command="echo device2"
    )
    
    # Pattern requiring buttons from both devices
    combined_pattern = ButtonEventPattern(
        sequence=[
            ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_DOWN),
            ButtonEventPatternElement(Button(4), ButtonEvent.BUTTON_DOWN),
            ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_UP),
            ButtonEventPatternElement(Button(4), ButtonEvent.BUTTON_UP)
        ],
        command="echo combined"
    )
    config.patterns.extend([dev1_pattern, dev2_pattern, combined_pattern])
    
    devices = [
        ("/dev/input/event0", [1, 2, 3]),
        ("/dev/input/event1", [4, 5, 6])
    ]
    
    mock_dev1 = MagicMock()
    mock_dev2 = MagicMock()
    mock_dev1.fileno.return_value = 1
    mock_dev2.fileno.return_value = 2
    
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = [mock_dev1, mock_dev2]
        handler = MultiDeviceHandler(devices, config)
        
        # Test individual device patterns
        # Button 1 press/release
        handler.handlers[0].process_event(create_event(1, 256, 1))  # Press
        handler.handlers[0].process_event(create_event(1, 256, 0))  # Release
        # Pattern execution is verified by stdout capture showing "Patterns run"
        # and "device1" command output
        # Test second device pattern
        # Button 4 press/release
        handler.handlers[1].process_event(create_event(1, 259, 1))  # Press
        handler.handlers[1].process_event(create_event(1, 259, 0))  # Release
        
        # Verify button state after press/release
        assert handler.handlers[1].pedal_state.get_state()[Button(4)] == ButtonEvent.BUTTON_UP
        # History should be empty after pattern execution
        assert len(handler.handlers[1].history.entries) == 0

        # Test combined pattern across devices
        handler.handlers[0].process_event(create_event(1, 256, 1))  # Button 1 press
        handler.handlers[1].process_event(create_event(1, 259, 1))  # Button 4 press
        handler.handlers[0].process_event(create_event(1, 256, 0))  # Button 1 release
        handler.handlers[1].process_event(create_event(1, 259, 0))  # Button 4 release
        
        # Verify final button states
        assert handler.handlers[0].pedal_state.get_state()[Button(1)] == ButtonEvent.BUTTON_UP
        assert handler.handlers[1].pedal_state.get_state()[Button(4)] == ButtonEvent.BUTTON_UP
        # History should be empty after pattern execution
        assert len(handler.handlers[0].history.entries) == 0
        assert len(handler.handlers[1].history.entries) == 0


def test_discovered_config_loading():
    """Test loading configuration from discovered devices"""
    config_content = """
# Discovered devices configuration
dev: /dev/input/event0 [1, 2, 3]
dev: /dev/input/event1 [4, 5, 6]

# Button mappings
1: echo "Device 1 Button 1"
2: echo "Device 1 Button 2"
4: echo "Device 2 Button 1"
5: echo "Device 2 Button 2"
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(config_content)
        config_path = f.name

    try:
        config = Config(config_path)
        
        # Verify devices loaded
        assert len(config.devices) == 2
        assert config.devices["/dev/input/event0"] == [1, 2, 3]
        assert config.devices["/dev/input/event1"] == [4, 5, 6]
        
        # Verify patterns loaded
        assert len(config.patterns) == 4
        
        # Check button mappings
        button_commands = {
            (int(p.sequence[0].button), p.command)
            for p in config.patterns
        }
        expected = {
            (1, 'echo "Device 1 Button 1"'),
            (2, 'echo "Device 1 Button 2"'),
            (4, 'echo "Device 2 Button 1"'),
            (5, 'echo "Device 2 Button 2"')
        }
        assert button_commands == expected
    finally:
        os.unlink(config_path)

def test_multi_device_button_events():
    """Test button events from multiple devices trigger correct patterns"""
    config = Config()
    
    # Add test patterns for different devices
    dev1_pattern = ButtonEventPattern(
        sequence=[
            ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_DOWN, 0),
            ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_UP, 0)
        ],
        command="echo device1"
    )
    dev2_pattern = ButtonEventPattern(
        sequence=[
            ButtonEventPatternElement(Button(4), ButtonEvent.BUTTON_DOWN, 0),
            ButtonEventPatternElement(Button(4), ButtonEvent.BUTTON_UP, 0)
        ],
        command="echo device2"
    )
    config.patterns.extend([dev1_pattern, dev2_pattern])
    
    devices = [
        ("/dev/input/event0", [1, 2, 3]),
        ("/dev/input/event1", [4, 5, 6])
    ]
    
    mock_dev1 = MagicMock()
    mock_dev2 = MagicMock()
    mock_dev1.fileno.return_value = 1
    mock_dev2.fileno.return_value = 2
    
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = [mock_dev1, mock_dev2]
        handler = MultiDeviceHandler(devices, config)
        
        # Simulate button press from device 1
        handler.handlers[0].process_event(create_event(1, 256, 1))  # Button 1 press
        handler.handlers[0].process_event(create_event(1, 256, 0))  # Button 1 release
        
        # Simulate button press from device 2
        handler.handlers[1].process_event(create_event(1, 259, 1))  # Button 4 press
        handler.handlers[1].process_event(create_event(1, 259, 0))  # Button 4 release
        
        # Verify final button states
        assert handler.handlers[0].pedal_state.get_state()[Button(1)] == ButtonEvent.BUTTON_UP
        assert handler.handlers[1].pedal_state.get_state()[Button(4)] == ButtonEvent.BUTTON_UP
        # History should be empty after pattern execution
        assert len(handler.handlers[0].history.entries) == 0
        assert len(handler.handlers[1].history.entries) == 0
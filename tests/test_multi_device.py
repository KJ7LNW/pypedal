"""
Tests for multi-device pedal event handling
"""
import os
import pytest
from unittest.mock import MagicMock, patch
from pypedal.core.multi_device import MultiDeviceHandler
from pypedal.core.config import Config
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
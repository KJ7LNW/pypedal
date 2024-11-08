import pytest
from unittest.mock import Mock, patch
from pypedal.core.device import DeviceHandler
from pypedal.core.config import Config, CommandPattern, ButtonEvent
from pprint import pprint

def create_event(type_, code, value):
    """Create a mock event"""
    return (0).to_bytes(8, 'little') + \
           (0).to_bytes(8, 'little') + \
           type_.to_bytes(2, 'little') + \
           code.to_bytes(2, 'little') + \
           value.to_bytes(4, 'little')

def test_mouse_button_sequence():
    """Test the sequence: B2p B2r triggering mousedown/mouseup"""
    config = Config()
    
    # Add the actual command patterns
    config.patterns = [
        CommandPattern(
            sequence=[ButtonEvent("2", "v")],
            command="echo mousedown 1",
            line_number=1
        ),
        CommandPattern(
            sequence=[ButtonEvent("2", "^")],
            command="echo mouseup 1",
            line_number=2
        )
    ]
    
    # Track executed commands
    executed_commands = []
    
    handler = DeviceHandler('/dev/null', config=config, quiet=True)

    # Create events for the sequence [B2p B2r]
    events = [
        create_event(1, 257, 1),  # B2 press
        create_event(1, 257, 0),  # B2 release
    ]

    with patch('subprocess.run') as mock_run:
        def capture_command(cmd, shell=True, check=True):
            executed_commands.append(cmd)
            return Mock()
        
        mock_run.side_effect = capture_command

        # Process each event in the sequence
        for event in events:
            handler.process_event(event)

    print("\nExecuted commands:")
    pprint(executed_commands)

    # Verify both mousedown and mouseup were triggered in correct order
    assert len(executed_commands) == 2, "Both mousedown and mouseup should be triggered"
    assert executed_commands[0] == "echo mousedown 1", "mousedown should be triggered on press"
    assert executed_commands[1] == "echo mouseup 1", "mouseup should be triggered on release"

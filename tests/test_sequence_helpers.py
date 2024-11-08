"""Helper functions for testing button sequences"""
import pytest
from unittest.mock import Mock, patch
from pypedal.core.device import DeviceHandler
from pypedal.core.config import Config

def create_event(type_, code, value):
    """Create a mock event"""
    return (0).to_bytes(8, 'little') + \
           (0).to_bytes(8, 'little') + \
           type_.to_bytes(2, 'little') + \
           code.to_bytes(2, 'little') + \
           value.to_bytes(4, 'little')

def run_button_sequence(config_lines, button_events, expected_commands):
    """
    Test a button sequence with given config and expected commands
    
    Args:
        config_lines: List of config lines (each line is "pattern: command")
        button_events: List of (code, value) tuples for button events
        expected_commands: List of expected commands in order
    """
    # Create config from text lines
    config = Config()
    for i, line in enumerate(config_lines, 1):
        config.load_line(line, i)
    
    # Track executed commands
    executed_commands = []
    
    handler = DeviceHandler('/dev/null', config=config, quiet=True)

    # Create events from button sequence
    events = [create_event(1, code, value) for code, value in button_events]

    with patch('subprocess.run') as mock_run:
        def capture_command(cmd, shell=True, check=True):
            executed_commands.append(cmd)
            return Mock()
        
        mock_run.side_effect = capture_command

        # Process each event in the sequence
        for event in events:
            handler.process_event(event)

    print("\nExecuted commands:")
    print(executed_commands)

    # Verify commands were triggered in correct order
    assert len(executed_commands) == len(expected_commands), \
        f"Expected {len(expected_commands)} commands, got {len(executed_commands)}"
    
    for i, (actual, expected) in enumerate(zip(executed_commands, expected_commands)):
        assert actual == expected, \
            f"Command {i} was '{actual}', expected '{expected}'"

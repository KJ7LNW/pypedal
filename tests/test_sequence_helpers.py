"""Helper functions for testing button sequences"""
import pytest
from unittest.mock import Mock, patch
from pypedal.core.device import DeviceHandler, Button
from pypedal.core.config import Config
from tests.test_device import create_event

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
    
    # Default key code mappings for tests
    key_codes = {
        (1, 256, 1): (Button(1), False),
        (1, 256, 0): (Button(1), False),
        (1, 257, 1): (Button(2), False),
        (1, 257, 0): (Button(2), False),
        (1, 258, 1): (Button(3), False),
        (1, 258, 0): (Button(3), False),
        (1, 259, 1): (Button(4), False),
        (1, 259, 0): (Button(4), False),
        (1, 260, 1): (Button(5), False),
        (1, 260, 0): (Button(5), False),
        (1, 261, 1): (Button(6), False),
        (1, 261, 0): (Button(6), False)
    }
    buttons = [Button(1), Button(2), Button(3), Button(4), Button(5), Button(6)]
    handler = DeviceHandler('/dev/null', key_codes=key_codes, buttons=buttons, config=config, quiet=True)

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

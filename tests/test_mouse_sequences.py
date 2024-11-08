"""Test mouse button sequences"""
from .test_sequence_helpers import run_button_sequence

def test_mouse_button_sequence():
    """Test the sequence: B2p B2r triggering mousedown/mouseup"""
    config_lines = [
        "2v: echo mousedown 1",  # Left click
        "2^: echo mouseup 1",    # un-Left click
    ]

    button_events = [
        (257, 1),  # B2 press
        (257, 0),  # B2 release
    ]

    expected_commands = [
        "echo mousedown 1",
        "echo mouseup 1"
    ]

    run_button_sequence(config_lines, button_events, expected_commands)

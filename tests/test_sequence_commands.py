"""Test command sequences"""
from .test_sequence_helpers import run_button_sequence

def test_virtual_key_sequence():
    """Test the sequence: B1p B2p B2r B3p B3r B1r B1p B1r"""
    config_lines = [
        "1v,2: echo ctrl+c",     # B1+B2 pressed -> ctrl+c
        "1v,3: echo ctrl+v",     # B1+B3 pressed -> ctrl+v
        "1: echo click 2",      # B1 alone -> click 2
    ]

    button_events = [
        (256, 1),  # B1p
        (257, 1),  # B2p
        (257, 0),  # B2r
        (258, 1),  # B3p
        (258, 0),  # B3r
        (256, 0),  # B1r
        (256, 1),  # B1p
        (256, 0),  # B1r
    ]

    expected_commands = [
        "echo ctrl+c",  # When B1+B2 are pressed
        "echo ctrl+v",  # When B1+B3 are pressed
        "echo click 2",  # When B1 is clicked
    ]

    run_button_sequence(config_lines, button_events, expected_commands)

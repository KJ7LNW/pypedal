import pytest
from datetime import datetime, timedelta
from pypedal.core.config import Config, ButtonEventPatternElement
from pypedal.core.history import HistoryEntry
from pypedal.core.pedal import ButtonEvent
from pypedal.core.device import Button
from pprint import pprint

@pytest.fixture
def sample_config():
    config = Config()
    config.load_line("1v,2v,2^: command1", 1)
    config.load_line("1v,3v,3^: command2", 2)
    config.load_line("2v: command3", 3)
    return config

def test_config_load(tmp_path):
    config_file = tmp_path / "test_config.conf"
    config_file.write_text(
        "1v,2v,2^: command1\n"
        "1v,3v,3^: command2\n"
        "2v: command3\n"
    )
    
    config = Config(str(config_file))
    print("\nConfig patterns:")
    pprint(config)
    
    # Verify first pattern (1v,2v,2^)
    assert len(config.patterns) == 3  # One pattern per line
    
    # Check first pattern sequence
    assert len(config.patterns[0].sequence) == 3
    assert config.patterns[0].sequence[0] == ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_DOWN)
    assert config.patterns[0].sequence[1] == ButtonEventPatternElement(Button(2), ButtonEvent.BUTTON_DOWN)
    assert config.patterns[0].sequence[2] == ButtonEventPatternElement(Button(2), ButtonEvent.BUTTON_UP)
    assert config.patterns[0].command == "command1"
    assert config.patterns[0].time_constraint == float('inf')
    
    # Check second pattern sequence
    assert len(config.patterns[1].sequence) == 3
    assert config.patterns[1].sequence[0] == ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_DOWN)
    assert config.patterns[1].sequence[1] == ButtonEventPatternElement(Button(3), ButtonEvent.BUTTON_DOWN)
    assert config.patterns[1].sequence[2] == ButtonEventPatternElement(Button(3), ButtonEvent.BUTTON_UP)
    assert config.patterns[1].command == "command2"
    assert config.patterns[1].time_constraint == float('inf')
    
    # Check third pattern sequence
    assert len(config.patterns[2].sequence) == 1
    assert config.patterns[2].sequence[0] == ButtonEventPatternElement(Button(2), ButtonEvent.BUTTON_DOWN)
    assert config.patterns[2].command == "command3"
    assert config.patterns[2].time_constraint == float('inf')

def test_config_load_with_timing(tmp_path):
    config_file = tmp_path / "test_config.conf"
    config_file.write_text(
        "1v,2v < 0.5: command1\n"  # Pattern with timing constraint
    )
    
    config = Config(str(config_file))
    print("\nConfig patterns with timing:")
    pprint(config)
    
    assert len(config.patterns) == 1  # One pattern
    
    # Verify timing constraint is set
    assert config.patterns[0].time_constraint == 0.5
    
    # Verify button sequence
    assert len(config.patterns[0].sequence) == 2
    assert config.patterns[0].sequence[0] == ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_DOWN)
    assert config.patterns[0].sequence[1] == ButtonEventPatternElement(Button(2), ButtonEvent.BUTTON_DOWN)

def test_config_get_matching_command(sample_config):
    now = datetime.now()
    history = [
        HistoryEntry(now, Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.1), Button(2), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_DOWN, Button(3): ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.2), Button(2), ButtonEvent.BUTTON_UP, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}),
    ]
    pressed_buttons = {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}

    command, length = sample_config.get_matching_command(history, pressed_buttons)
    assert command == "command1"
    assert length == 3

def test_config_no_match(sample_config):
    now = datetime.now()
    history = [
        HistoryEntry(now, Button(3), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_UP, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_DOWN}),
    ]
    pressed_buttons = {Button(1): ButtonEvent.BUTTON_UP, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_DOWN}

    command, length = sample_config.get_matching_command(history, pressed_buttons)
    assert command is None
    assert length is None

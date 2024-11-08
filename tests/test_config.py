import pytest
from datetime import datetime, timedelta
from pypedal.core.config import Config, CommandPattern
from pypedal.core.button import HistoryEntry, ButtonEvent

@pytest.fixture
def sample_config():
    config = Config()
    config.patterns = [
        CommandPattern.parse("1v,2v,2^", "command1", 1),
        CommandPattern.parse("1v,3v,3^", "command2", 2),
        CommandPattern.parse("2v", "command3", 3),
    ]
    return config

def test_config_load(tmp_path):
    config_file = tmp_path / "test_config.conf"
    config_file.write_text(
        "1v,2v,2^: command1\n"
        "1v,3v,3^: command2\n"
        "2v: command3\n"
    )
    
    config = Config(str(config_file))
    assert len(config.patterns) == 3
    assert config.patterns[0].command == "command1"
    assert config.patterns[1].command == "command2"
    assert config.patterns[2].command == "command3"

def test_config_get_matching_command(sample_config):
    now = datetime.now()
    history = [
        HistoryEntry(now, "1", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.1), "2", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_DOWN, "3": ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.2), "2", ButtonEvent.BUTTON_UP, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}),
    ]
    pressed_buttons = {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}

    command, length = sample_config.get_matching_command(history, pressed_buttons)
    assert command == "command1"
    assert length == 3

def test_config_no_match(sample_config):
    now = datetime.now()
    history = [
        HistoryEntry(now, "3", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_UP, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_DOWN}),
    ]
    pressed_buttons = {"1": ButtonEvent.BUTTON_UP, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_DOWN}

    command, length = sample_config.get_matching_command(history, pressed_buttons)
    assert command is None
    assert length is None

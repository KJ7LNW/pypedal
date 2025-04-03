import pytest
from datetime import datetime, timedelta
from pypedal.core.config import Config, ButtonEventPatternElement
from pypedal.core.history import HistoryEntry
from typing import Dict, List
from pypedal.core.pedal import ButtonEvent
from pypedal.core.device import Button
from pprint import pprint

@pytest.fixture
def sample_config():
    config = Config()
    config.load_line("dev: /dev/input/event0 [1,2,3]", 1)
    config.load_line("1v,2v,2^: command1", 2)
    config.load_line("1v,3v,3^: command2", 3)
    config.load_line("2v: command3", 4)
    return config

def test_device_config_parsing():
    """Test device configuration parsing"""
    config = Config()
    config.load_line("dev: /dev/input/event0 [1,2,3]")
    assert len(config.devices) == 1
    assert "/dev/input/event0" in config.devices
    assert config.devices["/dev/input/event0"] == [1, 2, 3]

def test_multiple_device_configs():
    """Test parsing multiple device configurations"""
    config = Config()
    config.load_line("dev: /dev/input/event0 [1,2,3]")
    config.load_line("dev: /dev/input/event1 [4,5,6]")
    assert len(config.devices) == 2
    assert config.devices["/dev/input/event0"] == [1, 2, 3]
    assert config.devices["/dev/input/event1"] == [4, 5, 6]

def test_config_load(tmp_path):
    config_file = tmp_path / "test_config.conf"
    config_file.write_text(
        "dev: /dev/input/event0 [1,2,3]\n"
        "1v,2v,2^: command1\n"
        "1v,3v,3^: command2\n"
        "2v: command3\n"
    )
    
    config = Config(str(config_file))
    print("\nConfig patterns:")
    pprint(config)
    
    # Verify device configuration
    assert len(config.devices) == 1
    assert "/dev/input/event0" in config.devices
    assert config.devices["/dev/input/event0"] == [1, 2, 3]

    # Verify patterns
    assert len(config.patterns) == 3  # Three pattern lines
    
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


def test_device_config(tmp_path):
    config_file = tmp_path / "test_config.conf"
    config_file.write_text(
        "dev: /dev/input/event0 [256,257,258]\n"
        "dev: /dev/input/event1 [259,260]\n"
        "1v,2v: command1\n"
    )
    
    config = Config(str(config_file))
    
    # Verify device configurations
    assert len(config.devices) == 2
    assert config.devices["/dev/input/event0"] == [256, 257, 258]
    assert config.devices["/dev/input/event1"] == [259, 260]

    # Verify pattern parsing
    assert len(config.patterns) == 1
    pattern = config.patterns[0]
    assert pattern.command == "command1"
    assert pattern.time_constraint == float('inf')
    
    # Verify pattern sequence - explicit v notation means no automatic releases
    assert len(pattern.sequence) == 2
    assert pattern.sequence[0] == ButtonEventPatternElement(Button(1), ButtonEvent.BUTTON_DOWN)
    assert pattern.sequence[1] == ButtonEventPatternElement(Button(2), ButtonEvent.BUTTON_DOWN)

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

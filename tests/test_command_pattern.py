import pytest
from datetime import datetime, timedelta
from pypedal.core.config import Config, ButtonEventPattern, ButtonEventPatternElement
from pypedal.core.history import HistoryEntry
from pypedal.core.pedal import ButtonEvent
from pypedal.core.device import Button

def test_pattern_parse():
    config = Config()
    config.load_line("1v,2v,2^: test_command", 1)
    pattern = config.patterns[0]
    
    assert pattern is not None
    assert len(pattern.sequence) == 3
    assert pattern.command == "test_command"
    assert pattern.line_number == 1

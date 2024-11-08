import pytest
from datetime import datetime, timedelta
from pypedal.core.config import Config, ButtonEventPattern, ButtonEventPatternElement
from pypedal.core.pedal import HistoryEntry, ButtonEvent
from pypedal.core.device import Button

def test_pattern_parse():
    config = Config()
    config.load_line("1v,2v,2^: test_command", 1)
    pattern = config.patterns[0]
    
    assert pattern is not None
    assert len(pattern.sequence) == 3
    assert pattern.command == "test_command"
    assert pattern.line_number == 1

def test_pattern_matches_history():
    config = Config()
    config.load_line("1v,2v,2^: test_command", 1)
    pattern = config.patterns[0]
    assert pattern is not None

    now = datetime.now()
    history = [
        HistoryEntry(now, Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.1), Button(2), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_DOWN, Button(3): ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.2), Button(2), ButtonEvent.BUTTON_UP, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}),
    ]
    pressed_buttons = {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}

    matches, length = pattern.matches_history(history, now + timedelta(seconds=0.3), pressed_buttons)
    assert matches
    assert length == 3

def test_pattern_does_not_match_when_extra_button_pressed():
    config = Config()
    config.load_line("1v,2v,2^: test_command", 1)
    pattern = config.patterns[0]
    assert pattern is not None

    now = datetime.now()
    history = [
        HistoryEntry(now, Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.1), Button(2), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_DOWN, Button(3): ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.2), Button(2), ButtonEvent.BUTTON_UP, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}),
    ]
    pressed_buttons = {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_DOWN}  # Extra button 3 is pressed

    matches, length = pattern.matches_history(history, now + timedelta(seconds=0.3), pressed_buttons)
    assert not matches

def test_pattern_respects_time_constraint():
    config = Config()
    config.load_line("1v,2v < 0.5: test_command", 1)
    pattern = config.patterns[0]
    assert pattern is not None

    now = datetime.now()
    # Test within time constraint
    history1 = [
        HistoryEntry(now, Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.4), Button(2), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_DOWN, Button(3): ButtonEvent.BUTTON_UP}),
    ]
    pressed_buttons = {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_DOWN, Button(3): ButtonEvent.BUTTON_UP}

    matches, length = pattern.matches_history(history1, now + timedelta(seconds=0.45), pressed_buttons)
    assert matches
    assert length == 2

    # Test exceeding time constraint
    history2 = [
        HistoryEntry(now, Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.6), Button(2), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN, Button(2): ButtonEvent.BUTTON_DOWN, Button(3): ButtonEvent.BUTTON_UP}),
    ]

    matches, length = pattern.matches_history(history2, now + timedelta(seconds=0.65), pressed_buttons)
    assert not matches

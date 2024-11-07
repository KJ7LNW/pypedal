import pytest
from datetime import datetime, timedelta
from pypedal.core.config import CommandPattern, ButtonEvent
from pypedal.core.button import HistoryEntry

def test_command_pattern_parse():
    pattern = CommandPattern.parse("1v,2v,2^", "test_command", 1)
    assert pattern is not None
    assert len(pattern.sequence) == 3
    assert pattern.command == "test_command"
    assert pattern.line_number == 1

def test_command_pattern_matches_history():
    pattern = CommandPattern.parse("1v,2v,2^", "test_command", 1)
    assert pattern is not None

    now = datetime.now()
    history = [
        HistoryEntry(now, "1", "pressed", {"1": True, "2": False, "3": False}),
        HistoryEntry(now + timedelta(seconds=0.1), "2", "pressed", {"1": True, "2": True, "3": False}),
        HistoryEntry(now + timedelta(seconds=0.2), "2", "released", {"1": True, "2": False, "3": False}),
    ]
    pressed_buttons = {"1": True, "2": False, "3": False}

    matches, length = pattern.matches_history(history, now + timedelta(seconds=0.3), pressed_buttons)
    assert matches
    assert length == 3

def test_command_pattern_does_not_match_when_extra_button_pressed():
    pattern = CommandPattern.parse("1v,2v,2^", "test_command", 1)
    assert pattern is not None

    now = datetime.now()
    history = [
        HistoryEntry(now, "1", "pressed", {"1": True, "2": False, "3": False}),
        HistoryEntry(now + timedelta(seconds=0.1), "2", "pressed", {"1": True, "2": True, "3": False}),
        HistoryEntry(now + timedelta(seconds=0.2), "2", "released", {"1": True, "2": False, "3": False}),
    ]
    pressed_buttons = {"1": True, "2": False, "3": True}  # Extra button 3 is pressed

    matches, length = pattern.matches_history(history, now + timedelta(seconds=0.3), pressed_buttons)
    assert not matches

def test_command_pattern_respects_time_constraint():
    pattern = CommandPattern.parse("1v,2v < 0.5", "test_command", 1)
    assert pattern is not None

    now = datetime.now()
    # Test within time constraint
    history1 = [
        HistoryEntry(now, "1", "pressed", {"1": True, "2": False, "3": False}),
        HistoryEntry(now + timedelta(seconds=0.4), "2", "pressed", {"1": True, "2": True, "3": False}),
    ]
    pressed_buttons = {"1": True, "2": True, "3": False}

    matches, length = pattern.matches_history(history1, now + timedelta(seconds=0.45), pressed_buttons)
    assert matches
    assert length == 2

    # Test exceeding time constraint
    history2 = [
        HistoryEntry(now, "1", "pressed", {"1": True, "2": False, "3": False}),
        HistoryEntry(now + timedelta(seconds=0.6), "2", "pressed", {"1": True, "2": True, "3": False}),
    ]

    matches, length = pattern.matches_history(history2, now + timedelta(seconds=0.65), pressed_buttons)
    assert not matches

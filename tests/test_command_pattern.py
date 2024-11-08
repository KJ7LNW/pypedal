import pytest
from datetime import datetime, timedelta
from pypedal.core.config import CommandPattern, ButtonEventPattern
from pypedal.core.button import HistoryEntry, ButtonEvent

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
        HistoryEntry(now, "1", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.1), "2", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_DOWN, "3": ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.2), "2", ButtonEvent.BUTTON_UP, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}),
    ]
    pressed_buttons = {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}

    matches, length = pattern.matches_history(history, now + timedelta(seconds=0.3), pressed_buttons)
    assert matches
    assert length == 3

def test_command_pattern_does_not_match_when_extra_button_pressed():
    pattern = CommandPattern.parse("1v,2v,2^", "test_command", 1)
    assert pattern is not None

    now = datetime.now()
    history = [
        HistoryEntry(now, "1", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.1), "2", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_DOWN, "3": ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.2), "2", ButtonEvent.BUTTON_UP, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}),
    ]
    pressed_buttons = {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_DOWN}  # Extra button 3 is pressed

    matches, length = pattern.matches_history(history, now + timedelta(seconds=0.3), pressed_buttons)
    assert not matches

def test_command_pattern_respects_time_constraint():
    pattern = CommandPattern.parse("1v,2v < 0.5", "test_command", 1)
    assert pattern is not None

    now = datetime.now()
    # Test within time constraint
    history1 = [
        HistoryEntry(now, "1", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.4), "2", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_DOWN, "3": ButtonEvent.BUTTON_UP}),
    ]
    pressed_buttons = {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_DOWN, "3": ButtonEvent.BUTTON_UP}

    matches, length = pattern.matches_history(history1, now + timedelta(seconds=0.45), pressed_buttons)
    assert matches
    assert length == 2

    # Test exceeding time constraint
    history2 = [
        HistoryEntry(now, "1", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_UP, "3": ButtonEvent.BUTTON_UP}),
        HistoryEntry(now + timedelta(seconds=0.6), "2", ButtonEvent.BUTTON_DOWN, {"1": ButtonEvent.BUTTON_DOWN, "2": ButtonEvent.BUTTON_DOWN, "3": ButtonEvent.BUTTON_UP}),
    ]

    matches, length = pattern.matches_history(history2, now + timedelta(seconds=0.65), pressed_buttons)
    assert not matches

import pytest
from datetime import datetime
from pypedal.core.config import ButtonEventPatternElement
from pypedal.core.button import HistoryEntry, ButtonEvent

def test_button_event_str():
    event = ButtonEventPatternElement(1, ButtonEvent.BUTTON_DOWN)
    assert str(event) == "1v"

    event = ButtonEventPatternElement(2, ButtonEvent.BUTTON_UP)
    assert str(event) == "2^"

def test_button_event_matches():
    event = ButtonEventPatternElement(1, ButtonEvent.BUTTON_DOWN)
    history_entry = HistoryEntry(datetime.now(), 1, ButtonEvent.BUTTON_DOWN, {1: ButtonEvent.BUTTON_DOWN, 2: ButtonEvent.BUTTON_UP, 3: ButtonEvent.BUTTON_UP})
    assert event.matches(history_entry)

    history_entry = HistoryEntry(datetime.now(), 1, ButtonEvent.BUTTON_UP, {1: ButtonEvent.BUTTON_UP, 2: ButtonEvent.BUTTON_UP, 3: ButtonEvent.BUTTON_UP})
    assert not event.matches(history_entry)

    history_entry = HistoryEntry(datetime.now(), 2, ButtonEvent.BUTTON_DOWN, {1: ButtonEvent.BUTTON_UP, 2: ButtonEvent.BUTTON_DOWN, 3: ButtonEvent.BUTTON_UP})
    assert not event.matches(history_entry)

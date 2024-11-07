from pypedal.core.config import ButtonEvent
from pypedal.core.button import HistoryEntry
from datetime import datetime

def test_button_event_str():
    event = ButtonEvent("1", "v")
    assert str(event) == "1v"

def test_button_event_matches():
    event = ButtonEvent("1", "v")
    history_entry = HistoryEntry(datetime.now(), "1", "pressed", {"1": True, "2": False, "3": False})
    assert event.matches(history_entry)

    history_entry = HistoryEntry(datetime.now(), "1", "released", {"1": False, "2": False, "3": False})
    assert not event.matches(history_entry)

    history_entry = HistoryEntry(datetime.now(), "2", "pressed", {"1": False, "2": True, "3": False})
    assert not event.matches(history_entry)

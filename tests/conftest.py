"""
Shared test fixtures for pypedal tests
"""
import os
import tempfile
import pytest
from datetime import datetime
from pypedal.core.pedal import PedalState, HistoryEntry, History, ButtonEvent
from pypedal.core.config import Config
from pypedal.core.device import Button

@pytest.fixture
def button_state():
    """Fixture providing a fresh PedalState instance"""
    return PedalState()

@pytest.fixture
def history():
    """Fixture providing a fresh History instance"""
    return History()

@pytest.fixture
def button_states():
    """Fixture providing a dict of button states"""
    return {Button(1): ButtonEvent.BUTTON_UP, Button(2): ButtonEvent.BUTTON_UP, Button(3): ButtonEvent.BUTTON_UP}

@pytest.fixture
def history_entry(button_states):
    """Fixture providing a sample HistoryEntry"""
    return HistoryEntry(
        timestamp=datetime.now(),
        button=Button(1),
        event=ButtonEvent.BUTTON_DOWN,
        button_states=button_states
    )

@pytest.fixture
def sample_config_file():
    """Fixture providing a temporary config file with sample patterns"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('1v: test command 1  # comment\n')
        f.write('2^: test command 2\n')
        f.write('# comment line\n')
        f.write('1v,2^ < 0.2: test command 3\n')
        f.write('3: test command 4')
        path = f.name

    yield path
    
    # Cleanup
    os.unlink(path)

@pytest.fixture
def config(sample_config_file):
    """Fixture providing a Config instance with sample patterns"""
    return Config(sample_config_file)

@pytest.fixture
def history_with_events(button_states):
    """Fixture providing History with a sequence of events"""
    history = History()
    base_time = datetime.now()
    
    # Add a sequence of events
    history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, button_states)
    history.add_entry(Button(1), ButtonEvent.BUTTON_UP, button_states)
    history.add_entry(Button(2), ButtonEvent.BUTTON_DOWN, button_states)
    history.add_entry(Button(2), ButtonEvent.BUTTON_UP, button_states)
    
    return history

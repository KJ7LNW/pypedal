"""
Shared test fixtures for pypedal tests
"""
import os
import tempfile
import pytest
from datetime import datetime
from pypedal.core.button import ButtonState, HistoryEntry, History
from pypedal.core.config import Config

@pytest.fixture
def button_state():
    """Fixture providing a fresh ButtonState instance"""
    return ButtonState()

@pytest.fixture
def history():
    """Fixture providing a fresh History instance"""
    return History()

@pytest.fixture
def button_states():
    """Fixture providing a dict of button states"""
    return {"1": False, "2": False, "3": False}

@pytest.fixture
def history_entry(button_states):
    """Fixture providing a sample HistoryEntry"""
    return HistoryEntry(
        timestamp=datetime.now(),
        button="1",
        event="pressed",
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
    history.add_entry("1", "pressed", button_states)
    history.add_entry("1", "released", button_states)
    history.add_entry("2", "pressed", button_states)
    history.add_entry("2", "released", button_states)
    
    return history

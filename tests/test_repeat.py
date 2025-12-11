import pytest
import time
import subprocess
from unittest.mock import Mock, patch, call
from pypedal.core.config import Config
from pypedal.core.device import DeviceHandler
from pypedal.core.pedal import Button, ButtonEvent, PedalState
from pypedal.core.history import History

@pytest.fixture
def repeat_config():
    config = Config()
    config.load_line("dev: /dev/input/event0 [1,2,3]", 1)
    config.load_line("1v repeat: echo 'repeat test'", 2)
    config.load_line("2v: echo 'no repeat'", 3)
    return config

@pytest.fixture
def device_handler(repeat_config):
    buttons = [Button(1), Button(2), Button(3)]
    key_codes = {
        (1, 1, 1): (Button(1), False),
        (1, 1, 0): (Button(1), False),
        (1, 2, 1): (Button(2), False),
        (1, 2, 0): (Button(2), False),
    }
    history = History()
    pedal_state = PedalState(buttons)

    handler = DeviceHandler(
        device_path="/dev/input/event0",
        key_codes=key_codes,
        buttons=buttons,
        config=repeat_config,
        quiet=True,
        history=history,
        pedal_state=pedal_state
    )
    return handler

def test_repeat_flag_parsing():
    """Test that repeat keyword is parsed from config"""
    config = Config()
    config.load_line("1v repeat: echo test", 1)

    assert len(config.patterns) == 1
    pattern = config.patterns[0]
    assert pattern.repeat is True
    assert pattern.command == "echo test"
    assert len(pattern.sequence) == 1

def test_non_repeat_flag():
    """Test that patterns without repeat keyword have repeat=False"""
    config = Config()
    config.load_line("1v: echo test", 1)

    assert len(config.patterns) == 1
    pattern = config.patterns[0]
    assert pattern.repeat is False

def test_check_and_fire_repeats_no_history(device_handler):
    """Test that check_and_fire_repeats does nothing when history is empty"""
    repeat_patterns = device_handler.find_repeat_patterns()
    assert len(repeat_patterns) == 0

    device_handler.check_and_fire_repeats(0.1)
    assert device_handler.last_repeat_time is None

def test_check_and_fire_repeats_first_fire(device_handler):
    """Test that first repeat doesn't fire until 2x interval has elapsed"""
    device_handler.history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN})
    device_handler.last_repeat_time = -time.monotonic()

    repeat_patterns = device_handler.find_repeat_patterns()
    assert len(repeat_patterns) == 1
    assert repeat_patterns[0].repeat is True

    with patch('subprocess.run') as mock_run:
        device_handler.check_and_fire_repeats(0.1)
        mock_run.assert_not_called()

        time.sleep(0.21)
        device_handler.check_and_fire_repeats(0.1)
        mock_run.assert_called_once()
        assert device_handler.last_repeat_time > 0

def test_check_and_fire_repeats_interval_not_elapsed(device_handler):
    """Test that repeat doesn't fire when interval hasn't elapsed"""
    device_handler.history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN})
    device_handler.last_repeat_time = time.monotonic()

    with patch('subprocess.run') as mock_run:
        device_handler.check_and_fire_repeats(0.1)
        mock_run.assert_not_called()

def test_check_and_fire_repeats_interval_elapsed(device_handler):
    """Test that repeat fires when interval has elapsed"""
    device_handler.history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN})
    device_handler.last_repeat_time = time.monotonic() - 0.15

    with patch('subprocess.run') as mock_run:
        device_handler.check_and_fire_repeats(0.1)
        mock_run.assert_called_once()
        assert "echo 'repeat test'" in str(mock_run.call_args)

def test_check_and_fire_repeats_timer_reset_on_clear(device_handler):
    """Test that timer resets when no repeat patterns match"""
    device_handler.history.add_entry(Button(2), ButtonEvent.BUTTON_DOWN, {Button(2): ButtonEvent.BUTTON_DOWN})
    device_handler.last_repeat_time = time.monotonic()

    device_handler.check_and_fire_repeats(0.1)
    assert device_handler.last_repeat_time is None

def test_find_repeat_patterns_ignores_non_repeat(device_handler):
    """Test that find_repeat_patterns only returns patterns with repeat=True"""
    device_handler.history.add_entry(Button(2), ButtonEvent.BUTTON_DOWN, {Button(2): ButtonEvent.BUTTON_DOWN})
    device_handler.history.add_entry(Button(2), ButtonEvent.BUTTON_UP, {Button(2): ButtonEvent.BUTTON_UP})

    repeat_patterns = device_handler.find_repeat_patterns()
    assert len(repeat_patterns) == 0

def test_process_event_sets_timer_for_repeat_pattern(device_handler):
    """Test that process_event sets timer baseline when repeat pattern fires"""
    mock_event = Mock()
    mock_event.type = 1
    mock_event.code = 1
    mock_event.value = 1

    assert device_handler.last_repeat_time is None

    with patch('subprocess.run'):
        device_handler.process_event(mock_event)

    assert device_handler.last_repeat_time is not None
    assert device_handler.last_repeat_time < 0

def test_repeat_command_failure_doesnt_crash(device_handler):
    """Test that command failure in repeat doesn't terminate loop"""
    device_handler.history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN})

    with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, "echo 'repeat test'")):
        device_handler.check_and_fire_repeats(0.1)

def test_multiple_repeat_cycles(device_handler):
    """Test that repeats fire multiple times at correct intervals"""
    device_handler.history.add_entry(Button(1), ButtonEvent.BUTTON_DOWN, {Button(1): ButtonEvent.BUTTON_DOWN})
    device_handler.last_repeat_time = -time.monotonic()

    with patch('subprocess.run') as mock_run:
        time.sleep(0.11)
        device_handler.check_and_fire_repeats(0.05)
        assert mock_run.call_count == 1

        time.sleep(0.06)
        device_handler.check_and_fire_repeats(0.05)
        assert mock_run.call_count == 2

        time.sleep(0.06)
        device_handler.check_and_fire_repeats(0.05)
        assert mock_run.call_count == 3

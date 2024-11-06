"""
Tests for configuration and command pattern handling
"""
import os
import tempfile
from datetime import datetime, timedelta
from pypedal.core.config import CommandPattern, Config, ButtonEvent
from pypedal.core.button import HistoryEntry

def test_button_event():
    """Test ButtonEvent functionality"""
    event = ButtonEvent("1", "v")
    assert str(event) == "1v"
    
    # Test matching
    history_entry = HistoryEntry(
        timestamp=datetime.now(),
        button="1",
        event="pressed",
        button_states={"1": True, "2": False, "3": False}
    )
    assert event.matches(history_entry)
    
    # Test non-matching
    history_entry = HistoryEntry(
        timestamp=datetime.now(),
        button="1",
        event="released",
        button_states={"1": False, "2": False, "3": False}
    )
    assert not event.matches(history_entry)

def test_command_pattern_parsing():
    """Test parsing of different command patterns"""
    # Test button press pattern
    pattern = CommandPattern.parse("1v", "test command")
    assert len(pattern.sequence) == 1
    assert pattern.sequence[0].button == "1"
    assert pattern.sequence[0].event == "v"
    assert pattern.command == "test command"
    assert pattern.time_constraint is None

    # Test button sequence pattern
    pattern = CommandPattern.parse("1,2,3,2,1", "test command")
    assert len(pattern.sequence) == 5
    assert [e.button for e in pattern.sequence] == ["1", "2", "3", "2", "1"]
    assert all(e.event == "v" for e in pattern.sequence)
    assert pattern.time_constraint is None

    # Test sequence with time constraint
    pattern = CommandPattern.parse("1,2,3 < 0.5", "test command")
    assert len(pattern.sequence) == 3
    assert [e.button for e in pattern.sequence] == ["1", "2", "3"]
    assert pattern.time_constraint == 0.5

    # Test shorthand notation
    pattern = CommandPattern.parse("1", "test command")
    assert len(pattern.sequence) == 2
    assert pattern.sequence[0].button == "1"
    assert pattern.sequence[0].event == "v"
    assert pattern.sequence[1].button == "1"
    assert pattern.sequence[1].event == "^"

def test_pattern_matching():
    """Test pattern matching against history"""
    base_time = datetime.now()
    button_states = {"1": False, "2": False, "3": False}
    
    # Create a sequence of button presses
    history = []
    sequence = ["1", "2", "3", "2", "1"]
    for i, button in enumerate(sequence):
        history.append(HistoryEntry(
            base_time + timedelta(seconds=0.1 * i),
            button,
            "pressed",
            button_states.copy()
        ))

    # Test matching full sequence
    pattern = CommandPattern.parse("1,2,3,2,1", "test")
    assert pattern.matches_history(history, base_time)

    # Test matching subsequence
    pattern = CommandPattern.parse("1,2,3", "test")
    assert pattern.matches_history(history[:3], base_time)

    # Test sequence with time constraint
    pattern = CommandPattern.parse("1,2,3 < 0.5", "test")
    assert pattern.matches_history(history[:3], base_time)

    # Test sequence that exceeds time constraint
    pattern = CommandPattern.parse("1,2,3 < 0.1", "test")
    assert not pattern.matches_history(history[:3], base_time)

def test_config_parsing():
    """Test configuration file parsing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('1v: test command 1  # comment\n')
        f.write('1,2,3: test command 2\n')
        f.write('# comment line\n')
        f.write('1,2,3,2,1 < 0.5: test command 3\n')
        f.write('3: test command 4')
        config_path = f.name

    try:
        config = Config(config_path)
        assert len(config.patterns) == 4
        
        # Test first pattern (button press)
        assert len(config.patterns[0].sequence) == 1
        assert config.patterns[0].sequence[0].button == "1"
        assert config.patterns[0].sequence[0].event == "v"
        assert config.patterns[0].command == "test command 1"
        
        # Test second pattern (sequence)
        assert len(config.patterns[1].sequence) == 3
        assert [e.button for e in config.patterns[1].sequence] == ["1", "2", "3"]
        assert config.patterns[1].command == "test command 2"
        
        # Test third pattern (sequence with time)
        assert len(config.patterns[2].sequence) == 5
        assert [e.button for e in config.patterns[2].sequence] == ["1", "2", "3", "2", "1"]
        assert config.patterns[2].time_constraint == 0.5
        assert config.patterns[2].command == "test command 3"
        
        # Test fourth pattern (shorthand)
        assert len(config.patterns[3].sequence) == 2
        assert config.patterns[3].sequence[0].button == "3"
        assert config.patterns[3].sequence[0].event == "v"
        assert config.patterns[3].sequence[1].button == "3"
        assert config.patterns[3].sequence[1].event == "^"
        assert config.patterns[3].command == "test command 4"

        # Test command matching
        base_time = datetime.now()
        button_states = {"1": False, "2": False, "3": False}
        history = [HistoryEntry(base_time, "1", "pressed", button_states)]
        
        command = config.get_matching_command(history)
        assert command == "test command 1"
    finally:
        os.unlink(config_path)

"""
Tests for core module initialization
"""
from pypedal import core

def test_core_exports():
    """Test that core module exports expected classes"""
    assert hasattr(core, 'ButtonState')
    assert hasattr(core, 'HistoryEntry')
    assert hasattr(core, 'History')
    assert hasattr(core, 'CommandPattern')
    assert hasattr(core, 'Config')
    assert hasattr(core, 'DeviceHandler')

def test_import_all():
    """Test that __all__ contains expected exports"""
    expected = {
        'ButtonState',
        'HistoryEntry',
        'History',
        'CommandPattern',
        'Config',
        'DeviceHandler'
    }
    assert set(core.__all__) == expected

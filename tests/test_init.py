"""
Test core module exports
"""
from pypedal import core

def test_core_exports():
    """Test that core module exports expected classes"""
    assert hasattr(core, 'ButtonState')
    assert hasattr(core, 'HistoryEntry')
    assert hasattr(core, 'History')
    assert hasattr(core, 'ButtonEventPattern')
    assert hasattr(core, 'ButtonEventPatternElement')
    assert hasattr(core, 'Config')
    assert hasattr(core, 'DeviceHandler')

def test_import_all():
    """Test that __all__ contains expected exports"""
    expected = {
        'ButtonState',
        'HistoryEntry',
        'History',
        'ButtonEventPattern',
        'ButtonEventPatternElement',
        'Config',
        'DeviceHandler'
    }
    assert set(core.__all__) == expected

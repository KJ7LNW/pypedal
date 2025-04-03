"""
Test core module exports
"""
from pypedal import core

def test_core_exports():
    """Test that core module exports expected classes"""
    assert hasattr(core, 'PedalState')
    assert hasattr(core, 'HistoryEntry')
    assert hasattr(core, 'History')
    assert hasattr(core, 'Button')
    assert hasattr(core, 'ButtonEvent')
    assert hasattr(core, 'ButtonEventPattern')
    assert hasattr(core, 'ButtonEventPatternElement')
    assert hasattr(core, 'Config')
    assert hasattr(core, 'DeviceHandler')
    assert hasattr(core, 'MultiDeviceHandler')

def test_import_all():
    """Test that __all__ contains expected exports"""
    expected = {
        'PedalState',
        'HistoryEntry',
        'History',
        'Button',
        'ButtonEvent',
        'ButtonEventPattern',
        'ButtonEventPatternElement',
        'Config',
        'DeviceHandler',
        'MultiDeviceHandler'
    }
    assert set(core.__all__) == expected

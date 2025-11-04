"""Test mnemonic parsing for wheel events"""
from evdev import ecodes
import re

def test_mnemonic_lookup() -> None:
    """Test that EV_REL and REL_WHEEL can be resolved"""

    # Test EV_REL lookup
    ev_rel = getattr(ecodes, 'EV_REL', None)
    print(f"EV_REL = {ev_rel}")
    assert ev_rel is not None, "EV_REL not found in ecodes"

    # Test REL_WHEEL lookup (direct attribute)
    rel_wheel_code = getattr(ecodes, 'REL_WHEEL', None)
    print(f"REL_WHEEL code = {rel_wheel_code}")
    assert rel_wheel_code is not None, "REL_WHEEL not found in ecodes"

def test_regex_pattern() -> None:
    """Test the type/code=value regex pattern"""
    pattern = r'^(\w+|\d+)/(\w+|\d+)=(-?\d+)$'

    test_cases = [
        'EV_REL/REL_WHEEL=-1',
        'EV_REL/REL_WHEEL=1',
        '2/8=-1',
        '273'
    ]

    for test in test_cases:
        match = re.match(pattern, test)
        print(f"{test}: {match.groups() if match else 'NO MATCH'}")

if __name__ == '__main__':
    print("Testing mnemonic lookup:")
    test_mnemonic_lookup()
    print("\nTesting regex pattern:")
    test_regex_pattern()

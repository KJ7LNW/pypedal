# pypedal

A sophisticated command-line tool for transforming USB foot pedals into powerful macro devices through custom button sequences and timing patterns.

## Overview

pypedal enables you to harness the full potential of USB foot pedals by defining button sequences and mapping them to custom commands. It supports both simple single-button actions and multi-button combinations with precise timing constraints, providing a flexible configuration system for creating custom macros.

## Installation

```bash
pip install -e .
```

## Core Features

### Button Pattern Recognition
pypedal tracks the state of each pedal button and recognizes various patterns:
- Single button press/release (e.g., `1v,1^`)
- Multi-button combinations (e.g., `1v,2`)
- Press-and-hold patterns (e.g., `2v,2^`)
- Time-constrained combinations (`1v,2 < T`)

### State Management
The tool maintains precise state tracking:
- Current button states (pressed/released)
- Event history for pattern matching
- Timing information for sequences
- Button usage tracking for pattern conflicts

### Command Execution
When patterns are recognized, pypedal executes the configured commands, supporting:
- Keyboard shortcuts via xdotool
- Mouse actions
- System commands
- Custom scripts

## Configuration

The configuration file defines button patterns and their associated commands. Here's a comprehensive example showing all supported patterns:

```bash
# Single button press (v) / release (^)
1v: xdotool click 1          # Left click (v) on button press
2^: xdotool key space        # Space on button release (^)

# Multi-button combinations
1v,2: xdotool key ctrl+c     # Copy when holding 1 and pressing 2
1v,3: xdotool key ctrl+v     # Paste when holding 1 and pressing 3

# Space/Right-click combinations
3v,1: xdotool key space      # Space when holding 3 and pressing 1
3v,2: xdotool click 3        # Right click when holding 3 and pressing 2

# Single button actions
1: xdotool click 2           # Middle click on button 1 press/release
3: xdotool key Return        # Enter key on button 3 press/release
3v,3^: foo                   # slightly different from just `3`, see `max_use`

# Mouse button control
2v: xdotool mousedown 1      # Hold left mouse button
2v,2^: xdotool mouseup 1     # Release left mouse button
2^: false                    # not possible, can't have up without down.
```

### Pattern Syntax

The configuration supports these pattern types:

- `Nv`: Execute when button N is pressed
- `N^`: Execute when button N is released
- `1v,2`: Execute when holding button 1 and press/releasing 2
- `1v,2 < T`: Execute when sequence is within T seconds
- `N`: Execute on both press and release (shorthand for Nv,N^)
- `2v,2^`: Execute when button 2 is pressed and released

Timing constraints can be added to any pattern:

```bash
# Execute only if the sequence happens within 0.5 seconds
1v,2 < 0.5: xdotool key ctrl+c
```

### Parsing Detail (and max_use)

When a user presses `1v,2v,2^,3v,3^,1^` on their keypad against the example above, the sequence gets processed like this:

1. `1v,2v,2^` arrives:
   - Matches `1v,2` pattern for ctrl+c
   - The `1v` remains in history with `used=1` waiting for potential next matches
   - The `2v,2^` is popped off stack on release.

2. After that match:
   - History still has `1v` waiting
   - System is ready for more potential matches using this `1v`

3. `3v,3^` arrives:
   - Combined with waiting `1v`, matches `1v,3` pattern for ctrl+v
   - The `3v,3^` is popped off stack on release.
   - The `1v` again remains in history waiting with `used=2`
   - The system is ready for more potential matches

4. Finally `1^` arrives:
   - Looking at history, we _now_ have `1v` and `1^`
   - This could (unintentionally) match the `1:` pattern for middle click (`xdotool click 2`)
   - But `1v` was already used in both ctrl+c and ctrl+v patterns so `1v` has `used=2`, so if will not:
       - When using the `N:` pattern, `max_use=0` is set internally (as a special case of `N:`) to prevent this unwanted trigger, so the sequence ends with no accidental command execution (`xdotool click 2`).
       - However, if the pattern were `1v,1^:` instead of `1:`, `max_use=None` and it **would** execute `xdotool click 2` on release when the stack terminates containing `1v,1^`.  

The above shows how the internal counter `used` and the `max_use` limit prevents unwanted pattern matches when holding buttons across multiple combinations. Without `max_use` tracking, releasing a held button could trigger unintended single-button patterns. Theoretically `max_use` could be configured per-sequence-element for complex sequences, but the syntax does not (currently) support that.  If if did, it might look like `1v[max_use=0],1^[max_use=0]: command` or `2v[max_use=99],3v[max_use=5],1v,...: command`. I'm not sure it that could be usefull or not...

## Usage

Basic command structure:

```bash
pypedal [OPTIONS] [DEVICE]
```

Common options:
- `--config, -c`: Config file with pattern:command mappings
- `--quiet, -q`: Suppress additional output
- `--debug`: Show config structure after loading

Example usage:

```bash
# Use default device with config file
pypedal -c example.conf

# Specify custom device path
pypedal /dev/input/event0 -c example.conf

# Debug configuration
pypedal -c example.conf --debug

# Quiet mode for less output
pypedal -c example.conf -q
```

## Real-time Feedback

pypedal provides colored terminal output for easy monitoring:
- Green: Button press events
- Red: Button release events
- Cyan: Matched patterns
- Yellow: Executed commands

The history display shows:
- Timestamp of each event
- Button number and action
- Current state of all buttons
- Pattern matching status

## Supported Devices
- Works out of the box with "USB 05f3:00ff PI Engineering, Inc. VEC Footpedal" without modification
- Could be made to work with any Linux event-based input device
- Button events are currently hard-coded and need to be made dynamic for better device compatibility, see pypedal/core/device.py if you get errors like 'Error: Unknown button code: 275'

## Development

Run the test suite:
```bash
python -m pytest tests/
```

The test suite covers:
- Button state tracking
- Pattern matching
- Command execution
- Configuration parsing
- Event handling
- History management

## Project Structure

```
pypedal/
├── pypedal/
│   ├── core/
│   │   ├── config.py      # Configuration handling
│   │   ├── device.py      # Device event processing
│   │   ├── history.py     # Event history tracking
│   │   └── pedal.py       # State management
│   ├── __init__.py
│   └── cli.py            # Command-line interface
├── tests/                # Comprehensive test suite
└── setup.py             # Package configuration
```

## Use Cases

pypedal is particularly useful for:
- Text editing: Quick access to copy/paste and navigation
- Mouse control: Precise button control for clicking and dragging
- System control: Custom keyboard shortcuts and commands
- Gaming: Macro combinations
- Accessibility: Alternative input method

## Error Handling

The tool provides robust error handling for:
- Device access permissions
- Configuration syntax errors
- Pattern conflicts
- Command execution failures
- Resource cleanup

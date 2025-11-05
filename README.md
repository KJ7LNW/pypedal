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

### Multi-Device Support
- Configure multiple input devices with sequential button numbering
- Shared pedal state across all devices for cross-device patterns
- Optional shared mode to allow other programs concurrent access
- Supports keyboards, mice, foot pedals, and any evdev device

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

## Device Configuration

Configure input devices using the `dev:` directive to map event codes to button numbers.

### Basic Syntax

```bash
dev: /path/to/device [code1,code2,code3]
```

Buttons are numbered sequentially across all devices in configuration order.

### Event Code Formats

Simple key codes (EV_KEY events):
```bash
dev: /dev/input/event0 [256,257,258]
```

Event type/code/value for specific events:
```bash
dev: /dev/input/event0 [273,EV_REL/REL_WHEEL=-1,EV_REL/REL_WHEEL=1]
```

Numeric or symbolic names work for both type and code:
```bash
dev: /dev/input/event0 [1/272=1,EV_KEY/BTN_LEFT=1]
```

### Auto-Release Behavior

Relative axis events (REL_WHEEL, REL_X, etc.) automatically generate press and release:
```bash
# Wheel down event generates button 11 press+release
dev: /dev/input/mouse [EV_REL/REL_WHEEL=-1]
```

### Shared Device Access

Allow other programs to receive events from the device:
```bash
dev: /dev/input/event0 [256,257,258] [shared]
```

Without `[shared]`, pypedal exclusively grabs the device.

### Multi-Device Setup

```bash
# First pedal: buttons 1,2,3
dev: /dev/input/by-path/pci-0000:75:00.0-usb-0:1.4:1.0-event [256,257,258]

# Second pedal: buttons 4,5,6
dev: /dev/input/by-path/pci-0000:74:00.3-usb-0:2:1.0-event [256,257,258]

# Mouse wheel: buttons 7,8
dev: /dev/input/by-id/usb-Mouse-event-mouse [EV_REL/REL_WHEEL=-1,EV_REL/REL_WHEEL=1]
```

## Configuration

The configuration file defines button patterns and their associated commands.

### Basic Patterns

```bash
# Single button press (v) / release (^)
1v: xdotool click 1          # Left click on button press
2^: xdotool key space        # Space on button release

# Multi-button combinations
1v,2: xdotool key ctrl+c     # Copy when holding 1 and pressing 2
1v,3: xdotool key ctrl+v     # Paste when holding 1 and pressing 3

# Single button actions
1: xdotool click 2           # Middle click on button 1 press/release
3: xdotool key Return        # Enter key on button 3 press/release

# Mouse button control
2v: xdotool mousedown 1      # Hold left mouse button
2v,2^: xdotool mouseup 1     # Release left mouse button
```

### Multi-Device Patterns

```bash
# Configure three foot pedals
dev: /dev/input/by-path/pci-0000:75:00.0-usb-0:1.4:1.0-event [256,257,258]
dev: /dev/input/by-path/pci-0000:74:00.3-usb-0:2:1.0-event [256,257,258]
dev: /dev/input/by-path/pci-0000:0e:00.0-usb-0:3:1.0-event [256,257,258]

# Buttons 1-9 from three pedals
4: xdotool key super+Left    # Button 4 from second pedal
6: xdotool key super+Right   # Button 6 from second pedal
1v,5: xdotool key super+Down # Cross-device: button 1 + button 5
```

### Mouse Wheel Events

```bash
# Configure mouse with wheel events
dev: /dev/input/by-id/usb-Mouse-event-mouse [273,EV_REL/REL_WHEEL=-1,EV_REL/REL_WHEEL=1]

# Buttons 10 (click), 11 (wheel down), 12 (wheel up)
11: xdotool click --repeat 2 5  # Wheel down scrolls down
12: xdotool click --repeat 2 4  # Wheel up scrolls up
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
pypedal [OPTIONS]
```

Options:
- `--config, -c`: Config file with device and pattern mappings (required)
- `--quiet, -q`: Suppress additional output
- `--debug`: Show config structure after loading

Example usage:

```bash
# Run with configuration file
pypedal -c example.conf

# Debug configuration
pypedal -c example.conf --debug

# Quiet mode for less output
pypedal -c example.conf -q
```

Devices are configured in the config file using `dev:` directives. See Device Configuration section.

## Debug Tools

### Device Event Monitor

Use `tools/debug_events.py` to discover event codes from input devices:

```bash
./tools/debug_events.py /dev/input/event88
./tools/debug_events.py /dev/input/by-id/usb-VEC_VEC_USB_Footpedal-event-if00
```

Monitor multiple devices simultaneously:
```bash
./tools/debug_events.py /dev/input/event88 /dev/input/event89
```

The tool displays:
- Real-time event stream with timestamps
- Event type, code, and value for each event
- Human-readable names for event types and codes

Press Ctrl+C to stop monitoring and view suggested configuration:
```
Discovered key codes and suggested configuration:

dev: /dev/input/event88 [256,257,258]
dev: /dev/input/event89 [273]
```

Copy the suggested `dev:` lines directly into your configuration file.

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
pypedal works with any Linux event-based input device through evdev. Device configuration maps input events to button numbers via the `dev:` configuration syntax.

Use `tools/debug_events.py` to discover device event codes for configuration.

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
│   │   ├── config.py         # Configuration handling
│   │   ├── device.py         # Device event processing
│   │   ├── multi_device.py   # Multi-device coordination
│   │   ├── history.py        # Event history tracking
│   │   └── pedal.py          # State management
│   ├── __init__.py
│   └── cli.py               # Command-line interface
├── tools/
│   └── debug_events.py      # Device event discovery
├── tests/                   # Test suite
└── setup.py                 # Package configuration
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

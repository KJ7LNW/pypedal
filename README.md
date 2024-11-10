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
- Single button press/release (e.g., `1v`, `1^`)
- Multi-button combinations (e.g., `1v,2`)
- Press-and-hold patterns (e.g., `2v,2^`)
- Time-constrained combinations (`2v,2^` < 0.5)

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
# Copy/Paste shortcuts
1v,2: xdotool key ctrl+c     # Copy when holding 1 and pressing 2
1v,3: xdotool key ctrl+v     # Paste when holding 1 and pressing 3

# Space/Right-click combinations
3v,1: xdotool key space      # Space when holding 3 and pressing 1
3v,2: xdotool click 3        # Right click when holding 3 and pressing 2

# Single button actions
1: xdotool click 2           # Middle click on button 1 press/release
3: xdotool key Return        # Enter key on button 3 press/release

# Mouse button control
2v: xdotool mousedown 1      # Hold left mouse button
2v,2^: xdotool mouseup 1     # Release left mouse button
```

### Pattern Syntax

The configuration supports these pattern types:

- `Nv`: Execute when button N is pressed
- `N^`: Execute when button N is released
- `N`: Execute on both press and release (shorthand for press/release pair)
- `Nv,M`: Execute when holding button N and pressing M
- `Nv,N^`: Execute when button N is pressed and released

Timing constraints can be added to any pattern:
```bash
# Execute only if the sequence happens within 0.5 seconds
1v,2 < 0.5: xdotool key ctrl+c
```

## Usage

Basic command structure:

```bash
pypedal [OPTIONS] [DEVICE]
```

Common options:
- `--config, -c`: Path to configuration file
- `--format, -f`: Output format (raw/decoded)
- `--quiet/--verbose, -q/-v`: Control output verbosity
- `--debug`: Show configuration structure

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

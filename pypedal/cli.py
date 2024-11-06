"""
Command line interface for pypedal
"""
import click
import struct
import select
import signal
import sys
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

# Event type mappings
EV_TYPES = {
    0: "EV_SYN",  # Synchronization event
    1: "EV_KEY",  # Key/Button event
    4: "EV_MSC"   # Miscellaneous event
}

# Key code mappings for the footpedal - using numeric identifiers
KEY_CODES = {
    256: "1",  # Left pedal
    257: "2",  # Middle pedal
    258: "3"   # Right pedal
}

@dataclass
class ButtonState:
    """Tracks the state of all buttons"""
    states: Dict[str, bool] = None

    def __init__(self):
        self.states = {"1": False, "2": False, "3": False}

    def update(self, button: str, pressed: bool) -> None:
        """Update the state of a button"""
        self.states[button] = pressed

    def get_state(self) -> Dict[str, bool]:
        """Get current state of all buttons"""
        return self.states.copy()

    def __str__(self) -> str:
        """String representation of button states"""
        return " ".join(f"B{b}:{'+' if s else '-'}" for b, s in self.states.items())

@dataclass
class HistoryEntry:
    """Represents a single event in history"""
    timestamp: datetime
    button: str
    event: str  # "pressed" or "released"
    button_states: Dict[str, bool]

    def __str__(self) -> str:
        """String representation of history entry"""
        states = " ".join(f"B{b}:{'+' if s else '-'}" for b, s in self.button_states.items())
        return f"{self.timestamp.strftime('%H:%M:%S.%f')[:-3]} B{self.button} {self.event:8} | {states}"

class History:
    """Maintains history of button events"""
    def __init__(self):
        self.entries: List[HistoryEntry] = []

    def add_entry(self, button: str, event: str, button_states: Dict[str, bool]) -> HistoryEntry:
        """Add a new entry to history"""
        entry = HistoryEntry(
            timestamp=datetime.now(),
            button=button,
            event=event,
            button_states=button_states.copy()
        )
        self.entries.append(entry)
        return entry

    def display_all(self) -> None:
        """Display all history entries with indentation"""
        click.clear()
        click.echo("History (B1/B2/B3: + = pressed, - = released):")
        click.echo("-" * 60)
        for i, entry in enumerate(self.entries, 1):
            click.echo(f"    {i:3d}. {entry}")
        click.echo("-" * 60)

def handle_interrupt(signum, frame):
    """Handle interrupt signal"""
    click.echo("\nReceived interrupt signal. Cleaning up...")
    sys.exit(0)

@click.group()
@click.version_option()
def main():
    """pypedal - A Python-based command line tool"""
    pass

@main.command()
@click.argument('device', default='/dev/input/by-id/usb-VEC_VEC_USB_Footpedal-event-if00', 
                type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option('--format', '-f', type=click.Choice(['raw', 'decoded']), default='decoded',
              help='Output format for events')
@click.option('--quiet/--verbose', '-q/-v', default=False,
              help='Suppress additional output')
def read(device, format, quiet):
    """Read events from an input device.
    
    DEVICE: Path to input device (default: USB footpedal)
    """
    EVENT_SIZE = 24  # struct input_event size
    EVENT_FORMAT = 'llHHI'  # struct input_event format

    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    # Initialize button state and history tracking
    button_state = ButtonState()
    history = History()

    if not quiet:
        click.echo(f"Reading events from: {device}")
        click.echo("Press Ctrl+C to stop")
        click.echo("\nHistory (B1/B2/B3: + = pressed, - = released):")
        click.echo("-" * 60)

    try:
        with open(device, 'rb') as dev:
            while True:
                # Use select to implement a timeout and check for interrupts
                ready, _, _ = select.select([dev], [], [], 0.1)
                if not ready:
                    continue

                event = dev.read(EVENT_SIZE)
                if not event:
                    break
                
                (tv_sec, tv_usec, type_, code, value) = struct.unpack(EVENT_FORMAT, event)
                
                if format == 'raw':
                    click.echo(f"Event: type={type_}, code={code}, value={value}")
                else:
                    # Skip synchronization events (type 0) to reduce noise
                    if type_ == 0:
                        continue
                        
                    type_name = EV_TYPES.get(type_, f"Unknown({type_})")
                    
                    if type_ == 1:  # Key events
                        button = KEY_CODES.get(code, f"Unknown({code})")
                        state = "pressed" if value == 1 else "released"
                        
                        # Update button state
                        button_state.update(button, value == 1)
                        
                        # Add to history and display all entries
                        history.add_entry(button, state, button_state.get_state())
                        history.display_all()
                    else:
                        if not quiet:
                            click.echo(f"Event: {type_name}, code={code}, value={value}")
                
    except PermissionError:
        click.echo("Error: Permission denied. Try running with sudo or set device permissions with:", err=True)
        click.echo("chmod 666 " + device, err=True)
    except FileNotFoundError:
        click.echo(f"Error: Device not found at {device}", err=True)
    except KeyboardInterrupt:
        if not quiet:
            click.echo("\nStopped reading events.")
            click.echo(f"Final state: {button_state}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
    finally:
        if not quiet:
            click.echo("\nExiting...")

if __name__ == '__main__':
    main()

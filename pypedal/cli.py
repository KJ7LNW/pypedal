"""
Command line interface for pypedal
"""
import click
import signal
import sys
from .core import Config, DeviceHandler

def handle_interrupt(signum, frame):
    """Handle interrupt signal"""
    sys.exit(0)

@click.group()
@click.version_option()
def main():
    """pypedal - A Python-based command line tool for USB foot pedals"""
    pass

@main.command()
@click.argument('device', default='/dev/input/by-id/usb-VEC_VEC_USB_Footpedal-event-if00')
@click.option('--config', '-c', type=click.Path(exists=True, dir_okay=False),
              help='Path to configuration file. Format: "pattern: command # comment"')
@click.option('--format', '-f', type=click.Choice(['raw', 'decoded']), default='decoded',
              help='Output format for events')
@click.option('--quiet/--verbose', '-q/-v', default=False,
              help='Suppress additional output')
@click.option('--timeout', '-t', type=float, default=1.0,
              help='Time in seconds to keep history entries for button up events (default: 1.0)')
@click.option('--debug', is_flag=True, help='Show the in-memory structure of the configuration after loading')
def read(device, config, format, quiet, timeout, debug):
    """Read events from a USB foot pedal and execute configured commands.
    
    DEVICE: Path to input device (default: USB footpedal)

    The configuration file supports the following patterns:
        Nv: command          # Run command when button N goes down
        N^: command          # Run command when button N goes up
        1,2,3: command      # Run command when buttons activated in sequence
        1,2,3 < T: command  # Run command when sequence within T seconds
        N: command          # Shorthand for Nv,N^ (button down and up)
        N < T: command      # Shorthand for Nv,N^ < T (within time T)

    Example config file:
        1v: xdotool click 1     # Click when button 1 goes down
        2^: xdotool key space   # Space when button 2 goes up
        1,2,3: echo sequence    # Echo when buttons activated in order
        3: xdotool key Return   # Enter key when button 3 goes down and up
    """
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    # Initialize configuration if provided
    config_handler = None
    if config:
        click.echo(f"Using configuration file: {config}")
        config_handler = Config(config)
        if debug:
            click.echo("Configuration structure:")
            config_handler.dump_structure()

    # Create and run device handler
    handler = DeviceHandler(device, config_handler, quiet, history_timeout=timeout)
    handler.read_events()

if __name__ == '__main__':
    main()

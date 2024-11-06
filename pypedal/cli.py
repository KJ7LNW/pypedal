"""
Command line interface for pypedal
"""
import click
import signal
import sys
from .core import Config, DeviceHandler

def handle_interrupt(signum, frame):
    """Handle interrupt signal"""
    click.echo("\nReceived interrupt signal. Cleaning up...")
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
def read(device, config, format, quiet):
    """Read events from a USB foot pedal and execute configured commands.
    
    DEVICE: Path to input device (default: USB footpedal)

    The configuration file supports the following patterns:
        Nv: command          # Run command when button N is pressed
        N^: command          # Run command when button N is released
        1,2,3: command      # Run command when buttons pressed in sequence
        1,2,3 < T: command  # Run command when sequence within T seconds
        N: command          # Shorthand for Nv,N^ (press and release same button)
        N < T: command      # Shorthand for Nv,N^ < T (within time T)

    Example config file:
        1v: xdotool click 1     # Click when button 1 pressed
        2^: xdotool key space   # Space when button 2 released
        1,2,3: echo sequence    # Echo when buttons pressed in order
        3: xdotool key Return   # Enter key when button 3 pressed and released
    """
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    # Initialize configuration if provided
    config_handler = None
    if config:
        if not quiet:
            click.echo(f"Using configuration file: {config}")
        config_handler = Config(config)

    # Create and run device handler
    handler = DeviceHandler(device, config_handler, quiet)
    handler.read_events()

if __name__ == '__main__':
    main()

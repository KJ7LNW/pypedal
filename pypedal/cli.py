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

@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option()
@click.argument('device', default='/dev/input/by-id/usb-VEC_VEC_USB_Footpedal-event-if00', required=False)
@click.option('--config', '-c', type=click.Path(exists=True, dir_okay=False),
              help='Path to configuration file. Format: "pattern: command # comment"')
@click.option('--format', '-f', type=click.Choice(['raw', 'decoded']), default='decoded',
              help='Output format for events')
@click.option('--quiet/--verbose', '-q/-v', default=False,
              help='Suppress additional output')
@click.option('--debug', is_flag=True, help='Show the in-memory structure of the configuration after loading')
def main(device, config, format, quiet, debug):
    """pypedal - A Python-based command line tool for USB foot pedals.
    
    DEVICE: Path to input device (default: USB footpedal)

    The configuration file supports the following patterns for the pedal's buttons:
        Nv: command          # Run command when pedal button N is pressed
        N^: command          # Run command when pedal button N is released
        1v,2: command        # Run command when holding 1 and pressing 2
        1v,2 < T: command    # Run command when sequence is within T seconds
        N: command           # Shorthand for Nv,N^ (button press and release)
        2v,2^: command       # Run command when button 2 pressed and released

    Example config file:
        1v: xdotool click 1      # Click when pedal button 1 is pressed
        2^: xdotool key space    # Space when pedal button 2 is released
        1v,2: xdotool key ctrl+c # Copy when holding 1 and pressing 2
        3: xdotool key Return    # Enter key when button 3 pressed and released
    """
    # Show help when no arguments provided
    if len(sys.argv) == 1:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit()

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
    handler = DeviceHandler(device, config_handler, quiet)
    handler.read_events()

if __name__ == '__main__':
    main()

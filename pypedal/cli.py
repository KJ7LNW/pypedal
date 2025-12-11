"""
Command line interface for pypedal
"""
import click
import signal
import sys
from .core.instance import InstanceManager

def handle_interrupt(signum, frame):
    """Handle interrupt signal"""
    sys.exit(0)

@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option()
@click.option('--config', '-c', type=click.Path(exists=True, dir_okay=False),
              multiple=True, help='Config file with device and pattern mappings')
@click.option('--quiet', '-q', is_flag=True, help='Suppress additional output')
@click.option('--debug', is_flag=True, help='Show config structure after loading')
@click.option('--repeat-rate', '-r', type=float, default=0.1,
              help='Repeat rate in seconds for patterns marked with repeat (default: 0.1)')
@click.pass_context
def main(ctx, config, quiet, debug, repeat_rate):
    """pypedal - A Python-based command line tool for multiple USB foot pedals.

The configuration file supports the following patterns for the pedal's buttons:

\b
Device configuration:
    dev: /path/to/device [1,2,3]   Configure device with button codes

Pattern syntax:
    Nv: command         Execute when button N is pressed (v)
    N^: command         Execute when button N is released (^)
    Nv,M: command       Execute when holding button N and press/releasing M
    Nv,Mv,M^ < T: command   Execute when sequence is within T seconds
    N: command          Shorthand for Nv,N^ (button press and release)
    2v,2^: command      Execute when button 2 pressed and released (see max_use)
    Nv repeat: command  Execute repeatedly while button N held (rate set via --repeat-rate)

\b
Example config file:
    # Single button press (v) / release (^)
    1v: xdotool click 1          # Left click on button press
    2^: xdotool key space        # Space on button release

\b
    # Multi-button combinations
    1v,2: xdotool key ctrl+c     # Copy when holding 1 and pressing 2
    1v,3: xdotool key ctrl+v     # Paste when holding 1 and pressing 3

\b
    # Mouse button control
    2v: xdotool mousedown 1      # Hold left mouse button
    2v,2^: xdotool mouseup 1     # Release left mouse button

\b
Note: Release-only events (^) must have corresponding press events (v).
      For example, '2^' alone is not valid without a matching '2v' event.
      See the mouse button control example above."""

    if not config:
        click.echo(ctx.get_help())
        ctx.exit(0)

    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    # Initialize instance manager
    manager = InstanceManager(quiet=quiet, debug=debug, repeat_rate=repeat_rate)

    for config_file in config:
        manager.add_config_file(config_file)

    # Create and run multi-instance event loop
    try:
        manager.open_all_devices()

        while manager.process_one_cycle():
            pass

    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except PermissionError as e:
        raise click.ClickException(str(e))
    finally:
        manager.close_all_devices()

if __name__ == '__main__':
    main()

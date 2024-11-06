"""
Command line interface for pypedal
"""
import click
import struct

# Event type mappings
EV_TYPES = {
    0: "EV_SYN",  # Synchronization event
    1: "EV_KEY",  # Key/Button event
    4: "EV_MSC"   # Miscellaneous event
}

# Key code mappings for the footpedal
KEY_CODES = {
    256: "LEFT_PEDAL",
    257: "MIDDLE_PEDAL",
    258: "RIGHT_PEDAL"
}

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

    if not quiet:
        click.echo(f"Reading events from: {device}")
        click.echo("Press Ctrl+C to stop")

    try:
        with open(device, 'rb') as dev:
            while True:
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
                        code_name = KEY_CODES.get(code, f"Unknown({code})")
                        state = "pressed" if value == 1 else "released"
                        click.echo(f"{code_name} {state}")
                    else:
                        click.echo(f"Event: {type_name}, code={code}, value={value}")
                
    except PermissionError:
        click.echo("Error: Permission denied. Try running with sudo or set device permissions with:", err=True)
        click.echo("chmod 666 " + device, err=True)
    except FileNotFoundError:
        click.echo(f"Error: Device not found at {device}", err=True)
    except KeyboardInterrupt:
        if not quiet:
            click.echo("\nStopped reading events.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == '__main__':
    main()

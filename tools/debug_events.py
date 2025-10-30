#!/usr/bin/env python3
"""
Debug script for monitoring input device events.
Displays raw event data and suggests device configuration.

Usage:
    ./debug_events.py /dev/input/event88
    ./debug_events.py /dev/input/by-id/usb-VEC_VEC_USB_Footpedal-event-if00
    ./debug_events.py /dev/input/event88 /dev/input/event89
"""
import signal
import sys
import click
from typing import Dict, Set, List, Optional
from pathlib import Path
from evdev import InputDevice, ecodes
from select import select

def get_code_name(event_type: int, code: int) -> Optional[str]:
    """
    Get human-readable name for event code

    Args:
        event_type: Event type (EV_KEY, EV_REL, etc.)
        code: Event code number

    Returns:
        Human-readable name or None if not found
    """
    try:
        code_map = ecodes.bytype.get(event_type, {})
        name = code_map.get(code)

        if isinstance(name, tuple):
            return '/'.join(name)

        return name
    except (KeyError, AttributeError):
        return None

class DeviceMonitor:
    """Monitor input device events and track discovered key codes"""

    def __init__(self, device_paths: List[str]):
        """
        Initialize device monitor

        Args:
            device_paths: List of device paths to monitor
        """
        self.device_paths = device_paths
        self.devices: Dict[str, InputDevice] = {}
        self.key_codes: Dict[str, Set[int]] = {}
        self.running = True

        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum: int, frame: Optional[object]) -> None:
        """Handle interrupt signal and display configuration suggestions"""
        self.running = False
        click.echo()
        click.secho("Discovered key codes and suggested configuration:", bold=True)
        click.echo()

        for path in self.device_paths:
            codes = sorted(self.key_codes.get(path, set()))
            if codes:
                codes_str = ','.join(map(str, codes))
                click.echo(f"{click.style('dev:', fg='green')} {path} [{codes_str}]")
            else:
                click.secho(f"# No key events detected for: {path}", fg="yellow")

        sys.exit(0)

    def open_devices(self) -> None:
        """Open all device paths for reading"""
        for path in self.device_paths:
            try:
                dev = InputDevice(path)

                try:
                    dev.grab()
                except OSError as e:
                    click.echo(f"{click.style('Warning:', fg='yellow')} Could not grab {path}: {e}", err=True)

                self.devices[path] = dev
                self.key_codes[path] = set()
                click.echo(f"{click.style('Monitoring:', fg='green')} {path}")
            except FileNotFoundError:
                click.secho(f"Error: Device not found: {path}", fg="red", err=True)
                sys.exit(1)
            except PermissionError:
                click.secho(f"Error: Permission denied: {path}", fg="red", err=True)
                click.echo(f"Try: sudo {' '.join(sys.argv)}", err=True)
                sys.exit(1)

    def close_devices(self) -> None:
        """Close all open devices"""
        for dev in self.devices.values():
            try:
                dev.ungrab()
            except OSError:
                pass
            dev.close()

    def display_event(self, path: str, event) -> None:
        """
        Display formatted event information

        Args:
            path: Device path
            event: evdev.InputEvent object
        """
        timestamp = event.timestamp()
        type_name = ecodes.EV.get(event.type, f"UNKNOWN({event.type})")

        device_name = click.style(Path(path).name, fg='cyan')
        type_styled = click.style(type_name, bold=True)

        code_name = get_code_name(event.type, event.code)
        if code_name:
            code_display = f"{event.code} ({code_name})"
        else:
            code_display = str(event.code)

        click.echo(f"{device_name} "
                   f"time={timestamp} "
                   f"type={type_styled} "
                   f"code={code_display} "
                   f"value={event.value}")

        if event.type == ecodes.EV_KEY:
            self.key_codes[path].add(event.code)

    def monitor_events(self) -> None:
        """Monitor and display events from all devices"""
        self.open_devices()

        try:
            while self.running:
                device_fds = {dev.fd: (path, dev) for path, dev in self.devices.items()}
                ready, _, _ = select(list(device_fds.keys()), [], [], 0.1)

                for fd in ready:
                    path, dev = device_fds[fd]
                    event = dev.read_one()

                    if event:
                        self.display_event(path, event)

        except Exception as e:
            click.secho(f"Error: {str(e)}", fg="red", err=True)
            raise
        finally:
            self.close_devices()

def main() -> None:
    """Main entry point"""
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        click.echo(__doc__)
        sys.exit(0 if len(sys.argv) > 1 else 1)

    device_paths = sys.argv[1:]

    click.secho("Input Device Event Monitor", bold=True)
    click.echo("Press Ctrl+C to stop and view configuration suggestions")
    click.echo()

    monitor = DeviceMonitor(device_paths)
    monitor.monitor_events()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate example keyboard configuration for all evdev key escape code sequences.
Outputs configuration in scancode sequence order.

Usage:
    ./generate_keyboard_config.py
    ./generate_keyboard_config.py -w keyboard-all.conf
"""
import sys
import click
from evdev import ecodes

@click.command()
@click.option('-w', '--write', 'output_file', type=click.Path(), help='Write output to file')
def main(output_file: str) -> None:
    """Generate keyboard configuration for all evdev key codes"""

    key_codes = []
    for code, name in ecodes.KEY.items():
        if code == 0:
            continue
        if isinstance(name, list):
            name = name[0]
        if isinstance(name, str) and name.startswith('KEY_'):
            key_codes.append((code, name))

    key_codes.sort()

    output = []
    codes_str = ','.join(str(code) for code, _ in key_codes)
    output.append(f"dev: /dev/input/eventX [{codes_str}]")
    output.append("")

    for i, (code, name) in enumerate(key_codes, 1):
        output.append(f"{i}: echo 'button={i} [code {code}, {name}]'")

    result = '\n'.join(output) + '\n'

    if output_file:
        with open(output_file, 'w') as f:
            f.write(result)
    else:
        print(result, end='')

if __name__ == "__main__":
    main()

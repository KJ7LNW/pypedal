#!/usr/bin/env python3
"""
Device discovery script for pypedal.
Identifies USB pedal devices and generates configuration entries.
"""
import subprocess
import re
import os
from pathlib import Path

def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{cmd}': {e}")
        return ""

def parse_usb_devices(vendor_product):
    """Parse USB device info to find pedal devices.
    
    Args:
        vendor_product: USB vendor:product ID (e.g. '05f3:00ff')
    """
    devices = []
    
    # Get list of devices matching vendor:product ID
    output = run_command(f"lsusb -d {vendor_product}")
    if not output:
        return devices
        
    for line in output.split('\n'):
        if not line:
            continue
        # Match lines like: Bus 005 Device 002: ID 05f3:00ff PI Engineering, Inc. VEC Footpedal
        match = re.match(r'Bus (\d+) Device (\d+): ID .*', line)
        if match:
            bus = match.group(1)
            dev = match.group(2)
            
            # Get PCI path from udevadm
            usb_dev = f"/dev/bus/usb/{bus.zfill(3)}/{dev.zfill(3)}"
            detail = run_command(f"udevadm info --query=all --name={usb_dev}")
            path_match = re.search(r'E: ID_PATH=(.*)', detail)
            if path_match:
                devices.append({
                    'usb_info': line.strip(),
                    'pci_path': path_match.group(1),
                    'bus': bus,
                    'dev': dev
                })
    
    return devices

def get_input_devices():
    """Get mapping of input device paths."""
    output = run_command("ls -l /dev/input/by-path")
    if not output:
        print("Warning: Could not read /dev/input/by-path")
        return {}

    devices = {}
    # Match lines like: pci-0000:74:00.3-usb-0:2:1.0-event -> ../event258
    for line in output.split('\n'):
        if not line or not 'usb' in line or not 'event' in line:
            continue
        parts = line.split(' -> ')
        if len(parts) != 2:
            continue
        path = parts[0].split()[-1]
        # Extract PCI path without interface numbers
        pci_match = re.match(r'(pci-[^-]+-usb-[^:]+)', path)
        if pci_match:
            base_path = pci_match.group(1)
            devices[base_path] = {
            'path': f"/dev/input/by-path/{path}",
            'event': parts[1].split('/')[-1]
        }
    
    return devices
def generate_config(usb_devices, input_devices):
    """Generate configuration entries for discovered devices."""
    config = []
    # TODO: These event codes are currently hardcoded for VEC Footpedal
    # Need to implement proper event code discovery by:
    # 1. Reading /sys/class/input/eventX/device/capabilities/key
    # 2. Parsing the key bitmap (e.g. "7 0 0 0 0") to determine available keys
    event_codes = [256, 257, 258]
    
    
    for device in usb_devices:
        config.append(f"# Device: {device['usb_info']}")
        
        # Find matching input device path using PCI path
        found = False
        for base_path, info in input_devices.items():
            if base_path in device['pci_path']:
                config.append(f"dev: {info['path']} [{','.join(map(str, event_codes))}]")
                found = True
                break
        
        if not found:
            config.append("# Warning: No matching input device found")
        
        config.append("")  # Empty line between devices
    
    return "\n".join(config).rstrip()  # Remove trailing newline

def main():
    """Main entry point."""
    vendor_product = "05f3:00ff"  # VEC Footpedal
    print(f"Discovering USB devices (ID {vendor_product})...")
    usb_devices = parse_usb_devices(vendor_product)
    
    if not usb_devices:
        print("No matching devices found")
        return
    
    print(f"Found {len(usb_devices)} device(s)\n")
    input_devices = get_input_devices()
    
    config = generate_config(usb_devices, input_devices)
    print("Generated configuration:")
    print("------------------------")
    print(config)

if __name__ == "__main__":
    main()
import sys
import tempfile
import os
from unittest.mock import patch
from click.testing import CliRunner
from pypedal.cli import main

print(f"Initial sys.argv: {sys.argv}")

runner = CliRunner()
result1 = runner.invoke(main, ['--version'])
print(f"\nAfter test_version:")
print(f"  sys.argv: {sys.argv}")
print(f"  exit_code: {result1.exit_code}")

with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
    f.write('dev: /dev/input/event0 [1,2,3]\n1v: echo test')
    config_path = f.name

try:
    with patch('pypedal.core.instance.InstanceManager') as MockManager:
        mock_instance = MockManager.return_value
        mock_instance.open_all_devices.side_effect = FileNotFoundError("Device not found")
        result2 = runner.invoke(main, ['--config', config_path])
        print(f"\nAfter test_command_with_config:")
        print(f"  sys.argv: {sys.argv}")
        print(f"  exit_code: {result2.exit_code}")
        print(f"  output: {result2.output}")
        print(f"  exception: {result2.exception}")
finally:
    os.unlink(config_path)

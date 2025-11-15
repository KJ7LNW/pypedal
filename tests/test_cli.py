"""
Tests for pypedal CLI interface
"""
import os
import signal
import tempfile
from unittest.mock import patch
import pytest
from click.testing import CliRunner
from pypedal.cli import main

@pytest.fixture(autouse=True)
def restore_signal_handlers():
    sigint_handler = signal.getsignal(signal.SIGINT)
    sigterm_handler = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)

def test_version():
    """Test version display"""
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert 'version' in result.output.lower()

def test_command_with_config():
    """Test with valid config file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('dev: /dev/input/event0 [1,2,3]\n1v: echo test')
        config_path = f.name

    try:
        runner = CliRunner()
        with patch('pypedal.core.instance.InputDevice') as MockDevice:
            MockDevice.side_effect = FileNotFoundError("Device not found")
            result = runner.invoke(main, ['--config', config_path])
            assert result.exit_code != 0
            assert 'Device not found' in result.output
    finally:
        os.unlink(config_path)

def test_command_no_config():
    """Test missing required config file"""
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert '--config' in result.output

def test_command_quiet_mode():
    """Test quiet mode suppresses output"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('dev: /dev/input/event0 [1,2,3]\n1v: echo test')
        config_path = f.name

    try:
        runner = CliRunner()
        with patch('pypedal.core.instance.InputDevice') as MockDevice:
            MockDevice.side_effect = FileNotFoundError("Device not found")
            result = runner.invoke(main, ['--quiet', '--config', config_path])
            assert result.exit_code != 0
            assert 'Device not found' in result.output
            assert 'Configuration file:' not in result.output
            result = runner.invoke(main, ['-q', '--config', config_path])
            assert result.exit_code != 0
            assert 'Configuration file:' not in result.output
    finally:
        os.unlink(config_path)

def test_command_permission_error():
    """Test permission error handling"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('dev: /dev/input/event0 [1,2,3]\n1v: echo test')
        config_path = f.name

    try:
        runner = CliRunner()
        with patch('pypedal.core.instance.InputDevice') as MockDevice:
            MockDevice.side_effect = PermissionError("Permission denied")
            result = runner.invoke(main, ['--config', config_path])
            assert result.exit_code != 0
            assert 'Permission denied' in result.output
    finally:
        os.unlink(config_path)

def test_config_no_devices():
    """Test config file with no device configurations"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('1v: echo test')
        config_path = f.name

    try:
        runner = CliRunner()
        result = runner.invoke(main, ['--config', config_path])
        assert result.exit_code != 0
        assert 'No devices configured' in result.output
    finally:
        os.unlink(config_path)

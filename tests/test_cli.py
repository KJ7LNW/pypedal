"""
Tests for pypedal CLI interface
"""
import os
import tempfile
from unittest.mock import patch
from click.testing import CliRunner
from pypedal.cli import main

def test_version():
    """Test version display"""
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert 'version' in result.output.lower()

def test_read_command_with_config():
    """Test read command with config file option"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('1v: echo test')
        config_path = f.name

    try:
        runner = CliRunner()
        with patch('pypedal.core.device.DeviceHandler.read_events') as mock_read:
            mock_read.side_effect = FileNotFoundError("Device not found")
            result = runner.invoke(main, ['read', '--config', config_path, '/nonexistent/device'])
            assert result.exit_code != 0
            assert 'Using configuration file:' in result.output
            assert 'Device not found' in str(result.exception)
    finally:
        os.unlink(config_path)

def test_read_command_no_config():
    """Test read command without config file"""
    runner = CliRunner()
    with patch('pypedal.core.device.DeviceHandler.read_events') as mock_read:
        mock_read.side_effect = FileNotFoundError("Device not found")
        result = runner.invoke(main, ['read', '/nonexistent/device'])
        assert result.exit_code != 0
        assert 'Using configuration file:' not in result.output
        assert 'Device not found' in str(result.exception)

def test_read_command_quiet_mode():
    """Test read command in quiet mode"""
    runner = CliRunner()
    with patch('pypedal.core.device.DeviceHandler.read_events') as mock_read:
        mock_read.side_effect = FileNotFoundError("Device not found")
        result = runner.invoke(main, ['read', '--quiet', '/nonexistent/device'])
        assert result.exit_code != 0
        assert 'Using configuration file:' not in result.output
        assert 'Device not found' in str(result.exception)

def test_read_command_format_option():
    """Test read command format option"""
    runner = CliRunner()
    # Test with invalid format
    result = runner.invoke(main, ['read', '--format', 'invalid', '/nonexistent/device'])
    assert result.exit_code != 0
    assert 'Invalid value for' in result.output

    # Test with valid format
    with patch('pypedal.core.device.DeviceHandler.read_events') as mock_read:
        mock_read.side_effect = FileNotFoundError("Device not found")
        result = runner.invoke(main, ['read', '--format', 'raw', '/nonexistent/device'])
        assert result.exit_code != 0
        assert 'Device not found' in str(result.exception)

def test_read_command_permission_error():
    """Test read command with permission error"""
    runner = CliRunner()
    with patch('pypedal.core.device.DeviceHandler.read_events') as mock_read:
        mock_read.side_effect = PermissionError("Permission denied")
        result = runner.invoke(main, ['read', '/dev/input/event0'])
        assert result.exit_code != 0
        assert 'Permission denied' in str(result.exception)

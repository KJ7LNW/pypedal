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

def test_command_with_config():
    """Test with config file option"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('1v: echo test')
        config_path = f.name

    try:
        runner = CliRunner()
        with patch('pypedal.core.device.DeviceHandler.read_events') as mock_read:
            mock_read.side_effect = FileNotFoundError("Device not found")
            result = runner.invoke(main, ['--config', config_path])
            assert result.exit_code != 0
            assert 'Using configuration file:' in result.output
            assert 'Device not found' in str(result.exception)
    finally:
        os.unlink(config_path)

def test_command_no_config():
    """Test without config file"""
    runner = CliRunner()
    with patch('pypedal.core.device.DeviceHandler.read_events') as mock_read:
        mock_read.side_effect = FileNotFoundError("Device not found")
        result = runner.invoke(main, ['/nonexistent/device'])
        assert result.exit_code != 0
        assert 'Using configuration file:' not in result.output
        assert 'Device not found' in str(result.exception)

def test_command_quiet_mode():
    """Test quiet mode suppresses output"""
    runner = CliRunner()
    with patch('pypedal.core.device.DeviceHandler.read_events') as mock_read:
        mock_read.side_effect = FileNotFoundError("Device not found")
        # Test with quiet flag
        result = runner.invoke(main, ['--quiet', '/nonexistent/device'])
        assert result.exit_code != 0
        assert 'Using configuration file:' not in result.output
        # Test with short flag
        result = runner.invoke(main, ['-q', '/nonexistent/device'])
        assert result.exit_code != 0
        assert 'Using configuration file:' not in result.output

def test_command_permission_error():
    """Test permission error handling"""
    runner = CliRunner()
    with patch('pypedal.core.device.DeviceHandler.read_events') as mock_read:
        mock_read.side_effect = PermissionError("Permission denied")
        result = runner.invoke(main, ['/dev/input/event0'])
        assert result.exit_code != 0
        assert 'Permission denied' in str(result.exception)

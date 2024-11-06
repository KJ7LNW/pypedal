"""
Tests for pypedal CLI
"""
import os
import tempfile
from click.testing import CliRunner
from pypedal.cli import main, Config

def test_version():
    """Test version display"""
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert 'version' in result.output.lower()

def test_config_parsing():
    """Test configuration file parsing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('1: test command 1  # comment\n')
        f.write('2: test command 2\n')
        f.write('# comment line\n')
        f.write('3: test command 3')
        config_path = f.name

    try:
        config = Config(config_path)
        assert config.get_action('1') == 'test command 1'
        assert config.get_action('2') == 'test command 2'
        assert config.get_action('3') == 'test command 3'
        assert config.get_action('4') is None
    finally:
        os.unlink(config_path)

def test_read_command_with_config():
    """Test read command with config file option"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('1: echo test')
        config_path = f.name

    try:
        runner = CliRunner()
        # Note: Using a non-existent device path since we can't easily mock device input
        result = runner.invoke(main, ['read', '--config', config_path, '/nonexistent/device'])
        assert result.exit_code != 0  # Should fail due to device not found
        assert 'Device not found' in result.output
        assert 'Using configuration file:' in result.output
    finally:
        os.unlink(config_path)

def test_read_command_no_config():
    """Test read command without config file"""
    runner = CliRunner()
    result = runner.invoke(main, ['read', '/nonexistent/device'])
    assert result.exit_code != 0  # Should fail due to device not found
    assert 'Device not found' in result.output
    assert 'Using configuration file:' not in result.output

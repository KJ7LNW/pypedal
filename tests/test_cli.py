"""
Tests for pypedal CLI
"""
from click.testing import CliRunner
from pypedal.cli import main

def test_version():
    """Test version display"""
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert 'version' in result.output.lower()

def test_info():
    """Test info command"""
    runner = CliRunner()
    result = runner.invoke(main, ['info'])
    assert result.exit_code == 0
    assert 'System Information' in result.output

def test_process_no_file():
    """Test process command with missing file"""
    runner = CliRunner()
    result = runner.invoke(main, ['process', 'nonexistent.txt'])
    assert result.exit_code == 2  # Click's error exit code
    assert 'Error' in result.output

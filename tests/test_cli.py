"""Tests for the inspect4all CLI."""

from click.testing import CliRunner

from inspect4all.cli import main

runner = CliRunner()


def test_version():
    """Test that --version prints the version."""
    from inspect4all import __version__

    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help():
    """Test that --help prints usage information."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "inspect4all" in result.output


def test_missing_input_path():
    """Test that missing required --input_path exits with error."""
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    assert (
        "Missing option" in result.output or "required" in result.output.lower()
    )

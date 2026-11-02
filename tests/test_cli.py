"""Tests for the inspect4all CLI."""

from unittest.mock import patch

from click.testing import CliRunner

from inspect4all.cli import main

runner = CliRunner()


def test_bare_input_runs_inspect_and_enrich(tmp_path):
    """No subcommand + -i runs the full pipeline (inspect then enrich)."""
    (tmp_path / "x.py").write_text("def f():\n    pass\n")
    out_dir = tmp_path / "out"
    with (
        patch("inspect4all.enrichment.llm.build_chat_model"),
        patch("inspect4all.enrichment.runner.enrich_repo") as mock_enrich,
        patch(
            "inspect4all.enrichment.runner.write_enriched_outputs"
        ) as mock_write,
    ):
        result = runner.invoke(main, ["-i", str(tmp_path), "-o", str(out_dir)])
    assert result.exit_code == 0, result.output
    assert (out_dir / "repository_analysis.json").exists()
    assert mock_enrich.call_count == 1
    assert mock_write.call_count == 1


def test_enrich_failure_keeps_inspect_outputs(tmp_path):
    """LLM being unreachable must not fail the run or drop inspect output."""
    (tmp_path / "x.py").write_text("def f():\n    pass\n")
    out_dir = tmp_path / "out"
    with patch(
        "inspect4all.enrichment.llm.build_chat_model",
        side_effect=ConnectionError("no server"),
    ):
        result = runner.invoke(main, ["-i", str(tmp_path), "-o", str(out_dir)])
    assert result.exit_code == 0, result.output
    assert (out_dir / "repository_analysis.json").exists()
    assert "enrichment failed" in result.output.lower()


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


def test_no_args_shows_group_help():
    """Invoking the bare group lists the available subcommands."""
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "inspect" in result.output and "enrich" in result.output


def test_cli_inspect_python_repo(tmp_path):
    (tmp_path / "main.py").write_text(
        '"""A simple module."""\n\n'
        "def hello(name: str) -> str:\n"
        '    """Greet someone.\n\n'
        "    Args:\n"
        "        name: The name to greet.\n\n"
        "    Returns:\n"
        "        Greeting string.\n"
        '    """\n'
        '    return f"Hello, {name}"\n\n'
        'if __name__ == "__main__":\n'
        '    print(hello("world"))\n'
    )
    (tmp_path / "README.md").write_text("# Test Repo\nA test repository.")
    out_dir = tmp_path / "output"
    result = runner.invoke(
        main, ["inspect", "-i", str(tmp_path), "-o", str(out_dir)]
    )
    assert result.exit_code == 0, result.output
    assert (out_dir / "repository_analysis.json").exists()


def test_cli_creates_output_dir(tmp_path):
    (tmp_path / "x.py").write_text("x = 1")
    out_dir = tmp_path / "nested" / "output"
    result = runner.invoke(
        main, ["inspect", "-i", str(tmp_path), "-o", str(out_dir)]
    )
    assert result.exit_code == 0
    assert out_dir.exists()


def test_cli_embedding_export_flag(tmp_path):
    """-ee/--embedding_export writes embedding_export.json; without the
    flag (and without --all) it is not produced."""
    (tmp_path / "x.py").write_text("def f():\n    pass\n")
    out_dir = tmp_path / "out_ee"
    result = runner.invoke(
        main, ["inspect", "-i", str(tmp_path), "-o", str(out_dir), "-ee"]
    )
    assert result.exit_code == 0, result.output
    assert (out_dir / "embedding_export.json").exists()

    out_dir2 = tmp_path / "out_plain"
    result = runner.invoke(
        main, ["inspect", "-i", str(tmp_path), "-o", str(out_dir2)]
    )
    assert result.exit_code == 0, result.output
    assert not (out_dir2 / "embedding_export.json").exists()


def test_cli_all_flag_includes_embedding_export(tmp_path):
    (tmp_path / "x.py").write_text("def f():\n    pass\n")
    out_dir = tmp_path / "out_all"
    result = runner.invoke(
        main, ["inspect", "-i", str(tmp_path), "-o", str(out_dir), "--all"]
    )
    assert result.exit_code == 0, result.output
    assert (out_dir / "embedding_export.json").exists()

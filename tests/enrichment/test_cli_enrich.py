from unittest.mock import patch

from click.testing import CliRunner

from inspect4all.cli import main


def test_enrich_subcommand_wires_runner(tmp_path):
    (tmp_path / "repository_analysis.json").write_text("{}")
    runner = CliRunner()
    with (
        patch("inspect4all.enrichment.runner.run_enrichment") as mock_run,
        patch("inspect4all.enrichment.llm.build_chat_model") as mock_model,
    ):
        mock_run.return_value.stats = {
            "enriched": 2,
            "failed": 0,
            "skipped": 1,
        }
        result = runner.invoke(
            main,
            [
                "enrich",
                "-i",
                str(tmp_path),
                "--model",
                "m",
                "--max-records",
                "5",
            ],
        )
    assert result.exit_code == 0, result.output
    mock_model.assert_called_once()
    assert mock_run.call_count == 1
    kwargs = mock_run.call_args.kwargs
    assert kwargs["max_records"] == 5
    assert kwargs["model_id"] == "m"


def test_enrich_help_lists_options():
    result = CliRunner().invoke(main, ["enrich", "--help"])
    assert result.exit_code == 0
    assert "--base-url" in result.output
    assert "--mode" in result.output
    assert "--docstring-target" in result.output


def test_enrich_docstring_target_all_passed_to_runner(tmp_path):
    (tmp_path / "repository_analysis.json").write_text("{}")
    runner = CliRunner()
    with (
        patch("inspect4all.enrichment.runner.run_enrichment") as mock_run,
        patch("inspect4all.enrichment.llm.build_chat_model"),
    ):
        mock_run.return_value.stats = {
            "enriched": 0,
            "failed": 0,
            "skipped": 0,
        }
        result = runner.invoke(
            main,
            ["enrich", "-i", str(tmp_path), "--docstring-target", "all"],
        )
    assert result.exit_code == 0, result.output
    assert mock_run.call_args.kwargs["docstring_target"] == "all"


def test_enrich_docstring_target_defaults_to_undocumented(tmp_path):
    (tmp_path / "repository_analysis.json").write_text("{}")
    runner = CliRunner()
    with (
        patch("inspect4all.enrichment.runner.run_enrichment") as mock_run,
        patch("inspect4all.enrichment.llm.build_chat_model"),
    ):
        mock_run.return_value.stats = {
            "enriched": 0,
            "failed": 0,
            "skipped": 0,
        }
        runner.invoke(main, ["enrich", "-i", str(tmp_path)])
    assert mock_run.call_args.kwargs["docstring_target"] == "undocumented"

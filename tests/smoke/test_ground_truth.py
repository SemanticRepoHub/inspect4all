"""Smoke gate: run the real CLI against complete repositories.

Two vendored repos under tests/fixtures/ (apache/beam-starter-python and
apache/beam-starter-java, .git stripped) always run, so the gate works on any
machine. Larger repos from the dissertation ground-truth dataset run when the
dataset is present and skip otherwise.

The CLI runs as a subprocess — subprocess exit codes catch
interpreter-teardown crashes (e.g. the libenry SIGSEGV) that in-process tests
cannot see. Deselected from the default pytest run; invoke with `make smoke`
or `uv run pytest -m smoke`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parents[1] / "fixtures"
GROUND_TRUTH = (
    Path.home() / "Documents/msc_studies/dissertation/data/ground_truth/data"
)

FIXTURE_REPOS = [
    pytest.param("beam-starter-python", "Python", id="fixture-python"),
    pytest.param("beam-starter-java", "Java", id="fixture-java"),
]

GROUND_TRUTH_REPOS = [
    pytest.param("dateutil/dateutil", "Python", id="dateutil"),
    pytest.param("coleifer/peewee", "Python", id="peewee"),
    pytest.param("coobird/thumbnailator", "Java", id="thumbnailator"),
]

pytestmark = pytest.mark.smoke


def _run_cli_and_validate(
    repo_path: Path, out_dir: Path, language: str
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inspect4all.cli",
            "inspect",
            "-i",
            str(repo_path),
            "-o",
            str(out_dir),
            "--all",
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode >= 0, (
        f"CLI crashed with signal {-result.returncode}: {result.stderr[-500:]}"
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr[-1000:]}"

    analysis = json.loads((out_dir / "repository_analysis.json").read_text())
    export = json.loads((out_dir / "embedding_export.json").read_text())

    assert analysis["repository"]["languages"].get(language, 0) > 0
    assert analysis["files"], "no files were analysed"
    assert export["code_records"], "embedding export has no code records"

    # Files whose language has no adapter must be recorded (language ->
    # repo-relative paths) for prevalence analysis.
    unhandled = analysis["metadata"]["unhandled_files"]
    for paths in unhandled.values():
        for path in paths:
            assert not path.startswith("/"), path

    # Paths and IDs must stay repo-relative (portable embedding IDs).
    for record in export["code_records"][:20]:
        assert not record["file_path"].startswith("/"), record["file_path"]
        assert not record["id"].startswith("/"), record["id"]


@pytest.mark.parametrize(("repo", "language"), FIXTURE_REPOS)
def test_cli_on_vendored_fixture(
    repo: str, language: str, tmp_path: Path
) -> None:
    _run_cli_and_validate(FIXTURES / repo, tmp_path, language)


@pytest.mark.skipif(
    not GROUND_TRUTH.is_dir(),
    reason=f"ground-truth dataset not found at {GROUND_TRUTH}",
)
@pytest.mark.parametrize(("repo", "language"), GROUND_TRUTH_REPOS)
def test_cli_on_ground_truth_repo(
    repo: str, language: str, tmp_path: Path
) -> None:
    repo_path = GROUND_TRUTH / repo
    if not repo_path.is_dir():
        pytest.skip(f"repo not present: {repo_path}")
    _run_cli_and_validate(repo_path, tmp_path, language)

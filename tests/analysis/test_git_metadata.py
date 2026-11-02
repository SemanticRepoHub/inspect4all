"""Tests for git metadata extraction via GitPython.

Fixtures build throwaway git repos inside tmp_path with subprocess git
commands — no mocks, real repositories.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from inspect4all.analysis.git_metadata import extract_git_metadata

if TYPE_CHECKING:
    from pathlib import Path


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "tester@example.com")
    _git(tmp_path, "config", "user.name", "Tester")
    (tmp_path / "a.txt").write_text("one\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "first")
    (tmp_path / "b.txt").write_text("two\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "second")
    return tmp_path


def test_non_git_directory_returns_none(tmp_path: Path) -> None:
    assert extract_git_metadata(tmp_path) is None


def test_extracts_commit_and_history(git_repo: Path) -> None:
    meta = extract_git_metadata(git_repo)
    assert meta is not None
    assert len(meta["commit"]) == 40  # full hexsha
    assert meta["n_commits"] == 2
    assert meta["n_contributors"] == 1
    assert meta["first_commit_date"] <= meta["last_commit_date"]
    assert isinstance(meta["branch"], str) and meta["branch"]


def test_no_remote_and_no_tags_are_none(git_repo: Path) -> None:
    meta = extract_git_metadata(git_repo)
    assert meta is not None
    assert meta["remote_url"] is None
    assert meta["latest_tag"] is None


def test_extracts_remote_and_tag(git_repo: Path) -> None:
    _git(git_repo, "remote", "add", "origin", "https://example.com/foo.git")
    _git(git_repo, "tag", "v1.0")
    meta = extract_git_metadata(git_repo)
    assert meta is not None
    assert meta["remote_url"] == "https://example.com/foo.git"
    assert meta["latest_tag"] == "v1.0"


def test_empty_git_repo_returns_none(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    assert extract_git_metadata(tmp_path) is None


def test_credentials_stripped_from_remote_url(git_repo: Path) -> None:
    """Clones made with a token in the URL must not leak it into output."""
    _git(
        git_repo,
        "remote",
        "add",
        "origin",
        "https://ghp_secrettoken123@github.com/org/repo.git",
    )
    meta = extract_git_metadata(git_repo)
    assert meta is not None
    assert meta["remote_url"] == "https://github.com/org/repo.git"


def test_ssh_remote_url_unchanged(git_repo: Path) -> None:
    _git(git_repo, "remote", "add", "origin", "git@github.com:org/repo.git")
    meta = extract_git_metadata(git_repo)
    assert meta is not None
    assert meta["remote_url"] == "git@github.com:org/repo.git"

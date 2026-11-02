"""Repository metadata from the local git history via GitPython.

Reads the clone's .git directory only — no network, no GitHub API. Returns
None when the directory is not a usable git repository so callers can omit
the metadata block instead of failing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from git import InvalidGitRepositoryError, NoSuchPathError, Repo

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def _sanitize_url(url: str) -> str:
    """Strip userinfo (tokens, passwords) from http(s) remote URLs.

    Clones made with credentials embedded in the URL (e.g.
    https://ghp_...@github.com/org/repo.git) would otherwise leak the secret
    into analysis output. SCP-style ssh URLs (git@host:path) have no
    parseable scheme and carry no secret, so they pass through unchanged.
    """
    parts = urlsplit(url)
    if parts.scheme and parts.netloc and "@" in parts.netloc:
        host = parts.netloc.rsplit("@", 1)[-1]
        return urlunsplit(parts._replace(netloc=host))
    return url


def extract_git_metadata(repo_path: Path) -> dict | None:
    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return None

    try:
        commits = list(repo.iter_commits())
    except ValueError:
        # Repository exists but has no commits yet.
        return None

    try:
        branch = repo.active_branch.name
    except TypeError:
        branch = None  # detached HEAD

    remote_url = None
    if repo.remotes:
        remote = (
            repo.remotes["origin"]
            if "origin" in [r.name for r in repo.remotes]
            else repo.remotes[0]
        )
        remote_url = _sanitize_url(remote.url)

    latest_tag = None
    if repo.tags:
        latest = max(repo.tags, key=lambda t: t.commit.committed_datetime)
        latest_tag = latest.name

    return {
        "commit": repo.head.commit.hexsha,
        "branch": branch,
        "remote_url": remote_url,
        "latest_tag": latest_tag,
        "n_commits": len(commits),
        "n_contributors": len({c.author.email for c in commits}),
        "first_commit_date": commits[-1].committed_datetime.isoformat(),
        "last_commit_date": commits[0].committed_datetime.isoformat(),
    }

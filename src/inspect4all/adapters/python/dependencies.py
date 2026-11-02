from __future__ import annotations

import re
from typing import TYPE_CHECKING

from inspect4all.core.models import Dependency

if TYPE_CHECKING:
    from pathlib import Path

_PKG_NAME_RE = re.compile(r"^([A-Za-z0-9_.-]+)")


def _parse_package_name(spec: str) -> str | None:
    spec = spec.strip()
    if not spec or spec.startswith("#"):
        return None
    m = _PKG_NAME_RE.match(spec)
    return m.group(1) if m else None


def _parse_version(spec: str) -> str | None:
    m = re.search(r"[>=<!\^~]+([\w.]+)", spec)
    return m.group(1) if m else None


class PythonDependencyExtractor:
    def extract(self, repo_path: Path) -> list[Dependency]:
        deps: list[Dependency] = []
        deps.extend(self._from_requirements_txt(repo_path))
        if not deps:
            deps.extend(self._from_pyproject_toml(repo_path))
        return deps

    def _from_requirements_txt(self, repo_path: Path) -> list[Dependency]:
        path = repo_path / "requirements.txt"
        if not path.exists():
            return []
        deps = []
        for line in path.read_text().splitlines():
            name = _parse_package_name(line)
            if name:
                deps.append(
                    Dependency(
                        name=name,
                        version=_parse_version(line),
                        source="requirements.txt",
                        language="Python",
                        scope="runtime",
                        build_tool="pip",
                    )
                )
        return deps

    def _from_pyproject_toml(self, repo_path: Path) -> list[Dependency]:
        path = repo_path / "pyproject.toml"
        if not path.exists():
            return []
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                return []
        with path.open("rb") as f:
            data = tomllib.load(f)
        raw = data.get("project", {}).get("dependencies", [])
        deps = []
        for spec in raw:
            name = _parse_package_name(spec)
            if name:
                deps.append(
                    Dependency(
                        name=name,
                        version=_parse_version(spec),
                        source="pyproject.toml",
                        language="Python",
                        scope="runtime",
                        build_tool="pip",
                    )
                )
        return deps

from __future__ import annotations

import dataclasses
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from inspect4all.core.models import RepositoryAnalysis


def _to_serializable(obj) -> object:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            k: _to_serializable(v)
            for k, v in dataclasses.asdict(obj).items()
            if v is not None
        }
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items() if v is not None}
    return obj


class JsonWriter:
    def __init__(self, output_dir: Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        repo: RepositoryAnalysis,
        filename: str = "repository_analysis.json",
    ) -> Path:
        data = {
            "repository": {
                "path": repo.repo_path,
                "languages": repo.languages,
                "software_type": repo.software_type,
                "software_invocation": [
                    _to_serializable(i) for i in repo.software_invocation
                ],
                "tests": [_to_serializable(t) for t in repo.tests],
            },
            "dependencies": [_to_serializable(d) for d in repo.dependencies],
            "license": _to_serializable(repo.license),
            "readme_files": [_to_serializable(r) for r in repo.readme_files],
            "directory_tree": [
                _to_serializable(e) for e in repo.directory_tree
            ],
            "metadata": repo.metadata,
            "files": [_to_serializable(f) for f in repo.files],
            "call_graph": repo.call_graph,
        }
        out = self._out / filename
        out.write_text(json.dumps(data, indent=2, default=str))
        return out

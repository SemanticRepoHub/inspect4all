from __future__ import annotations

import dataclasses
import json
import types
import typing
from pathlib import Path
from typing import Any, get_args, get_origin

from inspect4all.core import models  # noqa: F401  # resolves string hints
from inspect4all.core.models import (
    Dependency,
    FileAnalysis,
    FileTreeEntry,
    InvocationEntry,
    LicenseInfo,
    ReadmeFile,
    RepositoryAnalysis,
    TestEntry,
)


def _is_dataclass_type(tp: Any) -> bool:
    return isinstance(tp, type) and dataclasses.is_dataclass(tp)


def _empty_for(tp: Any) -> Any:
    origin = get_origin(tp)
    if origin in (list, tuple):
        return [] if origin is list else ()
    if origin is dict:
        return {}
    return None


def _convert(tp: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(tp)
    if origin in (typing.Union, types.UnionType):  # X | None
        inner = next((a for a in get_args(tp) if a is not type(None)), None)
        return _convert(inner, value) if inner is not None else value
    if origin is list:
        (item_tp,) = get_args(tp) or (Any,)
        return [_convert(item_tp, v) for v in value]
    if origin is tuple:
        args = get_args(tp)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_convert(args[0], v) for v in value)
        return tuple(_convert(a, v) for a, v in zip(args, value, strict=False))
    if origin is dict:
        args = get_args(tp)
        val_tp = args[1] if len(args) == 2 else Any
        return {k: _convert(val_tp, v) for k, v in value.items()}
    if _is_dataclass_type(tp):
        return _from_dict(tp, value)
    return value


def _from_dict(cls: type, data: dict | None) -> Any:
    if data is None:
        return None
    hints = typing.get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for field in dataclasses.fields(cls):
        tp = hints[field.name]
        if field.name in data:
            kwargs[field.name] = _convert(tp, data[field.name])
        elif field.default is not dataclasses.MISSING:
            kwargs[field.name] = field.default
        elif field.default_factory is not dataclasses.MISSING:
            kwargs[field.name] = field.default_factory()
        else:
            kwargs[field.name] = _empty_for(tp)
    return cls(**kwargs)


def file_analysis_from_dict(data: dict) -> FileAnalysis:
    """Deserialize a single FileAnalysis dict (same tolerant rules as load).

    Used by the enrichment emitters to validate LLM-produced payloads
    against the unified schema before accepting them.
    """
    return _from_dict(FileAnalysis, data)


def load_repository_analysis(path: Path) -> RepositoryAnalysis:
    """Rehydrate a RepositoryAnalysis from a (lossy) repository_analysis.json.

    Tolerant of missing/None keys: absent optional fields default to
    None / [] / {} and JSON lists are cast back to tuples where the
    dataclass field type is a tuple (e.g. line_range).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    repo = data.get("repository", {})
    license_data = data.get("license")
    return RepositoryAnalysis(
        repo_path=repo.get("path", ""),
        languages=repo.get("languages", {}),
        files=[_from_dict(FileAnalysis, f) for f in data.get("files", [])],
        readme_files=[
            _from_dict(ReadmeFile, r) for r in data.get("readme_files", [])
        ],
        directory_tree=[
            _from_dict(FileTreeEntry, e) for e in data.get("directory_tree", [])
        ],
        dependencies=[
            _from_dict(Dependency, d) for d in data.get("dependencies", [])
        ],
        software_type=repo.get("software_type", ""),
        software_invocation=[
            _from_dict(InvocationEntry, i)
            for i in repo.get("software_invocation", [])
        ],
        tests=[_from_dict(TestEntry, t) for t in repo.get("tests", [])],
        license=(
            _from_dict(LicenseInfo, license_data)
            if license_data is not None
            else LicenseInfo(detected=[], source_files=[], text=None)
        ),
        metadata=data.get("metadata", {}),
        call_graph=data.get("call_graph", {}),
    )

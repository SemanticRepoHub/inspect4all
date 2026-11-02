from __future__ import annotations

from typing import TYPE_CHECKING

from inspect4all.core.interfaces import SoftwareTypeResult

if TYPE_CHECKING:
    from pathlib import Path

    from inspect4all.core.models import FileAnalysis

_APPLICATION_MODIFIERS = frozenset({"public", "static"})


def detect_software_type(
    file_analyses: list[FileAnalysis],
    repo_path: Path,
) -> SoftwareTypeResult:
    # A file has a main method -> application
    for fa in file_analyses:
        for t in fa.types:
            for m in t.methods:
                if m.name == "main" and _APPLICATION_MODIFIERS.issubset(
                    set(m.modifiers)
                ):
                    return SoftwareTypeResult(
                        software_type="application",
                        invocation_entries=[],
                    )

    # Has pom.xml / build.gradle without a main -> library
    if (repo_path / "pom.xml").exists() or (
        repo_path / "build.gradle"
    ).exists():
        return SoftwareTypeResult(
            software_type="library", invocation_entries=[]
        )

    return SoftwareTypeResult(software_type="package", invocation_entries=[])

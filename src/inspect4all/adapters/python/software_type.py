from __future__ import annotations

from typing import TYPE_CHECKING

from inspect4all.core.interfaces import SoftwareTypeResult
from inspect4all.core.models import Dependency, FileAnalysis, InvocationEntry

if TYPE_CHECKING:
    from pathlib import Path


def detect_software_type(
    files: list[FileAnalysis],
    dependencies: list[Dependency],  # noqa: ARG001  # Phase 2: framework-based detection
    repo_path: Path,
) -> SoftwareTypeResult:
    has_init = any(f.file.path.endswith("__init__.py") for f in files)
    has_setup = (repo_path / "setup.py").exists() or (
        repo_path / "pyproject.toml"
    ).exists()
    has_main = any(f.main_info and f.main_info.has_main for f in files)

    if has_init and has_setup:
        software_type = "library"
    elif has_main:
        software_type = "script"
    else:
        software_type = "package" if has_init else "script"

    invocations = []
    for f in files:
        if f.main_info and f.main_info.has_main:
            invocations.append(
                InvocationEntry(
                    type=software_type,
                    run=f"python {f.file.path}",
                    language="Python",
                    entry_point=f.main_info.main_function,
                    has_main=True,
                    mentioned_in_readme=False,
                    ranking=1,
                )
            )

    return SoftwareTypeResult(
        software_type=software_type, invocation_entries=invocations
    )

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from inspect4all.core.models import (
        Dependency,
        FileAnalysis,
        RepositoryAnalysis,
        TestEntry,
    )


class UnsupportedFileTypeError(Exception):
    """Raised when a file is a known non-parseable type for this adapter.

    Use this instead of SyntaxError when the file is not genuinely broken but
    is simply the wrong type (e.g. a Cython file detected as Python, a Jinja2
    template, or Python 2 source that ast cannot parse in Python 3 mode).

    The pipeline routes these to metadata["unhandled_files"][file_type] rather
    than parse_failures, keeping failure counts meaningful.
    """

    def __init__(self, file_type: str, message: str = "") -> None:
        self.file_type = file_type
        super().__init__(message or f"Unsupported file type: {file_type}")


@dataclass
class ParseResult:
    file_path: Path
    tree: Any
    source: str


@dataclass
class SoftwareTypeResult:
    software_type: str
    invocation_entries: list


class LanguageAdapter(ABC):
    @property
    @abstractmethod
    def language_name(self) -> str: ...

    @property
    @abstractmethod
    def file_extensions(self) -> list[str]: ...

    @abstractmethod
    def parse_file(self, file_path: Path) -> ParseResult: ...

    @abstractmethod
    def extract_file_analysis(
        self, parse_result: ParseResult, repo_path: Path
    ) -> FileAnalysis:
        """Extract the unified analysis for one parsed file.

        repo_path is the repository root; adapters must emit repo-relative
        paths and qualified names so output is portable across machines.
        """

    def extract_dependencies(self, repo_path: Path) -> list[Dependency]:
        return []

    def detect_software_type(
        self,
        files: list[FileAnalysis],
        dependencies: list[Dependency],
        repo_path: Path,
    ) -> SoftwareTypeResult | None:
        return None

    def resolve_cross_file_calls(
        self, files: list[FileAnalysis]
    ) -> list[FileAnalysis]:
        return files

    def detect_tests(
        self,
        files: list[FileAnalysis],
        repo_path: Path,
    ) -> list[TestEntry]:
        return []

    def extract_ast_json(self, parse_result: ParseResult) -> dict | None:
        return None


class EnrichmentProcessor(ABC):
    stats: dict[str, int]

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def enrich(self, repo: RepositoryAnalysis) -> RepositoryAnalysis: ...

    def is_applicable(self, repo: RepositoryAnalysis) -> bool:
        return True

from __future__ import annotations

from typing import TYPE_CHECKING

from inspect4all.adapters.java.call_resolver import resolve_calls
from inspect4all.adapters.java.dependencies import JavaDependencyExtractor
from inspect4all.adapters.java.extractor import JavaExtractor
from inspect4all.adapters.java.parser import JavaParser
from inspect4all.adapters.java.software_type import detect_software_type
from inspect4all.core.interfaces import (
    LanguageAdapter,
    ParseResult,
    SoftwareTypeResult,
)
from inspect4all.core.models import (
    Dependency,
    FileAnalysis,
    FileInfo,
    TestEntry,
)

if TYPE_CHECKING:
    from pathlib import Path


class JavaAdapter(LanguageAdapter):
    @property
    def language_name(self) -> str:
        return "Java"

    @property
    def file_extensions(self) -> list[str]:
        return [".java"]

    def parse_file(self, file_path: Path) -> ParseResult:
        return JavaParser().parse(file_path)

    def extract_file_analysis(
        self, parse_result: ParseResult, repo_path: Path
    ) -> FileAnalysis:
        tree = parse_result.tree
        source = parse_result.source
        file_path = parse_result.file_path

        package = tree.package.name if tree.package else ""
        extractor = JavaExtractor(tree, source, file_path, package)
        types = extractor.extract_types()
        imports = extractor.extract_imports()

        try:
            rel = file_path.relative_to(repo_path)
        except ValueError:
            rel = file_path

        file_info = FileInfo(
            path=str(rel),
            name=file_path.stem,
            extension=".java",
            language="Java",
            package=package or None,
            documentation=None,
            is_test=_is_test_file(file_path),
        )
        return FileAnalysis(
            file=file_info,
            imports=imports,
            types=types,
            functions=[],
            main_info=None,
            language_specific={"package": package},
        )

    def extract_dependencies(self, repo_path: Path) -> list[Dependency]:
        return JavaDependencyExtractor().extract(repo_path)

    def detect_software_type(
        self,
        files: list[FileAnalysis],
        dependencies: list[Dependency],
        repo_path: Path,
    ) -> SoftwareTypeResult | None:
        if not files:
            return None
        return detect_software_type(files, repo_path)

    def detect_tests(
        self,
        files: list[FileAnalysis],
        repo_path: Path,
    ) -> list[TestEntry]:
        test_files = [f.file.path for f in files if f.file.is_test]
        if not test_files:
            return []
        if (repo_path / "build.gradle").exists() or (
            repo_path / "build.gradle.kts"
        ).exists():
            run = "gradle test"
        else:
            run = "mvn test"
        return [
            TestEntry(type="junit", run=run, language="Java", files=test_files)
        ]

    def resolve_cross_file_calls(
        self, file_analyses: list[FileAnalysis]
    ) -> list[FileAnalysis]:
        return resolve_calls(file_analyses)


def _is_test_file(path: Path) -> bool:
    parts = [p.lower() for p in path.parts]
    return (
        "test" in parts
        or path.stem.lower().startswith("test")
        or path.stem.lower().endswith("test")
    )

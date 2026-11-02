from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from inspect4all.adapters.python.call_resolver import resolve_calls
from inspect4all.adapters.python.dependencies import PythonDependencyExtractor
from inspect4all.adapters.python.docstring_parser import extract_documentation
from inspect4all.adapters.python.extractor import PythonExtractor, _get_name
from inspect4all.adapters.python.parser import PythonParser
from inspect4all.adapters.python.software_type import detect_software_type
from inspect4all.core.interfaces import (
    LanguageAdapter,
    ParseResult,
    SoftwareTypeResult,
)
from inspect4all.core.models import (
    Dependency,
    FileAnalysis,
    FileInfo,
    MainInfo,
    TestEntry,
)

if TYPE_CHECKING:
    from pathlib import Path


class PythonAdapter(LanguageAdapter):
    @property
    def language_name(self) -> str:
        return "Python"

    @property
    def file_extensions(self) -> list[str]:
        return [".py"]

    def parse_file(self, file_path: Path) -> ParseResult:
        return PythonParser().parse(file_path)

    def extract_file_analysis(
        self, parse_result: ParseResult, repo_path: Path
    ) -> FileAnalysis:
        path = parse_result.file_path
        tree = parse_result.tree
        source = parse_result.source
        try:
            rel_path = path.relative_to(repo_path)
        except ValueError:
            rel_path = path
        module_name = self._path_to_module(rel_path)

        extractor = PythonExtractor(
            tree=tree,
            source=source,
            file_path=path,
            module_name=module_name,
        )

        file_doc = extract_documentation(ast.get_docstring(tree))
        is_test = self._is_test_file(rel_path)
        main_info = self._extract_main_info(tree, module_name)

        return FileAnalysis(
            file=FileInfo(
                path=str(rel_path),
                name=path.stem,
                extension=path.suffix,
                language="Python",
                package=module_name,
                documentation=file_doc,
                is_test=is_test,
            ),
            imports=extractor.extract_imports(),
            types=extractor.extract_types(),
            functions=extractor.extract_functions(),
            main_info=main_info,
            language_specific={"body_calls": self._extract_body_calls(tree)},
        )

    def extract_dependencies(self, repo_path: Path) -> list[Dependency]:
        return PythonDependencyExtractor().extract(repo_path)

    def detect_software_type(
        self,
        files: list[FileAnalysis],
        dependencies: list[Dependency],
        repo_path: Path,
    ) -> SoftwareTypeResult | None:
        if not files:
            return None
        return detect_software_type(files, dependencies, repo_path)

    def detect_tests(
        self,
        files: list[FileAnalysis],
        repo_path: Path,
    ) -> list[TestEntry]:
        test_files = [f.file.path for f in files if f.file.is_test]
        if not test_files:
            return []
        return [
            TestEntry(
                type="pytest", run="pytest", language="Python", files=test_files
            )
        ]

    def resolve_cross_file_calls(
        self, files: list[FileAnalysis]
    ) -> list[FileAnalysis]:
        return resolve_calls(files)

    def _path_to_module(self, path: Path) -> str:
        parts = list(path.with_suffix("").parts)
        for i, p in enumerate(parts):
            if p in ("src", "lib"):
                parts = parts[i + 1 :]
                break
        return ".".join(parts)

    def _is_test_file(self, path: Path) -> bool:
        name = path.name
        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or "tests" in path.parts
        )

    def _extract_main_info(self, tree: ast.AST, module_name: str) -> MainInfo:
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"
            ):
                return MainInfo(
                    has_main=True,
                    main_function=f"{module_name}.__main__",
                    type="script",
                )
        return MainInfo(has_main=False, main_function=None, type=None)

    def _extract_body_calls(self, tree: ast.AST) -> list[str]:
        calls = []
        seen: set[str] = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                name = _get_name(node.value.func)
                if name and name not in seen:
                    calls.append(name)
                    seen.add(name)
        return calls

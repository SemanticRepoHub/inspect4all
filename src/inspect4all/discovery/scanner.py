from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from inspect4all.core.constants import DEFAULT_IGNORE_DIRS
from inspect4all.discovery.enry import Enry

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class FileEntry:
    path: Path
    language: str
    language_type: str  # "programming"|"markup"|"prose"|"data"|"binary"|""
    is_binary: bool
    is_vendored: bool
    is_generated: bool
    is_documentation: bool


@dataclass
class FileManifest:
    repo_path: Path
    entries: list[FileEntry]
    language_summary: dict[str, int]

    def group_by_language(self) -> dict[str, list[Path]]:
        groups: dict[str, list[Path]] = {}
        for entry in self.entries:
            if (
                entry.language_type == "programming"
                and not entry.is_binary
                and not entry.is_vendored
                and not entry.is_generated
                and entry.language
            ):
                groups.setdefault(entry.language, []).append(entry.path)
        return groups

    def get_readme_files(self) -> list[Path]:
        readmes = []
        for entry in self.entries:
            name = entry.path.name.upper()
            if name.startswith("README"):
                readmes.append(entry.path)
        return readmes

    def get_documentation_files(self) -> list[Path]:
        return [e.path for e in self.entries if e.is_documentation]


class RepositoryScanner:
    def __init__(
        self,
        enry: Enry | None = None,
        ignore_dirs: frozenset[str] | None = None,
    ):
        self._enry = enry or Enry()
        self._ignore_dirs = ignore_dirs or DEFAULT_IGNORE_DIRS

    def scan(
        self,
        repo_path: Path,
        ignore_dir_patterns: list[str] | None = None,
        ignore_file_patterns: list[str] | None = None,
    ) -> FileManifest:
        extra_ignore = set(ignore_dir_patterns or [])
        all_ignore_dirs = self._ignore_dirs | extra_ignore

        entries: list[FileEntry] = []
        language_summary: dict[str, int] = {}

        for file_path in self._walk(repo_path, all_ignore_dirs):
            try:
                raw = file_path.read_bytes()
            except OSError:
                continue

            rel = file_path.relative_to(repo_path)
            rel_str = str(rel)

            is_bin = self._enry.is_binary(raw)
            is_vend = self._enry.is_vendored(rel_str)
            is_gen = self._enry.is_generated(rel_str, raw)
            is_doc = self._enry.is_documentation(rel_str)

            if is_bin:
                language = ""
                lang_type = "binary"
            else:
                language = self._enry.detect(file_path.name, raw)
                lang_type = (
                    self._enry.get_language_type(language) if language else ""
                )

            entry = FileEntry(
                path=file_path,
                language=language,
                language_type=lang_type,
                is_binary=is_bin,
                is_vendored=is_vend,
                is_generated=is_gen,
                is_documentation=is_doc,
            )
            entries.append(entry)

            if (
                lang_type == "programming"
                and language
                and not is_bin
                and not is_vend
            ):
                language_summary[language] = (
                    language_summary.get(language, 0) + 1
                )

        return FileManifest(
            repo_path=repo_path,
            entries=entries,
            language_summary=language_summary,
        )

    def _walk(self, root: Path, ignore_dirs: frozenset[str]) -> list[Path]:
        files: list[Path] = []
        try:
            items = list(root.iterdir())
        except PermissionError:
            return files
        for item in items:
            if item.is_dir():
                if item.name not in ignore_dirs:
                    files.extend(self._walk(item, ignore_dirs))
            elif item.is_file():
                files.append(item)
        return files

from __future__ import annotations

from typing import TYPE_CHECKING

from inspect4all.core.models import FileTreeEntry

if TYPE_CHECKING:
    from inspect4all.discovery.scanner import FileEntry, FileManifest

_TEST_FRAGMENTS = {"test_", "_test", "/tests/", "/test/", "\\tests\\"}
_BUILD_EXTENSIONS = {".xml", ".gradle", ".toml", ".cfg", ".ini", ".lock"}
_DOC_EXTENSIONS = {".md", ".rst", ".txt"}


def build_directory_tree(manifest: FileManifest) -> list[FileTreeEntry]:
    entries = []
    for fe in manifest.entries:
        if fe.is_binary:
            continue
        rel = str(fe.path.relative_to(manifest.repo_path))
        ftype = _classify(rel, fe)
        entries.append(
            FileTreeEntry(
                path=rel,
                language=fe.language or None,
                type=ftype,
            )
        )
    return entries


def _classify(rel_path: str, fe: FileEntry) -> str:
    if any(p in rel_path for p in _TEST_FRAGMENTS):
        return "test"
    if fe.is_documentation or fe.path.suffix in _DOC_EXTENSIONS:
        return "documentation"
    if fe.path.suffix in _BUILD_EXTENSIONS:
        return "build"
    if fe.language_type == "programming":
        return "source"
    return "config"

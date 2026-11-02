from __future__ import annotations

from typing import TYPE_CHECKING

from inspect4all.core.models import ReadmeFile

if TYPE_CHECKING:
    from inspect4all.discovery.scanner import FileManifest


def extract_readmes(manifest: FileManifest) -> list[ReadmeFile]:
    readmes = []
    for path in manifest.get_readme_files():
        try:
            content = path.read_text(errors="replace")
            rel = str(path.relative_to(manifest.repo_path))
            readmes.append(ReadmeFile(path=rel, content=content))
        except OSError:
            pass
    return readmes

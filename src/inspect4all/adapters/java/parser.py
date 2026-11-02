from __future__ import annotations

from typing import TYPE_CHECKING

import javalang

from inspect4all.core.interfaces import ParseResult

if TYPE_CHECKING:
    from pathlib import Path


class JavaParser:
    def parse(self, file_path: Path) -> ParseResult:
        source = self._read(file_path)
        try:
            tree = javalang.parse.parse(source)
        except javalang.parser.JavaSyntaxError as e:
            raise SyntaxError(f"Java syntax error in {file_path}: {e}") from e
        except Exception as e:
            raise SyntaxError(f"Failed to parse {file_path}: {e}") from e
        return ParseResult(file_path=file_path, tree=tree, source=source)

    def _read(self, file_path: Path) -> str:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                return file_path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        return file_path.read_text(encoding="utf-8", errors="replace")

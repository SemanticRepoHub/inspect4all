from __future__ import annotations

import ast
import re
import tokenize
from typing import TYPE_CHECKING

from inspect4all.core.interfaces import ParseResult, UnsupportedFileTypeError

if TYPE_CHECKING:
    from pathlib import Path

_CYTHON_EXTENSIONS = {".pyx", ".pxd", ".pxi"}

# Unambiguous Python 2 syntax patterns for use when Python 3's own error
# message does not name the construct. Checked against the full source after
# ast.parse() fails.
_PY2_INDICATORS = (
    re.compile(
        r"\bexcept\s+\w[\w.]*\s*,\s*\w+\s*:", re.MULTILINE
    ),  # except E, e:
    re.compile(r"\braise\s+\w[\w.]*\s*,\s*\S", re.MULTILINE),  # raise E, msg
    re.compile(r"\b\d+[Ll]\b", re.MULTILINE),  # long int literal 123L
)

# Python 3 produces these messages when it recognises Python 2 print/exec
# statements, including inline forms (if cond: print x). Use them before
# falling back to _PY2_INDICATORS so we don't need a content regex that
# could match strings or comments.
_PY2_EXCEPTION_MSGS = (
    "Missing parentheses in call to 'print'",
    "Missing parentheses in call to 'exec'",
)

# Syntax from a Python version newer than this runtime, or an older minor
# version that used now-reserved keywords. Checked after ast.parse() fails.
_UNSUPPORTED_SYNTAX = (
    # Python 3.14 t-strings (PEP 750): upgrading the runtime to 3.14 fixes these.
    re.compile(r"""\bt['"]{1,3}""", re.MULTILINE),
    # 'async' used as a bare module or attribute name (valid <3.7, keyword >=3.7).
    re.compile(r"\b(?:from|import)\s[\w.]*\.async\b", re.MULTILINE),
)

# Jinja2 / Django template control-flow markers at the start of a content line.
_JINJA2_CONTENT = re.compile(r"^\s*\{[%{]", re.MULTILINE)

# Dockerfile instruction keywords - catches files go-enry misclassifies as
# Python due to a .py2/.py3-style extension (e.g. Dockerfile.py3).
_DOCKERFILE_CONTENT = re.compile(
    r"^(?:FROM|ARG|RUN|CMD|ENV|COPY|ADD|EXPOSE|ENTRYPOINT|WORKDIR|USER)\s",
    re.MULTILINE,
)


def _is_python2(source: str, exc: SyntaxError | None = None) -> bool:
    if exc is not None and any(
        m in (exc.msg or "") for m in _PY2_EXCEPTION_MSGS
    ):
        return True
    return any(pat.search(source) for pat in _PY2_INDICATORS)


def _is_unsupported_syntax(source: str) -> bool:
    return any(pat.search(source) for pat in _UNSUPPORTED_SYNTAX)


class PythonParser:
    def parse(self, file_path: Path) -> ParseResult:
        if file_path.suffix in _CYTHON_EXTENSIONS:
            raise UnsupportedFileTypeError(
                "Cython",
                f"Cython file (not parseable as Python): {file_path.name}",
            )
        # Jinja2 template paths embed {{ in the file name itself.
        if "{{" in str(file_path):
            raise UnsupportedFileTypeError(
                "Jinja2Template",
                f"Jinja2 template path: {file_path.name}",
            )

        with tokenize.open(str(file_path)) as f:
            source = f.read()

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as exc:
            if _is_python2(source, exc):
                raise UnsupportedFileTypeError(
                    "Python2Legacy",
                    f"Python 2 syntax: {file_path.name}",
                ) from None
            if _JINJA2_CONTENT.search(source):
                raise UnsupportedFileTypeError(
                    "Jinja2Content",
                    f"File contains Jinja2 template markers: {file_path.name}",
                ) from None
            if _DOCKERFILE_CONTENT.search(source):
                raise UnsupportedFileTypeError(
                    "DockerfileContent",
                    f"File contains Dockerfile instructions, not Python: {file_path.name}",
                ) from None
            if _is_unsupported_syntax(source):
                raise UnsupportedFileTypeError(
                    "UnsupportedPythonSyntax",
                    f"File uses Python syntax not supported by this runtime "
                    f"(t-strings require 3.14+, async-as-name requires <3.7): "
                    f"{file_path.name}",
                ) from None
            raise

        return ParseResult(file_path=file_path, tree=tree, source=source)

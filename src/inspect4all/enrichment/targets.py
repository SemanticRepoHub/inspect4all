from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inspect4all.core.models import (
        FileAnalysis,
        FunctionInfo,
        RepositoryAnalysis,
        TypeInfo,
    )


@dataclass(frozen=True)
class DocstringTarget:
    record_id: str
    qualified_name: str
    signature: str
    line_range: tuple[int, int]
    source_code: str
    language: str = ""
    class_context: dict | None = field(default=None, compare=False, hash=False)


def _strip_python_docstring(source: str) -> str:
    """Remove the leading triple-quoted docstring from a Python function body.

    inspect4all stores source_code starting at the 'def' line.  The docstring
    appears as the first statement in the body.  Strip it so the enricher
    generates from code logic rather than from the visible existing answer.

    Handles async def, type-annotated parameters, and multi-line signatures.
    Called for all Python targets; is a no-op when no docstring is present.
    """
    def_match = re.search(r"^(?:async\s+)?def\s+\w+", source, re.MULTILINE)
    if def_match is None:
        return source
    # Walk forward tracking bracket depth to find the ':' that closes the
    # function signature, skipping any ':' inside type annotations such as
    # 'a: int', '-> dict[str, int]', or multi-line parameter lists.
    i = def_match.end()
    depth = 0
    while i < len(source):
        ch = source[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            break
        i += 1
    else:
        return source
    after_colon = source[i + 1 :]
    stripped = after_colon.lstrip(" \t\n")
    for quote in ('"""', "'''"):
        if stripped.startswith(quote):
            end = stripped.find(quote, len(quote))
            if end != -1:
                pre = source[: i + 1]
                post = stripped[end + len(quote) :]
                return pre + post
    return source


def _is_undocumented(func: FunctionInfo) -> bool:
    doc = func.documentation
    return doc is None or not doc.full_text


def _signature(func: FunctionInfo) -> str:
    params = ", ".join(
        p.name if p.type is None else f"{p.name}: {p.type}"
        for p in func.parameters
    )
    ret = f" -> {func.return_type}" if func.return_type else ""
    return f"{func.name}({params}){ret}"


def _type_context(t: TypeInfo) -> dict:
    return {
        "name": t.name,
        "kind": t.kind,
        "base_classes": t.base_classes,
        "interfaces": t.interfaces,
    }


def _collect(
    fa: FileAnalysis,
    func: FunctionInfo,
    class_ctx: dict | None,
    targets: list[DocstringTarget],
    undocumented_only: bool = True,
) -> None:
    """Recursively collect targets from func and its nested functions."""
    if func.source_code and (not undocumented_only or _is_undocumented(func)):
        path = fa.file.path
        source = func.source_code
        if fa.file.language.lower() == "python":
            source = _strip_python_docstring(source)
        targets.append(
            DocstringTarget(
                record_id=f"{path}::{func.qualified_name}",
                qualified_name=func.qualified_name,
                signature=_signature(func),
                line_range=func.line_range,
                source_code=source,
                language=fa.file.language,
                class_context=class_ctx,
            )
        )
    for nested in func.nested_functions:
        # Nested functions lose the enclosing class context (they are closures).
        _collect(fa, nested, None, targets, undocumented_only)


def _select(
    repo: RepositoryAnalysis,
    undocumented_only: bool,
) -> dict[str, list[DocstringTarget]]:
    result: dict[str, list[DocstringTarget]] = {}
    for fa in repo.files:
        path = fa.file.path
        targets: list[DocstringTarget] = []
        for func in fa.functions:
            _collect(fa, func, None, targets, undocumented_only)
        for t in fa.types:
            ctx = _type_context(t)
            for method in t.methods:
                _collect(fa, method, ctx, targets, undocumented_only)
        if targets:
            result[path] = targets
    return result


def select_undocumented(
    repo: RepositoryAnalysis,
) -> dict[str, list[DocstringTarget]]:
    """Group undocumented functions/methods that have source, per file path.

    Methods inside classes carry their enclosing type as class_context so
    the prompt generator can include class name, kind, and base classes.
    """
    return _select(repo, undocumented_only=True)


def select_all(
    repo: RepositoryAnalysis,
) -> dict[str, list[DocstringTarget]]:
    """Group all functions/methods that have source, per file path.

    Like select_undocumented but includes already-documented functions.
    Used for held-out evaluation (--docstring-target all).
    """
    return _select(repo, undocumented_only=False)

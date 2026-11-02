"""Cross-file call resolution for Java.

Rewrites the local call names recorded by the extractor (`step`,
`Utils.help`, `Helper`) into package-qualified names using imports,
same-package visibility, this-class context, and one-hop-per-step
inheritance walking. Unresolved names (JDK, third-party, instance-variable
dispatch without type inference) are left unchanged — never dropped.

Runs pre-aggregation on adapter-owned FileAnalysis objects, so in-place
mutation of FunctionInfo.calls is acceptable here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from inspect4all.core.models import FileAnalysis, FunctionInfo


@dataclass
class _ClassEntry:
    qualified: str
    package: str
    methods: set[str] = field(default_factory=set)
    constructor: str | None = None
    bases: list[str] = field(default_factory=list)


_ClassIndex = dict[str, _ClassEntry]  # keyed by fully qualified class name


def _build_class_index(files: list[FileAnalysis]) -> _ClassIndex:
    index: _ClassIndex = {}
    for fa in files:
        package = fa.file.package or ""
        for t in fa.types:
            entry = _ClassEntry(
                qualified=t.qualified_name,
                package=package,
                bases=list(t.base_classes),
            )
            for m in t.methods:
                if m.is_constructor:
                    entry.constructor = m.qualified_name
                else:
                    entry.methods.add(m.name)
            index[t.qualified_name] = entry
    return index


def _resolve_class(
    simple_name: str,
    package: str,
    imports: dict[str, str],
    index: _ClassIndex,
) -> _ClassEntry | None:
    """Resolve a simple class name via imports, then same-package."""
    fqn = imports.get(
        simple_name, f"{package}.{simple_name}" if package else simple_name
    )
    return index.get(fqn)


def _find_method_owner(
    entry: _ClassEntry,
    member: str,
    imports: dict[str, str],
    index: _ClassIndex,
) -> _ClassEntry | None:
    """Walk the class then its internal ancestors looking for `member`."""
    visited: set[str] = set()
    current: _ClassEntry | None = entry
    while current and current.qualified not in visited:
        visited.add(current.qualified)
        if member in current.methods:
            return current
        current = next(
            (
                resolved
                for base in current.bases
                if (
                    resolved := _resolve_class(
                        base, current.package, imports, index
                    )
                )
            ),
            None,
        )
    return None


def _build_import_map(fa: FileAnalysis, index: _ClassIndex) -> dict[str, str]:
    """Map simple class names to internal fully qualified names."""
    imports: dict[str, str] = {}
    for imp in fa.imports:
        if imp.kind == "wildcard":
            prefix = imp.module
            for fqn in index:
                if fqn.rpartition(".")[0] == prefix:
                    imports[fqn.rpartition(".")[2]] = fqn
        else:
            fqn = f"{imp.module}.{imp.name}" if imp.module else imp.name
            if fqn in index:
                imports[imp.name] = fqn
    return imports


def _resolve_call(
    call: str,
    class_entry: _ClassEntry | None,
    imports: dict[str, str],
    index: _ClassIndex,
) -> str:
    head, sep, rest = call.partition(".")

    if not sep:
        # Bare name: this-class (or inherited) method, else a constructor.
        if class_entry:
            owner = _find_method_owner(class_entry, call, imports, index)
            if owner:
                return f"{owner.qualified}.{call}"
        target = _resolve_class(
            head, class_entry.package if class_entry else "", imports, index
        )
        if target:
            return target.constructor or target.qualified
        return call

    if head == "super" and class_entry:
        parent = next(
            (
                resolved
                for base in class_entry.bases
                if (
                    resolved := _resolve_class(
                        base, class_entry.package, imports, index
                    )
                )
            ),
            None,
        )
        if parent:
            owner = _find_method_owner(parent, rest, imports, index)
            if owner:
                return f"{owner.qualified}.{rest}"
        return call

    # Dotted: qualify when the head is a resolvable class with that member.
    target = _resolve_class(
        head, class_entry.package if class_entry else "", imports, index
    )
    if target:
        member = rest.partition(".")[0]
        owner = _find_method_owner(target, member, imports, index)
        if owner:
            return f"{owner.qualified}.{rest}"
    return call


def _iter_methods_with_class(
    fa: FileAnalysis, index: _ClassIndex
) -> Iterator[tuple[FunctionInfo, _ClassEntry | None]]:
    for t in fa.types:
        entry = index.get(t.qualified_name)
        for m in t.methods:
            yield m, entry
    for f in fa.functions:
        yield f, None


def resolve_calls(files: list[FileAnalysis]) -> list[FileAnalysis]:
    index = _build_class_index(files)
    for fa in files:
        imports = _build_import_map(fa, index)
        for method, class_entry in _iter_methods_with_class(fa, index):
            method.calls = [
                _resolve_call(c, class_entry, imports, index)
                for c in method.calls
            ]
    return files

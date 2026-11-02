"""Cross-file call resolution for Python.

Rewrites the bare call names recorded by the extractor into repo-qualified
names where they can be resolved through module symbols, imports, or class
context. Unresolved names (stdlib, third-party, dynamic dispatch) are left
unchanged — never dropped. This is a pragmatic subset of inspect4py's
resolver: no dynamic-call tracking, no attribute-type inference.

Runs pre-aggregation on adapter-owned FileAnalysis objects, so in-place
mutation of FunctionInfo.calls is acceptable here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from inspect4all.core.models import FileAnalysis, FunctionInfo

_SymbolIndex = dict[str, dict[str, str]]


def _build_symbol_index(files: list[FileAnalysis]) -> _SymbolIndex:
    """Map each module to its addressable short names -> qualified names."""
    index: _SymbolIndex = {}
    for fa in files:
        module = fa.file.package or ""
        symbols = index.setdefault(module, {})
        for func in fa.functions:
            symbols[func.name] = func.qualified_name
        for t in fa.types:
            symbols[t.name] = t.qualified_name
            for method in t.methods:
                symbols[f"{t.name}.{method.name}"] = method.qualified_name
    return index


def _resolve_internal_module(module: str, modules: set[str]) -> str | None:
    """Match an imported module name to a known repo module.

    Exact match first; suffix match covers relative imports whose recorded
    name lacks the package prefix. Ambiguous suffixes are not resolved.
    """
    if module in modules:
        return module
    candidates = [m for m in modules if m.endswith(f".{module}")]
    return candidates[0] if len(candidates) == 1 else None


def _build_alias_map(
    fa: FileAnalysis, modules: set[str], symbols: _SymbolIndex
) -> dict[str, str]:
    """Map local names introduced by imports to qualified targets."""
    aliases: dict[str, str] = {}
    for imp in fa.imports:
        local = imp.alias or imp.name
        if imp.module == imp.name:
            # `import m [as a]` — head of dotted calls maps to the module.
            target = _resolve_internal_module(imp.module, modules)
            if target:
                aliases[local] = target
        else:
            # `from m import n [as a]` — local name maps to m.n.
            target = _resolve_internal_module(imp.module, modules)
            if target and imp.name in symbols.get(target, {}):
                aliases[local] = symbols[target][imp.name]
    return aliases


def _resolve_call(
    call: str,
    module: str,
    class_name: str | None,
    symbols: _SymbolIndex,
    aliases: dict[str, str],
    modules: set[str],
) -> str:
    local_symbols = symbols.get(module, {})

    if class_name and call.startswith("self."):
        member = call.removeprefix("self.")
        key = f"{class_name}.{member}"
        if key in local_symbols:
            return local_symbols[key]
        return call

    head, sep, rest = call.partition(".")
    if not sep:
        if call in aliases:
            return aliases[call]
        if call in local_symbols:
            return local_symbols[call]
        return call

    if head in aliases:
        target = aliases[head]
        if target in modules:
            # module alias: only qualify when the member is known there.
            member = rest.partition(".")[0]
            if member in symbols.get(target, {}):
                return f"{target}.{rest}"
            return call
        # from-imported class: Cls.method -> qualified class + member.
        return f"{target}.{rest}"
    if head in local_symbols:
        return f"{local_symbols[head]}.{rest}"
    return call


def _iter_functions_with_class(
    fa: FileAnalysis,
) -> Iterator[tuple[FunctionInfo, str | None]]:
    def _walk(
        funcs: list[FunctionInfo], class_name: str | None
    ) -> Iterator[tuple[FunctionInfo, str | None]]:
        for f in funcs:
            yield f, class_name
            yield from _walk(f.nested_functions, class_name)

    yield from _walk(fa.functions, None)
    for t in fa.types:
        yield from _walk(t.methods, t.name)


def resolve_calls(files: list[FileAnalysis]) -> list[FileAnalysis]:
    symbols = _build_symbol_index(files)
    modules = set(symbols)
    for fa in files:
        module = fa.file.package or ""
        aliases = _build_alias_map(fa, modules, symbols)
        for func, class_name in _iter_functions_with_class(fa):
            func.calls = [
                _resolve_call(c, module, class_name, symbols, aliases, modules)
                for c in func.calls
            ]
    return files

from __future__ import annotations

from typing import TYPE_CHECKING

import javalang
import javalang.tree

from inspect4all.adapters.java.javadoc_parser import parse_javadoc
from inspect4all.core.models import (
    FieldInfo,
    FunctionInfo,
    ImportInfo,
    ParameterInfo,
    TypeInfo,
)

if TYPE_CHECKING:
    from pathlib import Path


def _type_name(type_node) -> str | None:
    if type_node is None:
        return None
    if hasattr(type_node, "name"):
        dims = getattr(type_node, "dimensions", None) or []
        base = type_node.name + "[]" * len(dims)
        args = getattr(type_node, "arguments", None)
        if args:
            rendered = ", ".join(_render_type_arg(a) for a in args)
            base = f"{base}<{rendered}>"
        return base
    return str(type_node)


def _render_type_arg(arg) -> str:
    # Wildcard: ? extends T  or  ? super T  or plain ?
    pattern = getattr(arg, "pattern_type", None)
    if pattern:
        inner = _type_name(getattr(arg, "type", None))
        return f"? {pattern} {inner}" if inner else "?"
    inner = _type_name(getattr(arg, "type", None))
    return inner if inner else "?"


def _annotations(node) -> list[str]:
    anns = getattr(node, "annotations", None) or []
    return [f"@{a.name}" for a in anns]


def _extract_source(node, source_lines: list[str]) -> str | None:
    if not hasattr(node, "position") or not node.position:
        return None
    start = node.position[0] - 1  # 0-based
    brace_count = 0
    found_open = False
    end = start
    for i in range(start, len(source_lines)):
        for ch in source_lines[i]:
            if ch == "{":
                brace_count += 1
                found_open = True
            elif ch == "}":
                brace_count -= 1
        if found_open and brace_count == 0:
            end = i
            break
    return "".join(source_lines[start : end + 1]).rstrip()


def _line_range_from_source(node, source_lines: list[str]) -> tuple[int, int]:
    """Use brace-counting on source lines — avoids recursive AST traversal."""
    if not hasattr(node, "position") or not node.position:
        return (0, 0)
    start = node.position[0]  # 1-based
    idx = start - 1
    brace_count = 0
    found_open = False
    end = start
    for i in range(idx, len(source_lines)):
        for ch in source_lines[i]:
            if ch == "{":
                brace_count += 1
                found_open = True
            elif ch == "}":
                brace_count -= 1
        if found_open and brace_count == 0:
            end = i + 1  # 1-based
            break
    return (start, end)


def _build_params(decl) -> list[ParameterInfo]:
    params = []
    for p in getattr(decl, "parameters", None) or []:
        params.append(
            ParameterInfo(
                name=p.name,
                type=_type_name(p.type),
                default=None,
                is_optional=False,
                annotations=_annotations(p),
            )
        )
    return params


def _build_javadoc_raw(node, source_lines: list[str]) -> str | None:
    if not hasattr(node, "position") or not node.position:
        return None
    i = node.position[0] - 2  # line before the declaration (0-based)
    while i >= 0:
        line = source_lines[i].strip()
        if line.endswith("*/"):
            lines: list[str] = [line]
            i -= 1
            while i >= 0:
                line = source_lines[i].strip()
                lines.insert(0, line)
                if line.startswith("/**"):
                    return "\n".join(lines)
                i -= 1
            break
        elif line == "" or line.startswith("//"):
            i -= 1
        else:
            break
    return None


def _extract_calls(decl) -> list[str]:
    """Collect deduplicated call names from a method body.

    MethodInvocation yields `qualifier.member` (or bare `member` for
    this-class calls), SuperMethodInvocation yields `super.member`,
    ClassCreator yields the constructed type name. Grouped by node kind,
    not strict source order.
    """
    calls: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        if name and name not in seen:
            calls.append(name)
            seen.add(name)

    for _path, node in decl.filter(javalang.tree.MethodInvocation):
        qualifier = getattr(node, "qualifier", None)
        _add(f"{qualifier}.{node.member}" if qualifier else node.member)
    for _path, node in decl.filter(javalang.tree.SuperMethodInvocation):
        _add(f"super.{node.member}")
    for _path, node in decl.filter(javalang.tree.ClassCreator):
        _add(_type_name(node.type) or "")
    return calls


def _build_function(
    decl,
    source_lines: list[str],
    package: str,
    class_name: str,
    is_constructor: bool,
) -> FunctionInfo:
    name = decl.name
    qualified = (
        f"{package}.{class_name}.{name}" if package else f"{class_name}.{name}"
    )
    raw_doc = _build_javadoc_raw(decl, source_lines)
    doc = parse_javadoc(raw_doc)
    if is_constructor:
        ret_type = None
    elif getattr(decl, "return_type", None) is None:
        ret_type = "void"
    else:
        ret_type = _type_name(decl.return_type)
    return FunctionInfo(
        name=name,
        qualified_name=qualified,
        documentation=doc,
        source_code=_extract_source(decl, source_lines),
        parameters=_build_params(decl),
        return_type=ret_type,
        modifiers=list(getattr(decl, "modifiers", None) or []),
        annotations=_annotations(decl),
        calls=_extract_calls(decl),
        line_range=_line_range_from_source(decl, source_lines),
        is_constructor=is_constructor,
        nested_functions=[],
        language_specific={},
    )


class JavaExtractor:
    def __init__(self, tree, source: str, file_path: Path, package: str):
        self._tree = tree
        self._source = source
        self._source_lines = source.splitlines(keepends=True)
        self._file_path = file_path
        self._package = package

    def extract_types(self) -> list[TypeInfo]:
        types: list[TypeInfo] = []
        if not self._tree.types:
            return types
        for type_decl in self._tree.types:
            if isinstance(type_decl, javalang.tree.ClassDeclaration):
                types.append(self._build_class(type_decl))
            elif isinstance(type_decl, javalang.tree.InterfaceDeclaration):
                types.append(self._build_interface(type_decl))
            elif isinstance(type_decl, javalang.tree.EnumDeclaration):
                types.append(self._build_enum(type_decl))
        return types

    def _build_class(self, decl) -> TypeInfo:
        methods = []
        for ctor in getattr(decl, "constructors", None) or []:
            methods.append(
                _build_function(
                    ctor, self._source_lines, self._package, decl.name, True
                )
            )
        for m in getattr(decl, "methods", None) or []:
            methods.append(
                _build_function(
                    m, self._source_lines, self._package, decl.name, False
                )
            )
        raw_doc = _build_javadoc_raw(decl, self._source_lines)
        extends = getattr(decl.extends, "name", None) if decl.extends else None
        implements = (
            [i.name for i in decl.implements] if decl.implements else []
        )
        return TypeInfo(
            kind="class",
            name=decl.name,
            qualified_name=f"{self._package}.{decl.name}"
            if self._package
            else decl.name,
            documentation=parse_javadoc(raw_doc),
            source_code=_extract_source(decl, self._source_lines),
            base_classes=[extends] if extends else [],
            interfaces=implements,
            modifiers=list(getattr(decl, "modifiers", None) or []),
            annotations=_annotations(decl),
            fields=self._extract_fields(decl),
            methods=methods,
            line_range=_line_range_from_source(decl, self._source_lines),
            language_specific={"extends": extends, "implements": implements},
        )

    def _build_interface(self, decl) -> TypeInfo:
        methods = []
        for m in getattr(decl, "methods", None) or []:
            methods.append(
                _build_function(
                    m, self._source_lines, self._package, decl.name, False
                )
            )
        raw_doc = _build_javadoc_raw(decl, self._source_lines)
        extends = [e.name for e in decl.extends] if decl.extends else []
        return TypeInfo(
            kind="interface",
            name=decl.name,
            qualified_name=f"{self._package}.{decl.name}"
            if self._package
            else decl.name,
            documentation=parse_javadoc(raw_doc),
            source_code=_extract_source(decl, self._source_lines),
            base_classes=extends,
            interfaces=[],
            modifiers=list(getattr(decl, "modifiers", None) or []),
            annotations=_annotations(decl),
            fields=self._extract_fields(decl),
            methods=methods,
            line_range=_line_range_from_source(decl, self._source_lines),
            language_specific={"extends": extends},
        )

    def _build_enum(self, decl) -> TypeInfo:
        raw_doc = _build_javadoc_raw(decl, self._source_lines)
        constants = (
            [c.name for c in decl.body.constants]
            if (decl.body and decl.body.constants)
            else []
        )
        return TypeInfo(
            kind="enum",
            name=decl.name,
            qualified_name=f"{self._package}.{decl.name}"
            if self._package
            else decl.name,
            documentation=parse_javadoc(raw_doc),
            source_code=_extract_source(decl, self._source_lines),
            base_classes=[],
            interfaces=[i.name for i in decl.implements]
            if getattr(decl, "implements", None)
            else [],
            modifiers=list(getattr(decl, "modifiers", None) or []),
            annotations=_annotations(decl),
            fields=[],
            methods=[],
            line_range=_line_range_from_source(decl, self._source_lines),
            language_specific={"enum_constants": constants},
        )

    def _extract_fields(self, type_decl) -> list[FieldInfo]:
        fields = []
        for field in getattr(type_decl, "fields", None) or []:
            for declarator in field.declarators:
                fields.append(
                    FieldInfo(
                        name=declarator.name,
                        type=_type_name(field.type),
                        modifiers=list(getattr(field, "modifiers", None) or []),
                        default_value=None,
                        annotations=_annotations(field),
                    )
                )
        return fields

    def extract_imports(self) -> list[ImportInfo]:
        imports = []
        for imp in self._tree.imports or []:
            path = imp.path
            is_wildcard = getattr(imp, "wildcard", False)
            is_static = getattr(imp, "static", False)
            if is_wildcard:
                imports.append(
                    ImportInfo(
                        module=path,
                        name="*",
                        alias=None,
                        is_internal=False,
                        kind="wildcard",
                    )
                )
            else:
                parts = path.split(".")
                name = parts[-1]
                module = ".".join(parts[:-1]) if len(parts) > 1 else ""
                imports.append(
                    ImportInfo(
                        module=module,
                        name=name,
                        alias=None,
                        is_internal=False,
                        kind="static_member" if is_static else "class",
                    )
                )
        return imports

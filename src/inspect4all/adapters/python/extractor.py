from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from inspect4all.adapters.python.docstring_parser import extract_documentation
from inspect4all.core.models import (
    FieldInfo,
    FunctionInfo,
    ImportInfo,
    ParameterInfo,
    TypeInfo,
)

if TYPE_CHECKING:
    from pathlib import Path


def _get_name(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return _get_name(node.func)
    return ""


def _annotation_to_str(node) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _default_to_str(node) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _extract_decorators(node) -> list[str]:
    names = []
    for dec in node.decorator_list:
        name = _get_name(dec)
        if name:
            names.append(name)
    return names


class PythonExtractor:
    def __init__(
        self,
        tree: ast.AST,
        source: str,
        file_path: Path,
        module_name: str,
    ):
        self._tree = tree
        self._source = source
        self._file_path = file_path
        self._module = module_name

    def _source_segment(self, node: ast.AST) -> str:
        try:
            seg = ast.get_source_segment(self._source, node)
            return seg or ""
        except Exception:
            return ""

    def _extract_params(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[ParameterInfo]:
        params = []
        args = func_node.args
        defaults_offset = len(args.args) - len(args.defaults)
        for i, arg in enumerate(args.args):
            default_idx = i - defaults_offset
            has_default = default_idx >= 0
            default_val = (
                _default_to_str(args.defaults[default_idx])
                if has_default
                else None
            )
            params.append(
                ParameterInfo(
                    name=arg.arg,
                    type=_annotation_to_str(arg.annotation),
                    default=default_val,
                    is_optional=has_default,
                    annotations=[],
                )
            )
        if args.vararg:
            params.append(
                ParameterInfo(
                    name=f"*{args.vararg.arg}",
                    type=_annotation_to_str(args.vararg.annotation),
                    default=None,
                    is_optional=True,
                    annotations=[],
                )
            )
        if args.kwarg:
            params.append(
                ParameterInfo(
                    name=f"**{args.kwarg.arg}",
                    type=_annotation_to_str(args.kwarg.annotation),
                    default=None,
                    is_optional=True,
                    annotations=[],
                )
            )
        return params

    def _extract_calls(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[str]:
        calls = []
        seen: set[str] = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                name = _get_name(node.func)
                if name and name not in seen:
                    calls.append(name)
                    seen.add(name)
        return calls

    def _build_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        qualified_prefix: str,
    ) -> FunctionInfo:
        qname = (
            f"{qualified_prefix}.{node.name}" if qualified_prefix else node.name
        )
        ds = ast.get_docstring(node)
        doc = extract_documentation(ds)
        decorators = _extract_decorators(node)
        is_async = isinstance(node, ast.AsyncFunctionDef)
        nested = [
            self._build_function(child, qname)
            for child in ast.iter_child_nodes(node)
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        return FunctionInfo(
            name=node.name,
            qualified_name=qname,
            documentation=doc,
            source_code=self._source_segment(node),
            parameters=self._extract_params(node),
            return_type=_annotation_to_str(node.returns),
            modifiers=["async"] if is_async else [],
            annotations=decorators,
            calls=self._extract_calls(node),
            line_range=(node.lineno, node.end_lineno or node.lineno),
            is_constructor=(node.name == "__init__"),
            nested_functions=nested,
            language_specific={
                "decorators": [{"name": d} for d in decorators],
                "is_async": is_async,
            },
        )

    def extract_functions(self) -> list[FunctionInfo]:
        funcs = []
        for node in ast.iter_child_nodes(self._tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.append(self._build_function(node, self._module))
        return funcs

    def extract_types(self) -> list[TypeInfo]:
        types = []
        for node in ast.iter_child_nodes(self._tree):
            if not isinstance(node, ast.ClassDef):
                continue
            qname = f"{self._module}.{node.name}"
            ds = ast.get_docstring(node)
            doc = extract_documentation(ds)
            decorators = _extract_decorators(node)

            base_classes = [
                s for s in (_annotation_to_str(b) for b in node.bases) if s
            ]

            methods = [
                self._build_function(item, qname)
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]

            fields = self._extract_fields(node)

            types.append(
                TypeInfo(
                    kind="class",
                    name=node.name,
                    qualified_name=qname,
                    documentation=doc,
                    source_code=self._source_segment(node),
                    base_classes=base_classes,
                    interfaces=[],
                    modifiers=[],
                    annotations=decorators,
                    fields=fields,
                    methods=methods,
                    line_range=(node.lineno, node.end_lineno or node.lineno),
                    language_specific={
                        "decorators": [{"name": d} for d in decorators]
                    },
                )
            )
        return types

    def _extract_fields(self, class_node: ast.ClassDef) -> list[FieldInfo]:
        fields = []
        for item in class_node.body:
            if (
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == "__init__"
            ):
                for stmt in ast.walk(item):
                    if isinstance(stmt, ast.AnnAssign) and (
                        isinstance(stmt.target, ast.Attribute)
                        and isinstance(stmt.target.value, ast.Name)
                        and stmt.target.value.id == "self"
                    ):
                        fields.append(
                            FieldInfo(
                                name=stmt.target.attr,
                                type=_annotation_to_str(stmt.annotation),
                                modifiers=[],
                                default_value=_default_to_str(stmt.value),
                                annotations=[],
                            )
                        )
        return fields

    def extract_imports(self) -> list[ImportInfo]:
        imports = []
        for node in ast.iter_child_nodes(self._tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module=alias.name,
                            name=alias.name,
                            alias=alias.asname,
                            is_internal=False,
                            kind="module",
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                is_relative = (node.level or 0) > 0
                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module=module,
                            name=alias.name,
                            alias=alias.asname,
                            is_internal=is_relative,
                            kind="module",
                        )
                    )
        return imports

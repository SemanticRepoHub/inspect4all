from __future__ import annotations

import json
from typing import TYPE_CHECKING

import tree_sitter_java
from tree_sitter import Language, Parser

from inspect4all.output.json_reader import file_analysis_from_dict

if TYPE_CHECKING:
    from collections.abc import Callable

    from inspect4all.core.models import FileAnalysis, FunctionInfo, TypeInfo

# Leaf text longer than this is elided from the CST JSON: identifiers and
# literals fit; string-block bodies the agent can fetch via read_source_slice.
_MAX_LEAF_TEXT = 120

_TYPE_NODE_TYPES = frozenset(
    {
        "class_declaration",
        "interface_declaration",
        "record_declaration",
        "enum_declaration",
        "annotation_type_declaration",
        "module_declaration",
    }
)

# Records use class_body in tree-sitter-java (not a separate record_body).
_BODY_NODE_TYPES = frozenset(
    {
        "class_body",
        "interface_body",
        "enum_body",
        "annotation_type_body",
        "module_body",
    }
)

_METHOD_NODE_TYPES = frozenset(
    {
        "method_declaration",
        "constructor_declaration",
    }
)

# Map from tree-sitter node type → FileAnalysis kind string.
_NODE_TO_KIND: dict[str, str] = {
    "class_declaration": "class",
    "interface_declaration": "interface",
    "record_declaration": "record",
    "enum_declaration": "enum",
    "annotation_type_declaration": "annotation",
    "module_declaration": "module",
}


def _node_to_json(node) -> dict:
    entry: dict = {
        "type": node.type,
        "start_line": node.start_point[0] + 1,
        "end_line": node.end_point[0] + 1,
    }
    children = [child for child in node.children if child.is_named]
    if children:
        entry["children"] = [_node_to_json(child) for child in children]
    else:
        text = (node.text or b"").decode("utf-8", errors="replace")
        if len(text) <= _MAX_LEAF_TEXT:
            entry["text"] = text
    return entry


def compute_cst(source: str) -> str:
    """Parse Java source with tree-sitter and return the CST as a JSON string."""
    parser = Parser(Language(tree_sitter_java.language()))
    tree = parser.parse(source.encode("utf-8"))
    return json.dumps(_node_to_json(tree.root_node))


def _expected_structure(source: str) -> dict[str, dict]:
    """Return per-type ground-truth structure derived from tree-sitter.

    Each entry contains:
      kind    — "class", "interface", "record", "enum", "annotation", "module"
      sealed  — True when the modifier "sealed" is present
      methods — names of all method_declaration / constructor_declaration nodes
      fields  — record component names (from formal_parameters) plus
                 field_declaration names from the body

    Only top-level type declarations are included; inner types are skipped.
    """
    parser = Parser(Language(tree_sitter_java.language()))
    tree = parser.parse(source.encode("utf-8"))

    def node_text(node) -> str:
        return (node.text or b"").decode("utf-8", errors="replace")

    def first_identifier(node) -> str | None:
        for child in node.children:
            if child.type in ("identifier", "scoped_identifier"):
                return node_text(child)
        return None

    def is_sealed(type_node) -> bool:
        for child in type_node.children:
            if child.type == "modifiers":
                text = node_text(child)
                return "sealed" in text.split()
        return False

    def record_component_names(type_node) -> list[str]:
        names: list[str] = []
        for child in type_node.children:
            if child.type == "formal_parameters":
                for param in child.children:
                    if param.type == "formal_parameter":
                        # In this tree-sitter-java version the parameter name
                        # is a direct `identifier` child — the type node uses
                        # integral_type / type_identifier / generic_type, so
                        # the lone `identifier` child is always the name.
                        for sub in param.children:
                            if sub.type == "identifier":
                                names.append(node_text(sub))
        return names

    def body_members(type_node) -> tuple[list[str], list[str]]:
        """Return (method_names, field_names) from the type body."""
        methods: list[str] = []
        fields: list[str] = []
        for child in type_node.children:
            if child.type not in _BODY_NODE_TYPES:
                continue
            for member in child.children:
                if member.type in _METHOD_NODE_TYPES:
                    m = first_identifier(member)
                    if m:
                        methods.append(m)
                elif member.type == "field_declaration":
                    # field_declaration → variable_declarator → variable_declarator_id → identifier
                    for vd in member.children:
                        if vd.type == "variable_declarator":
                            vid = next(
                                (
                                    c
                                    for c in vd.children
                                    if c.type == "variable_declarator_id"
                                ),
                                None,
                            )
                            if vid:
                                f = first_identifier(vid)
                                if f:
                                    fields.append(f)
        return methods, fields

    result: dict[str, dict] = {}
    for node in tree.root_node.children:
        if node.type not in _TYPE_NODE_TYPES:
            continue
        name = first_identifier(node)
        if name is None:
            continue
        kind = _NODE_TO_KIND[node.type]
        methods, body_fields = body_members(node)
        # Record components live in formal_parameters, not the body.
        comp_fields = (
            record_component_names(node)
            if node.type == "record_declaration"
            else []
        )
        result[name] = {
            "kind": kind,
            "sealed": is_sealed(node),
            "methods": methods,
            "fields": comp_fields + body_fields,
        }

    return result


def _normalize_import(entry: object) -> object:
    """Coerce a Java import into the structured ImportInfo schema.

    The backfill prompt asks the model for imports as fully-qualified
    name strings (e.g. "java.util.List"). Downstream expects an
    ImportInfo dict, so split each string into module + name here.
    Dict entries and non-strings are returned unchanged so structured
    payloads keep working.
    """
    if not isinstance(entry, str):
        return entry
    fqn = entry.strip()
    if fqn.startswith("static "):  # static member import
        fqn = fqn[len("static ") :].strip()
    if fqn.endswith(".*"):  # wildcard import
        return {
            "module": fqn[:-2],
            "name": "*",
            "alias": None,
            "is_internal": False,
            "kind": "wildcard",
        }
    module, _, name = fqn.rpartition(".")
    return {
        "module": module,
        "name": name or fqn,
        "alias": None,
        "is_internal": False,
        "kind": "class",
    }


def make_java_gap_backfill_tools(
    source: str,
    rel_path: str,
    collector: list[FileAnalysis],
) -> list[Callable]:
    """Build the per-file Java gap backfill tool belt.

    `source` is the text of one javalang-parse-failed file, `rel_path` its
    repo-relative path (the only path an emission may carry). Accepted
    emissions are appended to `collector` as validated FileAnalysis
    instances. The callables close over the file, so build a fresh belt
    per agent invocation.
    """
    lines = source.splitlines()

    def tree_sitter_parse() -> str:
        """Parse the Java file with tree-sitter and return its concrete
        syntax tree as JSON: nodes carry type, start_line, end_line,
        children, and text for short leaves (1-based inclusive lines)."""
        return compute_cst(source)

    def read_source_slice(start_line: int, end_line: int) -> str:
        """Return the raw source between start_line and end_line
        (1-based, inclusive)."""
        return "\n".join(lines[max(start_line - 1, 0) : end_line])

    def emit_file_analysis(payload: dict) -> str:
        """Record the reconstructed analysis for this file. `payload` must
        follow the unified FileAnalysis schema: `file` (path must be the
        given repo-relative path, plus name/extension/language), `imports`,
        `types` (each with kind/name/qualified_name/fields/methods/
        line_range), `functions`, `main_info`, `language_specific`.
        Line ranges are 1-based and must lie within the file."""
        raw_imports = payload.get("imports")
        if isinstance(raw_imports, list):
            payload["imports"] = [_normalize_import(i) for i in raw_imports]
        try:
            analysis = file_analysis_from_dict(payload)
        except Exception as e:  # any schema mismatch -> reject
            return f"error: payload does not fit the schema ({e})"
        if analysis.file is None or analysis.file.path != rel_path:
            return f"error: file.path must be {rel_path!r}"
        if not analysis.types and not analysis.all_functions():
            return (
                "error: payload has no types and no functions; "
                "re-analyse the file and emit again"
            )
        total = len(lines)
        items: list[TypeInfo | FunctionInfo] = [
            *analysis.types,
            *analysis.all_functions(),
        ]
        for item in items:
            span = item.line_range
            if span:
                try:
                    start, end = int(span[0]), int(span[1])
                except (TypeError, ValueError):
                    return (
                        f"error: line_range {list(span)} of {item.name!r} "
                        "must be integers"
                    )
                if not (1 <= start <= end <= total):
                    return (
                        f"error: line_range [{start}, {end}] of "
                        f"{item.name!r} is out of bounds "
                        f"(file has {total} lines)"
                    )
        collector.append(analysis)
        n_imports = len(analysis.imports)
        n_types = len(analysis.types)
        n_methods = sum(len(t.methods) for t in analysis.types)
        n_fields = sum(len(t.fields) for t in analysis.types)
        return (
            f"ok: recorded {rel_path} — "
            f"{n_imports} import(s), {n_types} type(s), "
            f"{n_methods} method(s), {n_fields} field(s). "
            "Now call check_completeness to verify nothing is missing."
        )

    def check_completeness() -> str:
        """Compare the last emitted FileAnalysis against tree-sitter ground truth.

        Checks structural presence (types, methods, fields) and semantic
        correctness of Java 9+ features:
          • kind must match the actual declaration (record vs class, etc.)
          • "sealed" must appear in modifiers when the source uses sealed
          • record components must appear as fields
          • all method names must be present

        Returns COMPLETE when everything matches, or a prioritised list of
        gaps. Call this after every successful emit_file_analysis."""
        if not collector:
            return (
                "error: no emission recorded yet — "
                "call emit_file_analysis first"
            )
        expected = _expected_structure(source)
        emitted = collector[-1]
        emitted_types = {t.name: t for t in emitted.types}

        issues: list[str] = []
        for tname, exp in expected.items():
            if tname not in emitted_types:
                issues.append(f"type {tname!r} is missing entirely")
                continue
            et = emitted_types[tname]

            # kind correctness — wrong kind is a fundamental schema error
            if et.kind != exp["kind"]:
                issues.append(
                    f"type {tname!r} has kind={et.kind!r} "
                    f"but should be {exp['kind']!r}"
                )

            # sealed modifier
            if exp["sealed"]:
                emitted_mods = [m.lower() for m in (et.modifiers or [])]
                if "sealed" not in emitted_mods:
                    issues.append(
                        f"type {tname!r} is sealed but 'sealed' is missing "
                        "from modifiers"
                    )

            # field names (record components + declared fields)
            if exp["fields"]:
                emitted_field_names = {f.name for f in et.fields}
                for fname in exp["fields"]:
                    if fname not in emitted_field_names:
                        issues.append(
                            f"field {fname!r} missing from type {tname!r}"
                        )

            # method names
            emitted_method_names = {m.name for m in et.methods}
            for mname in exp["methods"]:
                if mname not in emitted_method_names:
                    issues.append(
                        f"method {mname!r} missing from type {tname!r}"
                    )

        if issues:
            shown = issues[:8]
            tail = f"; and {len(issues) - 8} more" if len(issues) > 8 else ""
            return (
                f"INCOMPLETE ({len(issues)} gap(s)): "
                + "; ".join(shown)
                + tail
                + ". Fix and call emit_file_analysis again."
            )

        n_types = len(emitted_types)
        n_methods = sum(len(t.methods) for t in emitted.types)
        return (
            f"COMPLETE: {n_types} type(s), {n_methods} method(s), "
            "kind/sealed/fields all verified. Analysis accepted."
        )

    return [
        tree_sitter_parse,
        read_source_slice,
        emit_file_analysis,
        check_completeness,
    ]

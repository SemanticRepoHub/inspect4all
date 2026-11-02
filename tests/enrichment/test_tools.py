import json

from inspect4all.core.models import FileAnalysis
from inspect4all.enrichment.tools import make_java_gap_backfill_tools

MODERN_JAVA = (
    "package com.example;\n"
    "\n"
    "public record Point(int x, int y) {\n"
    "    public int sum() {\n"
    "        return x + y;\n"
    "    }\n"
    "}\n"
)

REL_PATH = "src/main/java/com/example/Point.java"


def _tools(source=MODERN_JAVA, rel_path=REL_PATH, collector=None):
    tools = make_java_gap_backfill_tools(
        source, rel_path, collector if collector is not None else []
    )
    return {t.__name__: t for t in tools}


def _payload(**overrides):
    payload = {
        "file": {
            "path": REL_PATH,
            "name": "Point.java",
            "extension": ".java",
            "language": "Java",
        },
        "imports": [],
        "types": [
            {
                "kind": "record",
                "name": "Point",
                "qualified_name": "com.example.Point",
                "source_code": None,
                "base_classes": [],
                "interfaces": [],
                "modifiers": ["public"],
                "annotations": [],
                "fields": [
                    {
                        "name": "x",
                        "type": "int",
                        "modifiers": [],
                        "annotations": [],
                    },
                    {
                        "name": "y",
                        "type": "int",
                        "modifiers": [],
                        "annotations": [],
                    },
                ],
                "methods": [
                    {
                        "name": "sum",
                        "qualified_name": "com.example.Point.sum",
                        "source_code": None,
                        "parameters": [],
                        "return_type": "int",
                        "modifiers": ["public"],
                        "annotations": [],
                        "calls": [],
                        "line_range": [4, 6],
                        "is_constructor": False,
                        "nested_functions": [],
                        "language_specific": {},
                    }
                ],
                "line_range": [3, 7],
                "language_specific": {"record": True},
            }
        ],
        "functions": [],
        "main_info": None,
        "language_specific": {},
    }
    payload.update(overrides)
    return payload


def test_tree_sitter_parse_reads_modern_java():
    """tree-sitter handles post-Java-8 syntax javalang cannot: the CST
    JSON exposes the record declaration with its line range."""
    cst = json.loads(_tools()["tree_sitter_parse"]())
    assert "record_declaration" in json.dumps(cst)

    def find(node, node_type):
        if node["type"] == node_type:
            return node
        for child in node.get("children", []):
            found = find(child, node_type)
            if found:
                return found
        return None

    record = find(cst, "record_declaration")
    assert record["start_line"] == 3
    assert record["end_line"] == 7


def test_read_source_slice_is_one_based_inclusive():
    tools = _tools()
    assert tools["read_source_slice"](3, 4) == (
        "public record Point(int x, int y) {\n    public int sum() {"
    )


def test_emit_accepts_valid_payload():
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    result = tools["emit_file_analysis"](_payload())
    assert result.startswith("ok")
    assert len(collector) == 1
    fa = collector[0]
    assert isinstance(fa, FileAnalysis)
    assert fa.file.path == REL_PATH
    assert fa.types[0].methods[0].qualified_name == "com.example.Point.sum"
    assert fa.types[0].line_range == (3, 7)


def test_emit_rejects_wrong_path():
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    payload = _payload()
    payload["file"]["path"] = "Other.java"
    result = tools["emit_file_analysis"](payload)
    assert result.startswith("error")
    assert collector == []


def test_emit_rejects_out_of_bounds_line_range():
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    payload = _payload()
    payload["types"][0]["line_range"] = [3, 99]
    result = tools["emit_file_analysis"](payload)
    assert result.startswith("error")
    assert collector == []


def test_emit_rejects_malformed_payload():
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    result = tools["emit_file_analysis"]({"types": "not-a-list"})
    assert result.startswith("error")
    assert collector == []


def test_emit_rejects_empty_payload():
    """A payload with no types and no functions must be rejected so the model retries."""
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    payload = _payload()
    payload["types"] = []
    result = tools["emit_file_analysis"](payload)
    assert result.startswith("error")
    assert "no types" in result
    assert collector == []


def test_emit_accepts_string_line_range():
    """Model may return line_range as strings; emit_file_analysis must coerce."""
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    payload = _payload()
    payload["types"][0]["line_range"] = ["3", "7"]
    payload["types"][0]["methods"][0]["line_range"] = ["4", "6"]
    result = tools["emit_file_analysis"](payload)
    assert result.startswith("ok")
    assert len(collector) == 1


def test_emit_rejects_out_of_bounds_string_line_range():
    """String line_range values that are out of bounds should still be rejected."""
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    payload = _payload()
    payload["types"][0]["line_range"] = ["3", "99"]
    result = tools["emit_file_analysis"](payload)
    assert result.startswith("error")
    assert collector == []


def test_emit_normalizes_string_imports():
    """The prompt asks for imports as FQN strings; emit must split each into
    a structured ImportInfo (module + name) instead of dropping the content."""
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    payload = _payload()
    payload["imports"] = [
        "com.github.kagkarlsson.jdbc.JdbcRunner",
        "java.util.List",
        "java.util.*",
    ]
    result = tools["emit_file_analysis"](payload)
    assert result.startswith("ok")
    imports = collector[0].imports
    assert [i.name for i in imports] == ["JdbcRunner", "List", "*"]
    assert [i.module for i in imports] == [
        "com.github.kagkarlsson.jdbc",
        "java.util",
        "java.util",
    ]
    assert imports[2].kind == "wildcard"


def test_emit_still_accepts_dict_imports():
    """Structured import dicts must keep working unchanged."""
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    payload = _payload()
    payload["imports"] = [
        {
            "module": "java.util",
            "name": "List",
            "alias": None,
            "is_internal": False,
            "kind": "class",
        }
    ]
    result = tools["emit_file_analysis"](payload)
    assert result.startswith("ok")
    assert collector[0].imports[0].name == "List"
    assert collector[0].imports[0].module == "java.util"


# ---------------------------------------------------------------------------
# check_completeness tests
# ---------------------------------------------------------------------------


def test_check_completeness_before_emit_returns_error():
    """check_completeness called before any emission must return an error."""
    tools = _tools(collector=[])
    result = tools["check_completeness"]()
    assert result.startswith("error")
    assert "emit_file_analysis" in result


def test_check_completeness_returns_complete_when_all_present():
    """A full emission matching tree-sitter should return COMPLETE."""
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    tools["emit_file_analysis"](_payload())
    result = tools["check_completeness"]()
    assert result.startswith("COMPLETE")
    assert "1 type(s)" in result
    assert "1 method(s)" in result


def test_check_completeness_returns_incomplete_when_method_missing():
    """If the emitted payload omits a method, check_completeness reports it."""
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    payload = _payload()
    payload["types"][0]["methods"] = []
    tools["emit_file_analysis"](payload)
    result = tools["check_completeness"]()
    assert result.startswith("INCOMPLETE")
    assert "sum" in result


def test_check_completeness_catches_wrong_kind():
    """check_completeness must flag kind='class' when the source declares a record."""
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    payload = _payload()
    payload["types"][0]["kind"] = "class"  # wrong — source uses `record`
    tools["emit_file_analysis"](payload)
    result = tools["check_completeness"]()
    assert result.startswith("INCOMPLETE")
    assert "kind" in result
    assert "record" in result


SEALED_JAVA = (
    "package com.example;\n"
    "\n"
    "public sealed interface Shape permits Circle, Square {}\n"
)
SEALED_REL_PATH = "src/main/java/com/example/Shape.java"


def _sealed_payload(**overrides):
    payload = {
        "file": {
            "path": SEALED_REL_PATH,
            "name": "Shape.java",
            "extension": ".java",
            "language": "Java",
        },
        "imports": [],
        "types": [
            {
                "kind": "interface",
                "name": "Shape",
                "qualified_name": "com.example.Shape",
                "source_code": None,
                "base_classes": [],
                "interfaces": [],
                "modifiers": ["public", "sealed"],
                "annotations": [],
                "fields": [],
                "methods": [],
                "line_range": [3, 3],
                "language_specific": {},
            }
        ],
        "functions": [],
        "main_info": None,
        "language_specific": {},
    }
    payload.update(overrides)
    return payload


def test_check_completeness_passes_sealed_interface():
    """A correctly emitted sealed interface should return COMPLETE."""
    collector: list[FileAnalysis] = []
    tools = _tools(
        source=SEALED_JAVA, rel_path=SEALED_REL_PATH, collector=collector
    )
    tools["emit_file_analysis"](_sealed_payload())
    result = tools["check_completeness"]()
    assert result.startswith("COMPLETE")


def test_check_completeness_catches_missing_sealed_modifier():
    """Missing 'sealed' in modifiers must be flagged."""
    collector: list[FileAnalysis] = []
    tools = _tools(
        source=SEALED_JAVA, rel_path=SEALED_REL_PATH, collector=collector
    )
    payload = _sealed_payload()
    payload["types"][0]["modifiers"] = ["public"]  # sealed omitted
    tools["emit_file_analysis"](payload)
    result = tools["check_completeness"]()
    assert result.startswith("INCOMPLETE")
    assert "sealed" in result


def test_check_completeness_catches_missing_record_component():
    """Record components not emitted as fields must be flagged."""
    collector: list[FileAnalysis] = []
    tools = _tools(
        collector=collector
    )  # MODERN_JAVA has record Point(int x, int y)
    payload = _payload()
    payload["types"][0]["fields"] = []  # x and y omitted
    tools["emit_file_analysis"](payload)
    result = tools["check_completeness"]()
    assert result.startswith("INCOMPLETE")
    assert "x" in result or "y" in result


def test_check_completeness_reflects_latest_emission():
    """After a corrected re-emission, check_completeness should return COMPLETE."""
    collector: list[FileAnalysis] = []
    tools = _tools(collector=collector)
    bad = _payload()
    bad["types"][0]["methods"] = []
    tools["emit_file_analysis"](bad)
    assert tools["check_completeness"]().startswith("INCOMPLETE")
    tools["emit_file_analysis"](_payload())
    result = tools["check_completeness"]()
    assert result.startswith("COMPLETE")

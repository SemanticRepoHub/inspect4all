import json

from langchain_core.messages import AIMessage

from inspect4all.core.models import (
    Documentation,
    FileAnalysis,
    FileInfo,
    FunctionInfo,
    LicenseInfo,
    RepositoryAnalysis,
)
from inspect4all.enrichment.runner import run_enrichment
from inspect4all.output.json_writer import JsonWriter
from tests.enrichment.fakes import FakeToolCallingModel


def _repo():
    func = FunctionInfo(
        name="foo",
        qualified_name="foo",
        documentation=None,
        source_code="def foo(): return 1",
        parameters=[],
        return_type="int",
        modifiers=[],
        annotations=[],
        calls=[],
        line_range=(1, 1),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )
    fa = FileAnalysis(
        file=FileInfo("m.py", "m.py", ".py", "Python", None, None, False),
        imports=[],
        types=[],
        functions=[func],
        main_info=None,
        language_specific={},
    )
    return RepositoryAnalysis(
        repo_path="/r",
        languages={},
        files=[fa],
        readme_files=[],
        directory_tree=[],
        dependencies=[],
        software_type="",
        software_invocation=[],
        tests=[],
        license=LicenseInfo([], [], None),
        metadata={},
        call_graph={},
    )


def _model():
    content = json.dumps(
        {"short_description": "Returns one.", "params": {}, "returns": None}
    )
    return FakeToolCallingModel(responses=[AIMessage(content=content)])


def test_run_enrichment_writes_enriched_outputs(tmp_path):
    JsonWriter(tmp_path).write(_repo())
    stats = run_enrichment(tmp_path, model=_model(), model_id="fake").stats
    assert stats["enriched"] == 1
    assert (tmp_path / "repository_analysis.enriched.json").exists()
    export = json.loads(
        (tmp_path / "embedding_export.enriched.json").read_text()
    )
    doc = export["doc_records"][0]
    # Formerly-undocumented record surfaces the enrichment in ENRICHED mode.
    assert doc["enriched_doc"] == "Returns one."


def test_second_pass_accumulates_prior_enrichments(tmp_path):
    """A rerun must not drop enrichments produced by an earlier pass."""
    JsonWriter(tmp_path).write(_repo())
    run_enrichment(tmp_path, model=_model(), model_id="fake")
    # Second pass: record is cached ok, so the model is never invoked;
    # the enriched export must still carry the pass-1 enrichment.
    stats = run_enrichment(tmp_path, model=_model(), model_id="fake").stats
    assert stats["skipped"] == 1
    export = json.loads(
        (tmp_path / "embedding_export.enriched.json").read_text()
    )
    assert export["doc_records"][0]["enriched_doc"] == "Returns one."


def test_original_output_untouched(tmp_path):
    JsonWriter(tmp_path).write(_repo())
    before = (tmp_path / "repository_analysis.json").read_text()
    run_enrichment(tmp_path, model=_model(), model_id="fake")
    after = (tmp_path / "repository_analysis.json").read_text()
    assert before == after


def test_run_enrichment_backfills_parse_failed_java(tmp_path):
    """The runner drives both processors: docstring enrichment and Java
    parse-failure gap backfill, with combined stats."""
    repo = _repo()
    repo.repo_path = str(tmp_path)
    repo.metadata = {"parse_failures": {"Java": ["C.java"]}}
    (tmp_path / "C.java").write_text(
        "package p;\n\npublic record C(int x) {}\n"
    )
    JsonWriter(tmp_path).write(repo)
    model = FakeToolCallingModel(
        responses=[
            # DocstringEnricher: one direct JSON generation for foo.
            AIMessage(
                content=json.dumps(
                    {
                        "short_description": "Returns one.",
                        "params": {},
                        "returns": None,
                    }
                )
            ),
            # JavaGapBackfillEnricher: scripted emit, then finish.
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "emit_file_analysis",
                        "args": {
                            "payload": {
                                "file": {
                                    "path": "C.java",
                                    "name": "C.java",
                                    "extension": ".java",
                                    "language": "Java",
                                },
                                "imports": [],
                                "types": [
                                    {
                                        "kind": "class",
                                        "name": "C",
                                        "qualified_name": "p.C",
                                        "base_classes": [],
                                        "interfaces": [],
                                        "modifiers": ["public"],
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
                        },
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    result = run_enrichment(tmp_path, model=model, model_id="fake")
    # One docstring record + one backfilled file, uniformly counted.
    assert result.stats["enriched"] == 2
    assert "backfilled" not in result.stats
    assert result.stats["failed"] == 0
    enriched = json.loads(
        (tmp_path / "repository_analysis.enriched.json").read_text()
    )
    paths = [f["file"]["path"] for f in enriched["files"]]
    assert "C.java" in paths


def _documented_repo():
    func = FunctionInfo(
        name="foo",
        qualified_name="foo",
        documentation=Documentation(
            short_description="Existing.",
            long_description=None,
            full_text="Existing.",
            params={},
            returns=None,
            raises=[],
            tags={},
            enrichments=[],
        ),
        source_code="def foo(): return 1",
        parameters=[],
        return_type="int",
        modifiers=[],
        annotations=[],
        calls=[],
        line_range=(1, 1),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )
    fa = FileAnalysis(
        file=FileInfo("m.py", "m.py", ".py", "Python", None, None, False),
        imports=[],
        types=[],
        functions=[func],
        main_info=None,
        language_specific={},
    )
    return RepositoryAnalysis(
        repo_path="/r",
        languages={},
        files=[fa],
        readme_files=[],
        directory_tree=[],
        dependencies=[],
        software_type="",
        software_invocation=[],
        tests=[],
        license=LicenseInfo([], [], None),
        metadata={},
        call_graph={},
    )


def test_docstring_target_all_enriches_documented_functions(tmp_path):
    JsonWriter(tmp_path).write(_documented_repo())
    stats = run_enrichment(
        tmp_path,
        model=_model(),
        model_id="fake",
        docstring_target="all",
        processors=("docstrings",),
    ).stats
    assert stats["enriched"] == 1


def test_docstring_target_undocumented_skips_documented_functions(tmp_path):
    JsonWriter(tmp_path).write(_documented_repo())
    stats = run_enrichment(
        tmp_path,
        model=_model(),
        model_id="fake",
        docstring_target="undocumented",
        processors=("docstrings",),
    ).stats
    assert stats["enriched"] == 0

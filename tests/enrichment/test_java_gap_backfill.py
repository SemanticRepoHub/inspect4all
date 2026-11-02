from langchain_core.messages import AIMessage

from inspect4all.core.models import LicenseInfo, RepositoryAnalysis
from inspect4all.enrichment.java_gap_backfill import JavaGapBackfillEnricher
from tests.enrichment.fakes import FakeToolCallingModel

_SOURCE = "package p;\n\npublic record C(int x) {}\n"


def _repo(tmp_path, failures=("C.java",)):
    for rel in failures:
        (tmp_path / rel).write_text(_SOURCE)
    return RepositoryAnalysis(
        repo_path=str(tmp_path),
        languages={"Java": 1},
        files=[],
        readme_files=[],
        directory_tree=[],
        dependencies=[],
        software_type="",
        software_invocation=[],
        tests=[],
        license=LicenseInfo([], [], None),
        metadata={"parse_failures": {"Java": list(failures)}},
        call_graph={},
    )


def _payload(rel="C.java"):
    return {
        "file": {
            "path": rel,
            "name": rel,
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
                "language_specific": {"record": True},
            }
        ],
        "functions": [],
        "main_info": None,
        "language_specific": {},
    }


def _emitting_model(rel="C.java"):
    return FakeToolCallingModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "emit_file_analysis",
                        "args": {"payload": _payload(rel)},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )


def test_backfills_parse_failed_file(tmp_path):
    repo = _repo(tmp_path)
    enr = JavaGapBackfillEnricher(
        model=_emitting_model(),
        model_id="fake-model",
        cache_path=tmp_path / "cache.jsonl",
    )
    out = enr.enrich(repo)
    assert enr.stats["enriched"] == 1
    assert len(out.files) == 1
    fa = out.files[0]
    assert fa.file.path == "C.java"
    backfilled = fa.language_specific["backfilled"]
    assert backfilled["by"] == "llm"
    assert backfilled["model"] == "fake-model"
    # parse_failures stays intact as the corpus metric; the cache
    # prevents re-work on rerun.
    assert out.metadata["parse_failures"] == {"Java": ["C.java"]}


def test_no_emission_marked_failed(tmp_path):
    repo = _repo(tmp_path)
    enr = JavaGapBackfillEnricher(
        model=FakeToolCallingModel(responses=[AIMessage(content="done")]),
        model_id="fake-model",
        cache_path=tmp_path / "cache.jsonl",
    )
    out = enr.enrich(repo)
    assert enr.stats["failed"] == 1
    assert out.files == []


def test_missing_source_file_marked_failed(tmp_path):
    repo = _repo(tmp_path)
    (tmp_path / "C.java").unlink()
    enr = JavaGapBackfillEnricher(
        model=FakeToolCallingModel(responses=[]),  # must never be invoked
        model_id="fake-model",
        cache_path=tmp_path / "cache.jsonl",
    )
    enr.enrich(repo)
    assert enr.stats["failed"] == 1


def test_rerun_skips_cached_ok(tmp_path):
    cache = tmp_path / "cache.jsonl"
    JavaGapBackfillEnricher(_emitting_model(), "fake-model", cache).enrich(
        _repo(tmp_path)
    )
    enr2 = JavaGapBackfillEnricher(_emitting_model(), "fake-model", cache)
    enr2.enrich(_repo(tmp_path))
    assert enr2.stats["skipped"] == 1
    assert enr2.stats["enriched"] == 0


def test_not_applicable_without_parse_failures(tmp_path):
    repo = _repo(tmp_path)
    repo.metadata = {}
    enr = JavaGapBackfillEnricher(
        model=FakeToolCallingModel(responses=[]),
        model_id="fake-model",
        cache_path=tmp_path / "cache.jsonl",
    )
    assert enr.is_applicable(repo) is False

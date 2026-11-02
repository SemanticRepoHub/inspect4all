import json

from langchain_core.messages import AIMessage

from inspect4all.core.models import (
    Documentation,
    FileAnalysis,
    FileInfo,
    FunctionInfo,
    RepositoryAnalysis,
)
from inspect4all.enrichment.docstring_enricher import DocstringEnricher
from tests.enrichment.fakes import FakeToolCallingModel


def _func(name, calls=()):
    return FunctionInfo(
        name=name,
        qualified_name=name,
        documentation=None,
        source_code=f"def {name}(): return 1",
        parameters=[],
        return_type="int",
        modifiers=[],
        annotations=[],
        calls=list(calls),
        line_range=(1, 1),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )


def _repo(funcs=None):
    functions = funcs if funcs is not None else [_func("foo")]
    fa = FileAnalysis(
        file=FileInfo("m.py", "m.py", ".py", "Python", None, None, False),
        imports=[],
        types=[],
        functions=functions,
        main_info=None,
        language_specific={},
    )
    call_graph = {f.qualified_name: f.calls for f in functions if f.calls}
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
        license=None,
        metadata={},
        call_graph=call_graph,
    )


def _json(desc):
    return json.dumps(
        {"short_description": desc, "params": {}, "returns": None}
    )


def _model(*descs):
    return FakeToolCallingModel(
        responses=[AIMessage(content=_json(d)) for d in descs]
    )


def test_enrich_attaches_enrichment_to_undocumented(tmp_path):
    repo = _repo()
    enr = DocstringEnricher(
        model=_model("Returns one."),
        model_id="fake-model",
        cache_path=tmp_path / "cache.jsonl",
    )
    out = enr.enrich(repo)
    func = out.files[0].functions[0]
    assert func.documentation is not None
    enrichment = func.documentation.enrichments[-1]
    assert enrichment.source == "docstring_enricher"
    assert enrichment.model == "fake-model"
    assert enrichment.content["short_description"] == "Returns one."
    assert enr.stats["enriched"] == 1


def test_extracted_text_not_overwritten(tmp_path):
    repo = _repo()
    enr = DocstringEnricher(
        model=_model("Returns one."),
        model_id="fake-model",
        cache_path=tmp_path / "cache.jsonl",
    )
    out = enr.enrich(repo)
    assert out.files[0].functions[0].documentation.full_text is None


def test_rerun_skips_cached_ok(tmp_path):
    cache = tmp_path / "cache.jsonl"
    DocstringEnricher(_model("Returns one."), "fake-model", cache).enrich(
        _repo()
    )
    enr2 = DocstringEnricher(_model("Returns one."), "fake-model", cache)
    enr2.enrich(_repo())
    assert enr2.stats["skipped"] == 1
    assert enr2.stats["enriched"] == 0


def test_failed_generation_cached_as_failed(tmp_path):
    enr = DocstringEnricher(
        model=FakeToolCallingModel(
            responses=[AIMessage(content="junk"), AIMessage(content="junk")]
        ),
        model_id="fake-model",
        cache_path=tmp_path / "cache.jsonl",
    )
    enr.enrich(_repo())
    assert enr.stats["failed"] == 1
    assert enr.stats["enriched"] == 0


def _documented_repo():
    func = FunctionInfo(
        name="foo",
        qualified_name="foo",
        documentation=Documentation(
            short_description="Existing doc.",
            long_description=None,
            full_text="Existing doc.",
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
        license=None,
        metadata={},
        call_graph={},
    )


def test_docstring_target_undocumented_skips_documented(tmp_path):
    enr = DocstringEnricher(
        model=_model("Should not be called."),
        model_id="fake",
        cache_path=tmp_path / "cache.jsonl",
        docstring_target="undocumented",
    )
    enr.enrich(_documented_repo())
    assert enr.stats["enriched"] == 0
    assert enr.stats["skipped"] == 0


def test_docstring_target_all_enriches_documented(tmp_path):
    enr = DocstringEnricher(
        model=_model("Generated doc."),
        model_id="fake",
        cache_path=tmp_path / "cache.jsonl",
        docstring_target="all",
    )
    out = enr.enrich(_documented_repo())
    assert enr.stats["enriched"] == 1
    enrichments = out.files[0].functions[0].documentation.enrichments
    assert enrichments[-1].content["short_description"] == "Generated doc."


def test_callee_docstring_feeds_caller_prompt(tmp_path):
    """b calls a: a is generated first and its summary appears in b's prompt."""
    captured: list[str] = []

    class Capturing(FakeToolCallingModel):
        def _generate(self, messages, stop=None, run_manager=None, **kw):
            captured.append(" ".join(str(m.content) for m in messages))
            return super()._generate(messages, stop, run_manager, **kw)

    repo = _repo([_func("b", calls=["a"]), _func("a")])
    model = Capturing(
        responses=[
            AIMessage(content=_json("Does the a thing.")),
            AIMessage(content=_json("Wraps a.")),
        ]
    )
    enr = DocstringEnricher(
        model=model, model_id="fake", cache_path=tmp_path / "cache.jsonl"
    )
    enr.enrich(repo)
    assert enr.stats["enriched"] == 2
    # First generation is for 'a' (no callees); second is 'b' and must see
    # a's freshly generated summary as callee context.
    assert "Function: a" in captured[0]
    assert "Function: b" in captured[1]
    assert "Does the a thing." in captured[1]

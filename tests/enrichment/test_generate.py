import json

from langchain_core.messages import AIMessage

from inspect4all.enrichment.generate import generate_docstring
from inspect4all.enrichment.targets import DocstringTarget
from tests.enrichment.fakes import FakeToolCallingModel


def _target():
    return DocstringTarget(
        "m.py::pkg.foo",
        "pkg.foo",
        "foo(a: int) -> int",
        (1, 2),
        "def foo(a): return bar(a)",
    )


def _model(*contents):
    return FakeToolCallingModel(
        responses=[AIMessage(content=c) for c in contents]
    )


def _valid(desc="Adds one."):
    return json.dumps(
        {"short_description": desc, "params": {"a": "input"}, "returns": "int"}
    )


def test_valid_json_accepted():
    result = generate_docstring(_model(_valid()), _target(), {})
    assert result == {
        "short_description": "Adds one.",
        "params": {"a": "input"},
        "returns": "int",
    }


def test_fenced_json_accepted():
    fenced = f"```json\n{_valid()}\n```"
    result = generate_docstring(_model(fenced), _target(), {})
    assert result["short_description"] == "Adds one."


def test_invalid_then_valid_retries_once():
    result = generate_docstring(
        _model("not json at all", _valid()), _target(), {}
    )
    assert result["short_description"] == "Adds one."


def test_invalid_twice_returns_none():
    assert generate_docstring(_model("nope", "nope"), _target(), {}) is None


def test_empty_description_rejected():
    empty = json.dumps({"short_description": "  "})
    assert generate_docstring(_model(empty, empty), _target(), {}) is None


def test_callee_docs_included_in_prompt():
    captured = []

    class Capturing(FakeToolCallingModel):
        def _generate(self, messages, stop=None, run_manager=None, **kw):
            captured.extend(messages)
            return super()._generate(messages, stop, run_manager, **kw)

    model = Capturing(responses=[AIMessage(content=_valid())])
    generate_docstring(model, _target(), {"pkg.bar": "Doubles the input."})
    prompt = " ".join(str(m.content) for m in captured)
    assert "pkg.bar" in prompt
    assert "Doubles the input." in prompt


def test_llm_settings_max_tokens_default():
    from inspect4all.core.config import LLMSettings

    assert LLMSettings().max_tokens == 4096

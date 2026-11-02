import time

from langchain_core.messages import AIMessage

from inspect4all.enrichment.harness import build_agent, run_agent
from inspect4all.enrichment.tools import make_java_gap_backfill_tools
from tests.enrichment.fakes import FakeToolCallingModel

_SOURCE = "package p;\n\npublic class C {}\n"


def _payload():
    return {
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


def test_agent_runs_scripted_tool_call_into_collector():
    collector = []
    tools = make_java_gap_backfill_tools(_SOURCE, "C.java", collector)
    model = FakeToolCallingModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "emit_file_analysis",
                        "args": {"payload": _payload()},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    agent = build_agent(model, tools, "Recover the failed file.")
    ok = run_agent(agent, "go")
    assert ok is True
    assert collector[0].types[0].qualified_name == "p.C"


class _StallingModel(FakeToolCallingModel):
    """Blocks in generation, simulating a runaway local-model response."""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        time.sleep(5)
        return super()._generate(messages, stop, run_manager, **kwargs)


def test_run_agent_times_out_on_stalled_model():
    model = _StallingModel(responses=[AIMessage(content="done")])
    agent = build_agent(model, [], "Do nothing.")
    start = time.monotonic()
    ok = run_agent(agent, "go", timeout_s=0.2)
    elapsed = time.monotonic() - start
    assert ok is False
    assert elapsed < 2  # returned at the timeout, not after the stall

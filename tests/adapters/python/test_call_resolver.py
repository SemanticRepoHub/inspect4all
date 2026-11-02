"""Pipeline-level tests for cross-file call resolution (real files)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from inspect4all.adapters import AdapterRegistry
from inspect4all.adapters.python.adapter import PythonAdapter
from inspect4all.pipeline import InspectionPipeline, InspectOptions

if TYPE_CHECKING:
    from pathlib import Path


def _analyse(tmp_path: Path):
    pipeline = InspectionPipeline(AdapterRegistry(PythonAdapter()))
    return pipeline.inspect(tmp_path, InspectOptions())


def _func(result, name):
    return next(
        f for fa in result.files for f in fa.all_functions() if f.name == name
    )


def test_from_import_resolved(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def helper():\n    pass\n")
    (tmp_path / "b.py").write_text(
        "from a import helper\n\ndef run():\n    helper()\n"
    )
    run = _func(_analyse(tmp_path), "run")
    assert "a.helper" in run.calls


def test_module_import_resolved(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def helper():\n    pass\n")
    (tmp_path / "b.py").write_text("import a\n\ndef run():\n    a.helper()\n")
    run = _func(_analyse(tmp_path), "run")
    assert "a.helper" in run.calls


def test_aliased_module_import_resolved(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def helper():\n    pass\n")
    (tmp_path / "b.py").write_text(
        "import a as mod\n\ndef run():\n    mod.helper()\n"
    )
    run = _func(_analyse(tmp_path), "run")
    assert "a.helper" in run.calls


def test_local_call_qualified(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text(
        "def helper():\n    pass\n\ndef run():\n    helper()\n"
    )
    run = _func(_analyse(tmp_path), "run")
    assert "m.helper" in run.calls


def test_self_method_resolved(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text(
        "class Cls:\n"
        "    def go(self):\n"
        "        self.step()\n"
        "    def step(self):\n"
        "        pass\n"
    )
    go = _func(_analyse(tmp_path), "go")
    assert "m.Cls.step" in go.calls


def test_external_call_unchanged(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text(
        "import os\n\ndef run():\n    os.path.join('a', 'b')\n"
    )
    run = _func(_analyse(tmp_path), "run")
    assert "os.path.join" in run.calls

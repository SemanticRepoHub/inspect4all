"""Pipeline-level tests for Java cross-file call resolution (real files)."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from inspect4all.adapters import AdapterRegistry
from inspect4all.adapters.java.adapter import JavaAdapter
from inspect4all.pipeline import InspectionPipeline, InspectOptions

if TYPE_CHECKING:
    from pathlib import Path


def _analyse(tmp_path: Path):
    pipeline = InspectionPipeline(AdapterRegistry(JavaAdapter()))
    return pipeline.inspect(tmp_path, InspectOptions())


def _method(result, name):
    return next(
        f for fa in result.files for f in fa.all_functions() if f.name == name
    )


def _write(tmp_path: Path, rel: str, src: str) -> None:
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(textwrap.dedent(src), encoding="utf-8")


def test_same_class_call_resolved(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "com/example/Runner.java",
        """\
        package com.example;

        public class Runner {
            public void run() {
                step();
            }
            public void step() {
            }
        }
    """,
    )
    run = _method(_analyse(tmp_path), "run")
    assert "com.example.Runner.step" in run.calls


def test_same_package_static_call_resolved(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "com/example/Runner.java",
        """\
        package com.example;

        public class Runner {
            public void run() {
                Utils.help();
            }
        }
    """,
    )
    _write(
        tmp_path,
        "com/example/Utils.java",
        """\
        package com.example;

        public class Utils {
            public static void help() {
            }
        }
    """,
    )
    run = _method(_analyse(tmp_path), "run")
    assert "com.example.Utils.help" in run.calls


def test_imported_class_call_resolved(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "com/example/Runner.java",
        """\
        package com.example;

        import com.other.Tool;

        public class Runner {
            public void run() {
                Tool.use();
            }
        }
    """,
    )
    _write(
        tmp_path,
        "com/other/Tool.java",
        """\
        package com.other;

        public class Tool {
            public static void use() {
            }
        }
    """,
    )
    run = _method(_analyse(tmp_path), "run")
    assert "com.other.Tool.use" in run.calls


def test_constructor_call_resolved(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "com/example/Runner.java",
        """\
        package com.example;

        public class Runner {
            public void run() {
                Helper h = new Helper();
            }
        }
    """,
    )
    _write(
        tmp_path,
        "com/example/Helper.java",
        """\
        package com.example;

        public class Helper {
            public Helper() {
            }
        }
    """,
    )
    run = _method(_analyse(tmp_path), "run")
    assert "com.example.Helper.Helper" in run.calls


def test_inherited_method_call_resolved(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "com/example/Child.java",
        """\
        package com.example;

        public class Child extends Base {
            public void run() {
                inherited();
            }
        }
    """,
    )
    _write(
        tmp_path,
        "com/example/Base.java",
        """\
        package com.example;

        public class Base {
            public void inherited() {
            }
        }
    """,
    )
    run = _method(_analyse(tmp_path), "run")
    assert "com.example.Base.inherited" in run.calls


def test_instance_call_unchanged(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "com/example/Runner.java",
        """\
        package com.example;

        public class Runner {
            public void run(Object h) {
                System.out.println("x");
            }
        }
    """,
    )
    run = _method(_analyse(tmp_path), "run")
    assert "System.out.println" in run.calls

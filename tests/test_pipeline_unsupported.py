"""Integration tests: UnsupportedFileTypeError routes misdetected Python files
to unhandled_files. Java parse failures (module-info, records) stay in
parse_failures unchanged.
"""

from __future__ import annotations

from inspect4all.adapters import build_default_registry
from inspect4all.pipeline import InspectionPipeline, InspectOptions


def _pipeline():
    return InspectionPipeline(build_default_registry())


# ── Python misdetected-as-Python fixes ───────────────────────────────────────


def test_cython_file_goes_to_unhandled_not_parse_failures(tmp_path):
    (tmp_path / "fast.pyx").write_text(
        "def add(int x, int y):\n    return x + y\n"
    )
    result = _pipeline().inspect(tmp_path, InspectOptions())
    assert "Cython" in result.metadata.get("unhandled_files", {})
    assert "Python" not in result.metadata.get("parse_failures", {})


def test_jinja2_template_goes_to_unhandled(tmp_path):
    tpl_dir = tmp_path / "{{ label }}"
    tpl_dir.mkdir()
    (tpl_dir / "app.py").write_text("class App:\n    pass\n")
    result = _pipeline().inspect(tmp_path, InspectOptions())
    assert "Jinja2Template" in result.metadata.get("unhandled_files", {})
    assert "Python" not in result.metadata.get("parse_failures", {})


def test_python2_file_goes_to_unhandled_not_parse_failures(tmp_path):
    (tmp_path / "legacy.py").write_text('print "hello"\n')
    result = _pipeline().inspect(tmp_path, InspectOptions())
    assert "Python2Legacy" in result.metadata.get("unhandled_files", {})
    assert "Python" not in result.metadata.get("parse_failures", {})


# ── Java: all failures stay in parse_failures (no change) ────────────────────


def test_module_info_java_stays_in_parse_failures(tmp_path):
    (tmp_path / "module-info.java").write_text(
        "module com.example { requires java.base; }\n"
    )
    result = _pipeline().inspect(tmp_path, InspectOptions())
    assert "Java" in result.metadata.get("parse_failures", {})


def test_post_java8_syntax_stays_in_parse_failures(tmp_path):
    (tmp_path / "Point.java").write_text(
        "package com.example;\npublic record Point(int x, int y) {}\n"
    )
    result = _pipeline().inspect(tmp_path, InspectOptions())
    assert "Java" in result.metadata.get("parse_failures", {})


# ── Normal files unaffected ───────────────────────────────────────────────────


def test_valid_python_and_java_produce_no_failures(tmp_path):
    (tmp_path / "app.py").write_text("def hello(): pass\n")
    (tmp_path / "pom.xml").write_text("<project/>")
    (tmp_path / "Hello.java").write_text(
        "public class Hello { public void hi() {} }\n"
    )
    result = _pipeline().inspect(tmp_path, InspectOptions())
    assert len(result.files) == 2
    assert not result.metadata.get("parse_failures")

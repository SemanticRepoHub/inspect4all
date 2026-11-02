"""Confirm that all Java parse failures (module-info, post-Java-8 syntax)
remain in parse_failures. No Java file type is rerouted to unhandled_files.
"""

from __future__ import annotations

import pytest

from inspect4all.adapters.java.parser import JavaParser


def test_module_info_raises_syntax_error(tmp_path):
    """module-info.java cannot be parsed by javalang - it is a parse failure."""
    f = tmp_path / "module-info.java"
    f.write_text(
        "module com.example.core {\n"
        "    requires java.base;\n"
        "    exports com.example.api;\n"
        "}\n"
    )
    with pytest.raises(SyntaxError):
        JavaParser().parse(f)


def test_record_raises_syntax_error(tmp_path):
    """Java 14+ records fail with javalang - parse failure by design."""
    f = tmp_path / "Point.java"
    f.write_text("package com.example;\npublic record Point(int x, int y) {}\n")
    with pytest.raises(SyntaxError):
        JavaParser().parse(f)


def test_normal_java_class_parses_successfully(tmp_path):
    f = tmp_path / "Hello.java"
    f.write_text(
        "package com.example;\n\n"
        "public class Hello {\n"
        "    public void greet() {}\n"
        "}\n"
    )
    result = JavaParser().parse(f)
    assert result.tree is not None

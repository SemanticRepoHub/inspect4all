import textwrap

from inspect4all.adapters.java.parser import JavaParser

SIMPLE_JAVA = textwrap.dedent("""\
    package com.example;

    /**
     * A simple class.
     */
    public class Hello {
        public static void main(String[] args) {
            System.out.println("Hello");
        }
    }
""")

SYNTAX_ERROR_JAVA = "public class Broken { public void foo( { }"


def test_parse_returns_parse_result(tmp_path):
    f = tmp_path / "Hello.java"
    f.write_text(SIMPLE_JAVA, encoding="utf-8")
    result = JavaParser().parse(f)
    assert result.tree is not None
    assert result.source == SIMPLE_JAVA


def test_parse_stores_file_path(tmp_path):
    f = tmp_path / "Hello.java"
    f.write_text(SIMPLE_JAVA, encoding="utf-8")
    result = JavaParser().parse(f)
    assert result.file_path == f


def test_parse_syntax_error_raises(tmp_path):
    f = tmp_path / "Broken.java"
    f.write_text(SYNTAX_ERROR_JAVA, encoding="utf-8")
    try:
        JavaParser().parse(f)
        raise AssertionError("expected SyntaxError")
    except SyntaxError:
        pass

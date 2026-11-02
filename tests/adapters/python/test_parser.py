import pytest

from inspect4all.adapters.python.parser import PythonParser


def test_parse_valid_python_file(tmp_path):
    src = tmp_path / "example.py"
    src.write_text("def hello():\n    return 'world'\n")
    result = PythonParser().parse(src)
    assert result.tree is not None
    assert "def hello" in result.source
    assert result.file_path == src


def test_parse_with_encoding(tmp_path):
    src = tmp_path / "utf8.py"
    src.write_bytes("# -*- coding: utf-8 -*-\nx = '日本語'\n".encode())
    result = PythonParser().parse(src)
    assert result.tree is not None


def test_parse_syntax_error_raises(tmp_path):
    src = tmp_path / "bad.py"
    src.write_text("def broken(\n")
    with pytest.raises(SyntaxError):
        PythonParser().parse(src)

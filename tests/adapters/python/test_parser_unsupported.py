"""Tests for PythonParser unsupported-file-type detection.

Covers Cython (.pyx/.pxd/.pxi), Jinja2 template paths and content,
Python 2 syntax (including beyond line 200), Dockerfile content,
and Python 3.14+ / pre-3.7 unsupported syntax (t-strings, async-as-name).
All should raise UnsupportedFileTypeError, not SyntaxError, so the pipeline
routes them to unhandled_files rather than parse_failures.
"""

from __future__ import annotations

import pytest

from inspect4all.adapters.python.parser import PythonParser
from inspect4all.core.interfaces import UnsupportedFileTypeError

# ── Cython ────────────────────────────────────────────────────────────────────


def test_pyx_file_raises_unsupported(tmp_path):
    f = tmp_path / "fast.pyx"
    f.write_text("def add(int x, int y):\n    return x + y\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Cython"


def test_pxd_file_raises_unsupported(tmp_path):
    f = tmp_path / "defs.pxd"
    f.write_text("cdef extern from 'math.h':\n    double sin(double x)\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Cython"


def test_pxi_file_raises_unsupported(tmp_path):
    f = tmp_path / "include.pxi"
    f.write_text("# Cython include\nDEBUG = True\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Cython"


# ── Jinja2 template ───────────────────────────────────────────────────────────


def test_jinja2_template_path_raises_unsupported(tmp_path):
    """A file whose path contains '{{' is a Jinja2 template, not real Python."""
    template_dir = tmp_path / "{{ label }}"
    template_dir.mkdir()
    f = template_dir / "app.py"
    f.write_text("class App:\n    pass\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Jinja2Template"


def test_jinja2_content_raises_unsupported(tmp_path):
    """A .py file containing Jinja2 control-flow markers is not real Python."""
    f = tmp_path / "template.py"
    f.write_text("{% for item in items %}\n{{ item }}\n{% endfor %}\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Jinja2Content"


def test_normal_python_not_treated_as_jinja2(tmp_path):
    """A valid Python file is parsed normally even if braces appear in content."""
    f = tmp_path / "normal.py"
    f.write_text('d = {"key": "{{ value }}"}\n')  # braces in string, not path
    result = PythonParser().parse(f)
    assert result.tree is not None


# ── Python 2 ──────────────────────────────────────────────────────────────────


def test_python2_print_statement_raises_unsupported(tmp_path):
    f = tmp_path / "old.py"
    f.write_text('print "hello world"\n')
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Python2Legacy"


def test_python2_inline_print_raises_unsupported(tmp_path):
    """Inline print after 'if cond: print msg' - not anchored to line start."""
    f = tmp_path / "old_inline.py"
    f.write_text('verbose = True\nif verbose: print "done"\n')
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Python2Legacy"


def test_python2_exec_statement_raises_unsupported(tmp_path):
    """Python 2 exec statement (not exec() call)."""
    f = tmp_path / "old_exec.py"
    f.write_text("exec 'from os import getcwd' in globals()\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Python2Legacy"


def test_python2_long_int_literal_raises_unsupported(tmp_path):
    """Python 2 long integer suffix (123L) removed in Python 3."""
    f = tmp_path / "old_long.py"
    f.write_text("import random\nrandom.seed(2342471922L)\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Python2Legacy"


def test_python2_beyond_line_200_raises_unsupported(tmp_path):
    """Python 2 syntax appearing after line 200 must still be detected."""
    filler = "# comment\n" * 210
    f = tmp_path / "late_py2.py"
    f.write_text(filler + 'print "hello"\n')
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Python2Legacy"


def test_python2_xrange_parses_as_valid_python3(tmp_path):
    # xrange(10) is syntactically valid Python 3 (NameError only at runtime),
    # so ast.parse() succeeds - no UnsupportedFileTypeError raised.
    f = tmp_path / "old.py"
    f.write_text("for i in xrange(10):\n    pass\n")
    result = PythonParser().parse(f)
    assert result.tree is not None


def test_python2_except_comma_raises_unsupported(tmp_path):
    f = tmp_path / "old.py"
    f.write_text("try:\n    pass\nexcept ValueError, e:\n    pass\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "Python2Legacy"


def test_python2_raw_input_parses_as_valid_python3(tmp_path):
    # raw_input(...) is syntactically valid Python 3 (NameError only at runtime).
    f = tmp_path / "old.py"
    f.write_text('name = raw_input("Enter name: ")\n')
    result = PythonParser().parse(f)
    assert result.tree is not None


def test_genuine_syntax_error_still_raises_syntax_error(tmp_path):
    """Garbled Python 3 that is not Python 2 must still raise SyntaxError."""
    f = tmp_path / "broken.py"
    f.write_text("def foo(\n    x = \n")  # incomplete def, not Python 2
    with pytest.raises(SyntaxError):
        PythonParser().parse(f)


def test_valid_python3_parses_normally(tmp_path):
    f = tmp_path / "valid.py"
    f.write_text("def greet(name: str) -> str:\n    return f'Hello {name}'\n")
    result = PythonParser().parse(f)
    assert result.tree is not None


# ── Dockerfile content ────────────────────────────────────────────────────────


def test_dockerfile_content_raises_unsupported(tmp_path):
    """A file with Dockerfile instructions and a .py-like extension is not Python."""
    f = tmp_path / "Dockerfile.py3"
    f.write_text("FROM python:3.12\nRUN pip install requests\nCOPY . /app\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "DockerfileContent"


# ── Unsupported Python syntax (version mismatch) ──────────────────────────────


def test_tstring_raises_unsupported(tmp_path):
    """t-string literals (PEP 750, Python 3.14+) are not parseable on 3.12."""
    f = tmp_path / "tstring.py"
    f.write_text('name = "world"\ngreeting = t"Hello {name!r}"\n')
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "UnsupportedPythonSyntax"


def test_async_as_module_name_raises_unsupported(tmp_path):
    """'async' as a bare name in an import path is valid pre-3.7 but a keyword now."""
    f = tmp_path / "old_import.py"
    f.write_text("from jobcontrol.async.jobs import run\n")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        PythonParser().parse(f)
    assert exc_info.value.file_type == "UnsupportedPythonSyntax"

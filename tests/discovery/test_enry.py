import pytest

from inspect4all.discovery.enry import Enry, default_lib_name, default_lib_path


@pytest.fixture
def enry():
    return Enry(lib_path=default_lib_path())


def test_default_lib_name_linux(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    assert default_lib_name() == "libenry.so"


def test_default_lib_name_macos(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assert default_lib_name() == "libenry.dylib"


def test_default_lib_name_windows(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    assert default_lib_name() == "libenry.dll"


def test_default_lib_path_points_into_libs():
    path = default_lib_path()
    assert path.parent.name == "libs"
    assert path.name == default_lib_name()


def test_detect_python(enry):
    assert enry.detect("main.py", b"import os\nprint('hello')") == "Python"


def test_detect_java(enry):
    assert enry.detect("App.java", b"public class App {}") == "Java"


def test_detect_markdown(enry):
    lang = enry.detect("README.md", b"# Hello\nThis is a readme.")
    assert lang in ("Markdown", "")


def test_is_binary_true(enry):
    assert enry.is_binary(b"\x00\x01\x02\xff") is True


def test_is_binary_false(enry):
    assert enry.is_binary(b"def hello(): pass\n") is False


def test_is_vendored_vendor_path(enry):
    assert enry.is_vendored("vendor/requests/__init__.py") is True


def test_is_vendored_normal(enry):
    assert enry.is_vendored("src/mylib/utils.py") is False


def test_get_language_type_programming(enry):
    assert enry.get_language_type("Python") == "programming"


def test_get_language_type_prose(enry):
    assert enry.get_language_type("Markdown") in ("prose", "markup")


def test_is_documentation_readme(enry):
    assert enry.is_documentation("README.md") is True


def test_is_documentation_source(enry):
    assert enry.is_documentation("main.py") is False

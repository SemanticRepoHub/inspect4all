import pytest

from inspect4all.discovery.enry import Enry, default_lib_path
from inspect4all.discovery.scanner import FileManifest, RepositoryScanner


@pytest.fixture
def scanner():
    return RepositoryScanner(enry=Enry(lib_path=default_lib_path()))


def test_scan_finds_python_files(scanner, tmp_path):
    (tmp_path / "main.py").write_text("import os\nprint('hello')")
    (tmp_path / "README.md").write_text("# My Project")
    manifest = scanner.scan(tmp_path)
    assert "Python" in manifest.language_summary
    groups = manifest.group_by_language()
    assert len(groups.get("Python", [])) == 1


def test_scan_skips_pycache(scanner, tmp_path):
    (tmp_path / "main.py").write_text("x = 1")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "main.cpython-312.pyc").write_bytes(b"\x00")
    manifest = scanner.scan(tmp_path)
    for entry in manifest.entries:
        assert "__pycache__" not in str(entry.path)


def test_scan_language_summary(scanner, tmp_path):
    (tmp_path / "a.py").write_text("x=1")
    (tmp_path / "b.py").write_text("y=2")
    (tmp_path / "App.java").write_text("public class App {}")
    manifest = scanner.scan(tmp_path)
    assert manifest.language_summary.get("Python", 0) == 2
    assert manifest.language_summary.get("Java", 0) == 1


def test_get_readme_files(scanner, tmp_path):
    (tmp_path / "README.md").write_text("# hello")
    (tmp_path / "main.py").write_text("x=1")
    manifest = scanner.scan(tmp_path)
    readmes = manifest.get_readme_files()
    names = [p.name for p in readmes]
    assert "README.md" in names


def test_manifest_is_file_manifest(scanner, tmp_path):
    (tmp_path / "x.py").write_text("pass")
    manifest = scanner.scan(tmp_path)
    assert isinstance(manifest, FileManifest)
    assert manifest.repo_path == tmp_path

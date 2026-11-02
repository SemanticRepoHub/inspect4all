import textwrap
from pathlib import Path

from inspect4all.adapters.java.adapter import JavaAdapter
from inspect4all.discovery.scanner import FileEntry, FileManifest

HELLO_JAVA = textwrap.dedent("""\
    package com.example;

    public class Hello {
        public static void main(String[] args) {
            System.out.println("Hello, World!");
        }
    }
""")


def _make_manifest(tmp_path: Path) -> FileManifest:
    f = tmp_path / "Hello.java"
    f.write_text(HELLO_JAVA, encoding="utf-8")
    entry = FileEntry(
        path=str(f),
        language="Java",
        language_type="programming",
        is_binary=False,
        is_vendored=False,
        is_generated=False,
        is_documentation=False,
    )
    return FileManifest(
        repo_path=str(tmp_path),
        entries=[entry],
        language_summary={"Java": 1},
    )


def test_adapter_language_name():
    assert JavaAdapter().language_name == "Java"


def test_adapter_file_extensions():
    assert ".java" in JavaAdapter().file_extensions


def test_extract_file_analysis(tmp_path):
    adapter = JavaAdapter()
    f = tmp_path / "Hello.java"
    f.write_text(HELLO_JAVA, encoding="utf-8")
    pr = adapter.parse_file(f)
    fa = adapter.extract_file_analysis(pr, tmp_path)
    assert fa is not None
    assert fa.file.language == "Java"
    assert len(fa.types) == 1
    assert fa.types[0].name == "Hello"


def test_main_method_detected(tmp_path):
    adapter = JavaAdapter()
    f = tmp_path / "Hello.java"
    f.write_text(HELLO_JAVA, encoding="utf-8")
    pr = adapter.parse_file(f)
    fa = adapter.extract_file_analysis(pr, tmp_path)
    method_names = [m.name for m in fa.types[0].methods]
    assert "main" in method_names


def test_software_type_application(tmp_path):
    adapter = JavaAdapter()
    f = tmp_path / "Hello.java"
    f.write_text(HELLO_JAVA, encoding="utf-8")
    pr = adapter.parse_file(f)
    fa = adapter.extract_file_analysis(pr, tmp_path)
    sw = adapter.detect_software_type([fa], [], tmp_path)
    assert sw is not None
    assert sw.software_type in ("application", "library", "package")

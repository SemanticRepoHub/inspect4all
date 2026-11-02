from inspect4all.core.constants import EmbeddingMode
from inspect4all.core.models import (
    Documentation,
    FileAnalysis,
    FileInfo,
    FunctionInfo,
    LicenseInfo,
    ReadmeFile,
    RepositoryAnalysis,
)
from inspect4all.output.embedding_export import EmbeddingExporter


def _make_repo_with_function() -> RepositoryAnalysis:
    func = FunctionInfo(
        name="process",
        qualified_name="mymod.process",
        documentation=Documentation(
            short_description="Process data.",
            long_description=None,
            full_text="Process data.",
            params={},
            returns=None,
            raises=[],
            tags={},
        ),
        source_code="def process(): pass",
        parameters=[],
        return_type=None,
        modifiers=[],
        annotations=[],
        calls=[],
        line_range=(1, 1),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )
    fa = FileAnalysis(
        file=FileInfo(
            path="mymod.py",
            name="mymod",
            extension=".py",
            language="Python",
            package="mymod",
            documentation=None,
            is_test=False,
        ),
        imports=[],
        types=[],
        functions=[func],
        main_info=None,
        language_specific={},
    )
    return RepositoryAnalysis(
        repo_path="/tmp/test",
        languages={"Python": 1},
        files=[fa],
        readme_files=[ReadmeFile(path="README.md", content="# Test Repo")],
        directory_tree=[],
        dependencies=[],
        software_type="library",
        software_invocation=[],
        tests=[],
        license=LicenseInfo(detected=[], source_files=[], text=None),
        metadata={},
        call_graph={},
    )


def test_embedding_export_has_readme():
    export = EmbeddingExporter().export(
        _make_repo_with_function(), EmbeddingMode.ORIGINAL
    )
    assert export["readme"]["text"] == "# Test Repo"


def test_embedding_export_code_records():
    export = EmbeddingExporter().export(
        _make_repo_with_function(), EmbeddingMode.ORIGINAL
    )
    assert len(export["code_records"]) == 1
    assert export["code_records"][0]["source_code"] == "def process(): pass"
    assert export["code_records"][0]["id"] == "mymod.process"


def test_embedding_export_doc_records():
    export = EmbeddingExporter().export(
        _make_repo_with_function(), EmbeddingMode.ORIGINAL
    )
    assert len(export["doc_records"]) == 1
    assert export["doc_records"][0]["original_doc"] == "Process data."


def test_code_and_doc_ids_match():
    export = EmbeddingExporter().export(
        _make_repo_with_function(), EmbeddingMode.ORIGINAL
    )
    code_ids = {r["id"] for r in export["code_records"]}
    doc_ids = {r["id"] for r in export["doc_records"]}
    assert code_ids == doc_ids

from inspect4all.core.models import (
    Documentation,
    FileAnalysis,
    FileInfo,
    FunctionInfo,
    LicenseInfo,
    RepositoryAnalysis,
)
from inspect4all.output.json_reader import load_repository_analysis
from inspect4all.output.json_writer import JsonWriter


def _repo():
    func = FunctionInfo(
        name="foo",
        qualified_name="pkg.foo",
        documentation=Documentation(None, None, "Docs.", {}, None, [], {}),
        source_code="def foo(): pass",
        parameters=[],
        return_type="int",
        modifiers=[],
        annotations=[],
        calls=[],
        line_range=(3, 5),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )
    fa = FileAnalysis(
        file=FileInfo("pkg/m.py", "m.py", ".py", "Python", None, None, False),
        imports=[],
        types=[],
        functions=[func],
        main_info=None,
        language_specific={},
    )
    return RepositoryAnalysis(
        repo_path="/r",
        languages={"Python": 1},
        files=[fa],
        readme_files=[],
        directory_tree=[],
        dependencies=[],
        software_type="library",
        software_invocation=[],
        tests=[],
        license=LicenseInfo(detected=[], source_files=[], text=None),
        metadata={},
        call_graph={},
    )


def test_roundtrip_preserves_core_fields(tmp_path):
    JsonWriter(tmp_path).write(_repo())
    loaded = load_repository_analysis(tmp_path / "repository_analysis.json")
    assert loaded.repo_path == "/r"
    assert loaded.software_type == "library"
    assert loaded.languages == {"Python": 1}
    func = loaded.files[0].functions[0]
    assert func.qualified_name == "pkg.foo"
    assert func.line_range == (3, 5)  # list cast back to tuple
    assert func.documentation.full_text == "Docs."


def test_missing_optional_fields_default_to_none(tmp_path):
    JsonWriter(tmp_path).write(_repo())
    loaded = load_repository_analysis(tmp_path / "repository_analysis.json")
    # main_info was None and dropped by the writer; loader restores None.
    assert loaded.files[0].main_info is None

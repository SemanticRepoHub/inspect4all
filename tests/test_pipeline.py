from inspect4all.adapters import AdapterRegistry, build_default_registry
from inspect4all.core.models import RepositoryAnalysis
from inspect4all.pipeline import InspectionPipeline, InspectOptions


def test_pipeline_empty_repo(tmp_path):
    (tmp_path / "data.csv").write_text("a,b\n1,2")
    pipeline = InspectionPipeline(AdapterRegistry())
    result = pipeline.inspect(tmp_path, InspectOptions())
    assert result.files == []
    assert result.repo_path == str(tmp_path)


def test_pipeline_returns_repository_analysis(tmp_path):
    (tmp_path / "x.py").write_text("x=1")
    pipeline = InspectionPipeline(AdapterRegistry())
    result = pipeline.inspect(tmp_path, InspectOptions())
    assert isinstance(result, RepositoryAnalysis)


def test_pipeline_java_repo_end_to_end(tmp_path):
    """Regression: Java adapter must be callable through the pipeline's
    LanguageAdapter contract (previously its drifted signatures caused all
    Java files to be silently dropped and aggregation to crash)."""
    from inspect4all.adapters.java.adapter import JavaAdapter

    (tmp_path / "pom.xml").write_text("<project></project>")
    (tmp_path / "Hello.java").write_text(
        "package com.example;\n\n"
        "public class Hello {\n"
        "    public static void main(String[] args) {\n"
        '        System.out.println("hi");\n'
        "    }\n"
        "}\n"
    )
    pipeline = InspectionPipeline(AdapterRegistry(JavaAdapter()))
    result = pipeline.inspect(tmp_path, InspectOptions(all_features=True))
    assert len(result.files) == 1
    assert result.files[0].file.language == "Java"
    assert result.software_type == "application"


def test_pipeline_python_paths_are_repo_relative(tmp_path):
    """Regression: FileInfo.path and qualified names must be repo-relative,
    not derived from the absolute filesystem path."""
    from inspect4all.adapters.python.adapter import PythonAdapter

    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("def greet():\n    pass\n")
    pipeline = InspectionPipeline(AdapterRegistry(PythonAdapter()))
    result = pipeline.inspect(tmp_path, InspectOptions())
    assert len(result.files) == 1
    fa = result.files[0]
    assert fa.file.path == "mypkg/mod.py"
    assert fa.functions[0].qualified_name == "mypkg.mod.greet"


def test_pipeline_records_unhandled_files(tmp_path):
    """Source files whose language has no registered adapter are recorded in
    metadata (language -> repo-relative paths) so Phase 2 can analyse their
    prevalence."""
    from inspect4all.adapters.python.adapter import PythonAdapter

    (tmp_path / "main.py").write_text("x = 1\n")
    (tmp_path / "App.java").write_text("public class App {}\n")
    sub = tmp_path / "scripts"
    sub.mkdir()
    (sub / "Util.java").write_text("public class Util {}\n")
    pipeline = InspectionPipeline(AdapterRegistry(PythonAdapter()))
    result = pipeline.inspect(tmp_path, InspectOptions())
    unhandled = result.metadata["unhandled_files"]
    assert sorted(unhandled["Java"]) == ["App.java", "scripts/Util.java"]


def test_pipeline_extracts_git_metadata_when_enabled(tmp_path):
    import subprocess

    def git(*args):
        subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True
        )

    (tmp_path / "x.py").write_text("x = 1\n")
    git("init")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "T")
    git("add", ".")
    git("commit", "-m", "init")

    pipeline = InspectionPipeline(AdapterRegistry())
    result = pipeline.inspect(tmp_path, InspectOptions(extract_metadata=True))
    assert len(result.metadata["git"]["commit"]) == 40

    result_off = pipeline.inspect(
        tmp_path, InspectOptions(extract_metadata=False)
    )
    assert "git" not in result_off.metadata


def test_pipeline_git_metadata_absent_for_non_git_repo(tmp_path):
    (tmp_path / "x.py").write_text("x = 1\n")
    pipeline = InspectionPipeline(AdapterRegistry())
    result = pipeline.inspect(tmp_path, InspectOptions(extract_metadata=True))
    assert "git" not in result.metadata


def test_adapter_registry_register_and_get():
    from unittest.mock import MagicMock

    from inspect4all.core.interfaces import LanguageAdapter

    registry = AdapterRegistry()
    adapter = MagicMock(spec=LanguageAdapter)
    adapter.language_name = "Python"
    registry.register(adapter)
    assert registry.get("Python") is adapter
    assert registry.get("Java") is None


def test_adapter_registry_supported_languages():
    from unittest.mock import MagicMock

    registry = AdapterRegistry()
    for lang in ["Python", "Java"]:
        a = MagicMock()
        a.language_name = lang
        registry.register(a)
    assert set(registry.supported_languages()) == {"Python", "Java"}


def test_adapter_registry_constructor_registers_adapters():
    from unittest.mock import MagicMock

    a, b = MagicMock(), MagicMock()
    a.language_name = "Python"
    b.language_name = "Java"
    registry = AdapterRegistry(a, b)
    assert registry.get("Python") is a
    assert dict(registry.items()) == {"Python": a, "Java": b}


def test_build_default_registry_has_python_and_java():
    registry = build_default_registry()
    assert set(registry.supported_languages()) == {"Python", "Java"}


def test_pipeline_mixed_language_repo(tmp_path):
    """A repo containing both Python and Java is dispatched per language:
    each file group goes to its registered adapter in the same run."""
    (tmp_path / "app.py").write_text("def greet():\n    pass\n")
    (tmp_path / "App.java").write_text(
        "package com.example;\n\n"
        "public class App {\n"
        "    public void run() {\n"
        "    }\n"
        "}\n"
    )
    pipeline = InspectionPipeline(build_default_registry())
    result = pipeline.inspect(tmp_path, InspectOptions())
    langs = {fa.file.language for fa in result.files}
    assert langs == {"Python", "Java"}
    assert result.metadata["unhandled_files"] == {}


def test_inspect_options_importable_from_core():
    """InspectOptions lives in core so analysis-layer modules can type
    against it without importing the pipeline (which would be circular)."""
    from inspect4all.core.options import InspectOptions as CoreOptions

    assert CoreOptions is InspectOptions


def test_pipeline_records_parse_failures(tmp_path):
    """Files the adapter cannot parse (e.g. post-Java-8 syntax javalang
    chokes on) are recorded in metadata['parse_failures'] as repo-relative
    paths per language, while parseable files are still analysed."""
    from inspect4all.adapters.java.adapter import JavaAdapter

    (tmp_path / "Point.java").write_text(
        "package com.example;\n\npublic record Point(int x, int y) {}\n"
    )
    (tmp_path / "Hello.java").write_text(
        "package com.example;\n\npublic class Hello {}\n"
    )
    pipeline = InspectionPipeline(AdapterRegistry(JavaAdapter()))
    result = pipeline.inspect(tmp_path, InspectOptions())
    assert result.metadata["parse_failures"] == {"Java": ["Point.java"]}
    assert [fa.file.path for fa in result.files] == ["Hello.java"]


def test_pipeline_no_parse_failures_key_when_clean(tmp_path):
    """A repo without parse failures gets no parse_failures key."""
    (tmp_path / "x.py").write_text("x = 1\n")
    pipeline = InspectionPipeline(build_default_registry())
    result = pipeline.inspect(tmp_path, InspectOptions())
    assert "parse_failures" not in result.metadata


def test_pipeline_extract_dependencies_gate(tmp_path):
    from inspect4all.adapters.python.adapter import PythonAdapter

    (tmp_path / "app.py").write_text("import requests\n")
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
    pipeline = InspectionPipeline(AdapterRegistry(PythonAdapter()))

    off = pipeline.inspect(tmp_path, InspectOptions(extract_dependencies=False))
    assert off.dependencies == []

    on = pipeline.inspect(tmp_path, InspectOptions(extract_dependencies=True))
    assert len(on.dependencies) > 0


def test_pipeline_detect_software_type_gate(tmp_path):
    from inspect4all.adapters.python.adapter import PythonAdapter

    (tmp_path / "main.py").write_text("def main():\n    pass\n")
    pipeline = InspectionPipeline(AdapterRegistry(PythonAdapter()))

    off = pipeline.inspect(tmp_path, InspectOptions(detect_software_type=False))
    assert off.software_type == "unknown"
    assert off.software_invocation == []

    on = pipeline.inspect(tmp_path, InspectOptions(detect_software_type=True))
    assert on.software_type != "unknown"


def test_pipeline_extract_license_gate(tmp_path):
    (tmp_path / "LICENSE").write_text(
        "MIT License\n\nCopyright (c) 2024 Test\n"
    )
    pipeline = InspectionPipeline(AdapterRegistry())

    off = pipeline.inspect(tmp_path, InspectOptions(extract_license=False))
    assert off.license.detected == []
    assert off.license.source_files == []

    on = pipeline.inspect(tmp_path, InspectOptions(extract_license=True))
    assert on.license.source_files != []


def test_pipeline_extract_readme_gate(tmp_path):
    (tmp_path / "README.md").write_text("# My Project\n")
    pipeline = InspectionPipeline(AdapterRegistry())

    off = pipeline.inspect(tmp_path, InspectOptions(extract_readme=False))
    assert off.readme_files == []

    on = pipeline.inspect(tmp_path, InspectOptions(extract_readme=True))
    assert len(on.readme_files) == 1
    assert on.readme_files[0].path == "README.md"

import json

from inspect4all.core.models import LicenseInfo, RepositoryAnalysis
from inspect4all.output.json_writer import JsonWriter


def _make_repo() -> RepositoryAnalysis:
    return RepositoryAnalysis(
        repo_path="/tmp/test",
        languages={"Python": 1},
        files=[],
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


def test_writes_repository_analysis_json(tmp_path):
    writer = JsonWriter(output_dir=tmp_path)
    writer.write(_make_repo())
    out = tmp_path / "repository_analysis.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["repository"]["path"] == "/tmp/test"
    assert data["repository"]["languages"] == {"Python": 1}


def test_json_is_valid(tmp_path):
    writer = JsonWriter(output_dir=tmp_path)
    writer.write(_make_repo())
    data = json.loads((tmp_path / "repository_analysis.json").read_text())
    assert isinstance(data, dict)


def test_returns_output_path(tmp_path):
    writer = JsonWriter(output_dir=tmp_path)
    result = writer.write(_make_repo())
    assert result.name == "repository_analysis.json"
    assert result.exists()

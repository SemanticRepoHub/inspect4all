from inspect4all.adapters.python.dependencies import PythonDependencyExtractor


def test_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "requests>=2.28\npandas\n# comment\n"
    )
    deps = PythonDependencyExtractor().extract(tmp_path)
    names = {d.name for d in deps}
    assert "requests" in names
    assert "pandas" in names
    assert all(d.language == "Python" for d in deps)
    assert all(d.scope == "runtime" for d in deps)


def test_pyproject_toml(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = [\n    "click>=8.0",\n    "pydantic>=2.0",\n]\n'
    )
    deps = PythonDependencyExtractor().extract(tmp_path)
    names = {d.name for d in deps}
    assert "click" in names


def test_no_dependency_files(tmp_path):
    deps = PythonDependencyExtractor().extract(tmp_path)
    assert deps == []

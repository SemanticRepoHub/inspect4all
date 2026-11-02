import pytest

from inspect4all.adapters.python.adapter import PythonAdapter

SOURCE = '''"""Module for data processing."""
import os
from typing import Optional


class DataProcessor:
    """Process raw data."""

    def __init__(self, root: str) -> None:
        self.root = root

    def process(self, name: str) -> Optional[dict]:
        """Process a named dataset.

        Args:
            name: Dataset identifier.

        Returns:
            Processed result.
        """
        path = os.path.join(self.root, name)
        return {"path": path}


def helper(x: int) -> int:
    """Help with x."""
    return x + 1
'''


@pytest.fixture
def adapter():
    return PythonAdapter()


def test_adapter_language_name(adapter):
    assert adapter.language_name == "Python"


def test_adapter_file_extensions(adapter):
    assert ".py" in adapter.file_extensions


def test_parse_file(adapter, tmp_path):
    f = tmp_path / "proc.py"
    f.write_text(SOURCE)
    result = adapter.parse_file(f)
    assert result.tree is not None
    assert "DataProcessor" in result.source


def test_extract_full_file(adapter, tmp_path):
    f = tmp_path / "proc.py"
    f.write_text(SOURCE)
    parsed = adapter.parse_file(f)
    analysis = adapter.extract_file_analysis(parsed, tmp_path)

    assert analysis.file.language == "Python"
    assert len(analysis.types) == 1
    assert analysis.types[0].name == "DataProcessor"
    assert len(analysis.types[0].methods) == 2  # __init__ + process
    assert len(analysis.functions) == 1
    assert analysis.functions[0].name == "helper"
    assert len(analysis.imports) >= 1


def test_source_code_always_present(adapter, tmp_path):
    f = tmp_path / "proc.py"
    f.write_text(SOURCE)
    parsed = adapter.parse_file(f)
    analysis = adapter.extract_file_analysis(parsed, tmp_path)
    for func in analysis.all_functions():
        assert func.source_code is not None


def test_documentation_extracted(adapter, tmp_path):
    f = tmp_path / "proc.py"
    f.write_text(SOURCE)
    parsed = adapter.parse_file(f)
    analysis = adapter.extract_file_analysis(parsed, tmp_path)
    process_method = next(
        m for m in analysis.types[0].methods if m.name == "process"
    )
    assert process_method.documentation is not None
    assert process_method.documentation.short_description is not None
    assert "name" in process_method.documentation.params

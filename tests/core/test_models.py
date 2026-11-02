from __future__ import annotations

from inspect4all.core.models import (
    Documentation,
    Enrichment,
    FileAnalysis,
    FileInfo,
    FunctionInfo,
    TypeInfo,
)


def test_function_info_defaults():
    func = FunctionInfo(
        name="process",
        qualified_name="mymod.process",
        documentation=None,
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
    assert func.name == "process"
    assert func.is_constructor is False


def test_file_analysis_all_functions():
    method = FunctionInfo(
        name="method1",
        qualified_name="mod.Cls.method1",
        documentation=None,
        source_code="def method1(self): pass",
        parameters=[],
        return_type=None,
        modifiers=[],
        annotations=[],
        calls=[],
        line_range=(5, 7),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )
    top_func = FunctionInfo(
        name="func1",
        qualified_name="mod.func1",
        documentation=None,
        source_code="def func1(): pass",
        parameters=[],
        return_type=None,
        modifiers=[],
        annotations=[],
        calls=[],
        line_range=(10, 12),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )
    type_info = TypeInfo(
        kind="class",
        name="Cls",
        qualified_name="mod.Cls",
        documentation=None,
        source_code=None,
        base_classes=[],
        interfaces=[],
        modifiers=[],
        annotations=[],
        fields=[],
        methods=[method],
        line_range=(1, 8),
        language_specific={},
    )
    file_info = FileInfo(
        path="mod.py",
        name="mod",
        extension=".py",
        language="Python",
        package="mod",
        documentation=None,
        is_test=False,
    )
    file = FileAnalysis(
        file=file_info,
        imports=[],
        types=[type_info],
        functions=[top_func],
        main_info=None,
        language_specific={},
    )
    all_funcs = file.all_functions()
    assert len(all_funcs) == 2
    assert {f.name for f in all_funcs} == {"method1", "func1"}


def test_documentation_enrichments():
    doc = Documentation(
        short_description="Test doc",
        long_description=None,
        full_text="Test doc",
        params={},
        returns=None,
        raises=[],
        tags={},
        enrichments=[
            Enrichment(
                source="docstring_enricher",
                timestamp="2026-01-01T00:00:00Z",
                model="test-model",
                content={"short_description": "Enhanced"},
                confidence=0.9,
            )
        ],
    )
    assert doc.short_description == "Test doc"
    assert len(doc.enrichments) == 1
    assert doc.enrichments[0].confidence == 0.9


def test_all_functions_includes_nested():
    def _func(name, qname, nested):
        return FunctionInfo(
            name=name,
            qualified_name=qname,
            documentation=None,
            source_code=None,
            parameters=[],
            return_type=None,
            modifiers=[],
            annotations=[],
            calls=[],
            line_range=(1, 1),
            is_constructor=False,
            nested_functions=nested,
            language_specific={},
        )

    inner = _func("inner", "mod.outer.inner", [])
    outer = _func("outer", "mod.outer", [inner])
    file_info = FileInfo(
        path="mod.py",
        name="mod",
        extension=".py",
        language="Python",
        package="mod",
        documentation=None,
        is_test=False,
    )
    file = FileAnalysis(
        file=file_info,
        imports=[],
        types=[],
        functions=[outer],
        main_info=None,
        language_specific={},
    )
    names = {f.qualified_name for f in file.all_functions()}
    assert names == {"mod.outer", "mod.outer.inner"}

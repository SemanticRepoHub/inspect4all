from inspect4all.core.models import (
    Documentation,
    FileAnalysis,
    FileInfo,
    FunctionInfo,
    ParameterInfo,
    RepositoryAnalysis,
)
from inspect4all.enrichment.targets import (
    _strip_python_docstring,
    select_all,
    select_undocumented,
)


def _func(name, doc, source="def x(): pass"):
    return FunctionInfo(
        name=name,
        qualified_name=name,
        documentation=doc,
        source_code=source,
        parameters=[
            ParameterInfo("a", "int", None, False, []),
        ],
        return_type="int",
        modifiers=[],
        annotations=[],
        calls=[],
        line_range=(1, 2),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )


def _repo(functions):
    fa = FileAnalysis(
        file=FileInfo("pkg/m.py", "m.py", ".py", "Python", None, None, False),
        imports=[],
        types=[],
        functions=functions,
        main_info=None,
        language_specific={},
    )
    return RepositoryAnalysis(
        repo_path="/r",
        languages={},
        files=[fa],
        readme_files=[],
        directory_tree=[],
        dependencies=[],
        software_type="",
        software_invocation=[],
        tests=[],
        license=None,
        metadata={},
        call_graph={},
    )


def _doc(full_text):
    return Documentation(None, None, full_text, {}, None, [], {})


def test_selects_only_undocumented():
    repo = _repo([_func("foo", None), _func("bar", _doc("has docs"))])
    result = select_undocumented(repo)
    assert list(result.keys()) == ["pkg/m.py"]
    ids = [t.record_id for t in result["pkg/m.py"]]
    assert ids == ["pkg/m.py::foo"]


def test_empty_full_text_counts_as_undocumented():
    repo = _repo([_func("foo", _doc(""))])
    result = select_undocumented(repo)
    assert result["pkg/m.py"][0].qualified_name == "foo"


def test_skips_records_without_source():
    repo = _repo([_func("foo", None, source=None)])
    assert select_undocumented(repo) == {}


def test_signature_includes_params_and_return():
    repo = _repo([_func("foo", None)])
    sig = repo and select_undocumented(repo)["pkg/m.py"][0].signature
    assert "foo" in sig and "int" in sig


def test_select_all_includes_documented():
    repo = _repo([_func("foo", _doc("has docs"))])
    result = select_all(repo)
    assert list(result.keys()) == ["pkg/m.py"]
    assert result["pkg/m.py"][0].record_id == "pkg/m.py::foo"


def test_select_all_includes_both_documented_and_undocumented():
    repo = _repo([_func("foo", None), _func("bar", _doc("has docs"))])
    result = select_all(repo)
    ids = {t.record_id for t in result["pkg/m.py"]}
    assert ids == {"pkg/m.py::foo", "pkg/m.py::bar"}


def test_select_all_still_skips_no_source():
    repo = _repo([_func("foo", _doc("has docs"), source=None)])
    assert select_all(repo) == {}


def test_select_all_supersets_select_undocumented():
    repo = _repo([_func("foo", None), _func("bar", _doc("has docs"))])
    undoc = {t.record_id for t in select_undocumented(repo).get("pkg/m.py", [])}
    all_ = {t.record_id for t in select_all(repo).get("pkg/m.py", [])}
    assert undoc < all_


# ---------------------------------------------------------------------------
# Python docstring stripping
# ---------------------------------------------------------------------------

_DOUBLE_DOC = 'def foo():\n    """Summary line."""\n    return 1'
_SINGLE_DOC = "def foo():\n    '''Summary line.'''\n    return 1"
_NO_DOC = "def foo():\n    return 1"
_MULTILINE_DOC = (
    'def foo():\n    """First line.\n\n    More detail.\n    """\n    return 1'
)
_ANNOTATED_PARAMS = 'def foo(a: int, b: str):\n    """Doc."""\n    return 1'
_DICT_ANNOTATION = 'def foo(a: dict[str, int]):\n    """Doc."""\n    return 1'
_ASYNC_DEF = 'async def foo():\n    """Doc."""\n    return 1'
_MULTILINE_SIG = 'def foo(\n    a: int,\n    b: str,\n) -> None:\n    """Doc."""\n    return 1'
_NESTED_ASYNC = (
    'async def foo(a: dict[str, int]) -> None:\n    """Doc."""\n    return 1'
)


def test_strip_removes_double_quoted_docstring():
    result = _strip_python_docstring(_DOUBLE_DOC)
    assert '"""' not in result
    assert "return 1" in result


def test_strip_removes_single_quoted_docstring():
    result = _strip_python_docstring(_SINGLE_DOC)
    assert "'''" not in result
    assert "return 1" in result


def test_strip_is_noop_when_no_docstring():
    assert _strip_python_docstring(_NO_DOC) == _NO_DOC


def test_strip_removes_multiline_docstring():
    result = _strip_python_docstring(_MULTILINE_DOC)
    assert '"""' not in result
    assert "return 1" in result


def test_strip_annotated_params():
    # first ':' inside 'a: int' must not be mistaken for the signature colon
    result = _strip_python_docstring(_ANNOTATED_PARAMS)
    assert '"""' not in result
    assert "return 1" in result


def test_strip_dict_annotation():
    # 'dict[str, int]' contains both '[' and ':' — bracket depth must be tracked
    result = _strip_python_docstring(_DICT_ANNOTATION)
    assert '"""' not in result
    assert "return 1" in result


def test_strip_async_def():
    result = _strip_python_docstring(_ASYNC_DEF)
    assert '"""' not in result
    assert "return 1" in result


def test_strip_multiline_signature():
    result = _strip_python_docstring(_MULTILINE_SIG)
    assert '"""' not in result
    assert "return 1" in result


def test_strip_nested_async_with_annotation():
    result = _strip_python_docstring(_NESTED_ASYNC)
    assert '"""' not in result
    assert "return 1" in result


def _py_func(name, doc, source):
    return FunctionInfo(
        name=name,
        qualified_name=name,
        documentation=doc,
        source_code=source,
        parameters=[],
        return_type=None,
        modifiers=[],
        annotations=[],
        calls=[],
        line_range=(1, 3),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )


def _py_repo(functions, language="Python"):
    fa = FileAnalysis(
        file=FileInfo("pkg/m.py", "m.py", ".py", language, None, None, False),
        imports=[],
        types=[],
        functions=functions,
        main_info=None,
        language_specific={},
    )
    return RepositoryAnalysis(
        repo_path="/r",
        languages={},
        files=[fa],
        readme_files=[],
        directory_tree=[],
        dependencies=[],
        software_type="",
        software_invocation=[],
        tests=[],
        license=None,
        metadata={},
        call_graph={},
    )


def test_select_all_strips_python_docstring_from_source_code():
    """Documented Python functions must have docstring stripped before enrichment."""
    func = _py_func("foo", _doc("Summary line."), _DOUBLE_DOC)
    repo = _py_repo([func])
    targets = select_all(repo)["pkg/m.py"]
    assert len(targets) == 1
    assert '"""' not in targets[0].source_code
    assert "return 1" in targets[0].source_code


def test_select_undocumented_strip_is_noop_for_python():
    """Undocumented Python functions have no docstring to strip."""
    func = _py_func("foo", None, _NO_DOC)
    repo = _py_repo([func])
    targets = select_undocumented(repo)["pkg/m.py"]
    assert targets[0].source_code == _NO_DOC


def test_java_source_code_not_stripped():
    """Java source_code is passed through unchanged (Javadoc is never in source_code)."""
    java_source = "public void foo() {\n    return;\n}"
    fa = FileAnalysis(
        file=FileInfo(
            "Foo.java", "Foo.java", ".java", "Java", None, None, False
        ),
        imports=[],
        types=[],
        functions=[_py_func("foo", None, java_source)],
        main_info=None,
        language_specific={},
    )
    repo = RepositoryAnalysis(
        repo_path="/r",
        languages={},
        files=[fa],
        readme_files=[],
        directory_tree=[],
        dependencies=[],
        software_type="",
        software_invocation=[],
        tests=[],
        license=None,
        metadata={},
        call_graph={},
    )
    targets = select_undocumented(repo)["Foo.java"]
    assert targets[0].source_code == java_source

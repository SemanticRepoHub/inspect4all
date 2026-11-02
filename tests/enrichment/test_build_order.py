from inspect4all.core.models import (
    FileAnalysis,
    FileInfo,
    FunctionInfo,
    RepositoryAnalysis,
)
from inspect4all.enrichment.build_order import build_order, resolve_call_edges


def _func(qname, calls=()):
    name = qname.split(".")[-1]
    return FunctionInfo(
        name=name,
        qualified_name=qname,
        documentation=None,
        source_code=f"def {name}(): pass",
        parameters=[],
        return_type=None,
        modifiers=[],
        annotations=[],
        calls=list(calls),
        line_range=(1, 1),
        is_constructor=False,
        nested_functions=[],
        language_specific={},
    )


def _file(path, functions):
    return FileAnalysis(
        file=FileInfo(path, path, ".py", "Python", None, None, False),
        imports=[],
        types=[],
        functions=functions,
        main_info=None,
        language_specific={},
    )


def _repo(files, call_graph=None):
    if call_graph is None:
        call_graph = {}
        for fa in files:
            for f in fa.all_functions():
                if f.calls:
                    call_graph[f.qualified_name] = f.calls
    return RepositoryAnalysis(
        repo_path="/r",
        languages={},
        files=files,
        readme_files=[],
        directory_tree=[],
        dependencies=[],
        software_type="",
        software_invocation=[],
        tests=[],
        license=None,
        metadata={},
        call_graph=call_graph,
    )


def test_exact_qualified_name_resolves():
    repo = _repo(
        [
            _file(
                "a.py", [_func("pkg.helper"), _func("pkg.main", ["pkg.helper"])]
            )
        ]
    )
    edges = resolve_call_edges(repo)
    assert edges["a.py::pkg.main"] == ["a.py::pkg.helper"]


def test_unique_last_segment_resolves():
    repo = _repo(
        [
            _file("a.py", [_func("pkg.util.helper")]),
            _file("b.py", [_func("pkg.main", ["helper"])]),
        ]
    )
    edges = resolve_call_edges(repo)
    assert edges["b.py::pkg.main"] == ["a.py::pkg.util.helper"]


def test_ambiguous_suffix_dropped_unless_same_file():
    repo = _repo(
        [
            _file("a.py", [_func("a.helper")]),
            _file("b.py", [_func("b.helper"), _func("b.main", ["helper"])]),
            _file("c.py", [_func("c.main", ["helper"])]),
        ]
    )
    edges = resolve_call_edges(repo)
    # b.main: two candidates, but one shares its file -> same-file wins.
    assert edges["b.py::b.main"] == ["b.py::b.helper"]
    # c.main: two candidates, none in c.py -> dropped.
    assert edges.get("c.py::c.main", []) == []


def test_builtins_and_self_edges_dropped():
    repo = _repo([_file("a.py", [_func("pkg.f", ["print", "len", "pkg.f"])])])
    assert resolve_call_edges(repo).get("a.py::pkg.f", []) == []


def test_callee_ordered_before_caller():
    edges = {"m": ["h"], "h": []}
    assert build_order(["m", "h"], edges) == ["h", "m"]


def test_order_only_considers_given_targets():
    # 'x' is an edge target but not in targets: ignored, no KeyError.
    edges = {"m": ["h", "x"], "h": ["x"]}
    assert build_order(["m", "h"], edges) == ["h", "m"]


def test_cycle_breaks_and_yields_all_nodes():
    edges = {"a": ["b"], "b": ["a"], "c": []}
    order = build_order(["a", "b", "c"], edges)
    assert sorted(order) == ["a", "b", "c"]
    assert order[0] == "c"  # acyclic node first


def test_order_is_deterministic():
    edges = {"a": [], "b": [], "c": []}
    assert build_order(["c", "a", "b"], edges) == build_order(
        ["b", "c", "a"], edges
    )

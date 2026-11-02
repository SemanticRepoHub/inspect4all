from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inspect4all.core.models import FileAnalysis


def build_call_graph(file_analyses: list[FileAnalysis]) -> dict:
    graph: dict[str, list[str]] = {}
    for fa in file_analyses:
        for func in fa.all_functions():
            if func.calls:
                graph[func.qualified_name] = func.calls
    return graph

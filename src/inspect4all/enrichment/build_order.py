from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inspect4all.core.models import RepositoryAnalysis


def _function_index(repo: RepositoryAnalysis) -> dict[str, str]:
    """Map qualified_name -> record_id for every function in the repo."""
    index: dict[str, str] = {}
    for fa in repo.files:
        for func in fa.all_functions():
            index[func.qualified_name] = (
                f"{fa.file.path}::{func.qualified_name}"
            )
    return index


def resolve_call_edges(repo: RepositoryAnalysis) -> dict[str, list[str]]:
    """Resolve raw call names to in-project callee record_ids per caller.

    Resolution per call name: exact qualified-name match; else a unique
    match on the last dotted segment; else, among ambiguous candidates,
    the one defined in the caller's own file if exactly one is. Anything
    else (builtins, stdlib, unresolvable) is dropped, as are self-edges.
    """
    by_qname = _function_index(repo)
    by_last: dict[str, list[str]] = {}
    for qname, record_id in by_qname.items():
        by_last.setdefault(qname.split(".")[-1], []).append(record_id)

    edges: dict[str, list[str]] = {}
    for caller_qname, calls in (repo.call_graph or {}).items():
        caller_id = by_qname.get(caller_qname)
        if caller_id is None:
            continue
        caller_file = caller_id.split("::", 1)[0]
        resolved: list[str] = []
        for call in calls:
            callee_id = _resolve_one(call, caller_file, by_qname, by_last)
            if callee_id is not None and callee_id != caller_id:
                resolved.append(callee_id)
        edges[caller_id] = resolved
    return edges


def _resolve_one(
    call: str,
    caller_file: str,
    by_qname: dict[str, str],
    by_last: dict[str, list[str]],
) -> str | None:
    if call in by_qname:
        return by_qname[call]
    candidates = by_last.get(call.split(".")[-1], [])
    if len(candidates) == 1:
        return candidates[0]
    same_file = [c for c in candidates if c.split("::", 1)[0] == caller_file]
    if len(same_file) == 1:
        return same_file[0]
    return None


def build_order(
    target_ids: list[str], edges: dict[str, list[str]]
) -> list[str]:
    """Order targets callees-first; break cycles by fewest unmet deps.

    Only edges between the given targets are considered. Deterministic:
    ties are broken by sorted record_id.
    """
    targets = set(target_ids)
    pending = {
        t: {c for c in edges.get(t, []) if c in targets and c != t}
        for t in sorted(targets)
    }
    order: list[str] = []
    while pending:
        ready = sorted(t for t, deps in pending.items() if not deps)
        if not ready:
            # Cycle: emit the node with fewest unmet deps (stable pick).
            ready = [min(pending, key=lambda t: (len(pending[t]), t))]
        for t in ready:
            order.append(t)
            del pending[t]
        done = set(order)
        for deps in pending.values():
            deps -= done
    return order

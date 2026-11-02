from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from inspect4all.core.interfaces import EnrichmentProcessor
from inspect4all.core.models import Documentation, Enrichment
from inspect4all.enrichment.build_order import (
    build_order,
    resolve_call_edges,
)
from inspect4all.enrichment.cache import (
    append_cache,
    content_hash,
    load_cache_full,
)
from inspect4all.enrichment.generate import generate_docstring
from inspect4all.enrichment.targets import (
    DocstringTarget,
    select_all,
    select_undocumented,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from inspect4all.core.models import FunctionInfo, RepositoryAnalysis

logger = logging.getLogger(__name__)


class DocstringEnricher(EnrichmentProcessor):
    """LLM docstring enrichment for undocumented functions and methods.

    Generates bottom-up over the call graph: callees are documented
    before their callers, and each generation call receives the (already
    extracted or freshly generated) docstrings of the record's resolved
    in-project callees as context.
    """

    def __init__(
        self,
        model: BaseChatModel,
        model_id: str,
        cache_path: Path | None = None,
        max_records: int | None = None,
        docstring_target: str = "undocumented",
    ):
        self._model = model
        self._model_id = model_id
        self._cache_path = cache_path or Path("enrichment_cache.jsonl")
        self._max_records = max_records
        self._docstring_target = docstring_target
        self.stats: dict[str, int] = {
            "enriched": 0,
            "failed": 0,
            "skipped": 0,
        }

    @property
    def name(self) -> str:
        return "docstring_enricher"

    def _select(
        self, repo: RepositoryAnalysis
    ) -> dict[str, list[DocstringTarget]]:
        if self._docstring_target == "all":
            return select_all(repo)
        return select_undocumented(repo)

    def is_applicable(self, repo: RepositoryAnalysis) -> bool:
        return bool(self._select(repo))

    def enrich(self, repo: RepositoryAnalysis) -> RepositoryAnalysis:
        cached = load_cache_full(self._cache_path)
        func_index = self._build_func_index(repo)
        docs_by_id = self._known_docs(func_index)

        targets_by_id: dict[str, DocstringTarget] = {}
        for targets in self._select(repo).values():
            for target in targets:
                targets_by_id[target.record_id] = target

        def _is_fresh(rid: str) -> bool:
            entry = cached.get(rid)
            return (
                entry is not None
                and entry["status"] == "ok"
                and entry["hash"]
                == content_hash(targets_by_id[rid].source_code)
            )

        pending = [rid for rid in targets_by_id if not _is_fresh(rid)]
        self.stats["skipped"] += len(targets_by_id) - len(pending)
        if self._max_records is not None:
            pending = pending[: self._max_records]
        if not pending:
            return repo

        edges = resolve_call_edges(repo)
        order = build_order(pending, edges)
        total = len(order)
        logger.info("%d records to enrich", total)
        for i, record_id in enumerate(order):
            logger.info("[%*d/%d] %s", len(str(total)), i + 1, total, record_id)
            target = targets_by_id[record_id]
            callee_docs = {
                callee_id.split("::", 1)[1]: docs_by_id[callee_id]
                for callee_id in edges.get(record_id, [])
                if callee_id in docs_by_id
            }
            t0 = time.perf_counter()
            content = generate_docstring(self._model, target, callee_docs)
            elapsed = time.perf_counter() - t0
            if content is None:
                append_cache(
                    self._cache_path,
                    record_id,
                    content_hash(target.source_code),
                    "failed",
                    elapsed_s=elapsed,
                )
                self.stats["failed"] += 1
                continue
            self._attach(func_index[record_id], content)
            docs_by_id[record_id] = content["short_description"]
            append_cache(
                self._cache_path,
                record_id,
                content_hash(target.source_code),
                "ok",
                elapsed_s=elapsed,
            )
            self.stats["enriched"] += 1
        return repo

    def _attach(self, func: FunctionInfo, content: dict) -> None:
        enrichment = Enrichment(
            source="docstring_enricher",
            timestamp=datetime.now(UTC).isoformat(),
            model=self._model_id,
            content=content,
            confidence=None,
        )
        if func.documentation is None:
            func.documentation = Documentation(
                short_description=None,
                long_description=None,
                full_text=None,
                params={},
                returns=None,
                raises=[],
                tags={},
                enrichments=[enrichment],
            )
        else:
            existing = func.documentation.enrichments or []
            func.documentation.enrichments = [*existing, enrichment]

    def _build_func_index(
        self, repo: RepositoryAnalysis
    ) -> dict[str, FunctionInfo]:
        index: dict[str, FunctionInfo] = {}
        for fa in repo.files:
            for func in fa.all_functions():
                index[f"{fa.file.path}::{func.qualified_name}"] = func
        return index

    def _known_docs(
        self, func_index: dict[str, FunctionInfo]
    ) -> dict[str, str]:
        """One-line docs for already-documented functions (callee context).

        Prefers prior enrichments (rerun accumulation), then the extracted
        short description, then the first line of the extracted full text.
        """
        docs: dict[str, str] = {}
        for record_id, func in func_index.items():
            doc = func.documentation
            if doc is None:
                continue
            if doc.enrichments:
                generated = doc.enrichments[-1].content.get("short_description")
                if generated:
                    docs[record_id] = generated
                    continue
            if doc.short_description:
                docs[record_id] = doc.short_description
            elif doc.full_text:
                docs[record_id] = doc.full_text.strip().splitlines()[0]
        return docs

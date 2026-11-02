from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from inspect4all.core.constants import EmbeddingMode
from inspect4all.enrichment.docstring_enricher import DocstringEnricher
from inspect4all.enrichment.java_gap_backfill import JavaGapBackfillEnricher
from inspect4all.enrichment.pipeline import EnrichmentPipeline
from inspect4all.output.embedding_export import EmbeddingExporter
from inspect4all.output.json_reader import load_repository_analysis
from inspect4all.output.json_writer import JsonWriter

if TYPE_CHECKING:
    from pathlib import Path

    from langchain_core.language_models import BaseChatModel

    from inspect4all.core.interfaces import EnrichmentProcessor
    from inspect4all.core.models import RepositoryAnalysis


@dataclass(frozen=True)
class EnrichmentResult:
    """Combined outcome of one enrichment pass across all processors."""

    stats: dict[str, int]


_ALL_PROCESSORS = ("docstrings", "java-backfill")


def enrich_repo(
    repo: RepositoryAnalysis,
    *,
    model: BaseChatModel,
    model_id: str,
    cache_path: Path,
    max_records: int | None = None,
    processors: tuple[str, ...] = _ALL_PROCESSORS,
    docstring_target: str = "undocumented",
) -> EnrichmentResult:
    """Enrich an in-memory RepositoryAnalysis in place.

    `processors` selects which enrichers run: any subset of
    ("docstrings", "java-backfill"). Defaults to both.
    `docstring_target` controls which functions the docstring enricher
    considers: "undocumented" (default) or "all" (including documented).
    Returns the combined stats across active processors.
    """
    active: list[EnrichmentProcessor] = []
    if "docstrings" in processors:
        active.append(
            DocstringEnricher(
                model=model,
                model_id=model_id,
                cache_path=cache_path,
                max_records=max_records,
                docstring_target=docstring_target,
            )
        )
    if "java-backfill" in processors:
        active.append(
            JavaGapBackfillEnricher(
                model=model,
                model_id=model_id,
                cache_path=cache_path,
                max_records=max_records,
            )
        )
    EnrichmentPipeline(active).run(repo)
    stats = {"enriched": 0, "failed": 0, "skipped": 0}
    for processor in active:
        for key in stats:
            stats[key] += processor.stats[key]
    return EnrichmentResult(stats=stats)


def write_enriched_outputs(
    output_dir: Path,
    repo: RepositoryAnalysis,
    mode: EmbeddingMode,
) -> None:
    """Write repository_analysis.enriched.json + embedding_export.enriched.json."""
    JsonWriter(output_dir).write(
        repo, filename="repository_analysis.enriched.json"
    )
    export = EmbeddingExporter().export(repo, mode)
    (output_dir / "embedding_export.enriched.json").write_text(
        json.dumps(export, indent=2, default=str)
    )


def run_enrichment(
    input_dir: Path,
    *,
    model: BaseChatModel,
    model_id: str,
    max_records: int | None = None,
    mode: EmbeddingMode = EmbeddingMode.ENRICHED,
    processors: tuple[str, ...] = _ALL_PROCESSORS,
    docstring_target: str = "undocumented",
) -> EnrichmentResult:
    """Two-stage enrich: load prior analysis from disk, enrich, write outputs.

    Resumes from repository_analysis.enriched.json when present so that
    enrichments from earlier passes accumulate instead of being dropped
    (cached-ok records are skipped and would otherwise lose their output).
    """
    enriched_path = input_dir / "repository_analysis.enriched.json"
    source = (
        enriched_path
        if enriched_path.exists()
        else input_dir / "repository_analysis.json"
    )
    repo = load_repository_analysis(source)
    result = enrich_repo(
        repo,
        model=model,
        model_id=model_id,
        cache_path=input_dir / "enrichment_cache.jsonl",
        max_records=max_records,
        processors=processors,
        docstring_target=docstring_target,
    )
    write_enriched_outputs(input_dir, repo, mode)
    return result

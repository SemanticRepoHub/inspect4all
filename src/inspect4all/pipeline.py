from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from inspect4all.core.options import InspectOptions
from inspect4all.discovery.scanner import RepositoryScanner

if TYPE_CHECKING:
    from pathlib import Path

    from inspect4all.adapters import AdapterRegistry
    from inspect4all.core.interfaces import EnrichmentProcessor
    from inspect4all.core.models import FileAnalysis, RepositoryAnalysis

__all__ = ["InspectOptions", "InspectionPipeline"]

logger = logging.getLogger(__name__)


class InspectionPipeline:
    def __init__(
        self,
        registry: AdapterRegistry,
        enrichment_processors: list[EnrichmentProcessor] | None = None,
        scanner: RepositoryScanner | None = None,
    ):
        self._registry = registry
        self._processors = enrichment_processors or []
        self._scanner = scanner or RepositoryScanner()

    def inspect(
        self,
        repo_path: Path,
        options: InspectOptions | None = None,
    ) -> RepositoryAnalysis:
        if options is None:
            options = InspectOptions()

        manifest = self._scanner.scan(
            repo_path,
            ignore_dir_patterns=options.ignore_dir_patterns,
            ignore_file_patterns=options.ignore_file_patterns,
        )

        from inspect4all.core.interfaces import UnsupportedFileTypeError

        file_analyses: list[FileAnalysis] = []
        parse_failures: dict[str, list[str]] = {}
        unsupported_files: dict[str, list[str]] = {}
        for language, file_paths in manifest.group_by_language().items():
            adapter = self._registry.get(language)
            if not adapter:
                continue
            lang_analyses: list[FileAnalysis] = []
            for path in file_paths:
                try:
                    parsed = adapter.parse_file(path)
                    analysis = adapter.extract_file_analysis(parsed, repo_path)
                    lang_analyses.append(analysis)
                except UnsupportedFileTypeError as e:
                    # Misdetected file type (e.g. Cython as Python, Jinja2 template,
                    # Python 2 source): not a parser failure, route to unhandled_files.
                    logger.debug(
                        "Skipping %s: unsupported type %s", path, e.file_type
                    )
                    rel = path.relative_to(repo_path).as_posix()
                    unsupported_files.setdefault(e.file_type, []).append(rel)
                except SyntaxError as e:
                    logger.warning("Skipping %s: syntax error (%s)", path, e)
                    rel = path.relative_to(repo_path).as_posix()
                    parse_failures.setdefault(language, []).append(rel)
                except Exception:
                    logger.warning(
                        "Skipping %s: %s adapter failed",
                        path,
                        language,
                        exc_info=True,
                    )
            lang_analyses = adapter.resolve_cross_file_calls(lang_analyses)
            file_analyses.extend(lang_analyses)

        repo = self._aggregate(repo_path, file_analyses, manifest, options)
        if parse_failures:
            repo.metadata["parse_failures"] = parse_failures
        if unsupported_files:
            unhandled = repo.metadata.setdefault("unhandled_files", {})
            for file_type, paths in unsupported_files.items():
                unhandled.setdefault(file_type, []).extend(paths)

        for processor in self._processors:
            if processor.is_applicable(repo):
                repo = processor.enrich(repo)

        return repo

    def _aggregate(
        self,
        repo_path: Path,
        file_analyses: list[FileAnalysis],
        manifest,
        options: InspectOptions,
    ) -> RepositoryAnalysis:
        from inspect4all.analysis.aggregator import RepositoryAggregator

        return RepositoryAggregator(registry=self._registry).aggregate(
            repo_path, file_analyses, manifest, options
        )

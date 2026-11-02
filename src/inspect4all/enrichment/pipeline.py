from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inspect4all.core.interfaces import EnrichmentProcessor
    from inspect4all.core.models import RepositoryAnalysis

logger = logging.getLogger(__name__)


class EnrichmentPipeline:
    def __init__(self, processors: list[EnrichmentProcessor] | None = None):
        self.processors = processors or []

    def run(self, repo: RepositoryAnalysis) -> RepositoryAnalysis:
        for processor in self.processors:
            if processor.is_applicable(repo):
                logger.info("=== %s ===", processor.name.replace("_", " "))
                repo = processor.enrich(repo)
        return repo

from inspect4all.core.models import LicenseInfo, RepositoryAnalysis
from inspect4all.enrichment.pipeline import EnrichmentPipeline


def _minimal_repo() -> RepositoryAnalysis:
    return RepositoryAnalysis(
        repo_path="/tmp/test",
        languages={},
        files=[],
        readme_files=[],
        directory_tree=[],
        dependencies=[],
        software_type="script",
        software_invocation=[],
        tests=[],
        license=LicenseInfo(detected=[], source_files=[], text=None),
        metadata={},
        call_graph={},
    )


def test_empty_pipeline_passthrough():
    pipeline = EnrichmentPipeline(processors=[])
    repo = _minimal_repo()
    result = pipeline.run(repo)
    assert result.repo_path == repo.repo_path


def test_pipeline_runs_processor():
    from unittest.mock import MagicMock

    from inspect4all.core.interfaces import EnrichmentProcessor

    processor = MagicMock(spec=EnrichmentProcessor)
    processor.is_applicable.return_value = True
    processor.enrich.side_effect = lambda r: r
    pipeline = EnrichmentPipeline(processors=[processor])
    repo = _minimal_repo()
    pipeline.run(repo)
    processor.enrich.assert_called_once()


def test_pipeline_skips_non_applicable():
    from unittest.mock import MagicMock

    processor = MagicMock()
    processor.is_applicable.return_value = False
    pipeline = EnrichmentPipeline(processors=[processor])
    repo = _minimal_repo()
    pipeline.run(repo)
    processor.enrich.assert_not_called()

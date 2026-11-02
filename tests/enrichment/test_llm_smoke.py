import json
import os
from pathlib import Path

import pytest

from inspect4all.core.constants import EmbeddingMode
from inspect4all.enrichment.llm import LLMSettings, build_chat_model
from inspect4all.enrichment.runner import run_enrichment
from inspect4all.output.json_writer import JsonWriter
from tests.enrichment.test_runner import _repo

pytestmark = pytest.mark.llm_smoke


@pytest.mark.skipif(
    not os.environ.get("INSPECT4ALL_LLM_BASE_URL"),
    reason="requires a live OpenAI-compatible server",
)
def test_live_enrichment_end_to_end(tmp_path: Path):
    JsonWriter(tmp_path).write(_repo())
    settings = LLMSettings()
    enricher = run_enrichment(
        tmp_path,
        model=build_chat_model(settings),
        model_id=settings.model,
        mode=EmbeddingMode.ENRICHED,
    )
    assert enricher.stats["enriched"] >= 1
    export = json.loads(
        (tmp_path / "embedding_export.enriched.json").read_text()
    )
    assert export["doc_records"][0]["enriched_doc"]
    # Original analysis untouched.
    original = json.loads((tmp_path / "repository_analysis.json").read_text())
    assert "enrichments" not in json.dumps(original)


@pytest.mark.skipif(
    not os.environ.get("INSPECT4ALL_LLM_BASE_URL"),
    reason="requires a live OpenAI-compatible server",
)
def test_live_java_gap_backfill_end_to_end(tmp_path: Path):
    from inspect4all.adapters.java.adapter import JavaAdapter
    from inspect4all.adapters.registry import AdapterRegistry
    from inspect4all.pipeline import InspectionPipeline, InspectOptions

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "Point.java").write_text(
        "package com.example;\n"
        "\n"
        "public record Point(int x, int y) {\n"
        "    public String quadrant() {\n"
        "        return switch (Integer.signum(x)) {\n"
        '            case 1 -> "right";\n'
        '            case -1 -> "left";\n'
        '            default -> "axis";\n'
        "        };\n"
        "    }\n"
        "}\n"
    )
    repo = InspectionPipeline(AdapterRegistry(JavaAdapter())).inspect(
        repo_dir, InspectOptions()
    )
    assert repo.metadata["parse_failures"] == {"Java": ["Point.java"]}

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    JsonWriter(out_dir).write(repo)
    settings = LLMSettings()
    result = run_enrichment(
        out_dir,
        model=build_chat_model(settings),
        model_id=settings.model,
        mode=EmbeddingMode.ENRICHED,
    )
    assert result.stats["enriched"] >= 1
    enriched = json.loads(
        (out_dir / "repository_analysis.enriched.json").read_text()
    )
    backfilled = [
        f for f in enriched["files"] if f["file"]["path"] == "Point.java"
    ]
    assert backfilled, "backfilled FileAnalysis missing from enriched output"
    assert backfilled[0]["language_specific"]["backfilled"]["by"] == "llm"
    assert backfilled[0]["types"], "backfilled file should carry its type"

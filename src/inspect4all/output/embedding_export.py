from __future__ import annotations

from typing import TYPE_CHECKING

from inspect4all.core.constants import EmbeddingMode

if TYPE_CHECKING:
    from inspect4all.core.models import (
        FileAnalysis,
        FunctionInfo,
        RepositoryAnalysis,
    )


def _get_container(func: FunctionInfo, fa: FileAnalysis) -> str | None:
    for t in fa.types:
        if func in t.methods:
            return t.name
    return None


class EmbeddingExporter:
    def export(
        self,
        repo: RepositoryAnalysis,
        mode: EmbeddingMode = EmbeddingMode.ORIGINAL,
    ) -> dict:
        readme_text = " ".join(r.content for r in repo.readme_files) or None

        code_records = []
        doc_records = []

        for fa in repo.files:
            for func in fa.all_functions():
                if not func.source_code:
                    continue
                rec_id = func.qualified_name
                container = _get_container(func, fa)
                kind = (
                    "constructor"
                    if func.is_constructor
                    else ("method" if container else "function")
                )

                code_records.append(
                    {
                        "id": rec_id,
                        "file_path": fa.file.path,
                        "language": fa.file.language,
                        "qualified_name": func.qualified_name,
                        "type": kind,
                        "container": container,
                        "source_code": func.source_code,
                        "line_range": list(func.line_range),
                    }
                )

                original_doc = (
                    func.documentation.full_text if func.documentation else None
                )
                enriched_doc = None

                if func.documentation and mode in (
                    EmbeddingMode.ENRICHED,
                    EmbeddingMode.COMBINED,
                ):
                    enrichments = func.documentation.enrichments or []
                    if enrichments:
                        enriched_doc = enrichments[-1].content.get(
                            "short_description"
                        )
                    if (
                        mode == EmbeddingMode.COMBINED
                        and original_doc
                        and enriched_doc
                    ):
                        original_doc = f"{original_doc}\n{enriched_doc}"

                params = {}
                returns_val = None
                if func.documentation:
                    params = {
                        k: {"description": v.description, "type": v.type}
                        for k, v in func.documentation.params.items()
                    }
                    if func.documentation.returns:
                        returns_val = {
                            "description": func.documentation.returns.description,
                            "type": func.documentation.returns.type,
                        }

                doc_records.append(
                    {
                        "id": rec_id,
                        "file_path": fa.file.path,
                        "language": fa.file.language,
                        "qualified_name": func.qualified_name,
                        "original_doc": original_doc,
                        "enriched_doc": enriched_doc,
                        "params": params,
                        "returns": returns_val,
                    }
                )

        repo_id = (
            repo.repo_path.rstrip("/").split("/")[-1] if repo.repo_path else ""
        )
        return {
            "repo_id": repo_id,
            "repo_path": repo.repo_path,
            "readme": {
                "text": readme_text,
                "source_files": [r.path for r in repo.readme_files],
            },
            "code_records": code_records,
            "doc_records": doc_records,
        }

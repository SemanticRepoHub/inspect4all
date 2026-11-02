from __future__ import annotations

from typing import TYPE_CHECKING

from inspect4all.core.models import (
    FileAnalysis,
    LicenseInfo,
    RepositoryAnalysis,
)

if TYPE_CHECKING:
    from pathlib import Path

    from inspect4all.adapters import AdapterRegistry
    from inspect4all.core.options import InspectOptions
    from inspect4all.discovery.scanner import FileManifest


class RepositoryAggregator:
    def __init__(self, registry: AdapterRegistry):
        self._registry = registry

    def aggregate(
        self,
        repo_path: Path,
        file_analyses: list[FileAnalysis],
        manifest: FileManifest,
        options: InspectOptions,
    ) -> RepositoryAnalysis:
        from inspect4all.analysis.call_graph import build_call_graph
        from inspect4all.analysis.directory_tree import build_directory_tree
        from inspect4all.analysis.license import detect_license
        from inspect4all.analysis.readme import extract_readmes

        languages = dict(manifest.language_summary)

        dependencies = []
        if options.extract_dependencies:
            for _, adapter in self._registry.items():
                dependencies.extend(adapter.extract_dependencies(repo_path))

        software_type = "unknown"
        software_invocation = []
        if options.detect_software_type:
            for lang, adapter in self._registry.items():
                lang_files = [
                    f for f in file_analyses if f.file.language == lang
                ]
                result = adapter.detect_software_type(
                    lang_files, dependencies, repo_path
                )
                if result:
                    software_type = result.software_type
                    software_invocation = result.invocation_entries
                    break

        license_info = LicenseInfo(detected=[], source_files=[], text=None)
        if options.extract_license:
            license_info = detect_license(repo_path)

        readme_files = []
        if options.extract_readme:
            readme_files = extract_readmes(manifest)

        directory_tree = build_directory_tree(manifest)
        call_graph = build_call_graph(file_analyses)

        # Record source files whose enry-detected language has no registered
        # adapter (language -> repo-relative paths) so their prevalence can
        # be analysed in Phase 2.
        unhandled_files: dict[str, list[str]] = {}
        for lang, paths in manifest.group_by_language().items():
            if self._registry.get(lang) is not None:
                continue
            unhandled_files[lang] = sorted(
                str(p.relative_to(repo_path)) for p in paths
            )

        metadata: dict = {"unhandled_files": unhandled_files}
        if options.extract_metadata:
            from inspect4all.analysis.git_metadata import extract_git_metadata

            git_metadata = extract_git_metadata(repo_path)
            if git_metadata is not None:
                metadata["git"] = git_metadata

        return RepositoryAnalysis(
            repo_path=str(repo_path),
            languages=languages,
            files=file_analyses,
            readme_files=readme_files,
            directory_tree=directory_tree,
            dependencies=dependencies,
            software_type=software_type,
            software_invocation=software_invocation,
            tests=[
                entry
                for lang, adapter in self._registry.items()
                for entry in adapter.detect_tests(
                    [f for f in file_analyses if f.file.language == lang],
                    repo_path,
                )
            ],
            license=license_info,
            metadata=metadata,
            call_graph=call_graph,
        )

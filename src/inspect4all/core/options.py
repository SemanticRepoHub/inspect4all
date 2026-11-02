"""Per-run analysis options, shared by the CLI, pipeline, and aggregator.

Lives in core (not pipeline) so analysis-layer modules can type against it
without importing the pipeline, which would be circular.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InspectOptions:
    ignore_dir_patterns: list[str] = field(default_factory=list)
    ignore_file_patterns: list[str] = field(default_factory=list)
    extract_dependencies: bool = False
    detect_software_type: bool = False
    extract_license: bool = False
    extract_readme: bool = False
    extract_metadata: bool = False
    all_features: bool = False

    def __post_init__(self):
        if self.all_features:
            self.extract_dependencies = True
            self.detect_software_type = True
            self.extract_license = True
            self.extract_readme = True
            self.extract_metadata = True

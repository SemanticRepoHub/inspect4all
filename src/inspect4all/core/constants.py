from enum import StrEnum

DEFAULT_IGNORE_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".tox",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
        "target",
    }
)

DEFAULT_IGNORE_PATTERNS = frozenset(
    {
        "*.pyc",
        "*.pyo",
        "*.class",
        "*.jar",
    }
)


class EmbeddingMode(StrEnum):
    ORIGINAL = "original"
    ENRICHED = "enriched"
    COMBINED = "combined"

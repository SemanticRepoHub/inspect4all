"""
inspect4all

A single language-agnostic tool for inspecting and understanding software repositories.
"""

from email.utils import parseaddr
from importlib.metadata import PackageNotFoundError, metadata, version

_meta = metadata("inspect4all")

__author__ = _meta.get("Author") or parseaddr(_meta.get("Author-email", ""))[0]
__license__ = "BSD 3-Clause"

try:
    __version__: str = version("inspect4all")
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.0"


from inspect4all.cli import main  # noqa: E402

__all__ = [
    "__author__",
    "__version__",
    "main",
]

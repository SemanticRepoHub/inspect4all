"""License extraction and SPDX type detection.

Matches the repository's license text against the vendored SPDX templates
(choosealicense.com format, same set inspect4py bundles) using a bigram
Dice coefficient. Matches above the threshold are recorded as
LicenseMatch entries sorted by confidence.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from inspect4all.core.models import LicenseInfo, LicenseMatch

_LICENSE_NAMES = {
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
    "LICENSE.rst",
    "COPYING",
    "COPYING.txt",
    "COPYING.md",
    "COPYING.rst",
    "LICENCE",
}

_TEMPLATES_DIR = Path(__file__).parents[1] / "resources" / "licenses"

# choosealicense.com frontmatter: extract spdx-id and the template body.
_TEMPLATE_RE = re.compile(
    r"(---\n.*(spdx-id: )(?P<id>.+?)\n.*---\n)(?P<template>.*)", re.DOTALL
)

_DICE_THRESHOLD = 0.9


def _dice_coefficient(a: str, b: str) -> float:
    """Bigram-set Dice coefficient: 2|A∩B| / (|A| + |B|)."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    a_bigrams = {a[i : i + 2] for i in range(len(a) - 1)}
    b_bigrams = {b[i : i + 2] for i in range(len(b) - 1)}
    return 2.0 * len(a_bigrams & b_bigrams) / (len(a_bigrams) + len(b_bigrams))


@cache
def _load_templates() -> tuple[tuple[str, str], ...]:
    templates = []
    for path in sorted(_TEMPLATES_DIR.glob("*.txt")):
        parsed = _TEMPLATE_RE.search(path.read_text(encoding="utf-8"))
        if parsed is None:
            continue
        templates.append((parsed.group("id"), parsed.group("template").strip()))
    return tuple(templates)


def _match_license(text: str) -> list[LicenseMatch]:
    stripped = text.strip()
    matches = [
        LicenseMatch(type=spdx_id, confidence=round(score, 3))
        for spdx_id, template in _load_templates()
        if (score := _dice_coefficient(stripped, template)) > _DICE_THRESHOLD
    ]
    return sorted(matches, key=lambda m: m.confidence, reverse=True)


def detect_license(repo_path: Path) -> LicenseInfo:
    for name in _LICENSE_NAMES:
        f = repo_path / name
        if f.exists():
            try:
                text = f.read_text(errors="replace")
            except OSError:
                text = None
            detected = _match_license(text) if text else []
            return LicenseInfo(
                detected=detected, source_files=[name], text=text
            )
    return LicenseInfo(detected=[], source_files=[], text=None)

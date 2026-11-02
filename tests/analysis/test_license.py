"""Tests for license detection with Dice-coefficient SPDX matching."""

from __future__ import annotations

from pathlib import Path

from inspect4all.analysis.license import detect_license

RESOURCES = Path(__file__).parents[2] / "src/inspect4all/resources/licenses"


def _template_body(name: str) -> str:
    raw = (RESOURCES / name).read_text()
    return raw.split("---", 2)[2]


def test_detects_mit_license(tmp_path: Path) -> None:
    body = (
        _template_body("mit.txt")
        .replace("[year]", "2026")
        .replace("[fullname]", "Tester")
    )
    (tmp_path / "LICENSE").write_text(body)
    info = detect_license(tmp_path)
    assert info.detected, "expected at least one SPDX match"
    assert info.detected[0].type == "MIT"
    assert info.detected[0].confidence > 0.9


def test_detects_apache_license(tmp_path: Path) -> None:
    (tmp_path / "LICENSE.txt").write_text(_template_body("apache-2.0.txt"))
    info = detect_license(tmp_path)
    assert info.detected[0].type == "Apache-2.0"


def test_matches_sorted_by_confidence(tmp_path: Path) -> None:
    (tmp_path / "LICENSE").write_text(_template_body("bsd-3-clause.txt"))
    info = detect_license(tmp_path)
    confidences = [m.confidence for m in info.detected]
    assert confidences == sorted(confidences, reverse=True)


def test_no_license_file(tmp_path: Path) -> None:
    info = detect_license(tmp_path)
    assert info.detected == []
    assert info.text is None


def test_unrecognised_text_keeps_text(tmp_path: Path) -> None:
    (tmp_path / "LICENSE").write_text("do whatever you want\n")
    info = detect_license(tmp_path)
    assert info.detected == []
    assert info.text is not None

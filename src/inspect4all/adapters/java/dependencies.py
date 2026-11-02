from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from inspect4all.core.models import Dependency

if TYPE_CHECKING:
    from pathlib import Path


def _parse_pom(pom_path: Path) -> list[Dependency]:
    deps = []
    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
        # Handle namespace-qualified tags transparently
        tag = root.tag
        ns = tag[1 : tag.index("}")] if tag.startswith("{") else ""
        prefix = f"{{{ns}}}" if ns else ""
        for dep in root.iter(f"{prefix}dependency"):
            group = dep.findtext(f"{prefix}groupId") or ""
            artifact = dep.findtext(f"{prefix}artifactId") or ""
            version = dep.findtext(f"{prefix}version")
            scope = dep.findtext(f"{prefix}scope") or "compile"
            name = f"{group}:{artifact}" if group else artifact
            deps.append(
                Dependency(
                    name=name,
                    version=version,
                    source="pom.xml",
                    language="Java",
                    scope=scope,
                    build_tool="maven",
                )
            )
    except Exception:
        pass
    return deps


def _parse_gradle(gradle_path: Path) -> list[Dependency]:
    deps: list[Dependency] = []
    try:
        text = gradle_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return deps
    pattern = re.compile(
        r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly)\s+['"]([^'"]+)['"]"""
    )
    for m in pattern.finditer(text):
        coords = m.group(1).split(":")
        if len(coords) >= 2:
            name = f"{coords[0]}:{coords[1]}"
            version = coords[2] if len(coords) > 2 else None
            deps.append(
                Dependency(
                    name=name,
                    version=version,
                    source=gradle_path.name,
                    language="Java",
                    scope="compile",
                    build_tool="gradle",
                )
            )
    return deps


class JavaDependencyExtractor:
    def extract(self, repo_path: Path) -> list[Dependency]:
        deps: list[Dependency] = []
        pom = repo_path / "pom.xml"
        if pom.exists():
            deps.extend(_parse_pom(pom))
        for name in ("build.gradle", "build.gradle.kts"):
            gf = repo_path / name
            if gf.exists():
                deps.extend(_parse_gradle(gf))
        return deps

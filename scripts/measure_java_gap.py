"""Measure the javalang parse-failure rate across the ground-truth corpus.

Sizes the Plan B recovery workload (design doc §7): for every .java file
in every ground-truth repo, attempt a javalang parse and count failures.

Usage: env -u VIRTUAL_ENV uv run python scripts/measure_java_gap.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import javalang

GROUND_TRUTH = Path(
    "/Users/boonheng/Documents/msc_studies/dissertation/data/ground_truth/data"
)


def parse_ok(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        javalang.parse.parse(source)
        return True
    except Exception:
        return False


def main() -> int:
    total_files = 0
    failed_files = 0
    repos_with_java = 0
    repos_with_failures: list[tuple[str, int, int]] = []

    for owner in sorted(GROUND_TRUTH.iterdir()):
        if not owner.is_dir():
            continue
        for repo in sorted(owner.iterdir()):
            if not repo.is_dir():
                continue
            java_files = [
                p for p in repo.rglob("*.java") if ".git" not in p.parts
            ]
            if not java_files:
                continue
            repos_with_java += 1
            failures = sum(1 for p in java_files if not parse_ok(p))
            total_files += len(java_files)
            failed_files += failures
            if failures:
                repos_with_failures.append(
                    (f"{owner.name}/{repo.name}", failures, len(java_files))
                )

    print(f"repos with Java: {repos_with_java}")
    print(f"java files: {total_files}")
    print(
        f"javalang failures: {failed_files} "
        f"({100 * failed_files / max(total_files, 1):.2f}%)"
    )
    print(f"repos with >=1 failure: {len(repos_with_failures)}")
    for name, failures, total in sorted(
        repos_with_failures, key=lambda item: -item[1]
    )[:15]:
        print(f"  {name}: {failures}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

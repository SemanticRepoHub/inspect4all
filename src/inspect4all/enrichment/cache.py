from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def content_hash(source: str) -> str:
    """Return a short stable hash of a record's source text."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def load_cache(path: Path) -> dict[str, str]:
    """Return a record_id -> status map; later lines override earlier ones."""
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        result[entry["id"]] = entry["status"]
    return result


def load_cache_full(path: Path) -> dict[str, dict]:
    """Return a record_id -> {status, hash, elapsed_s?} map; later lines win."""
    if not path.exists():
        return {}
    result: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        record: dict = {
            "status": entry["status"],
            "hash": entry.get("hash", ""),
        }
        if "elapsed_s" in entry:
            record["elapsed_s"] = entry["elapsed_s"]
        result[entry["id"]] = record
    return result


def append_cache(
    path: Path,
    record_id: str,
    source_hash: str,
    status: str,
    elapsed_s: float | None = None,
) -> None:
    """Append one cache entry (jsonl). Creates the file/parent if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    entry: dict = {"id": record_id, "hash": source_hash, "status": status}
    if elapsed_s is not None:
        entry["elapsed_s"] = round(elapsed_s, 3)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

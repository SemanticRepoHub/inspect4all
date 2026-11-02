"""Run inspect4all over every ground-truth repository and record outcomes.

Each repo is analysed via the CLI in a subprocess (negative return codes
reveal crash signals; a per-repo timeout keeps the batch moving). One JSON
line per repo is appended to <out_dir>/results.jsonl as soon as it finishes,
so an interrupted run can resume — repos already present in results.jsonl
are skipped.

Usage:
    uv run python scripts/run_ground_truth.py [out_dir]

Defaults: dataset at ~/Documents/msc_studies/dissertation/data/ground_truth/
data, outputs under scripts/gt_run/.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(format="%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

GROUND_TRUTH = (
    Path.home() / "Documents/msc_studies/dissertation/data/ground_truth/data"
)
DEFAULT_OUT = Path(__file__).parent / "gt_run"
PER_REPO_TIMEOUT_S = 600


def _discover_repos(dataset: Path) -> list[Path]:
    return sorted(
        repo
        for org in dataset.iterdir()
        if org.is_dir()
        for repo in org.iterdir()
        if repo.is_dir()
    )


def _completed_repos(results_path: Path) -> set[str]:
    if not results_path.exists():
        return set()
    done = set()
    for line in results_path.read_text().splitlines():
        try:
            done.add(json.loads(line)["repo"])
        except (json.JSONDecodeError, KeyError):
            continue
    return done


def _summarise_outputs(out_dir: Path) -> dict:
    analysis = json.loads((out_dir / "repository_analysis.json").read_text())
    export = json.loads((out_dir / "embedding_export.json").read_text())
    docs_with_text = sum(
        1 for r in export["doc_records"] if r.get("original_doc")
    )
    return {
        "languages": analysis["repository"]["languages"],
        "software_type": analysis["repository"]["software_type"],
        "n_files": len(analysis["files"]),
        "n_code_records": len(export["code_records"]),
        "n_doc_records_with_text": docs_with_text,
        "unhandled_files": analysis["metadata"]["unhandled_files"],
    }


def _run_one(repo: Path, out_dir: Path) -> dict:
    start = time.time()
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "inspect4all.cli",
                "-i",
                str(repo),
                "-o",
                str(out_dir),
                "--all",
            ],
            capture_output=True,
            text=True,
            timeout=PER_REPO_TIMEOUT_S,
            check=False,
        )
        status = (
            "ok"
            if proc.returncode == 0
            else ("crash" if proc.returncode < 0 else "error")
        )
        record: dict = {
            "status": status,
            "exit_code": proc.returncode,
            "seconds": round(time.time() - start, 1),
        }
        if status == "ok":
            try:
                record.update(_summarise_outputs(out_dir))
            except (OSError, json.JSONDecodeError, KeyError) as e:
                record["status"] = "bad_output"
                record["stderr_tail"] = f"{type(e).__name__}: {e}"
        else:
            record["stderr_tail"] = proc.stderr[-500:]
        return record
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "exit_code": None,
            "seconds": round(time.time() - start, 1),
        }


def main() -> int:
    out_root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out_root.mkdir(parents=True, exist_ok=True)
    results_path = out_root / "results.jsonl"

    repos = _discover_repos(GROUND_TRUTH)
    done = _completed_repos(results_path)
    todo = [r for r in repos if f"{r.parent.name}/{r.name}" not in done]
    logger.info(
        "%d repos total, %d already done, %d to run",
        len(repos),
        len(done),
        len(todo),
    )

    with results_path.open("a") as results:
        for i, repo in enumerate(todo, 1):
            repo_id = f"{repo.parent.name}/{repo.name}"
            out_dir = out_root / repo.parent.name / repo.name
            record = {"repo": repo_id, **_run_one(repo, out_dir)}
            results.write(json.dumps(record) + "\n")
            results.flush()
            logger.info(
                "[%d/%d] %s: %s (%.1fs)",
                i,
                len(todo),
                repo_id,
                record["status"],
                record["seconds"],
            )
    logger.info("done — results in %s", results_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

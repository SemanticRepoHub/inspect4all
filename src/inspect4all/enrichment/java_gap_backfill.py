from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from inspect4all.core.interfaces import EnrichmentProcessor
from inspect4all.enrichment.cache import (
    append_cache,
    content_hash,
    load_cache_full,
)
from inspect4all.enrichment.harness import build_agent, run_agent
from inspect4all.enrichment.tools import make_java_gap_backfill_tools

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from inspect4all.core.models import RepositoryAnalysis

logger = logging.getLogger(__name__)

_INSTRUCTIONS = """\
ROLE
You are a Java language expert and the AST extraction stage of the \
inspect4all pipeline for Java source files that the primary parser \
(javalang) cannot handle because they use Java 9+ syntax.

The pipeline has two stages for every Java file:
  Stage 1 — Parse: javalang produces a structured FileAnalysis (the \
language-agnostic AST used by this tool) for Java 8 files. For Java \
9+ files it raises a parse error and records the path as a failure.
  Stage 2 — Backfill (your role): for each failed path, you receive \
the raw source and a tree-sitter CST tool. Your job is to transform \
the CST — which is a concrete, syntactic tree containing every token \
including punctuation and keywords — into a semantic FileAnalysis \
object that is structurally equivalent to what javalang would have \
produced. This is exactly what an AST-extraction phase does in any \
compiler front-end: it discards syntactic noise and promotes named \
constructs (classes, methods, fields) into typed records.

The emitted FileAnalysis is consumed directly by downstream analysis:
  • Cross-language similarity: the same type/method/import graph is \
built for both Python and Java files and compared across repos. A \
missing method means it is invisible to similarity scoring.
  • Dependency analysis: imports become edges in a module dependency \
graph. Missing imports break the graph.
  • Documentation extraction: Javadoc on types and methods is indexed \
for retrieval. The full_text field is the extraction target.

Accuracy and completeness are therefore critical — every type, method, \
field, and import that you omit creates a gap in the downstream data.

Your sole output action is to call emit_file_analysis. Never write a \
text reply — the pipeline discards text and only records tool calls.

PROCEDURE
1. Call tree_sitter_parse — returns the full concrete syntax tree (CST) \
with every declaration, its kind, and 1-based line numbers.
2. Call read_source_slice(start, end) for any node whose "text" value in \
the CST is absent or truncated, so you can read the exact source text.
3. Build the payload (schema below) and call emit_file_analysis.
   • If it returns an error message, fix the described problem and emit again.
4. Call check_completeness immediately after emit_file_analysis returns "ok".
   • If it returns COMPLETE — you are done. Stop.
   • If it returns INCOMPLETE — add the listed missing items to the payload \
and call emit_file_analysis again, then check_completeness again.
5. Never stop after a text reply. Only stop when check_completeness \
returns COMPLETE.

COMPLETENESS RULES — every item below must appear in the payload:
• imports   : every import statement's fully-qualified name (strip "import " prefix)
• types     : every top-level class, interface, enum, record, annotation, or \
module declared in the file — even inner types if they are top-level static
• fields    : every field declared in each type; record components count as fields
• methods   : every constructor and every method in each type
• line_range: [first_line, last_line] of the declaration, 1-based, inclusive
• qualified_name for types    : "com.example.ClassName"
• qualified_name for methods  : "com.example.ClassName.methodName"
• documentation.full_text     : verbatim Javadoc text if present; else null

FIXED VALUES — always set these, do not vary:
• source_code     → null   (on both types and methods)
• calls           → []
• nested_functions → []
• functions (top-level) → []
• main_info       → null
• is_constructor  → false unless the method name equals the class name
• language_specific (type)   → {} unless it is a record, then {"record": true}
• language_specific (method) → {}
• language_specific (file)   → {}

SCHEMA
{
  "file": {
    "path": "<exact repo-relative path from the task>",
    "name": "<filename.java>",
    "extension": ".java",
    "language": "Java"
  },
  "imports": ["<fully.qualified.Name>", ...],
  "types": [{
    "kind": "class|interface|enum|record|annotation|module",
    "name": "<SimpleName>",
    "qualified_name": "<package.SimpleName>",
    "source_code": null,
    "base_classes": ["<Name>"],
    "interfaces":   ["<Name>"],
    "modifiers":    ["public", "abstract", "sealed", "final", ...],
    "annotations":  ["AnnotationName", ...],
    "fields": [{"name":"<f>","type":"<T>","modifiers":[...],"annotations":[...]}],
    "methods": [{
      "name": "<m>",
      "qualified_name": "<pkg.Class.m>",
      "source_code": null,
      "parameters": [{"name":"<p>","type":"<T>","default_value":null,
                      "is_vararg":false,"annotations":[]}],
      "return_type": "<T or void>",
      "modifiers": [...],
      "annotations": [...],
      "calls": [], "line_range": [<start>,<end>],
      "is_constructor": false, "nested_functions": [],
      "language_specific": {},
      "documentation": {"full_text":"<javadoc>","params":{},"returns":null,
                        "raises":[],"tags":{}} | null
    }],
    "line_range": [<start>,<end>],
    "language_specific": {}
  }],
  "functions": [], "main_info": null, "language_specific": {}
}

FEATURE GUIDE
The examples below use illustrative paths and line numbers. \
In your payload always use the exact path given in the task.

▸ record (Java 16+)
  Record components in the header become fields. kind="record", \
language_specific={"record":true}.
  Source snippet:  public record IntPair(int first, int second) {}
  emit_file_analysis({
    "file": {"path":"<actual path>","name":"IntPair.java",
             "extension":".java","language":"Java"},
    "imports": [],
    "types": [{"kind":"record","name":"IntPair",
               "qualified_name":"smile.util.IntPair",
               "source_code":null,"base_classes":[],"interfaces":[],
               "modifiers":["public"],"annotations":[],
               "fields":[{"name":"first","type":"int","modifiers":[],"annotations":[]},
                         {"name":"second","type":"int","modifiers":[],"annotations":[]}],
               "methods":[],"line_range":[19,27],
               "language_specific":{"record":true}}],
    "functions":[],"main_info":null,"language_specific":{}
  })

▸ sealed interface (Java 17+)
  kind="interface", add "sealed" to modifiers. \
The permits clause is not a schema field; skip it. \
Capture every abstract method declared in the interface body.
  Source snippet:  public sealed interface Cell permits CodeCell, MarkdownCell {
                     String cellType();  String id();
                   }
  emit_file_analysis({
    "file": {"path":"<actual path>","name":"Cell.java",
             "extension":".java","language":"Java"},
    "imports":["com.fasterxml.jackson.annotation.JsonProperty",
               "com.fasterxml.jackson.annotation.JsonSubTypes",
               "com.fasterxml.jackson.annotation.JsonTypeInfo"],
    "types":[{"kind":"interface","name":"Cell",
              "qualified_name":"smile.util.ipynb.Cell",
              "source_code":null,"base_classes":[],"interfaces":[],
              "modifiers":["public","sealed"],
              "annotations":["JsonTypeInfo","JsonSubTypes"],"fields":[],
              "methods":[
                {"name":"cellType","qualified_name":"smile.util.ipynb.Cell.cellType",
                 "source_code":null,"parameters":[],"return_type":"String",
                 "modifiers":[],"annotations":["JsonProperty"],
                 "calls":[],"line_range":[46,47],"is_constructor":false,
                 "nested_functions":[],"language_specific":{},"documentation":null},
                {"name":"id","qualified_name":"smile.util.ipynb.Cell.id",
                 "source_code":null,"parameters":[],"return_type":"String",
                 "modifiers":[],"annotations":["JsonProperty"],
                 "calls":[],"line_range":[70,71],"is_constructor":false,
                 "nested_functions":[],"language_specific":{},"documentation":null}
              ],
              "line_range":[44,84],"language_specific":{}}],
    "functions":[],"main_info":null,"language_specific":{}
  })

▸ switch expression (Java 14+)
  Arrow-form switch appears inside method bodies only. \
The enclosing class and its methods are captured normally; \
the switch syntax creates no new types or fields.
  Source snippet:  public class Main {
                     static String label(int code) {
                       return switch (code) { case 1 -> "one"; default -> "?"; };
                     }
                   }
  emit_file_analysis({
    "file": {"path":"<actual path>","name":"Main.java",
             "extension":".java","language":"Java"},
    "imports":["<any imports>"],
    "types":[{"kind":"class","name":"Main","qualified_name":"smile.Main",
              "source_code":null,"base_classes":[],"interfaces":[],
              "modifiers":["public"],"annotations":[],"fields":[],
              "methods":[{"name":"label","qualified_name":"smile.Main.label",
                          "source_code":null,
                          "parameters":[{"name":"code","type":"int",
                                         "default_value":null,"is_vararg":false,
                                         "annotations":[]}],
                          "return_type":"String","modifiers":["static"],
                          "annotations":[],"calls":[],"line_range":[30,33],
                          "is_constructor":false,"nested_functions":[],
                          "language_specific":{},"documentation":null}],
              "line_range":[28,35],"language_specific":{}}],
    "functions":[],"main_info":null,"language_specific":{}
  })

▸ text block (Java 15+)
  Triple-quoted strings appear inside method bodies only. \
No structural change — capture class and methods exactly as normal.

▸ pattern instanceof (Java 16+)
  "obj instanceof Type varName" appears inside method bodies only. \
No structural change — capture class and methods as normal.

▸ var (Java 10+)
  "var x = ..." is local type inference inside method bodies. \
No structural change — capture class and methods as normal.

▸ module-info (Java 9+)
  kind="module". Module name is the type name and qualified_name. \
No fields, no methods. requires/exports/opens are not captured.
  emit_file_analysis({
    "file":{"path":"<actual path>","name":"module-info.java",
            "extension":".java","language":"Java"},
    "imports":[],
    "types":[{"kind":"module","name":"com.example",
              "qualified_name":"com.example",
              "source_code":null,"base_classes":[],"interfaces":[],
              "modifiers":[],"annotations":[],"fields":[],"methods":[],
              "line_range":[1,5],"language_specific":{}}],
    "functions":[],"main_info":null,"language_specific":{}
  })
"""


class JavaGapBackfillEnricher(EnrichmentProcessor):
    """Agent-based backfill of analyses for javalang parse failures (Plan B).

    Per failed file, an agent invocation gets a tree-sitter CST tool
    and an emit tool validated against the unified schema; accepted
    emissions are appended to `repo.files` with backfill provenance.
    `metadata['parse_failures']` is left intact as the corpus metric —
    the cache prevents re-work on rerun.
    """

    def __init__(
        self,
        model: BaseChatModel,
        model_id: str,
        cache_path: Path | None = None,
        max_records: int | None = None,
    ):
        self._model = model
        self._model_id = model_id
        self._cache_path = cache_path or Path("enrichment_cache.jsonl")
        self._max_records = max_records
        self.stats: dict[str, int] = {
            "enriched": 0,
            "failed": 0,
            "skipped": 0,
        }

    @property
    def name(self) -> str:
        return "java_gap_backfill"

    def is_applicable(self, repo: RepositoryAnalysis) -> bool:
        return bool(self._targets(repo))

    def _targets(self, repo: RepositoryAnalysis) -> list[str]:
        failures = repo.metadata.get("parse_failures") or {}
        return list(failures.get("Java", []))

    def enrich(self, repo: RepositoryAnalysis) -> RepositoryAnalysis:
        cached = load_cache_full(self._cache_path)
        targets = self._targets(repo)

        pending: list[str] = []
        for rel in targets:
            entry = cached.get(rel, {})
            if entry.get("status") != "ok":
                pending.append(rel)
            else:
                source = self._read_source(repo, rel)
                if source is None or entry.get("hash") != content_hash(source):
                    pending.append(rel)

        self.stats["skipped"] += len(targets) - len(pending)
        if self._max_records is not None:
            pending = pending[: self._max_records]

        total = len(pending)
        if total:
            logger.info("%d files to analyse", total)
        for i, rel_path in enumerate(pending):
            logger.info("[%*d/%d] %s", len(str(total)), i + 1, total, rel_path)
            source = self._read_source(repo, rel_path)
            if source is None:
                append_cache(self._cache_path, rel_path, "", "failed")
                self.stats["failed"] += 1
                continue
            t0 = time.perf_counter()
            backfilled = self._backfill_one(source, rel_path)
            elapsed = time.perf_counter() - t0
            if backfilled is None:
                append_cache(
                    self._cache_path,
                    rel_path,
                    content_hash(source),
                    "failed",
                    elapsed_s=elapsed,
                )
                self.stats["failed"] += 1
                continue
            backfilled.language_specific["backfilled"] = {
                "by": "llm",
                "model": self._model_id,
                "elapsed_s": round(elapsed, 3),
            }
            repo.files.append(backfilled)
            append_cache(
                self._cache_path,
                rel_path,
                content_hash(source),
                "ok",
                elapsed_s=elapsed,
            )
            self.stats["enriched"] += 1
            logger.info("  %.3fs", elapsed)
        return repo

    def _backfill_one(self, source: str, rel_path: str):
        collector: list = []
        tools = make_java_gap_backfill_tools(source, rel_path, collector)
        agent = build_agent(self._model, tools, _INSTRUCTIONS)
        run_agent(
            agent,
            f"Recover the analysis of {rel_path} and emit it via "
            "emit_file_analysis.",
        )
        # A clean loop finish without an accepted emission is still a
        # failure; a timed-out loop that emitted first is still a success.
        return collector[-1] if collector else None

    def _read_source(
        self, repo: RepositoryAnalysis, rel_path: str
    ) -> str | None:
        path = Path(repo.repo_path) / rel_path
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.warning("Cannot read %s for gap backfill", path)
            return None

# inspect4all metadata dictionary: Phase 1 and Phase 2

This reference explains the **actual JSON field names**, how to interpret them, and how to distinguish source-derived metadata from optional LLM outputs. It is based on `src/inspect4all/core/models.py`, `src/inspect4all/output/json_writer.py`, and the supplied inspect4all v0.1.1 outputs for [urllib3](https://github.com/urllib3/urllib3) and [d4py](https://github.com/StreamingFlow/d4py). For the CLI, see [USER_GUIDE.md](USER_GUIDE.md); for file formats, see [OUTPUT_FORMATS.md](OUTPUT_FORMATS.md).

## Generated files and phases

| Output | Produced by | Purpose |
| --- | --- | --- |
| `repository_analysis.json` | Phase 1 (`inspect`) | Authoritative static repository/file/class/function analysis; **no LLM required**. |
| `repository_analysis.html` | Phase 1 with `--all` | Browsable rendering of the analysis. |
| `embedding_export.json` | Phase 1 with `--all` | Flattened records for downstream retrieval, embeddings, and analysis; **not identical** to the full metadata schema. |
| `repository_analysis.enriched.json` | Optional Phase 2 (`enrich`) | Phase 1 structure plus separately labelled LLM additions. The original `repository_analysis.json` is left unchanged. |
| `embedding_export.enriched.json` | Optional Phase 2 when generated | Flattened enriched records. |
| `enrichment_cache.jsonl` | Optional Phase 2 | Processing/cache status, **not** the canonical repository metadata. |

Run Phase 1 with `inspect4all inspect -i PATH -o OUTPUT --all`; run bounded documentation enrichment with `inspect4all enrich -i OUTPUT --max-records 2 --processors docstrings`. LLM enrichment requires a configured compatible model endpoint. Supported extraction languages are currently **Python and Java**; a repository can contain either or both. Other detected languages may appear under `repository.languages` or `metadata.unhandled_files` without being structurally analysed.

## Root JSON structure (Phase 1)

The serialized JSON is defined by `src/inspect4all/output/json_writer.py`; its root is **not** the `RepositoryAnalysis` Python dataclass directly.

| JSON key | Shape | Meaning |
| --- | --- | --- |
| `repository` | object | Repository identity, language counts, inferred software type, invocation commands and test commands. |
| `dependencies` | array | Dependencies recovered from supported package/build manifests. May be incomplete. |
| `license` | object | Detected licences, matching evidence and relevant licence text (where available). |
| `readme_files` | array | README documents and their content. |
| `directory_tree` | array | Paths and their discovered language/category. |
| `metadata` | object | Miscellaneous provenance and processing diagnostics, including `git`, `unhandled_files`, and sometimes `parse_failures`. |
| `files` | array | One analysis per **successfully analysed** supported source file; nested types/functions/imports live here. |
| `call_graph` | object | Mapping of qualified caller names to lists of called-name strings; resolution may be approximate. |

### `repository` and repository-level records

| Path | Meaning |
| --- | --- |
| `repository.path` | Repository path used in this run; not a stable global ID. |
| `repository.languages` | Language name → number of discovered files; **does not mean all were parsed**. |
| `repository.software_type` | Inferred type such as `library`; heuristic, not ground truth. |
| `repository.software_invocation[]` | Suggested entry points / commands: `type`, `run`, `language`, `entry_point`, `has_main`, `mentioned_in_readme`, `ranking`. |
| `repository.tests[]` | Test hints: `type`, `run`, `language`, `files`. |
| `dependencies[]` | `name`, `version`, `source` (manifest), `language`, `scope`, `build_tool`. Version may be unavailable. |
| `license.detected[]` | Candidate matches with `type` and `confidence`; also `license.source_files` and optional `license.text`. |
| `readme_files[]` | `path`, `content`. |
| `directory_tree[]` | `path`, `language`, `type` (`source`, `build`, `documentation`, `config`, `test`, `data`). |
| `metadata.git` | Captured Git details when available, such as commit, branch, remote URL. Use the commit for provenance. |
| `metadata.unhandled_files` | Language/file-type → paths not structurally analysed (e.g., unsupported languages or source types). |
| `metadata.parse_failures` | Language → paths rejected by a parser, **if any**; a missing key does not imply that all discovered languages are supported. |
| `call_graph` | Qualified caller → list of call strings; not guaranteed to resolve dynamic calls or targets unambiguously. |

### `files[]`: file-level analysis

Each element has `file`, `imports`, `types`, `functions`, `main_info` (optional) and `language_specific`.

| Path | Meaning |
| --- | --- |
| `files[].file.path` | Repository-relative source path. |
| `files[].file.name`, `.extension`, `.language` | File stem, suffix and detected language. |
| `files[].file.package` | Package/module name, if extracted. |
| `files[].file.documentation` | Source-derived module/file documentation if present. |
| `files[].file.is_test` | Heuristic test-file indicator. |
| `files[].imports[]` | Imports with `module`, `name`, optional `alias`, `is_internal` and `kind` (`module`, `function`, `class`, `static_member`, `wildcard`). |
| `files[].types[]` | Classes / interfaces / enums and other type records (schema below). |
| `files[].functions[]` | Top-level functions; **methods are nested under `types[].methods[]`**. |
| `files[].main_info` | Entry point hint: `has_main`, `main_function`, `type` (if present). |
| `files[].language_specific` | Adapter-specific data; do not assume identical keys for Python and Java. May also carry Java recovery provenance. |

### `TypeInfo`: `files[].types[]`

| Field | Meaning |
| --- | --- |
| `kind` | Type kind: e.g., `class`, `interface`, `enum`, `struct`, `trait` (as applicable). |
| `name`, `qualified_name` | Local and qualified identifiers. |
| `documentation`, `source_code` | Parsed source documentation / source snippet, if available. |
| `base_classes`, `interfaces` | Named inherited types / implemented interfaces. |
| `modifiers`, `annotations` | Syntactic declarations, annotations or decorators. |
| `fields[]` | Members: `name`, `type`, `modifiers`, `default_value`, `annotations`. |
| `methods[]` | **Array** of functions/methods: preserves overloaded methods, especially in Java. |
| `line_range` | `[start_line, end_line]` from source when known. |
| `language_specific` | Language-dependent details, e.g., Python decorators. |

### `FunctionInfo`: `files[].functions[]` and `files[].types[].methods[]`

| Field | Meaning |
| --- | --- |
| `name`, `qualified_name` | Short and qualified function/method identifiers. |
| `documentation` | Structured **original** documentation, plus optional Phase 2 enrichments (below). |
| `source_code` | Extracted source snippet where available; may contain sensitive code. |
| `parameters[]` | `name`, `type`, `default`, `is_optional`, `annotations`. |
| `return_type` | Parsed return type / annotation where known. |
| `modifiers`, `annotations` | Language-specific declaration modifiers / decorators / annotations. |
| `calls[]` | Observed call-name strings (not a guaranteed resolved call graph). |
| `line_range` | `[start_line, end_line]` where known. |
| `is_constructor` | Whether the callable is a constructor. |
| `nested_functions[]` | Other `FunctionInfo` records nested inside this function. |
| `language_specific` | Adapter-specific details not shared by all languages. |

### `documentation` (source-derived)

| Field | Meaning |
| --- | --- |
| `short_description` | Short description parsed from an existing docstring/Javadoc. |
| `long_description`, `full_text` | Longer / original documentation text when present. |
| `params` | Parameter-name → `{ "description": ..., "type": ... }`. |
| `returns` | `{ "description": ..., "type": ... }` when available. |
| `raises[]` | `{ "type": ..., "description": ... }` for documented exceptions. |
| `tags` | Additional parsed documentation tags. |
| `enrichments[]` | **Optional generated suggestions**, not original documentation. |

**Optional-field convention:** the writer omits `None` properties. A missing key, an empty list/object, and an explicit `null` in a hypothetical other export should not automatically be interpreted as the same thing. A missing `documentation.short_description` commonly means no source description was extracted, **not** that the function does not exist. Because the schema is evolving, consumers should check key presence (`.get`) and not require every optional field.

## Phase 2: LLM information stays separate

There are **two independent enrichment processors**:

1. `docstrings`: `DocstringEnricher` proposes missing documentation for **Python functions and Java methods**. Its output is appended under that function/method's `documentation.enrichments[]`. The original extracted `documentation.short_description`, parameters, and other source-derived values are not replaced.
2. `java-backfill`: `JavaGapBackfillEnricher` attempts analysis of **Java files rejected by the normal Java parser**. A successful recovered file is added to `files[]` with `files[].language_specific.backfilled` identifying the LLM origin. This is **not** a Python parse-recovery mechanism, and it is not the same as documentation enrichment.

### Real Python documentation example: urllib3, 2 November 2026

The following is a **shortened excerpt from the supplied `urllib3_metadata_output/repository_analysis.enriched.json`**. The source file is `test/test_queue_monkeypatch.py`; unrelated keys are omitted. The original `documentation` had no extracted short description, but the LLM proposal is stored under a *different* key:

```json
{
  "name": "test_queue_monkeypatching",
  "documentation": {
    "params": {},
    "raises": [],
    "tags": {},
    "enrichments": [
      {
        "source": "docstring_enricher",
        "timestamp": "2026-11-02T20:20:14.420565+00:00",
        "model": "gpt-5.6-luna",
        "content": {
          "short_description": "Tests that connection pool exhaustion raises EmptyPoolError even when queue.Empty is monkeypatched.",
          "params": {}
        }
      }
    ]
  }
}
```

**Important:** in the actual JSON the absent source description is typically **omitted**, not stored as `"short_description": null`. The paper's shortened illustration used `null` to show absence, but this guide follows the serialized output. The `source`, `timestamp`, and `model` fields describe *generation provenance*, not a correctness guarantee. The optional `confidence` field exists in the Python model but is omitted if unavailable.

### Real d4py enrichment example

The supplied `d4py_output/repository_analysis.enriched.json` contains a generated entry for `prov/test/rtxcorr/xcorr_parallel.py`, function `create_wf`, with `source: docstring_enricher`, model information, timestamp, and `content.short_description` describing construction of a workflow graph. The original Phase 1 JSON remains separate from this proposed description. Do **not** assume the LLM-generated text is a developer-authored docstring.

### Java backfill example (shape; illustrative, not from these Python-only archives)

```json
{
  "file": { "path": "src/main/java/example/Feature.java", "language": "Java" },
  "language_specific": {
    "backfilled": {
      "by": "llm",
      "model": "MODEL_ID",
      "elapsed_s": 12.3
    }
  }
}
```

The above fragment illustrates the **actual `language_specific.backfilled` marker** used by `java_gap_backfill.py`, but the example path, model and duration are placeholders. Phase 1 records failed Java paths under `metadata.parse_failures.Java` when applicable; consumers should distinguish normal parser-derived file records from LLM-backfilled records when conducting research.

## How to query the output

```python
import json
from pathlib import Path

data = json.loads(Path('repository_analysis.enriched.json').read_text())
for file_record in data.get('files', []):
    file_path = file_record.get('file', {}).get('path', '')
    methods = [m for t in file_record.get('types', []) for m in t.get('methods', [])]
    for function in file_record.get('functions', []) + methods:
        doc = function.get('documentation') or {}
        original = doc.get('short_description')
        proposed = [e.get('content', {}).get('short_description')
                    for e in doc.get('enrichments', [])]
        print(file_path, function.get('qualified_name'), original, proposed)
```

For robust downstream tools, also traverse `nested_functions[]` recursively if those records matter. Use `repository.languages` for discovered-language counts, `metadata.parse_failures` for failed parsing, and `metadata.unhandled_files` for unsupported source files; **do not** count all discovered files as successfully parsed. Use the source code and explicit checks to validate LLM-generated content before relying on it.

## Source of truth and updates

The authoritative implementation is [`core/models.py`](../src/inspect4all/core/models.py), [`output/json_writer.py`](../src/inspect4all/output/json_writer.py), [`output/json_reader.py`](../src/inspect4all/output/json_reader.py), and the two processors in [`enrichment/`](../src/inspect4all/enrichment/). When these models change, update this dictionary and its examples in the same pull request.

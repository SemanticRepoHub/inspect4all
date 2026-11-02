# Adding a new programming language to inspect4all

inspect4all currently extracts **Python** and **Java** structure. The pipeline is modular: discovery, aggregation and JSON/HTML output are shared, while parsing/extraction are implemented by **language adapters**. A contributor can add R, C, C++ or another language without rewriting the whole pipeline, but a reliable adapter still requires language-specific parser integration, mapping, tests and documentation.

## What to read first

- [`core/interfaces.py`](../src/inspect4all/core/interfaces.py): the `LanguageAdapter` abstract interface and `ParseResult`.
- [`core/models.py`](../src/inspect4all/core/models.py): unified `FileAnalysis`, `FileInfo`, `TypeInfo`, `FunctionInfo`, `ImportInfo`, `Dependency` and other dataclasses.
- [`adapters/registry.py`](../src/inspect4all/adapters/registry.py): `AdapterRegistry` and language name lookup.
- [`adapters/__init__.py`](../src/inspect4all/adapters/__init__.py): **`build_default_registry()` — register new adapters here**.
- [`adapters/python/adapter.py`](../src/inspect4all/adapters/python/adapter.py) and [`adapters/java/adapter.py`](../src/inspect4all/adapters/java/adapter.py): working examples.
- [`pipeline.py`](../src/inspect4all/pipeline.py): groups discovered files by language, looks up adapters and invokes them.
- [`discovery/scanner.py`](../src/inspect4all/discovery/scanner.py) and [`discovery/enry.py`](../src/inspect4all/discovery/enry.py): file/language discovery via go-enry.
- [`output/json_writer.py`](../src/inspect4all/output/json_writer.py) and [metadata dictionary](METADATA_SCHEMA.md): resulting fields.

## Contributor checklist

1. **Choose a parser and align detection names.** Determine the language string emitted by go-enry (e.g. `C++`; confirm this in a small local fixture rather than guessing). Decide how to parse its source files (e.g. an appropriate tree-sitter grammar, libclang/Clang for C/C++, or an R parser). Check dependency and licence compatibility. `AdapterRegistry.get(language)` uses an exact language-name match.
2. **Create a new adapter package**, e.g. `src/inspect4all/adapters/cpp/` containing `__init__.py`, `adapter.py`, and, as needed, `parser.py`, `extractor.py`, `dependencies.py`, `call_resolver.py`, `software_type.py`. Keep parser-specific nodes and conversion logic inside this package; do not put C++ AST objects into the shared JSON model.
3. **Implement `LanguageAdapter`** in `adapter.py`. The four required members are `language_name`, `file_extensions`, `parse_file(file_path) -> ParseResult`, and `extract_file_analysis(parse_result, repo_path) -> FileAnalysis`. The parser must return `ParseResult(file_path, tree, source)`; the extractor maps syntax into shared dataclasses, with repository-relative file paths and qualified names.
4. **Map core metadata deliberately.** Populate `FileInfo` (language, path, extension, package, test flag and optional documentation); `imports`, `types`, top-level `functions`, `main_info` as appropriate; types' `fields` and `methods`; function parameters, return types, call sites, line ranges and source documentation. Place genuine language-specific extras in `language_specific`, **not** new incompatible top-level keys. Preserve overloaded C++ methods as separate list entries.
5. **Handle failures explicitly.** Raise `UnsupportedFileTypeError` from `core/interfaces.py` when a file is a recognised but unsupported kind; the pipeline records it under `metadata.unhandled_files`. Syntax errors are recorded under `metadata.parse_failures` (see [`pipeline.py`](../src/inspect4all/pipeline.py)). Avoid silently returning incomplete *successful* records.
6. **Optionally implement repository-level hooks:** `extract_dependencies`, `detect_software_type`, `detect_tests`, `resolve_cross_file_calls` and `extract_ast_json`. Default implementations exist in `LanguageAdapter` and are valid initially; document unsupported features. Dependency extraction for C/C++ will require careful treatment of build systems such as CMake, Meson and Make.
7. **Register the adapter** in [`src/inspect4all/adapters/__init__.py`](../src/inspect4all/adapters/__init__.py), importing and instantiating it in `build_default_registry()`. This is the central integration point. Do not assume adding a source-file extension alone registers a language.
8. **Add unit and integration tests** under [`tests/adapters/`](../tests/adapters/) and [`tests/fixtures/`](../tests/fixtures/) with positive, unsupported and malformed examples; check outputs and optional fields. Use [`tests/output/`](../tests/output/) where appropriate and follow the existing test conventions.
9. **Validate the CLI and exports** with `inspect4all inspect --all -i /path/to/cpp-fixture -o /tmp/inspect4all-cpp-test`. Inspect `repository_analysis.json`, HTML and `embedding_export.json`; check that file records appear under `files[]`, the root `repository.languages` counts are sensible, and no parser objects or `None`-filled artifacts leak into serialized JSON.
10. **Update docs**: add the new language to [README](../README.md), [output documentation](OUTPUT_FORMATS.md), [metadata dictionary](METADATA_SCHEMA.md), examples and limits; add at least one reproducible mini-example. Open a PR with tests and note known parser/language-version limitations.

## Minimal adapter skeleton (illustrative)

This skeleton identifies the integration contract; it is **not** a finished C++ parser or a drop-in implementation.

```python
from pathlib import Path
from inspect4all.core.interfaces import LanguageAdapter, ParseResult
from inspect4all.core.models import FileAnalysis

class CppAdapter(LanguageAdapter):
    @property
    def language_name(self) -> str:
        return "C++"  # confirm exact go-enry output

    @property
    def file_extensions(self) -> list[str]:
        return [".cpp", ".cc", ".cxx", ".hpp", ".h"]

    def parse_file(self, file_path: Path) -> ParseResult:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ...  # invoke a C++ parser here
        return ParseResult(file_path=file_path, tree=tree, source=source)

    def extract_file_analysis(
        self, parse_result: ParseResult, repo_path: Path
    ) -> FileAnalysis:
        ...  # build the unified FileAnalysis / TypeInfo / FunctionInfo records
```

Then modify `src/inspect4all/adapters/__init__.py`:

```python
from inspect4all.adapters.cpp.adapter import CppAdapter
# retain the existing PythonAdapter and JavaAdapter imports
return AdapterRegistry(PythonAdapter(), JavaAdapter(), CppAdapter())
```

**C/C++ specifics:** header extensions such as `.h` are ambiguous; let the language detector and parser determine whether they should be treated as C or C++. Decide up front how to represent namespaces, free functions, templates, macros, overloaded operators, methods, and declarations versus definitions. Some structures will need `language_specific` fields rather than being shoehorned into inappropriate generic fields. Parser coverage, build-system integration and call resolution are significant work; *modular* means the existing pipeline can be reused, not that language support is automatic.

## Running checks

```bash
make libenry
uv sync
uv run pytest tests -q
inspect4all inspect --all -i examples/hello-world-python -o /tmp/inspect4all-python-check
inspect4all inspect --all -i examples/hello-world-java -o /tmp/inspect4all-java-check
```

Add a new-language fixture/run to this smoke-check sequence. Core inspection should remain usable **without** an LLM/API key; language-specific LLM processing (such as current Java parser-gap recovery) is **separate optional work** rather than automatically provided by an adapter.

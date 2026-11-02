# inspect4all — full technical reference
[![Pipeline Status](https://git.ecdf.ed.ac.uk/semanticrepohub/inspect4all/badges/main/pipeline.svg)](https://git.ecdf.ed.ac.uk/semanticrepohub/inspect4all/-/pipelines/latest)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
![Initial development is in progress, but there has not yet been a stable, usable release suitable for the public.](https://www.repostatus.org/badges/latest/wip.svg)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

<img src="docs/images/logo.png" alt="logo" width="200"/>

Inspect4all is a single language-agnostic tool for inspecting and understanding software repositories.

inspect4all is a **clean-room redesign** based on the extraction approaches and techniques of [inspect4py](https://github.com/SoftwareUnderstanding/inspect4py) (Python) and inspect4j (Java): rather than wrapping either tool, it rebuilds their structural extraction from first principles under one unified, language-agnostic schema. It extracts relevant information and metadata (functions/APIs, documentation such as README, dependencies, licenses, etc.) from software repositories in multiple programming languages, and outputs structured JSON for downstream analysis.

## Features

Given a folder (i.e. a git repository) with code, `inspect4all` will:

- Extract all imported modules, components, libraries, and APIs
- Extract all functions in the code, including their definitions, (parameters, return type, etc,), and documentation
- Extract all classes and structures in the code
- Extract the hierarchy of directories and files
- Extract library and software dependencies used in the software project or component
- Identify and classify tests from files
- Identify and classify the main type of the software project (script, package, library or service)
- Detect software invocation commands (entry points, test runners)

The main format for all metadata extracted is in JSON for supporting machine readability and automation.

inspect4all works only for **Python and Java projects** or a mix of these two languages (i.e. polyglot repository) for now. Other languages will be supported subsequently.

## Work Phases

The work on `inspect4all` is organized into three distinct phases and phase 1 is futher separated into phase 1a and phase 1b:

![inspect4all Processing Flow](docs/images/diss-overview.png)

1.  **Phase 1: Static Extraction (MVP)** — The core engine traverses the repository, identifies source files (using `go-enry`), and invokes language-specific adapters (Python/Java) to extract structural metadata into a unified JSON schema.
    - Phase 1a - Language Detection
    - Phase 1b - File and Repository Metadata Extraction
2.  **Phase 2: LLM-based and Agentic AI Enrichment (Stretch)** — An opt-in enrichment pipeline fills gaps that static analysis leaves: a `DocstringEnricher` generates documentation for undocumented functions via direct structured LLM generation, and a `JavaGapBackfillEnricher` recovers the structure of Java files the static parser could not read, using a minimal tool-using agent.
3.  **Future Work: Repository Similarity Detection** — Research into repository similarity detection with a reranker. A high-precision reranking agent reasons over the structured metadata to rescore top-k results, providing explainable and higher-precision rankings.

Below depicted a more details flow.

![inspect4all Detailed Flow](docs/images/inspect4all-flow.png)


## Architecture Overview

![inspect4all Pipeline Architecture](docs/images/pipeline-architecture.png)


## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [Go](https://go.dev/) 1.21+ (only to build the bundled language-detection library, see below)
- Docker (optional, for containerized development)

### Development Setup

```bash
# Clone and setup development environment
make dev-setup
```

This installs all dependencies and configures pre-commit hooks. Pre-commit hooks enforce ruff linting on every commit.

### Build the Language-Detection Library

Discovery uses [go-enry](https://github.com/go-enry/go-enry) (GitHub's linguist
port) through CFFI. The shared library is not tracked in git, so build it once
for development work after cloning:

```bash
make libenry
```

This clones go-enry at the pinned tag (`GO_ENRY_VERSION`, currently v2.9.4),
compiles its stock `shared/enry.go` c-shared wrapper with
`go build -buildmode=c-shared`, and places `libenry.dylib` in
`src/inspect4all/libs/`, where `discovery/enry.py` loads it from by default.

The Makefile detects the platform automatically: it produces `libenry.dylib` on macOS and `libenry.so` on Linux.

### Build the Tool

To build the python wheel and package for `inspect4all`, run the make command below. Additionally, a docker image can also be built.

```bash
# Build python wheel and sdist
make build

# Build production Docker image
make docker-build
```

### Run the Tool (development)

After building with `make build`:

```bash
inspect4all --help
inspect4all inspect -i /path/to/repo
```

During development, run directly with uv (no build step needed):

```bash
uv run inspect4all --help
uv run inspect4all inspect -i /path/to/repo
```

### Run on EIDF

Two approaches are available on an EIDF Ubuntu Linux VM. Docker (Approach A) requires no Python setup but needs registry authentication. Installing via uvx (Approach B) is lighter if Docker is not available or not preferred.

#### Approach A: Docker

The published multi-arch image lets you run the tool without a local Python environment.

The image is stored in the private GitLab container registry at `git.ecdf.ed.ac.uk:5050/semanticrepohub/inspect4all`. You must authenticate before pulling -- see [Accessing the private container registry](#accessing-the-private-container-registry) below.

Once authenticated, mount the repository to inspect as read-only and provide a writable output directory:

```bash
# Inspect only
docker run --rm \
  -v /path/to/repo:/repo:ro \
  -v /path/to/output:/out \
  git.ecdf.ed.ac.uk:5050/semanticrepohub/inspect4all:latest \
  inspect -i /repo -o /out -ee -r

# Inspect + enrich (requires LLM settings -- see Configuring with .env below)
docker run --rm \
  --env-file .env \
  -v /path/to/repo:/repo:ro \
  -v /path/to/output:/out \
  git.ecdf.ed.ac.uk:5050/semanticrepohub/inspect4all:latest \
  inspect -i /repo -o /out -ee -r --enrich

# Show CLI help
docker run --rm \
  git.ecdf.ed.ac.uk:5050/semanticrepohub/inspect4all:latest \
  --help
```

Output files (`repository_analysis.json`, `embedding_export.json`, etc.) are written to the host directory bound to `/out`.

#### Configuring with .env

Tool settings (LLM endpoint, model, API key, etc.) are read from environment variables. You can pass them into the container either via a file or inline:

```bash
# Option A: .env file (recommended for repeated use)
cp .env.example .env
# Edit .env with your LLM endpoint, model, and API key
docker run --rm --env-file .env ...

# Option B: inline environment variables (useful for one-off runs)
docker run --rm \
  -e INSPECT4ALL_LLM_BASE_URL=http://your-llm-server/v1 \
  -e INSPECT4ALL_LLM_MODEL=your-model-id \
  -e INSPECT4ALL_LLM_API_KEY=your-key \
  ...
```

The key variables are `INSPECT4ALL_LLM_BASE_URL`, `INSPECT4ALL_LLM_API_KEY`, and `INSPECT4ALL_LLM_MODEL`. See the [LLM Enrichment](#llm-enrichment-phase-2) section for the full variable reference.

#### Accessing the private container registry

The GitLab container registry at `git.ecdf.ed.ac.uk:5050` requires authentication because the project is private. The recommended approach on an EIDF Ubuntu Linux VM is a deploy token with `read_registry` scope (safer than a personal access token as it is read-only and project-scoped).

**Step 1 -- Create a deploy token in GitLab**

In the project, go to Settings > Repository > Deploy tokens. Create a token with the `read_registry` scope. Copy the username and token value shown on screen (the token is shown only once).

**Step 2 -- Install Docker on the VM** (skip if already installed)

```bash
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
# Log out and back in so the group change takes effect
```

**Step 3 -- Authenticate with the registry**

```bash
echo "<DEPLOY_TOKEN_VALUE>" | docker login git.ecdf.ed.ac.uk:5050 \
  --username <DEPLOY_TOKEN_USERNAME> --password-stdin
```

**Step 4 -- Pull and run**

```bash
docker pull git.ecdf.ed.ac.uk:5050/semanticrepohub/inspect4all:latest

docker run --rm \
  -v /path/to/repo:/repo:ro \
  -v /path/to/output:/out \
  git.ecdf.ed.ac.uk:5050/semanticrepohub/inspect4all:latest \
  inspect -i /repo -o /out -ee -r
```

#### Approach B: uvx (Python package)

`uvx` runs inspect4all from an isolated, cached environment. No Python project setup or Docker is needed. The first call downloads and installs the package; subsequent calls reuse the cache and start quickly.

**Install uv (if not already available):**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Then restart your shell, or add uv to the current session:
export PATH="$HOME/.local/bin:$PATH"
```

**From the internal GitLab package registry (latest dev build):**

The registry at `https://git.ecdf.ed.ac.uk/api/v4/projects/17748/packages/pypi/simple` requires a GitLab personal access token with `read_package_registry` scope. Embed the credentials in the URL so you are not prompted interactively:

```bash
# One-shot via uvx
uvx --prerelease=allow \
    --refresh-package inspect4all \
    --index-url "https://<username>:<token>@git.ecdf.ed.ac.uk/api/v4/projects/17748/packages/pypi/simple" \
    --extra-index-url https://pypi.org/simple \
    inspect4all --help

# Persistent install or update (works for first-time install and subsequent updates)
uv tool install \
  --reinstall \
  --refresh-package inspect4all \
  --prerelease=allow \
  --index-url "https://<username>:<token>@git.ecdf.ed.ac.uk/api/v4/projects/17748/packages/pypi/simple" \
  --extra-index-url https://pypi.org/simple \
  inspect4all
inspect4all --help
inspect4all inspect -i /path/to/repo -o /path/to/output -ee -r
```

Three flags are needed for dev builds from this registry:

- `--prerelease=allow` — dev builds (e.g. `0.1.dev117`) are pre-releases; uv skips them unless this flag is set.
- `--refresh-package inspect4all` — invalidates uv's cached index metadata so it sees the latest published wheel.
- `--reinstall` — forces replacement even when the installed and available versions share the same public version number (dev builds carry a `+g<commit>` local identifier that uv does not use for upgrade comparisons).

### LLM Enrichment (Phase 2)

Phase 2 runs two independent enrichment processors, selectable via `--processors`. Both share the same cache file (`enrichment_cache.jsonl`) and environment-variable configuration.

#### Processor 1: Docstring enrichment (`--processors docstrings`)

Generates docstring-style summaries for undocumented (or all) functions and methods, writing them as provenance-tagged enrichments so the original extracted documentation is never mutated.

- **Call-graph guided order**: callees are documented before callers. The extracted call graph is topologically sorted so each generation receives short summaries of the function's resolved in-project callees as context.
- **Language-specific prompts**: Java methods get Javadoc-style guidance; Python functions get Google-style guidance. The correct prompt is selected automatically from `FileInfo.language`.
- **Class context for methods**: when a method is inside a class, the enclosing class name, kind, and base classes/interfaces are included in the prompt.
- **Direct structured generation**: one `model.invoke` per record returns a JSON object (`short_description`, `params`, `returns`) validated in Python. One automatic retry on malformed output; failed records are cached and retried on the next run.
- **Target selection**: by default (`--docstring-target undocumented`) only functions without existing documentation are processed. Pass `--docstring-target all` to generate or replace docstrings for every function, including already-documented ones.
- **Hash-based cache invalidation**: the cache stores a content hash alongside the status. If a function's source is edited, the stale "ok" entry is invalidated and the record is re-generated.

#### Processor 2: Java gap backfill (`--processors java-backfill`)

`javalang` (the primary Java parser) does not support post-Java-8 syntax — records, sealed classes, switch expressions, text blocks. Files that fail parsing are recorded in `metadata.parse_failures["Java"]` during inspection; they produce no `FileAnalysis` and are invisible to the embedding export and downstream similarity.

The gap backfill processor recovers these files using a minimal tool-using agent with four task-specific tools:

- **Input**: the repo-relative path and raw source of each failed file.
- **Tools**: `tree_sitter_parse` (returns the concrete syntax tree as JSON), `read_source_slice(start, end)` (returns raw source lines), `emit_file_analysis` (validates the agent's structured output against the unified schema and writes it to a collector), and `check_completeness` (verifies the emitted analysis against a **deterministic** tree-sitter ground truth, returning `COMPLETE` or a prioritised list of gaps to fix).
- **Loop**: up to 20 tool turns and 300 seconds per file. The agent calls `tree_sitter_parse`, reads any needed slices, emits with `emit_file_analysis` (reconstructed imports, types, fields, methods, Javadoc, and line ranges), and `check_completeness` closes the loop — on a validation error or a reported gap the agent fixes the payload and emits again.
- **Output**: an accepted emission is appended to `repo.files` as a new `FileAnalysis` with `language_specific.backfilled = {"by": "llm", "model": "..."}`. `metadata.parse_failures` is left intact as a corpus metric.
- **Cache**: the same hash-based `enrichment_cache.jsonl` prevents re-work across reruns.

Configuration comes from environment variables (or a `.env` file):

| Variable | Default | Description |
| --- | --- | --- |
| `INSPECT4ALL_LLM_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible endpoint (LM Studio default) |
| `INSPECT4ALL_LLM_API_KEY` | `lm-studio` | API key (local servers usually ignore it) |
| `INSPECT4ALL_LLM_MODEL` | `qwen/qwen3.5-35b-a3b` | Model id to request |
| `INSPECT4ALL_LLM_TEMPERATURE` | `0.0` | Sampling temperature |
| `INSPECT4ALL_LLM_MAX_TOKENS` | `4096` | Max generation tokens per LLM call |
| `INSPECT4ALL_LLM_REASONING_EFFORT` | unset | Set to `none` for reasoning models: hidden thinking otherwise counts against `MAX_TOKENS` and can leave the visible answer empty. Leave unset for non-reasoning models |

Any OpenAI-compatible server works by config only: LM Studio, a LiteLLM
proxy, Ollama, or OpenAI itself. When serving locally, load the model
with a context window of 8k+ tokens so gap-backfill syntax trees fit.

See [CLI Reference](#cli-reference) below for all subcommands and flags. In the full pipeline, an unreachable LLM server downgrades enrichment to
a warning; the inspection outputs are always written.

Enriched outputs are written alongside the originals as
`repository_analysis.enriched.json` and `embedding_export.enriched.json`;
the original `repository_analysis.json` and `embedding_export.json` are
never modified. A per-record `enrichment_cache.jsonl` in the output
directory makes reruns skip already-enriched records while keeping their
earlier enrichments.

An opt-in live smoke test verifies the full loop against a running
server: `uv run pytest -m llm_smoke` (requires `INSPECT4ALL_LLM_BASE_URL`
to be set).

## CLI Reference

### `inspect4all inspect`

Inspect a repository and write structural analysis to an output directory.

```bash
inspect4all inspect -i /path/to/repo [options]
```

| Flag | Long form | Description |
|------|-----------|-------------|
| `-i` | `--input_path` | **(required)** Path to the repository to inspect. |
| `-o` | `--output_dir` | Output directory. Created if it does not exist. Default: `inspect4all_output/` in the current directory. |
| `-r` | `--requirements` | Extract library dependencies (`requirements.txt`, `pom.xml`, `build.gradle`, etc.). |
| `-ee` | `--embedding_export` | Write `embedding_export.json` with embedding-ready text records (code, docs, README, combined). Intended for downstream repository similarity detection. |
| `-ld` | `--license_detection` | Detect the repository license. |
| `-rm` | `--readme` | Extract all README files in the repository. |
| `-si` | `--software_invocation` | Detect software invocation commands (entry points, test commands). |
| `-md` | `--metadata` | Extract GitHub repository metadata via the GitHub API. |
| `-html` | `--html_output` | Generate an HTML view of `repository_analysis.json` in the output directory. |
| `--enrich` | | After inspecting, run LLM enrichment (docstring generation + Java gap backfill) and write `repository_analysis.enriched.json` and `embedding_export.enriched.json` alongside the originals. |
| `--all` | | Enable all analysis features. |
| `-v` | `--verbose` | Enable verbose output. |
| `-ignore_dir` | `--ignore_dir_pattern` | Ignore directories matching a pattern. Repeatable. |
| `-ignore_file` | `--ignore_file_pattern` | Ignore files matching a pattern. Repeatable. |

**Outputs written to `--output_dir`:**

| File | Condition | Description |
|------|-----------|-------------|
| `repository_analysis.json` | always | Full structural analysis (types, methods, calls, imports, docs, etc.). |
| `embedding_export.json` | `-ee` or `--all` | Flat embedding export with `code_records[]` and `doc_records[]`. |
| `repository_analysis.enriched.json` | `--enrich` | Enriched analysis (enrichments appended; original never modified). |
| `embedding_export.enriched.json` | `--enrich` | Enriched embedding export (`enriched_doc` filled for undocumented methods). |
| `enrichment_cache.jsonl` | `--enrich` | Per-record cache -- reruns skip already-enriched records. |

### `inspect4all enrich`

Enrich a previously written analysis directory with LLM enrichment (docstrings and Java gap backfill).

```bash
inspect4all enrich -i /path/to/output_dir [options]
```

| Flag | Description |
|------|-------------|
| `-i` / `--input_dir` | **(required)** Directory containing a prior `repository_analysis.json`. |
| `--model ID` | Override `INSPECT4ALL_LLM_MODEL`. |
| `--base-url URL` | Override `INSPECT4ALL_LLM_BASE_URL`. |
| `--api-key KEY` | Override `INSPECT4ALL_LLM_API_KEY`. |
| `--temperature F` | Override `INSPECT4ALL_LLM_TEMPERATURE`. |
| `--max-tokens N` | Override `INSPECT4ALL_LLM_MAX_TOKENS`. |
| `--reasoning-effort S` | Override `INSPECT4ALL_LLM_REASONING_EFFORT` (e.g. `none` for reasoning models). |
| `--max-records N` | Cap the number of records enriched per run (cost control). |
| `--mode enriched\|combined` | Embedding export mode for `embedding_export.enriched.json`. Default: `enriched`. |
| `--processors docstrings\|java-backfill` | Enrichers to run. Repeatable: `--processors docstrings --processors java-backfill`. Defaults to both when omitted. `docstrings` generates LLM summaries for undocumented (or all) functions; `java-backfill` recovers Java files that failed javalang parsing using a tree-sitter agent. |
| `--docstring-target undocumented\|all` | Which functions the docstring enricher considers. `undocumented` (default) skips already-documented functions; `all` re-enriches everything. |

### `inspect4all run`

Inspect a repository and immediately enrich it. Enrichment always runs — there is no `--enrich` flag on this subcommand. Accepts all the same inspect flags otherwise.

```bash
inspect4all run -i /path/to/repo -ee -r -ld -rm
# equivalent (run is the default when no subcommand is given):
inspect4all -i /path/to/repo -ee -r -ld -rm
```

### Typical usage in corpus pipelines

```bash
# Phase 1: inspect all repos -- extract structure + embedding export
inspect4all inspect -i /path/to/repo -o out/ -ee -r -ld -rm

# Phase 2: enrich a previously inspected output directory
inspect4all enrich -i out/ --max-records 40

# One-shot: inspect + enrich in a single call
inspect4all inspect -i /path/to/repo -o out/ -ee -r -ld -rm --enrich
```

## Commands

### Development

| Command              | Description                                                     |
| -------------------- | --------------------------------------------------------------- |
| `make dev-setup`     | Setup development environment (install deps + pre-commit hooks) |
| `uv run inspect4all` | Run inspect4all (pass flags directly, e.g. `inspect -i /path/to/repo`) |
| `make test`          | Run tests                                                       |
| `make test-cov`      | Run tests with coverage report                                  |

### Code Quality

| Command             | Description                                                |
| ------------------- | ---------------------------------------------------------- |
| `make lint`         | Check linting (ruff)                                       |
| `make lint-fix`     | Auto-fix lint issues                                       |
| `make format`       | Format code (ruff)                                         |
| `make format-check` | Check code formatting                                      |
| `make type-check`   | Run type checking (mypy)                                   |
| `make all-checks`   | Run all quality checks (lint + format + type-check + test) |

### Docker

| Command                          | Description                              |
| -------------------------------- | ---------------------------------------- |
| `make docker-build`              | Build production Docker image            |
| `make docker-build-all`| Build production image for amd64 + arm64 |
| `make docker-test`               | Run tests in container                   |
| `make docker-lint`               | Run linting in container                 |
| `make docker-down`               | Stop Docker containers                   |

<details>
<summary>Alternative: Using docker and docker compose directly</summary>

```bash
# Run tests
docker compose run --rm test

# Run linting
docker compose run --rm lint

# Build production image
docker build --target production -t inspect4all .

# Run the CLI tool via the production image
docker run --rm inspect4all --help
docker run --rm -v /path/to/repo:/data inspect4all inspect -i /data
```

</details>

### DevContainer (VS Code / GitHub Codespaces) Support

Open the project in VS Code, and select "Reopen in Container" when prompted, or use the Command Palette: `Dev Containers: Reopen in Container`.

## Releasing

This project uses [semver](https://semver.org/) with versions derived automatically from git tags via `hatch-vcs`.

To create a new release:

```bash
# 1. Ensure all checks pass
make all-checks

# 2. Tag the release
git tag v0.2.0
git push origin v0.2.0

# 3. The CI pipeline will run automatically. Go to the GitLab pipeline
#    and click the play button on the "publish-pypi" job to publish to PyPI.
```

The tag format must be `vMAJOR.MINOR.PATCH` (e.g., `v0.2.0`, `v1.0.0`). The `v` prefix is stripped automatically when setting the package version.

### Multi-platform wheel distribution

`inspect4all` bundles `libenry`, a Go-compiled shared library (`libenry.so` on Linux, `libenry.dylib` on macOS). Because each wheel contains a platform-specific binary, Linux and macOS wheels are separate files and must both be published for users on either platform.

**Platform coverage:**

| Platform | Build | Publish |
|---|---|---|
| Linux (x86\_64, arm64) | Automatic — CI pipeline on every push to `main` | Automatic — `publish-internal` CI job |
| macOS (arm64) | Manual — no macOS runner available on EIDF | Manual — run steps below from a Mac |

#### After every push to `main` (internal GitLab registry)

The CI pipeline publishes the Linux wheel automatically. To make the macOS wheel available from the internal registry at the same version, run the following from a Mac after the pipeline completes:

```bash
# 1. Pull to be at the exact same commit as the CI build
git pull

# 2. Build the macOS shared library (requires Go)
make libenry

# 3. Build the macOS wheel -- version is derived from git and will match the CI Linux wheel
uv build --wheel

# 4. Publish to the internal GitLab package registry
uv publish \
  --publish-url "https://git.ecdf.ed.ac.uk/api/v4/projects/17748/packages/pypi" \
  --username <your-gitlab-username> \
  --password <personal-access-token-with-write_package_registry-scope> \
  dist/inspect4all-*-macosx_*.whl
```

The version in step 3 is computed by `hatch-vcs` from the git history. As long as you run `git pull` first (step 1), the macOS wheel version will match the Linux wheel already in the registry.

#### On a tagged release (internal registry)

The CI `publish-internal` job publishes the Linux wheel automatically on a tag. Run the following from a Mac after that pipeline completes:

```bash
# 1. Check out the release tag
git fetch --tags
git checkout v<version>

# 2. Build macOS library and wheel
make libenry
uv build --wheel

# 3. Publish the macOS wheel to the internal GitLab registry
uv publish \
  --publish-url "https://git.ecdf.ed.ac.uk/api/v4/projects/17748/packages/pypi" \
  --username <your-gitlab-username> \
  --password <personal-access-token-with-write_package_registry-scope> \
  dist/inspect4all-*-macosx_*.whl
```

#### Installing and using from the internal registry

Once both platform wheels are published (Linux by CI, macOS manually), follow [Approach B: uvx](#approach-b-uvx-python-package) in the Quick Start section to install and run inspect4all.

## Project Structure

```
.
|-- src
|   |__ inspect4all
|       |-- cli.py              # Click entry point
|       |-- pipeline.py         # Orchestrates discovery -> adapters -> analysis -> output
|       |-- core/               # Shared vocabulary: no dependencies on other layers
|       |   |-- models.py       #   Unified schema (FileAnalysis, FunctionInfo, Documentation, ...)
|       |   |-- interfaces.py   #   LanguageAdapter (parse_file, extract_file_analysis, detect_tests, ...) + EnrichmentProcessor ABCs
|       |   |-- options.py      #   InspectOptions (per-run flags)
|       |   |-- constants.py    #   EmbeddingMode, default ignore dirs
|       |   |__ config.py       #   Settings via pydantic-settings
|       |-- discovery/          # Language detection (go-enry via cffi) + repo scanning
|       |   |-- enry.py         #   go-enry CFFI bindings (language + type per file)
|       |   |__ scanner.py      #   RepositoryScanner: walks the tree -> FileManifest
|       |-- adapters/           # One package per language + AdapterRegistry
|       |   |-- __init__.py     #   build_default_registry() — register new languages here
|       |   |-- registry.py     #   AdapterRegistry (language name -> adapter lookup)
|       |   |-- python/         #   parser, extractor, docstrings, calls, deps, software type
|       |   |__ java/           #   parser, extractor, javadoc, calls, deps, software type
|       |-- analysis/           # Language-agnostic aggregation (Phase 1b, repository level)
|       |   |-- aggregator.py      #   Orchestrates repo-level ops -> RepositoryAnalysis
|       |   |-- call_graph.py      #   Cross-file call graph construction
|       |   |-- directory_tree.py  #   Flat directory tree with per-file metadata
|       |   |-- git_metadata.py    #   Git / remote metadata extraction
|       |   |-- license.py         #   SPDX license detection (Dice similarity)
|       |   |__ readme.py          #   README discovery and extraction
|       |-- enrichment/         # LLM enrichment processors (Phase 2)
|       |   |-- docstring_enricher.py  #   Undocumented function/method enrichment
|       |   |-- java_gap_backfill.py   #   Agent-based recovery for javalang parse failures
|       |   |-- generate.py            #   Direct structured LLM call + JSON validation
|       |   |-- build_order.py         #   Call-graph topological sort (callees first)
|       |   |-- targets.py             #   Target selection with language + class context
|       |   |-- harness.py             #   Agent loop runner with timeout + recursion limit
|       |   |-- backoff.py             #   Exponential backoff for transient LLM errors
|       |   |-- tools.py               #   Java gap backfill tool belt (tree-sitter + emit)
|       |   |-- cache.py               #   JSONL cache with content-hash invalidation
|       |   |-- pipeline.py            #   EnrichmentPipeline (runs processors in order)
|       |   |-- runner.py              #   Disk-level entry point (load -> enrich -> write)
|       |   |__ llm.py                 #   Model factory (OpenAI-compatible, env-configured)
|       |-- output/             # JSON writer + four-level embedding export
|       |-- libs/               # Compiled go-enry shared library (libenry.so/.dylib)
|       |__ resources/          # Vendored SPDX license templates
|-- tests/                      # Mirrors src layout; tests/smoke runs the CLI on real repos
|   |__ fixtures/               # Vendored single-language repos for the smoke gate
|-- scripts/                    # Ground-truth batch runner + analysis notes
|-- docs/                       # Architecture docs and implementation plans
|-- .devcontainer/              # VS Code devcontainer config
|-- .env.example                # Environment variables template
|-- Dockerfile                  # Multi-stage Docker build
|-- docker-compose.yaml         # Local development setup
|-- Makefile                    # Common commands
|__ pyproject.toml              # Project config and dependencies
```

## Python Parser: Non-Standard Syntax

The Python adapter's `ast`-based parser is limited to syntax supported by the current runtime (Python 3.12). Files that fail `ast.parse()` are routed to `metadata.unhandled_files` (not `metadata.parse_failures`) when a cause can be identified:

| Cause | `unhandled_files` kind | Notes |
|-------|------------------------|-------|
| Python 2 (`print` statement incl. inline, `exec` statement, `except E, e:`, `raise E, msg`) | `Python2Legacy` | Detected via Python 3's own `SyntaxError.msg` for print/exec; regex for other forms; full source scanned (no line limit) |
| t-strings (`t"..."`, PEP 750) | `UnsupportedPythonSyntax` | Supported natively if runtime is upgraded to Python 3.14+ |
| `async` as a module name (`from x.async.y import`) | `UnsupportedPythonSyntax` | Valid pre-3.7; `async` became a reserved keyword in Python 3.7 |
| Jinja2 template content (`{%`, `{{` markers in source) | `Jinja2Content` | Catches `.py`-extension templates with no Jinja2 path markers |
| Dockerfile instructions (`FROM`, `RUN`, `COPY`, ...) | `DockerfileContent` | Catches misnamed files such as `Dockerfile.py3` |

Files that are genuinely invalid Python with no identifiable cause remain in `metadata.parse_failures`.

## Adding a New Language

Support for a language is a self-contained **adapter package**: the pipeline,
analysis, and output layers never change. The contract is the
`LanguageAdapter` ABC in `src/inspect4all/core/interfaces.py`; the
`AdapterRegistry` is how the pipeline finds your adapter by the language name
that [go-enry](https://github.com/go-enry/go-enry) reports for each file.

The steps below use **C++** as the example (enry reports it as `"C++"`).

### 1. Create the adapter package

```
src/inspect4all/adapters/cpp/
|-- __init__.py
|-- parser.py          # Source text -> AST (e.g. tree-sitter-cpp or libclang)
|-- extractor.py       # AST -> unified models (FunctionInfo, TypeInfo, ...)
|-- doc_parser.py      # Doc comments (Doxygen) -> Documentation model
|-- call_resolver.py   # Optional: qualify cross-file call names
|-- dependencies.py    # Optional: CMakeLists.txt / conanfile -> Dependency
|-- software_type.py   # Optional: detect service/library/application
|__ adapter.py         # CppAdapter — wires the pieces to the ABC
```

Mirror the same layout under `tests/adapters/cpp/`. Write the tests first —
see the existing `tests/adapters/java/` suite for the expected shape.

### 2. Implement the `LanguageAdapter` contract

Only two methods plus two properties are mandatory; everything else has a
safe default in the ABC. The skeleton below is a minimal but complete
starting point using [tree-sitter](https://tree-sitter.github.io/)
(`uv add tree-sitter tree-sitter-cpp`) — it extracts free functions with
their source and line ranges; the `TODO` markers show where each further
feature plugs in.

```python
# src/inspect4all/adapters/cpp/parser.py
from __future__ import annotations

from pathlib import Path

import tree_sitter_cpp
from tree_sitter import Language, Parser

from inspect4all.core.interfaces import ParseResult

_CPP_LANGUAGE = Language(tree_sitter_cpp.language())


class CppParser:
    def parse(self, file_path: Path) -> ParseResult:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = Parser(_CPP_LANGUAGE).parse(source.encode())
        # tree-sitter is error-tolerant: a partial tree is still usable.
        # Raise UnsupportedFileTypeError for input that is not C++ at all
        # (e.g. enry misidentified the file); raise SyntaxError for genuinely
        # broken C++ that cannot be partially recovered.
        return ParseResult(file_path=file_path, tree=tree, source=source)
```

```python
# src/inspect4all/adapters/cpp/adapter.py
from __future__ import annotations

from pathlib import Path

from inspect4all.adapters.cpp.parser import CppParser
from inspect4all.core.interfaces import LanguageAdapter, ParseResult
from inspect4all.core.models import FileAnalysis, FileInfo, FunctionInfo


class CppAdapter(LanguageAdapter):
    @property
    def language_name(self) -> str:
        return "C++"  # MUST match enry's label exactly

    @property
    def file_extensions(self) -> list[str]:
        return [".cpp", ".cc", ".cxx", ".hpp", ".h"]

    def parse_file(self, file_path: Path) -> ParseResult:
        return CppParser().parse(file_path)

    def extract_file_analysis(
        self, parse_result: ParseResult, repo_path: Path
    ) -> FileAnalysis:
        path = parse_result.file_path
        try:
            rel = path.relative_to(repo_path)  # repo-relative, always
        except ValueError:
            rel = path
        module = str(rel.with_suffix("")).replace("/", ".")

        functions = [
            self._build_function(node, module)
            for node in _walk(parse_result.tree.root_node)
            if node.type == "function_definition"
        ]

        file_info = FileInfo(
            path=str(rel),
            name=path.stem,
            extension=path.suffix,
            language="C++",
            package=None,  # TODO: map enclosing namespace here
            documentation=None,
            is_test="test" in path.stem.lower(),
        )
        return FileAnalysis(
            file=file_info,
            imports=[],  # TODO: preproc_include nodes -> ImportInfo
            types=[],  # TODO: class_specifier/struct_specifier -> TypeInfo
            functions=functions,
            main_info=None,  # TODO: detect int main(...)
            language_specific={},
        )

    def _build_function(self, node, module: str) -> FunctionInfo:
        declarator = node.child_by_field_name("declarator")
        name_node = (
            declarator.child_by_field_name("declarator") if declarator else None
        )
        name = name_node.text.decode() if name_node else "<anonymous>"
        return FunctionInfo(
            name=name,
            qualified_name=f"{module}.{name}",
            documentation=None,  # TODO: preceding Doxygen comment -> doc_parser
            source_code=node.text.decode(),
            parameters=[],  # TODO: parameter_list -> ParameterInfo
            return_type=None,
            modifiers=[],
            annotations=[],
            calls=[],  # TODO: call_expression nodes, then call_resolver.py
            line_range=(node.start_point[0] + 1, node.end_point[0] + 1),
            is_constructor=False,
            nested_functions=[],
            language_specific={},
        )


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)
```

This skeleton already satisfies the contract: register it (step 3) and C++
files will appear in `repository_analysis.json` and `embedding_export.json`
with names, source, and line ranges.

Optional overrides (defaults are no-ops, so you can ship incrementally):

| Method | Purpose | Reference implementation |
|---|---|---|
| `extract_dependencies(repo_path)` | Declared deps from manifests (`CMakeLists.txt`, `conanfile.txt`) | `adapters/python/dependencies.py` |
| `detect_software_type(files, deps, repo_path)` | service / library / application heuristic; returns `SoftwareTypeResult` | `adapters/java/software_type.py` |
| `resolve_cross_file_calls(files)` | Rewrite local call names to repo-internal qualified names | `adapters/java/call_resolver.py` |
| `detect_tests(files, repo_path)` | Identify test files and emit `TestEntry` records (type, run command, language, file list) | `adapters/python/adapter.py` |
| `extract_ast_json(parse_result)` | Return a language-specific AST snapshot for the embedding export's `ast_json` field; return `None` to omit | `adapters/java/adapter.py` |

Conventions the rest of the pipeline relies on:

- **Repo-relative everything** — `FileInfo.path` and every `qualified_name` must not contain absolute filesystem paths.
- **Unresolved calls stay unchanged** — never drop a call name you cannot qualify; stdlib/third-party calls are expected to remain unqualified.
- **Doc comments go through `Documentation`** — populate `short_description`, `params`, `returns`, `raises` so documentation is uniformly structured in the output JSON.
- **Raise on failure, never silently skip** — two exception types with different pipeline routing:
  - `SyntaxError`: the file is genuinely broken (invalid syntax); the pipeline logs a warning and routes it to `metadata.parse_failures`.
  - `UnsupportedFileTypeError(file_type)`: the file is valid but not parseable by this adapter (e.g. a Cython file detected as Python, a Jinja2 template, Python 2 source); the pipeline routes it to `metadata.unhandled_files` instead, keeping `parse_failures` counts meaningful.

### 3. Register the adapter

One line in `src/inspect4all/adapters/__init__.py`:

```python
def build_default_registry() -> AdapterRegistry:
    from inspect4all.adapters.java.adapter import JavaAdapter
    from inspect4all.adapters.python.adapter import PythonAdapter
    from inspect4all.adapters.cpp.adapter import CppAdapter  # add this

    return AdapterRegistry(PythonAdapter(), JavaAdapter(), CppAdapter())  # add CppAdapter
```

That is the only integration point. Discovery already detects C++ files (via
enry); until an adapter is registered they are listed under
`metadata.unhandled_files` in the output, and once registered they flow
through parsing, aggregation, the call graph, and the embedding export
automatically.

### 4. Verify

```bash
# Unit tests for the new adapter
env -u VIRTUAL_ENV uv run pytest tests/adapters/cpp -v

# Mixed-language dispatch still works (see test_pipeline_mixed_language_repo)
env -u VIRTUAL_ENV uv run pytest tests/test_pipeline.py -v

# Full gate: lint, format, mypy, unit + smoke on real repos
make all-checks
```

Optionally vendor a small real C++ repository under `tests/fixtures/` and add
it to `FIXTURE_REPOS` in `tests/smoke/test_ground_truth.py` so the smoke gate
exercises the new language end-to-end on every run.

## Configuration

Configuration is managed via environment variables using `pydantic-settings`. Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

## Tech Stack

- **Language**: Python 3.12+
- **Package Management**: uv
- **Linting/Formatting**: ruff
- **Type Checking**: mypy
- **Testing**: pytest, pytest-cov
- **Containerization**: Docker, docker-compose, devcontainer

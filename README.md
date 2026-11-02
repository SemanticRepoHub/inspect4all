# inspect4all

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://python.org) [![BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE) [![Zenodo DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23895264.svg)](https://doi.org/10.5281/zenodo.23895264)

**Inspect Python and Java code repositories, export structured metadata, and optionally enrich missing documentation using an LLM.** The core inspection is entirely usable **without an OpenAI API key**. LLM enrichment is opt-in and needs an accessible model endpoint (for OpenAI, an API key and API credits).

![Workflow overview](docs/images/workflow.svg)

## Features

- Detect languages using go-enry, parse Python and Java, recover functions, methods, types, dependencies, calls and repository structure.
- Export `repository_analysis.json`, optionally HTML and embedding-ready JSON.
- Optionally generate missing function/method descriptions and backfill Java parse failures with LLMs, retaining the original analysis and provenance metadata.
- Support mixed Python/Java repositories. Other language adapters and similarity reranking are future work, not current CLI features.

## Installation

### Option 1 — Install from PyPI (recommended)

The published package is available on **[PyPI — inspect4all](https://pypi.org/project/inspect4all/)**. With **Python 3.12+**, create an isolated environment and install it using pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install inspect4all
inspect4all --help
```

On **2 November 2026**, `inspect4all==0.1.1` was successfully installed in a fresh Python 3.12 virtual environment on **macOS Apple Silicon**, without building the native `libenry` library separately. Its packaged native library worked for repository inspection. In that test, `inspect4all inspect --all -i d4py -o d4py_output` completed successfully and produced `repository_analysis.json`, `repository_analysis.html`, and `embedding_export.json`. Other platforms have not been independently verified in this test; platform-specific wheels may differ in availability.

To try the tool directly on a real repository after installation:

```bash
git clone https://github.com/StreamingFlow/d4py.git
inspect4all inspect --all -i d4py -o d4py_output
ls -lh d4py_output/
```

**Static inspection does not need an LLM API key.** The optional `enrich` command requires an accessible and configured model endpoint, as described below.

To upgrade a PyPI installation within the active environment:

```bash
python -m pip install --upgrade inspect4all
```

### Option 2 — Build and install from GitHub source

Choose this method if you want to develop inspect4all, use unreleased source changes, or build the native language-detection library yourself. **Requirements:** Git, Python 3.12+, [uv](https://docs.astral.sh/uv/), [Go](https://go.dev/), Make, and a C compiler (CGo). On macOS, Go can be installed with Homebrew:

```bash
brew install go
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Ubuntu/Debian, ensure Git, Make, a C compiler, and a sufficiently recent Go compiler are installed. The Makefile supports Linux, but a fresh Linux installation was not independently tested here. Native Windows installation is not yet documented.

```bash
git clone https://github.com/SemanticRepoHub/inspect4all.git
cd inspect4all
make libenry
uv tool install --force .
inspect4all --help
inspect4all inspect --help
inspect4all enrich --help
```

> When **building from source**, the order matters: `make libenry` builds the platform-specific library before Python packaging. This does **not** apply to the verified prebuilt PyPI wheel on macOS Apple Silicon. A direct `uv tool install git+https://...` may still fail because it does not run the native build step first.

To update a source installation:

```bash
cd /path/to/inspect4all
git pull --ff-only
make libenry
uv tool install --force .
```

## Test 1: Inspect a repository (NO API key)

The following bundled examples are available **after cloning the GitHub repository**; run them from the repository root. If you installed only from PyPI, start with the d4py example above or another local repository.

**Bundled Python fixture:**

```bash
inspect4all inspect --all -i examples/hello-world-python -o python_inspect
ls -lh python_inspect/
```

**Bundled Java fixture:**

```bash
inspect4all inspect --all -i examples/hello-world-java -o java_inspect
```

**Any local repository:**

```bash
inspect4all inspect --all -i /absolute/path/to/your/repository -o repo_inspect
```

You should see `repository_analysis.json`, `repository_analysis.html`, and `embedding_export.json` with `--all`. In a fresh GitHub source installation, a local d4py checkout was inspected successfully in approximately **4.713 seconds** (one test, not a reproducible performance benchmark).

## Real-world example — inspect and enrich StreamingFlow/d4py

Alongside the bundled Python and Java mini-examples, we provide a **real, reproducible repository inspection** using [StreamingFlow/d4py](https://github.com/StreamingFlow/d4py), an open-source scientific-workflow codebase.

![Real-world d4py inspection and optional LLM enrichment](docs/images/d4py-real-world.svg)

*Note: Example results may vary by repository revision, model, and configuration.*

The diagram distinguishes **static inspection (no API key)** from **optional LLM enrichment (a configured compatible model endpoint and credentials)**. The reported two successful enrichments come from the supplied d4py test output, not an assertion that every run produces identical text.

```bash
git clone https://github.com/StreamingFlow/d4py.git demo-d4py
inspect4all inspect --all -i demo-d4py -o d4py_inspect
```

This completed successfully on macOS Apple Silicon on 2 November 2026 and produced the JSON, HTML and embedding export outputs. Two functions were then enriched with `gpt-5.6-luna` using the optional LLM processor (two successes recorded in the cache):

```bash
inspect4all enrich -i d4py_inspect --max-records 2 --processors docstrings
```

**See [the complete real-world walkthrough and actual before/after metadata](examples/d4py-real-world/README.md)**. An API key is **not** required for inspection; enrichment requires an authorised OpenAI-compatible LLM service and its credentials. The University of Edinburgh ELM gateway may be used if configured and authorised; a University key is not interchangeable with a direct OpenAI API key.

## Test 2: Optional LLM enrichment (OpenAI API key required for OpenAI)

![LLM enrichment](docs/images/enrichment.svg)

After **Test 1**, you can ask a configured LLM to enrich a small sample. Inspect4all can use an **OpenAI-compatible API**: this can be OpenAI's hosted API, or a compatible local model server. It does **not** automatically provide an OpenAI key or API credits. A ChatGPT subscription is separate from OpenAI API billing.

### Option A — OpenAI

1. Create an API key in your [OpenAI API account](https://platform.openai.com/api-keys), and check that API billing and model access are enabled.
2. Use a **model identifier actually available to your API account**, rather than an older example name.
3. Configure the endpoint and key. The following invisible-key prompt works in macOS **zsh**:

```bash
export INSPECT4ALL_LLM_BASE_URL="https://api.openai.com/v1"
export INSPECT4ALL_LLM_MODEL="YOUR_SUPPORTED_OPENAI_API_MODEL"
export INSPECT4ALL_LLM_MAX_TOKENS=4096
read -s "INSPECT4ALL_LLM_API_KEY?OpenAI API key: "
export INSPECT4ALL_LLM_API_KEY
echo
```

For bash replace the `read -s` line with `read -r -s -p "OpenAI API key: " INSPECT4ALL_LLM_API_KEY`.

**Small, cost-limited example:**

```bash
inspect4all enrich -i python_inspect --max-records 2 --processors docstrings
ls -lh python_inspect/
```

When eligible records are present and the LLM call succeeds, this writes `repository_analysis.enriched.json` and cache files **without overwriting the original**. The outputs contain model-derived documentation and provenance; descriptions need human review.

**Java recovery**, when applicable, uses `--processors java-backfill`. Run `inspect4all enrich --help` for all flags, including `--docstring-target`, `--model`, `--reasoning-effort`, and `--max-records`.

### Option B — Local model, no OpenAI API key

If you run a compatible local endpoint (for example LM Studio), you can use:

```bash
export INSPECT4ALL_LLM_BASE_URL="http://localhost:1234/v1"
export INSPECT4ALL_LLM_API_KEY="lm-studio"
export INSPECT4ALL_LLM_MODEL="YOUR_LOADED_LOCAL_MODEL_ID"
inspect4all enrich -i python_inspect --max-records 2 --processors docstrings
```

The local model must already be running and support the necessary response format; compatibility and quality vary. No OpenAI account or OpenAI key is needed for this option.

**Security and cost:** LLM enrichment may transmit selected source-code snippets to the configured provider. Do not send private code without authorisation. Never commit actual API keys, `.env` files, or tokens. Don't put secrets directly in command arguments or URLs. Start with `--max-records 2` to constrain API usage. When finished, run `unset INSPECT4ALL_LLM_API_KEY`.

## Viewing output and understanding the schema

Inspect the real schema (rather than assuming example fields):

```bash
python3 -m json.tool python_inspect/repository_analysis.json | head -100
```

See [the runnable examples](examples/README.md) and [an explicitly illustrative enrichment example](examples/illustrative-enrichment.json). Model-produced outputs can differ across models and runs.

## Development and documentation

- [User guide](docs/USER_GUIDE.md) — Installation, inspection, and enrichment
- [Output formats](docs/OUTPUT_FORMATS.md) — JSON, HTML, embedding exports, and metadata provenance
- [Technical reference](docs/technical-reference.md) — Architecture, CLI options, and language adapters
- [Evaluation](docs/EVALUATION.md) — Study design, findings, and limitations
- [Evaluation evidence](docs/evaluation-evidence.md) — Supporting results and methodology
- [Troubleshooting](docs/TROUBLESHOOTING.md) — Common problems
- [Real-world d4py example](examples/d4py-real-world/README.md) — Inspection and optional enrichment
- [Legacy GitLab and EIDF deployment](docs/legacy-gitlab-deployment.md) — Historical internal instructions
- [Experiments](experiments/README.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Run local checks after `make libenry`:

```bash
uv sync
uv run pytest tests -q
```

Some live LLM smoke tests require credentials and can incur cost; they are not part of the documented offline example.

## Limitations

Python and Java adapters are implemented; other languages may be detected but not structurally analysed. LLM-generated information is uncertain and optional. Source builds require compiling a native library; a prebuilt PyPI wheel has been verified on macOS Apple Silicon, but availability and operation on other platforms have not been independently verified here. Native Windows support is not yet documented.

## Cite inspect4all

**Version 0.1.1** has been archived on Zenodo and can be cited using its
[version-specific DOI](https://doi.org/10.5281/zenodo.23895264).
For a citation representing all releases of the software, use the
[all-versions DOI](https://doi.org/10.5281/zenodo.23895263).

> Zhang, H. and Filgueira, R. (2026). *inspect4all: Unified Repository Metadata Extraction with Provenance-Aware Enrichment* (Version 0.1.1) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.23895264

For machine-readable citation metadata, see [CITATION.cff](CITATION.cff).
The [GitHub v0.1.1 release](https://github.com/SemanticRepoHub/inspect4all/releases/tag/v0.1.1)
and the [PyPI distribution](https://pypi.org/project/inspect4all/) are also available.

## Licence

BSD-3-Clause, see [LICENSE](LICENSE). See repository history and [citation metadata](CITATION.cff) for attribution; third-party example repository licences must also be respected.

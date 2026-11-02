# inspect4all User Guide

[Main README](../README.md) · [Output formats](OUTPUT_FORMATS.md) · [Troubleshooting](TROUBLESHOOTING.md)

inspect4all performs **static Python/Java repository inspection without an LLM key**. Optional enrichment calls an OpenAI-compatible service and may require its API key and incur costs. These installation instructions have been verified on macOS Apple Silicon; cross-platform installation needs independent testing.

## 1. Install

Prerequisites: Git, Python 3.12+, [uv](https://docs.astral.sh/uv/), Go, Make, a C compiler and CGO. On a Mac with Homebrew:

```bash
brew install go
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart the shell if uv is not yet on PATH. Then:

```bash
git clone https://github.com/SemanticRepoHub/inspect4all.git
cd inspect4all
make libenry
uv tool install --force .
inspect4all --help
inspect4all inspect --help
inspect4all enrich --help
```

**Order matters:** `make libenry` compiles the required platform-specific native library. Do not substitute a direct Git URL installation unless that packaging path is subsequently verified.

## 2. Inspect: no API key needed

From the cloned inspect4all root:

```bash
inspect4all inspect --all -i examples/hello-world-python -o python_inspect
inspect4all inspect --all -i examples/hello-world-java -o java_inspect
```

For a real research software repository:

```bash
git clone https://github.com/StreamingFlow/d4py.git demo-d4py
git -C demo-d4py rev-parse HEAD
inspect4all inspect --all -i demo-d4py -o d4py_inspect
ls -lh d4py_inspect/
```

The commit hash is worth recording: upstream d4py may change, affecting output. The 2 November 2026 macOS run created `repository_analysis.json`, `repository_analysis.html` and `embedding_export.json`. The observed 4.713 seconds is a single run, not a benchmark.

## 3. Read outputs

Open `repository_analysis.html` in a browser, or inspect JSON with:

```bash
python3 -m json.tool d4py_inspect/repository_analysis.json | less
```

The JSON includes repository language counts, test/invocation candidates, dependencies, a per-file directory tree, functions, methods, source-code ranges and a call graph. See [OUTPUT_FORMATS.md](OUTPUT_FORMATS.md). Invocation candidates and LLM descriptions should not be interpreted as independently validated execution or ground truth.

## 4. Optional LLM enrichment

**OpenAI-hosted option:** obtain a separate API key and use an exact supported model ID. In macOS zsh, enter the key without printing it or storing it in shell history:

```bash
export INSPECT4ALL_LLM_BASE_URL="https://api.openai.com/v1"
export INSPECT4ALL_LLM_MODEL="YOUR_AVAILABLE_MODEL_ID"
export INSPECT4ALL_LLM_MAX_TOKENS=4096
read -s "INSPECT4ALL_LLM_API_KEY?API key: "
export INSPECT4ALL_LLM_API_KEY
echo
```

**University ELM/gateway option:** use the university-issued base URL, model identifier, and key, not the direct OpenAI endpoint or key interchangeably. **Local LLM option:** configure an OpenAI-compatible local server, e.g. `http://localhost:1234/v1`, and its loaded model ID (some local servers accept `lm-studio` as a dummy key). Model support varies.

Try a small run:

```bash
inspect4all enrich -i d4py_inspect --max-records 2 --processors docstrings
ls -lh d4py_inspect/
```

This preserves the original `repository_analysis.json` and writes `repository_analysis.enriched.json` and a cache. Actual d4py before/after results from the supplied successful test are in [verified-two-records.json](../examples/d4py-real-world/verified-two-records.json). For unsupported Java syntax, the separate `java-backfill` processor may apply when failures are present; see `inspect4all enrich --help`.

**Before uploading any output or source snippets:** check license, privacy, institutional approval and data retention. Source-code snippets may be transmitted to the chosen LLM. Never commit credentials or `.env` files. Cached results can invalidate comparisons across model runs: use separate output directories and record both model and repository commit.

## 5. Update, test, and get help

```bash
cd /path/to/inspect4all
git pull --ff-only origin main
make libenry
uv tool install --force .
```

See [Troubleshooting](TROUBLESHOOTING.md), [evaluation and limitations](EVALUATION.md), and [technical reference](technical-reference.md). Evaluation evidence is from the MSc dissertation and is separate from the two-record d4py test.

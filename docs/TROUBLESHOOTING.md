# Troubleshooting

| Error / symptom | What to check |
|---|---|
| `make: No rule to make target libenry` | Wrong working directory or old checkout. Check `pwd`, `git log -1`, and `Makefile`. |
| `/bin/sh: go: command not found` | Install Go and confirm `go version`. On Homebrew macOS use `brew install go`. |
| `libenry.dylib not found` during build | Run `make libenry` from the source root **before** `uv tool install --force .`. Confirm `src/inspect4all/libs/`. |
| `inspect` is an unexpected extra argument | An old inspect4all CLI is installed. Check `uv tool list`, update source and force reinstall. |
| `Path ... does not exist` | Use `pwd`, `ls -ld /absolute/input/path`; pass a valid absolute path to `-i`. |
| `uv: command not found` | Install uv, restart terminal or correct PATH. |
| LLM 401/unauthorised | Verify provider-specific endpoint and key without displaying the secret. Check expiry, entitlement and permissions. |
| LLM 404/model not found | Use exactly the model ID offered by the chosen provider. |
| No enrichments or all skipped | Check eligible undocumented functions, logs and `enrichment_cache.jsonl`. For controlled comparisons, use fresh output directories. |
| Works on Mac, not Linux | Native binaries differ; compile `libenry.so` on Linux using the project's Makefile. |

## Nonsecret diagnostic information

```bash
pwd
git log -1 --oneline
go version
uv --version
uv tool list
inspect4all --help
inspect4all inspect --help
inspect4all enrich --help
```

Report reproducible issues with OS/architecture, versions, repository SHA, minimal nonconfidential input and complete **redacted** error messages. Do not share tokens, `.env` files or confidential source. For sensitive reports, follow the repository's `SECURITY.md`.

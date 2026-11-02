# Legacy GitLab and EIDF deployment

> **Historical/internal material.** This records the original University of Edinburgh
> GitLab, private package registry and EIDF deployment procedures. Access may require
> institutional permissions and some steps may be outdated. For the supported public
> installation workflow, see the [main README](../README.md) and
> [User guide](USER_GUIDE.md).

### Run on EIDF (legacy/internal GitLab deployment)

> **Note:** This section documents the original University of Edinburgh GitLab deployment. The links and registries below may require institutional permissions and are not the public GitHub installation method. For public source installation, see [the main README](../README.md).

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

# Preliminary Investigations on tree-sitter

This section touches on the experimentation done to explore tree-sitter. The exploration is carried out using jupyter notebook: [tree-sitter.ipynb](./tree-sitter.ipynb)

## Setup

Ensure `uv` (https://docs.astral.sh/uv/) is installed as the notebook is in a Python virtual environment managed by `uv`.

```sh
# run sync to sync the environment with all dependencies according to the lock file
uv sync
```

## Running the Notebook

Launch Jupyter and open `tree-sitter.ipynb`:

```sh
uv run jupyter notebook tree-sitter.ipynb
```

Then run all cells in order via **Cell > Run All**.

## Key Observations

- Tree-sitter provides a uniform parsing interface across languages, but operates at the syntactic (CST) level rather than the semantic level. Extracting meaningful metadata (function signatures, call targets, docstrings) still requires substantial per-language conversion logic on top of the CST output.
- From the experiment's experience (i.e. most of the online blogs post and tutorials on Tree-sitter are found to be no longer valid with recent version of Tree-sitter), it is clear that Tree-sitter undergoes frequent breaking API changes as the project matures. The Python bindings API changed significantly between versions, and online documentation and learning resources (blog posts, tutorials) often cover older syntax that no longer works. This creates a practical engineering risk: time spent learning the API may be invalidated by the next release.

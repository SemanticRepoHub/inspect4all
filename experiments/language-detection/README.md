# Source Code / Language Detection

This section touches on the investigation done for detecting the programming languages used in a typical source code file.

A number of libraries and tooling exists, and the following are explored:

- `guesslang`: ML-base, uses a TensorFlow model trained on GitHub repos to classify source code into 50+ languages.
- `linguist`: Developed by GitHub, and Gitlab uses a modified version of this. It is Ruby based but a Python wrapper exists.
- `pygments`: Primiarily a syntax highlighter but its lexer detection (`pygments.lexers.guess_lexer()`) can be used for inferencing inlanguage from code content. Heuristic based, not ML. Battle-tested and covers over 500+ languages. Lightweight and pure Python.
- `go-enry`: Go port of `linguist`. It runs twice as fast (5-20X for smaller project) compared to `linguist` and uses the same detection algorithms and data.

The exploration is carried out using jupyter notebook: [lang-detect.ipynb](./lang-detect.ipynb)

## Setup

Ensure `uv` (https://docs.astral.sh/uv/) is installed as the notebook is in a Python virtual environment managed by `uv`.

```sh
# run sync to sync the environment with all dependencies according to the lock file
uv sync
```

## Running the Notebook

Launch Jupyter and open `lang-detect.ipynb`:

```sh
uv run jupyter notebook lang-detect.ipynb
```

Then run all cells in order via **Cell > Run All**.

## Conclusion from Experiment

It is probably best to choose between `pygments` and `go-enry`. The final conclusion is to go with `go-enry` since it is more effective and fast. The FFI implementation has already been ironed out and the use of FFI has no performance implementation. See More details on the tooling below.

`pygments` with a big lookup table to cover common file format is great because:

- it is fast and lightweight
- pure Python
- hugely effective

The lookup table is sufficient since it is expected that the codebase in git repositories are usually reviewed and thus should have conform to certain file quality

`go-enry` is production grade but it introduces a new go shared library depedencies and maintenance complexity. In addition, need to consider the following issues with the use of FFI:

- FFI based implementation tends to be error-prone
  - little or no support for static checking (e.g. compile time check)
  - interface code need to handle difference in data structure and type system between the two languages
  - Reference: Li, S. (2014). Improving Quality of Software with Foreign Function Interfaces using Static Analysis (Doctoral dissertation, Lehigh University).
- FFI is often used to invoke code reuse and for performance gain
  - there is no significant difference in runtime performance between direct C API call and language binding from higher level language (e.g. Python) although there is increased CPU and memory consumption
  - Python, C and Go binding are commonly used for software reuse
  - Reference: Molina Bocanegra, D. F. (2013). Bindings performance analysis across programming languages
    [Master's thesis, UMEA UNIVERSITY].
    https://www.diva-portal.org/smash/get/diva2:648887/FULLTEXT01.pdf

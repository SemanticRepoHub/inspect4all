# Reproducible minimal examples

These are **new example inputs** to try the CLI, not validated golden outputs or performance measurements.

```bash
inspect4all inspect --all -i examples/hello-world-python -o python_inspect
inspect4all inspect --all -i examples/hello-world-java -o java_inspect
```

Inspect the actual JSON:

```bash
python3 -m json.tool python_inspect/repository_analysis.json | head -100
```

For optional OpenAI enrichment, first configure your own API key using the root README, then run `inspect4all enrich -i python_inspect --max-records 2 --processors docstrings`.

`illustrative-enrichment.json` is a **schematic illustration**, not output from a real executed test, and should not be used for schema validation.

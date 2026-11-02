# Add the documentation links to the main README

This update is intentionally **additive**. It does not replace `README.md` or existing diagrams, so it avoids undoing the successful branch merge. Add this block under the current **Development and documentation** section:

```markdown
### User documentation

- [User guide](docs/USER_GUIDE.md) — installation, basic inspection and optional LLM enrichment
- [Understanding outputs](docs/OUTPUT_FORMATS.md) — JSON schema, HTML, embedding export and LLM provenance
- [Evaluation and limitations](docs/EVALUATION.md) — sourced dissertation evidence, scope and caveats
- [Troubleshooting](docs/TROUBLESHOOTING.md) — installation and LLM API errors
- [Verified d4py before/after sample](examples/d4py-real-world/verified-two-records.json)
```

The existing real-world d4py workflow diagram and sample README can remain unchanged.

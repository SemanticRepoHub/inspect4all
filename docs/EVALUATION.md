# Evaluation: evidence and limits


| Study | Reported result | Conditions / interpretation |
|---|---|---|
| Language labels | **156/168 = 92.9%** agreement | 84 Java, 84 Python repositories; 12 mismatches were judged definitional (catalogue/API language versus file-majority implementation language), **not** evidence of a 100%-correct classifier |
| Static extraction assessment | All **14 file-level dimensions 4–5/5** | 30 repositories, 18-dimension LLM-as-judge rubric; weakest repository-level dimension, dependency extraction, was 3.64/5 |
| Docstring hold-out | **4.40/5 generated** vs **4.54/5 human reference** | 50 functions; evaluation reports 95% interval for overall difference including zero; judge-driven rubric |
| Java backfill | **197/199** completed | Three-repository parser-gap evaluation, with **type recall 0.978** and **method F1 0.972** against parser oracle; no hallucinated types reported |
| Exploratory locally hosted model | **95.7%** of reference score, vs hosted **97.0%** | One machine, reduced repository context, not a controlled equal-condition model comparison |

## Corpus and reproduction

The evaluation describes 168 GitHub repositories in 33 categories and 64 manually validated cross-language pairs. Its reproducibility appendix reports a Step 0 full-inspection pass, fixed sampling seed **42**, a lockfile, and generated outputs of roughly **8.4 GB** that were not committed. To make the full evaluation independently reproducible, verify release permissions and provide a public manifest with pinned SHA references, data generation scripts, evaluation rubrics, model/provider configuration (without keys), and versioned output summaries.

## Limitations

- Community-curated repository selection may not represent less popular, specialised or poorly documented research software.
- The LLM judge was not validated against a human-annotated reference set; cross-judge consistency was mixed.
- Java backfill covers only a three-repository sample with two failures.
- Local-vs-hosted model figures use different context conditions and are illustrative, not controlled.
- Enrichment was sequential and can be slow/costly for large codebases.
- **Cross-language similarity ranking remained proposed future work**, not an implemented/validated inspect4all feature.

## Distinct d4py demonstration

On **2 November 2026**, inspect4all from a fresh macOS Apple Silicon GitHub clone inspected [StreamingFlow/d4py](https://github.com/StreamingFlow/d4py). The observed 4.713 s is one run, not a benchmark. The optional `gpt-5.6-luna` docstring enrichment produced **two successful records, zero failed cache entries** for `create_wf` and `create_graph_with_prov`. This is a small smoke test, 
distinct from evaluation sample. [See actual records](../examples/d4py-real-world/verified-two-records.json).


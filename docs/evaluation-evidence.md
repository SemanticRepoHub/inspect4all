# Evaluation Evidence 


| Evaluation | Reported result | Scope / caveat |
|---|---|---|
| Language identification | 92.9% agreement with corpus labels | 168 repositories, balanced 84 Python and 84 Java |
| Static metadata quality | Fourteen assessed file-level dimensions scored between 4.0 and 5.0 / 5 | LLM-judged sample of 30 repositories; judge-dependent assessment |
| Docstring generation | Mean 4.40 vs 4.54 human-reference score | 50-function hold-out; reported 95% interval for overall difference included zero |
| Java parser-gap backfill | Completed 197 of 199 files | Three-repository evaluation; parser-oracle comparison |
| Java recovered structure | Type recall 0.978 and method F1 0.972 | Oracle-defined scope, not a universal correctness guarantee |

For exact experiment setup, confidence intervals, sampling, judge prompts, full limitations and attribution, contact the authors. 

The two-record d4py enrichment example is an **additional demonstration**, not part of those aggregate evaluation statistics.

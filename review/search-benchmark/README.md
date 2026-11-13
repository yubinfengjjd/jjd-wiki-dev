# Fixed 40-query retrieval benchmark

Labels in `queries.json` were written before the BM25 implementation. Categories: 15 method, 10 template, 10 theory, 5 limitations. Expected IDs refer to existing canonical pages; labels assess retrieval relevance, not scientific validity.

| Engine | Recall@3 | Recall@5 | Recall@10 | MRR@10 |
|---|---:|---:|---:|---:|
| Legacy catalog substring | 85.0% | 85.0% | 95.0% | 0.7484 |
| Full knowledge section BM25 | 97.5% | 97.5% | 100.0% | 0.9042 |

The baseline runner executes the entire original `finder.py` module, including its own helpers, from fixed tracked commit `76d4bd7cbc8ad0bb57cf45e4b9fb078866d2d864` in an isolated namespace with `__package__="rwiki"`. A read-only request snapshot covers the baseline batch to avoid repeated metadata I/O without changing ranking. The BM25 runner uses the current live `search` API and fresh evidence checks per query. Timings therefore describe different I/O paths and are not a fair engine speed comparison.

## Daily-question regressions

- `我想做差异表达分析`: canonical `differential-expression` rank 7 → 3.
- `我想给细胞做注释`: canonical `cell-type-annotation` rank 1 → 3. Both satisfy the agreed top-three gate; annotation ranking regressed.
- `判断每个细胞属于什么类型`: canonical `cell-type-annotation` rank 20 → 1. This exact original regression is separate from the frozen 40 labels; details are in `regressions.json`.
- `PR` boundary has a separate fixture: it matches precision-recall and never matches coexpression/approximation substrings.

## Remaining failure

`SHAP 背景分布和输出单位`: canonical `shap-explanation` rank 2 → 6. Other relevant SHAP interfaces/templates outrank the canonical theory page. This is reported, not tuned away with a query-specific alias. No labels were changed after ranking. `after-initial-v1.json` retains the initial implementation result; the final index v4 adds bounded general Chinese stopwords and transparent query-topic expansion, without aliases containing a benchmark question.

## Reproduce

Use `D:\anaconda\python.exe -X utf8 run_benchmark.py --phase before` or `--phase after` from this directory. The runner supports both legacy `review/` and canonical `archive/review/` locations and pins the baseline SHA independently of the current branch HEAD. The runner imports the canonical skill package, reads the real Wiki, and writes only benchmark JSON and external derivative search cache. It never installs dependencies, changes sources, promotes status, or runs scientific analysis.

## Coverage and limits

The benchmark uses one author-independent expected canonical ID per query, rather than exhaustive relevance judgments. The query sample is small and local to this Wiki. Source scope, blocks exclusion, incremental refresh, light-checkout evidence, API parity and static rank parity are tested separately in `tests/test_unified_search.py`; source-code relevance has no 40-query claim. BM25 cannot guarantee the scientific suitability of a method.

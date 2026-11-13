# Fixed 40-query retrieval benchmark

Labels in `queries.json` were written before the BM25 implementation. Categories: 15 method, 10 template, 10 theory, 5 limitations. Expected IDs refer to existing canonical pages; labels assess retrieval relevance, not scientific validity.

| Engine | Recall@3 | Recall@5 | Recall@10 | MRR@10 |
|---|---:|---:|---:|---:|
| Legacy catalog substring | 85.0% | 85.0% | 95.0% | 0.7484 |
| Full knowledge section BM25 | 97.5% | 97.5% | 100.0% | 0.9036 |

The baseline runner executes the entire original `finder.py` module, including its own helpers, from fixed tracked commit `76d4bd7cbc8ad0bb57cf45e4b9fb078866d2d864` in an isolated namespace with `__package__="rwiki"`. A read-only request snapshot covers the baseline batch to avoid repeated metadata I/O without changing ranking. The BM25 runner uses the current live `search` API and fresh evidence checks per query. Timings therefore describe different I/O paths and are not a fair engine speed comparison.

## Daily-question regressions

- `我想做差异表达分析`: canonical `differential-expression` rank 7 → 3.
- `我想给细胞做注释`: canonical `cell-type-annotation` rank 1 → 3. Both satisfy the agreed top-three gate; annotation ranking regressed.
- `判断每个细胞属于什么类型`: canonical `cell-type-annotation` rank 20 → 1. This exact original regression is separate from the frozen 40 labels; details are in `regressions.json`.
- `PR` boundary has a separate fixture: it matches precision-recall and never matches coexpression/approximation substrings.

## Remaining failure

`SHAP 背景分布和输出单位`: canonical `shap-explanation` rank 2 → 7. Other relevant SHAP interfaces/templates outrank the canonical theory page. This is reported, not tuned away with a query-specific alias. No labels were changed after ranking. `after-initial-v1.json` retains the initial implementation result; the final index v5 includes nonarchived layout reference pages, bounded ordered-phrase relevance and source-provenance filtering. General Chinese stopwords and topic expansion remain transparent; no aliases contain a benchmark question.

## Reproduce

Use `D:\anaconda\python.exe -X utf8 run_benchmark.py --phase before` or `--phase after` from this directory. The runner supports both legacy `review/` and canonical `archive/review/` locations and pins the baseline SHA independently of the current branch HEAD. The runner imports the canonical skill package, reads the real Wiki, and writes only benchmark JSON and external derivative search cache. It never installs dependencies, changes sources, promotes status, or runs scientific analysis.

## Coverage and limits

The benchmark uses one author-independent expected canonical ID per query, rather than exhaustive relevance judgments. The query sample is small and local to this Wiki. Source scope, blocks exclusion, incremental refresh, light-checkout evidence, API parity and static rank parity are tested separately in `tests/test_unified_search.py`; source-code relevance has no 40-query claim. BM25 cannot guarantee the scientific suitability of a method.


## Final retrieval review fixes (index v5)

- Ordered phrases add at most 50% of a matching section's BM25 score (`phrase_weight=0.5`), at most four phrases and 120 characters per phrase. Double/Chinese quotes preserve explicit grouping. Otherwise the full query is considered only with at least two ASCII words or four CJK characters; leading generic instruction words may be removed. Internal words remain literal so stopword removal cannot concatenate separated words into a spurious exact phrase. ASCII phrase edges use word boundaries. Matching title, summary or section text adds the visible `精确短语` reason. The same contract runs in Python and JavaScript.
- L0 availability follows the actual pinned upstream snapshot/item, not the Wiki's `items.jsonl`. A read-only local Git index distinguishes sparse omitted (`S`) files from unexpectedly missing tracked files. An absent/unknown snapshot remains not downloaded, and every L0 item remains non-executable. Search never fetches or runs source code.
- Author-removed modules and archived promoted recipe provenance are excluded by exact upstream directory components. Removing `Gone` preserves `GoneExtra`. Both source files and fallback L0 descriptions respect the exclusion; unrelated source modules remain searchable.

`tests/fixtures/build_search_parity.py` deterministically rebuilds the synthetic 16-case Python/JavaScript parity fixture, including quoted order, ASCII boundaries, multiple phrases and normalized Chinese questions. Separate real-corpus regressions and source fixtures verify current availability and author-removal behavior. These are software retrieval checks, not scientific validation.

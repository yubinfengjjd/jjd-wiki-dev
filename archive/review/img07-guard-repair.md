# img07 archive guard repair

Scope: resolve the two push-guard findings from dev PR #61 while preserving the imported replication archive. This is repository validation, not figure acceptance or a new R execution.

## Diagnosis and change

The original import commit `2291b1dfd17a1a953eec3b6da6ff3f424b126345` triggers exactly two findings: an archived container activation path in `replications/2026-11-12_img07/code/run_all.sh`, and the complete `replications/2026-11-12_img07/data/go_enrichment_all.tsv` above the default 5 MiB threshold.

The existing guard supports per-rule, exact-path exceptions. Two entries were added to `.push-guard-allow`, each with an explanation. There are no wildcard exceptions, size-limit changes, scanner changes, or CI exclusions.

## Resource check

The GO table has 43,814 rows, 17 modules and 15 columns containing ontology terms, gene sets, module identifiers and aggregate enrichment statistics. Its documented source is the public hdWGCNA tutorial data; it contains no patient/sample-level fields. Full-text secret-pattern checks on both files were negative.

| File | Bytes | SHA-256 |
|---|---:|---|
| `data/go_enrichment_all.tsv` | 8,973,440 | `48b9d339f9ac7659380b13e981ae725302b94c52e00ef1fe73440a987ac8bc0e` |
| `code/run_all.sh` | 4,350 | `63de45c6599cfaae763353673d87f3c8a648a0ae41e5211f88b543655426b029` |

All 39 archived files were hashed before and after the change: zero changes. Existing commands, output hashes and historical QA failures remain intact. In particular, no full workflow rerun, new scientific-validation pass or author visual sign-off is claimed; this repair does not make the archive ready for Wiki ingestion or publication.

## Regression evidence

- Before the change: `wiki.py --config ci/config.ci.json gh guard --range 63e4199^1..HEAD` exits 1 with exactly the original abs-path and size findings.
- After the change: the same original-import-inclusive scan exits 0 with `OK`.
- Direct rule-boundary checks pass: adjacent filenames remain blocked; the script is not exempt from size checks; the table is not exempt from absolute-path checks; secret detection remains active even for an exempt path.
- Existing push-guard and risk test suites and final CI results are recorded in the repair PR.

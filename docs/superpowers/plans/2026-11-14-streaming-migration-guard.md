# Streaming migration guard implementation plan

Goal: make the existing full push-range scanner handle the 8,338-file canonical-path migration without holding the entire patch or all blob bodies in memory.

Scope: `skills/research-wiki/rwiki/push_guard.py` and focused regression tests. No rule exclusions, no threshold changes, no source/statistical changes, no new dependencies.

1. Add a real Git regression with many medium text/code files and a peak-memory assertion; observe failure on the original scanner. Include secrets/paths beyond file heads, historical deletion/rewrite and binary/mode-only edge cases, checking parity with the existing small-fixture scanner semantics.
2. Spool the Git patch to a temporary file; parse one changed file at a time preserving added-line behavior and per-commit coverage. Read blob prefixes incrementally with bounded binary chunks. Preserve fail-closed Git error handling and clean temporary files/processes on success or error.
3. Run focused new tests, existing guard/risk tests, independent review, then real canonical migration guard. Publish the dev fix through reviewed green CI first; deploy through existing source gate if required by the installed pre-push hook. Resume the unchanged content migration PR after its full guard succeeds.

Execution: implementer subagent owns the dev fix; a separate reviewer checks correctness/security. Main agent retains the content migration and PR/CI integration. No package installation or scientific execution.

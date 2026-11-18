"""AutoSci research workflow schema, freshness tracking, and tiered semantic lint rules.

Derived from ``atomicstrata/llm-wiki-compiler``:
- ``src/profile/templates/builtin/autosci/{entities,relations,workflows,artifacts}.ts``:
  AutoSci ``paper -> idea -> experiment -> evidence`` schema, entity lifecycles,
  typed directed relations, and artifact contracts.
- ``src/linter/tiers.ts``: three-tier finding classification
  (``deterministic`` | ``provider-judgement`` | ``derived-view``).
- ``src/freshness/index.ts``: SHA-256 source-hash freshness classifier
  (``fresh`` | ``stale`` | ``orphaned`` | ``unverified``).
- ``src/linter/{rules,rules-citations,rules-crosslinks}.ts``: broken wikilinks,
  citation span checks (``^[file.md:N-N]`` / ``^[file.md#LN-LN]``), schema
  cross-link minimums, and missing-summary / empty-page checks.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

# ---------------------------------------------------------------------------
# 1. AutoSci Schema (from llm-wiki-compiler/src/profile/templates/builtin/autosci)
# ---------------------------------------------------------------------------

AUTOSCI_SCHEMA: dict[str, Any] = {
    "schema_version": 1,
    "profile_id": "autosci",
    "profile_version": "0.4.0",
    "entities": {
        "papers": {
            "directory": "wiki/papers",
            "title_field": "title",
            "required_fields": ["title", "authors", "stage"],
            "lifecycle": {
                "field": "stage",
                "initial": "imported",
                "terminal": ["distilled"],
                "transitions": {"imported": ["triaged"], "triaged": ["distilled"]},
                "transition_requirements": {
                    "triaged": ["triageNote"],
                    "distilled": ["distilledSummary"],
                },
            },
        },
        "ideas": {
            "directory": "wiki/ideas",
            "title_field": "title",
            "required_fields": ["title", "rationale", "stage"],
            "lifecycle": {
                "field": "stage",
                "initial": "proposed",
                "terminal": ["validated", "rejected"],
                "transitions": {
                    "proposed": ["explored"],
                    "explored": ["validated", "rejected"],
                },
            },
        },
        "experiments": {
            "directory": "wiki/experiments",
            "title_field": "title",
            "required_fields": ["title", "hypothesis", "stage"],
            "lifecycle": {
                "field": "stage",
                "initial": "designed",
                "terminal": ["complete"],
                "transitions": {"designed": ["running"], "running": ["complete"]},
                "transition_requirements": {"complete": ["resultSummary"]},
                "transition_relation_requirements": {
                    "complete": [
                        {
                            "relation_type": "tests",
                            "role": "from",
                            "other_types": ["ideas"],
                            "other_states": ["proposed", "explored", "validated"],
                            "min_count": 1,
                        }
                    ]
                },
            },
        },
        "methods": {
            "directory": "wiki/methods",
            "title_field": "title",
            "required_fields": ["title", "inputs", "outputs"],
            "lifecycle": {
                "field": "stage",
                "initial": "proposed",
                "terminal": ["deprecated"],
                "transitions": {"proposed": ["validated"], "validated": ["deprecated"]},
            },
        },
        "manuscripts": {
            "directory": "wiki/manuscripts",
            "title_field": "title",
            "required_fields": ["title", "abstract", "stage"],
            "lifecycle": {
                "field": "stage",
                "initial": "drafting",
                "terminal": ["submitted"],
                "transitions": {
                    "drafting": ["citation-checked"],
                    "citation-checked": ["submitted"],
                },
            },
        },
    },
    "relations": {
        "cites": {"from": ["papers", "manuscripts"], "to": ["sources", "papers"], "direction": "directed"},
        "builds-on": {"from": ["ideas"], "to": ["papers", "ideas"], "direction": "directed"},
        "tests": {"from": ["experiments"], "to": ["ideas"], "direction": "directed"},
        "challenges": {"from": ["manuscripts", "ideas"], "to": ["papers", "ideas"], "direction": "directed"},
        "introduces-concept": {"from": ["papers"], "to": ["research-concepts"], "direction": "directed"},
        "uses-concept": {"from": ["methods", "experiments", "manuscripts"], "to": ["research-concepts"], "direction": "directed"},
        "proposes-method": {"from": ["papers"], "to": ["methods"], "direction": "directed"},
        "extends-method": {"from": ["methods"], "to": ["methods"], "direction": "directed"},
        "supports": {"from": ["experiments"], "to": ["ideas"], "direction": "directed"},
        "contradicts": {"from": ["experiments"], "to": ["ideas"], "direction": "directed"},
        "derived-from": {"from": ["research-outputs", "methods"], "to": ["experiments", "foundations"], "direction": "directed"},
        "addresses-gap": {"from": ["ideas"], "to": ["topics"], "direction": "directed"},
    },
    "workflows": {
        "research": {
            "pipeline": ["paper", "idea", "experiment", "evidence"],
            "stages": [
                {"id": "import-paper", "reads": ["papers"], "writes": ["papers"], "gate": "trust:high"},
                {"id": "triage-paper", "reads": ["papers"], "writes": ["papers"]},
                {"id": "distill-paper", "reads": ["papers"], "writes": ["papers"]},
                {"id": "write-idea", "reads": ["papers"], "writes": ["ideas"]},
                {"id": "link-idea", "reads": ["ideas", "papers"], "writes": ["ideas", "papers"]},
                {"id": "write-experiment", "reads": ["ideas"], "writes": ["experiments"]},
                {"id": "start-experiment", "reads": ["experiments"], "writes": ["experiments"]},
                {"id": "link-experiment", "reads": ["experiments", "ideas"], "writes": ["experiments", "ideas"]},
                {"id": "complete-experiment", "reads": ["experiments", "ideas"], "writes": ["experiments"]},
            ],
        },
        "experiment-design": {
            "stages": [
                {"id": "propose-method", "reads": ["ideas", "methods"], "writes": ["methods"]},
                {"id": "design-experiment", "reads": ["ideas", "methods"], "writes": ["experiments"], "gate": "agent:reviewed"},
                {"id": "link-method", "reads": ["experiments", "methods"], "writes": ["experiments", "methods"]},
            ]
        },
    },
    "artifacts": {
        "experiment-result": {
            "file_name": "result.json",
            "content_kind": "json",
            "max_bytes": 65536,
            "metadata": {"accuracy": {"type": "number", "required": True}, "runtimeMs": {"type": "integer"}},
        },
        "paper-source-metadata": {
            "file_name": "source-metadata.json",
            "content_kind": "json",
            "max_bytes": 65536,
            "metadata": {"retrievedFrom": {"type": "string", "required": True}, "retrievedAt": {"type": "string"}},
        },
        "experiment-plan": {
            "file_name": "plan.json",
            "content_kind": "json",
            "max_bytes": 65536,
            "metadata": {"hypothesis": {"type": "string", "required": True}, "steps": {"type": "integer"}},
        },
    },
}

# ---------------------------------------------------------------------------
# 2. Tiered Lint Types (ported from src/linter/tiers.ts)
# ---------------------------------------------------------------------------

LintTier = Literal["deterministic", "provider-judgement", "derived-view"]
LintSeverity = Literal["error", "warning", "info"]
FreshnessStatus = Literal["fresh", "stale", "orphaned", "unverified"]


@dataclass
class LintResult:
    rule: str
    severity: LintSeverity
    file: str
    message: str
    tier: LintTier = "deterministic"
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "rule": self.rule,
            "severity": self.severity,
            "tier": self.tier,
            "file": self.file,
            "message": self.message,
        }
        if self.line is not None:
            out["line"] = self.line
        return out


@dataclass
class TieredLintReport:
    deterministic: list[LintResult] = field(default_factory=list)
    provider_judgement: list[LintResult] = field(default_factory=list)
    derived_view: list[LintResult] = field(default_factory=list)

    @property
    def deterministic_errors(self) -> int:
        return sum(1 for r in self.deterministic if r.severity == "error")

    def to_dict(self) -> dict[str, Any]:
        return {
            "deterministic": [r.to_dict() for r in self.deterministic],
            "providerJudgement": [r.to_dict() for r in self.provider_judgement],
            "derivedView": [r.to_dict() for r in self.derived_view],
            "deterministicErrors": self.deterministic_errors,
            "totalFindings": len(self.deterministic) + len(self.provider_judgement) + len(self.derived_view),
        }


def build_tiered_report(results: list[LintResult]) -> TieredLintReport:
    report = TieredLintReport()
    for r in results:
        if r.tier == "deterministic":
            report.deterministic.append(r)
        elif r.tier == "provider-judgement":
            report.provider_judgement.append(r)
        else:
            report.derived_view.append(r)
    return report


# ---------------------------------------------------------------------------
# 3. Markdown / Frontmatter helpers
# ---------------------------------------------------------------------------

_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
_CITATION_RE = re.compile(r"\^\[([^\]]+)\]")
_SPAN_RE = re.compile(r"^(.+?)(?::(\d+(?:-\d+)?(?:\s*,\s*\d+(?:-\d+)?)*)|#L(\d+)(?:-L(\d+))?)?$")


def parse_markdown_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            raw_yaml = "".join(lines[1:idx])
            body = "".join(lines[idx + 1 :])
            try:
                meta = yaml.safe_load(raw_yaml) or {}
                if not isinstance(meta, dict):
                    meta = {}
            except yaml.YAMLError:
                meta = {}
            return meta, body
    return {}, text


def slugify_target(target: str) -> str:
    clean = target.strip().split("#", 1)[0].strip()
    if clean.endswith(".md"):
        clean = clean[:-3]
    return re.sub(r"\s+", "-", clean.lower())


# ---------------------------------------------------------------------------
# 4. Freshness classification (ported from src/freshness/index.ts)
# ---------------------------------------------------------------------------


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_freshness_snapshot(
    sources_dir: Path,
    recorded_sources: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build per-run SHA-256 snapshot of sources for staleness checks."""
    recorded = recorded_sources or {}
    classified: dict[str, dict[str, Any]] = {}
    for rel_file, entry in recorded.items():
        target = (sources_dir / rel_file).resolve()
        try:
            inside = target.is_relative_to(sources_dir.resolve())
        except AttributeError:
            inside = str(target).startswith(str(sources_dir.resolve()))
        if not inside or not target.is_file():
            classified[rel_file] = {
                "recordedHash": entry.get("hash", ""),
                "currentHash": None,
                "exists": False,
                "concepts": list(entry.get("concepts", [])),
            }
            continue
        content = target.read_text(encoding="utf-8", errors="replace")
        classified[rel_file] = {
            "recordedHash": entry.get("hash", ""),
            "currentHash": sha256_text(content),
            "exists": True,
            "concepts": list(entry.get("concepts", [])),
        }
    return {"stateStatus": "ok", "sources": classified}


def compute_freshness(
    slug: str,
    meta: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    page_directory: str = "concepts",
) -> dict[str, Any]:
    """Port of ``computeFreshness`` from ``llm-wiki-compiler/src/freshness/index.ts``."""
    contradicted = isinstance(meta.get("contradictedBy"), list) and len(meta["contradictedBy"]) > 0
    archived = meta.get("archived") is True or meta.get("status") == "archived"

    def _classify() -> FreshnessStatus:
        if snapshot.get("stateStatus") != "ok":
            return "unverified"
        if page_directory == "queries":
            return "unverified"
        if meta.get("orphaned") is True:
            return "orphaned"
        owners = [
            src
            for src in snapshot.get("sources", {}).values()
            if slug in src.get("concepts", [])
        ]
        if not owners:
            return "unverified"
        live = [o for o in owners if o.get("exists")]
        if not live:
            return "orphaned"
        if len(live) < len(owners):
            return "stale"
        if any(o.get("currentHash") != o.get("recordedHash") for o in live):
            return "stale"
        return "fresh"

    return {
        "freshnessStatus": _classify(),
        "contradicted": contradicted,
        "archived": archived,
    }


# ---------------------------------------------------------------------------
# 5. Semantic, Citation, Freshness & Bio-Stepwise Lint Rules
# ---------------------------------------------------------------------------


def check_broken_wikilinks(pages: list[tuple[str, str]]) -> list[LintResult]:
    """Port of ``checkBrokenWikilinksFrom`` (tier: deterministic)."""
    existing_slugs = {Path(fp).stem.lower() for fp, _ in pages}
    results: list[LintResult] = []
    for file_path, content in pages:
        in_fence = False
        for lineno, line in enumerate(content.splitlines(), start=1):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for m in _WIKILINK_RE.finditer(line):
                target = m.group(1)
                slug = slugify_target(target)
                if slug and slug not in existing_slugs:
                    results.append(
                        LintResult(
                            rule="broken-wikilink",
                            severity="error",
                            tier="deterministic",
                            file=file_path,
                            line=lineno,
                            message=f"Broken wikilink [[{target}]] — no matching page found",
                        )
                    )
    return results


def check_broken_citations(pages: list[tuple[str, str]], sources_dir: Path) -> list[LintResult]:
    """Port of ``checkBrokenCitationsFrom`` supporting ``^[file.md:N-N]`` and ``^[file.md#LN-LN]``."""
    line_count_cache: dict[str, int] = {}
    results: list[LintResult] = []
    for file_path, content in pages:
        meta, _ = parse_markdown_frontmatter(content)
        if meta.get("provenanceState") == "imported":
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            for m in _CITATION_RE.finditer(line):
                entries = [e.strip() for e in m.group(1).split(",") if e.strip()]
                for entry in entries:
                    sm = _SPAN_RE.match(entry)
                    if not sm:
                        results.append(
                            LintResult(
                                rule="malformed-claim-citation",
                                severity="error",
                                tier="deterministic",
                                file=file_path,
                                line=lineno,
                                message=f"Malformed citation ^[{entry}]",
                            )
                        )
                        continue
                    fname = sm.group(1).strip()
                    src_path = sources_dir / fname
                    if not src_path.is_file():
                        results.append(
                            LintResult(
                                rule="broken-citation",
                                severity="error",
                                tier="deterministic",
                                file=file_path,
                                line=lineno,
                                message=f"Citation ^[{entry}] references missing source {fname}",
                            )
                        )
                        continue
                    if fname not in line_count_cache:
                        line_count_cache[fname] = len(
                            src_path.read_text(encoding="utf-8", errors="replace").splitlines()
                        )
                    max_line = line_count_cache[fname]
                    nums = [int(n) for n in re.findall(r"\d+", entry[len(fname) :])]
                    if any(n > max_line for n in nums):
                        results.append(
                            LintResult(
                                rule="broken-citation",
                                severity="warning",
                                tier="deterministic",
                                file=file_path,
                                line=lineno,
                                message=f"Citation ^[{entry}] line span exceeds {fname} ({max_line} lines)",
                            )
                        )
    return results


def check_schema_crosslinks(
    pages: list[tuple[str, str]],
    min_links_by_type: dict[str, int] | None = None,
) -> list[LintResult]:
    """Port of ``checkSchemaCrossLinksFrom`` (``src/linter/rules-crosslinks.ts``)."""
    mins = min_links_by_type or {"scenario": 1, "project": 1, "method": 1}
    results: list[LintResult] = []
    for file_path, content in pages:
        meta, body = parse_markdown_frontmatter(content)
        kind = str(meta.get("type") or meta.get("kind") or "concept")
        required = mins.get(kind, 0)
        if required <= 0:
            continue
        found = len(_WIKILINK_RE.findall(body))
        if found < required:
            results.append(
                LintResult(
                    rule="schema-cross-link-minimum",
                    severity="warning",
                    tier="deterministic",
                    file=file_path,
                    message=f'Page kind "{kind}" requires at least {required} [[wikilinks]] but only {found} found.',
                )
            )
    return results


def check_stale_pages(
    pages: list[tuple[str, str]],
    snapshot: dict[str, Any],
) -> list[LintResult]:
    """Port of ``checkStalePagesFrom`` (tier: derived-view)."""
    results: list[LintResult] = []
    for file_path, content in pages:
        meta, _ = parse_markdown_frontmatter(content)
        if meta.get("orphaned") is True:
            continue
        p = Path(file_path)
        fr = compute_freshness(p.stem, meta, snapshot, page_directory=p.parent.name)
        status = fr["freshnessStatus"]
        if status == "stale":
            results.append(
                LintResult(
                    rule="stale-page",
                    severity="warning",
                    tier="derived-view",
                    file=file_path,
                    message="Page is stale — a source it was compiled from has changed since the last compile",
                )
            )
        elif status == "orphaned":
            results.append(
                LintResult(
                    rule="orphaned-page",
                    severity="warning",
                    tier="derived-view",
                    file=file_path,
                    message="Page is orphaned — every source it was compiled from has been deleted",
                )
            )
    return results


def check_bio_method_next_steps(
    pages: list[tuple[str, str]],
    known_interfaces: set[str] | None = None,
    known_templates: set[str] | None = None,
) -> list[LintResult]:
    """Validate bioinformatics stepwise ``next_steps`` and AutoSci lifecycle fields."""
    results: list[LintResult] = []
    for file_path, content in pages:
        meta, _ = parse_markdown_frontmatter(content)
        ptype = meta.get("type")
        if ptype == "method" and "next_steps" in meta:
            steps = meta.get("next_steps")
            if not isinstance(steps, list):
                results.append(
                    LintResult(
                        rule="autosci/invalid-next-steps",
                        severity="error",
                        tier="deterministic",
                        file=file_path,
                        message="next_steps must be a list of stepwise branch objects",
                    )
                )
                continue
            for idx, step in enumerate(steps):
                if not isinstance(step, dict) or not step.get("direction") or not step.get("when"):
                    results.append(
                        LintResult(
                            rule="autosci/incomplete-next-step",
                            severity="warning",
                            tier="deterministic",
                            file=file_path,
                            message=f"next_steps[{idx}] must include non-empty 'direction' and 'when'",
                        )
                    )
                iface = step.get("intermediate_interface") if isinstance(step, dict) else None
                if iface and known_interfaces is not None and iface not in known_interfaces:
                    results.append(
                        LintResult(
                            rule="autosci/unknown-interface-ref",
                            severity="error",
                            tier="deterministic",
                            file=file_path,
                            message=f"next_steps[{idx}] references unknown interface '{iface}'",
                        )
                    )
                for tpl in (step.get("viz_templates") or []) if isinstance(step, dict) else []:
                    if known_templates is not None and tpl not in known_templates:
                        results.append(
                            LintResult(
                                rule="autosci/unknown-template-ref",
                                severity="warning",
                                tier="deterministic",
                                file=file_path,
                                message=f"next_steps[{idx}] references unknown template '{tpl}'",
                            )
                        )
        # AutoSci entity lifecycle stage validation
        if ptype in AUTOSCI_SCHEMA["entities"]:
            entity_def = AUTOSCI_SCHEMA["entities"][ptype]
            lc = entity_def.get("lifecycle", {})
            stage_field = lc.get("field", "stage")
            if stage_field in meta:
                valid_stages = set(lc.get("transitions", {}).keys()) | set(lc.get("terminal", []))
                if meta[stage_field] not in valid_stages:
                    results.append(
                        LintResult(
                            rule=f"autosci/invalid-{ptype}-stage",
                            severity="error",
                            tier="deterministic",
                            file=file_path,
                            message=f"Invalid {ptype}.{stage_field}='{meta[stage_field]}'",
                        )
                    )
    return results


def run_tiered_autosci_lint(
    wiki_root: Path,
    *,
    sources_dir: Path | None = None,
    recorded_sources: dict[str, dict[str, Any]] | None = None,
) -> TieredLintReport:
    """Run all AutoSci & semantic/staleness checks over ``wiki_root`` and return a tiered report."""
    md_files = sorted(wiki_root.rglob("*.md"))
    pages = [
        (str(p.relative_to(wiki_root)).replace("\\", "/"), p.read_text(encoding="utf-8", errors="replace"))
        for p in md_files
    ]
    known_interfaces = {p.stem for p in (wiki_root / "interfaces").glob("*.md")} if (wiki_root / "interfaces").is_dir() else None
    known_templates = {p.stem for p in (wiki_root / "templates").glob("*.md")} if (wiki_root / "templates").is_dir() else None

    findings: list[LintResult] = []
    findings.extend(check_broken_wikilinks(pages))
    if sources_dir and sources_dir.is_dir():
        findings.extend(check_broken_citations(pages, sources_dir))
        if recorded_sources:
            snap = build_freshness_snapshot(sources_dir, recorded_sources)
            findings.extend(check_stale_pages(pages, snap))
    findings.extend(check_schema_crosslinks(pages))
    findings.extend(check_bio_method_next_steps(pages, known_interfaces, known_templates))
    return build_tiered_report(findings)

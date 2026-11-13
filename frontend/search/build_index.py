#!/usr/bin/env python3
"""Build the static search index for frontend/search/ from a Wiki catalog.

Read-only: reads ``知识库/catalog.jsonl`` (and optionally ``知识库/chart-types/``)
plus the controlled vocabulary ``spec/scenario_taxonomy.yaml`` and writes one
JSON file. Nothing in the Wiki or the vocabulary is modified.

The entry count is never assumed: every non-blank catalog line becomes one
entry, so recipes added later appear after a rebuild. Missing or malformed
fields degrade to empty values; a line that is not a JSON object is skipped
and reported in ``stats.skipped_lines``.

Facets
- 图型 (chart): ``chart_types``; slugs are checked against ``chart-types/*.md``.
- 领域 (domain): ``tags`` mapped to taxonomy keys. A key, its Chinese label or
  an alias all map to the key (same rule as rwiki/tags.py, which accepts keys
  and labels). Values outside the vocabulary keep their raw text and are
  flagged ``unknown`` instead of being dropped.
- R 包 (package): ``requires`` of R entries (``language`` r or absent).
  ``knitr``/``rmarkdown`` are runner boilerplate and are left out of the facet.

Standard library only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
BOILERPLATE_PACKAGES = frozenset({"knitr", "rmarkdown"})
TEXT_FIELDS = ("title", "summary", "scenario", "not_for")


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _strings(value) -> list[str]:
    """A list of non-blank strings, de-duplicated in order; anything else -> []."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(v.strip() for v in value if isinstance(v, str) and v.strip()))


def load_vocabulary(path: Path) -> tuple[dict, dict]:
    """(scenarios, lookup). lookup maps key/label/alias (casefolded) -> key."""
    data = json.loads(path.read_text(encoding="utf-8"))
    scenarios = data.get("scenarios") if isinstance(data, dict) else None
    if not isinstance(scenarios, dict):
        raise SystemExit(f"{path}: scenarios 必须为对象")
    lookup: dict[str, str] = {}
    # Keys and labels first so an alias never shadows a canonical name.
    for key, item in scenarios.items():
        item = item if isinstance(item, dict) else {}
        for name in (key, _text(item.get("label"))):
            if name:
                lookup.setdefault(name.casefold(), key)
    for key, item in scenarios.items():
        item = item if isinstance(item, dict) else {}
        for alias in _strings(item.get("aliases")):
            lookup.setdefault(alias.casefold(), key)
    return scenarios, lookup


def load_chart_types(directory: Path | None) -> dict[str, str]:
    """slug -> title from chart-types/*.md frontmatter; empty when absent."""
    known: dict[str, str] = {}
    if directory is None or not directory.is_dir():
        return known
    for md in sorted(directory.glob("*.md")):
        title = md.stem
        lines = md.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines and lines[0].strip() == "---":
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                if line.startswith("title:") and line[6:].strip():
                    title = line[6:].strip().strip("'\"")
        known[md.stem] = title
    return known


def read_catalog(path: Path) -> tuple[list[dict], list[int]]:
    rows, skipped = [], []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                skipped.append(number)
                continue
            if isinstance(row, dict):
                rows.append(row)
            else:
                skipped.append(number)
    return rows, skipped


def build_entry(row: dict, lookup: dict, chart_known: dict) -> dict:
    domains, unknown_tags = [], []
    for tag in _strings(row.get("tags")):
        key = lookup.get(tag.casefold())
        if key:
            if key not in domains:
                domains.append(key)
        else:
            unknown_tags.append(tag)
    language = _text(row.get("language")).lower()
    packages = []
    if language in ("", "r"):
        packages = [p for p in _strings(row.get("requires")) if p not in BOILERPLATE_PACKAGES]
    charts = _strings(row.get("chart_types"))
    entry_id = _text(row.get("id"))
    page = _text(row.get("page"))
    entry = {
        "id": entry_id,
        "title": _text(row.get("title")) or entry_id,
        "kind": _text(row.get("kind")),
        "level": _text(row.get("level")),
        "status": _text(row.get("status")),
        "run": _text(row.get("run")),
        "language": language,
        "page": page,
        "summary": _text(row.get("summary")),
        "charts": charts,
        "domains": domains,
        "unknown_tags": unknown_tags,
        "packages": packages,
        "keywords": _strings(row.get("keywords")),
    }
    unknown_charts = [c for c in charts if chart_known and c not in chart_known]
    if unknown_charts:
        entry["unknown_charts"] = unknown_charts
    # Lowercased haystack so the page does no per-keystroke normalisation.
    hay = [entry_id, page, *charts, *domains, *unknown_tags, *packages, *entry["keywords"]]
    hay += [_text(row.get(f)) for f in TEXT_FIELDS]
    entry["_text"] = " ".join(h for h in hay if h).casefold()
    return entry


def build_index(catalog: Path, taxonomy: Path, chart_dir: Path | None = None,
                source_rev: str = "") -> dict:
    scenarios, lookup = load_vocabulary(taxonomy)
    chart_known = load_chart_types(chart_dir)
    rows, skipped = read_catalog(catalog)
    entries = []
    for row in rows:
        entry = build_entry(row, lookup, chart_known)
        labels = [_text((scenarios.get(k) or {}).get("label")) for k in entry["domains"]]
        labels += [chart_known.get(c, "") for c in entry["charts"]]
        entry["_text"] = (entry["_text"] + " " + " ".join(l for l in labels if l)).casefold()
        entries.append(entry)
    entries.sort(key=lambda e: (e["kind"], e["id"]))

    def facet(field: str) -> list[dict]:
        counts = Counter(v for e in entries for v in e[field])
        return [{"value": v, "count": n} for v, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    domain_counts = Counter(v for e in entries for v in e["domains"])
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "catalog_sha256": hashlib.sha256(catalog.read_bytes()).hexdigest(),
            "taxonomy_sha256": hashlib.sha256(taxonomy.read_bytes()).hexdigest(),
            "rev": source_rev,
        },
        "vocabulary": {
            "domains": [{"value": k, "label": _text(v.get("label")) if isinstance(v, dict) else "",
                         "count": domain_counts.get(k, 0)} for k, v in scenarios.items()],
            "charts": [{"value": k, "label": t} for k, t in chart_known.items()],
        },
        "facets": {
            "charts": facet("charts"),
            "domains": facet("domains"),
            "packages": facet("packages"),
            "kinds": [{"value": v, "count": n} for v, n in sorted(Counter(e["kind"] for e in entries).items())],
            "unknown_tags": facet("unknown_tags"),
        },
        "stats": {"entries": len(entries), "skipped_lines": skipped},
        "entries": entries,
    }


def default_taxonomy() -> Path:
    for parent in Path(__file__).resolve().parents:
        for folder in ('docs', 'spec'):
            candidate = parent / folder / "scenario_taxonomy.yaml"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError("Cannot locate spec/scenario_taxonomy.yaml; pass --taxonomy")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wiki", type=Path, required=True,
                        help="Wiki 子树目录（含 catalog.jsonl，如 jjd-wiki/知识库）")
    parser.add_argument("--taxonomy", type=Path,
                        default=default_taxonomy())
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "search-index.json")
    parser.add_argument("--rev", default="", help="可选：catalog 所在仓库的提交号，写入 source.rev")
    args = parser.parse_args(argv)
    catalog = args.wiki / "catalog.jsonl"
    if not catalog.is_file():
        print(f"找不到 {catalog}", file=sys.stderr)
        return 2
    index = build_index(catalog, args.taxonomy, args.wiki / "chart-types", args.rev)
    args.out.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    stats = index["stats"]
    print(json.dumps({"out": str(args.out), "entries": stats["entries"],
                      "skipped_lines": stats["skipped_lines"], **index["source"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Multi-dimensional pre-ingestion duplicate detection and confirmation gate."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .aliases import resolve_page_ref
from .config import Config
from .errors import WikiError
from .pages import read_page

_ASCII_WORD_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_PREFIX_STRIP_RE = re.compile(r"^(?:fy-|figureya-\d*)")
_VERSION_STRIP_RE = re.compile(r"(?:-?v\d+|-update|-updated|-plus)+$")


def _normalize_id(value: str) -> str:
    slug = (value or "").strip().lower().replace("_", "-")
    slug = slug.split("--", 1)[0]
    slug = _PREFIX_STRIP_RE.sub("", slug)
    slug = _VERSION_STRIP_RE.sub("", slug)
    return slug.strip("-")


def _normalize_title(value: str) -> str:
    clean = re.sub(r"\s+", "", (value or "").casefold())
    clean = re.sub(r"[（()）\[\]【】·:：,，。.!！_-]+", "", clean)
    return clean


def _text_ngrams(text: str) -> set[str]:
    clean = _normalize_title(text)
    if not clean:
        return set()
    grams: set[str] = set()
    grams.update(_ASCII_WORD_RE.findall((text or "").casefold()))
    cjk = "".join(_CJK_RE.findall(clean))
    if len(cjk) == 1:
        grams.add(cjk)
    elif len(cjk) >= 2:
        grams.update(cjk[i : i + 2] for i in range(len(cjk) - 1))
    return grams


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _load_method_map(wiki_root: Path) -> dict[str, list[str]]:
    map_path = wiki_root / "recipes" / "method-map.json"
    if not map_path.is_file():
        return {}
    try:
        payload = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    mappings = payload.get("mappings")
    if not isinstance(mappings, dict):
        return {}
    out: dict[str, list[str]] = {}
    for rid, entry in mappings.items():
        if isinstance(rid, str) and isinstance(entry, dict):
            methods = [m.strip() for m in (entry.get("methods") or []) if isinstance(m, str) and m.strip()]
            if methods:
                out[rid] = methods
    return out


def _template_interfaces(page_path: Path) -> set[str]:
    spec_path = page_path.with_suffix("") / "spec.json"
    if not spec_path.is_file():
        return set()
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    tables = spec.get("tables")
    if not isinstance(tables, dict):
        return set()
    return {
        str(tbl.get("interface")).strip()
        for tbl in tables.values()
        if isinstance(tbl, dict) and isinstance(tbl.get("interface"), str) and tbl.get("interface").strip()
    }


def _resolve_method_ids(wiki_root: Path, raw_ids: list[str] | None) -> set[str]:
    resolved: set[str] = set()
    for raw in raw_ids or []:
        if not isinstance(raw, str) or not raw.strip():
            continue
        target = resolve_page_ref(wiki_root, raw.strip(), expected_type="method")
        resolved.add(target.stem if target else raw.strip())
    return resolved


def _iter_existing_candidates(wiki_root: Path, kind: str) -> list[dict]:
    method_map = _load_method_map(wiki_root)
    candidates: list[dict] = []
    promoted_recipes: set[str] = set()

    folders = ("methods",) if kind == "method" else ("templates", "recipes")
    for folder in folders:
        directory = wiki_root / folder
        if not directory.is_dir():
            continue
        for page in sorted(directory.glob("*.md")):
            try:
                meta, _ = read_page(page)
            except Exception:
                continue
            if meta.get("status") == "archived":
                continue
            cid = str(meta.get("id") or page.stem)
            ctype = str(meta.get("type") or folder.rstrip("s"))
            methods: set[str] = set()
            interfaces: set[str] = set()
            if ctype == "template":
                pm = meta.get("primary_method")
                if isinstance(pm, str) and pm.strip():
                    target = resolve_page_ref(wiki_root, pm.strip(), expected_type="method")
                    pm_id = target.stem if target else pm.strip()
                    methods.add(pm_id)
                    for src in meta.get("sources") or []:
                        if isinstance(src, str) and src.startswith("recipes/"):
                            rid = src.split("/", 1)[1].removesuffix(".md")
                            if pm_id in method_map.get(rid, []):
                                promoted_recipes.add(rid)
                interfaces = _template_interfaces(page)
            elif ctype == "recipe":
                if cid in promoted_recipes:
                    continue
                methods.update(method_map.get(cid, []))
                for inp in meta.get("inputs") or []:
                    if isinstance(inp, dict) and isinstance(inp.get("file"), str):
                        interfaces.add(inp["file"])
            elif ctype == "method":
                methods.add(cid)
                interfaces.update(
                    s.strip() for s in (meta.get("inputs") or []) + (meta.get("outputs") or [])
                    if isinstance(s, str) and s.strip()
                )
            candidates.append(
                {
                    "id": cid,
                    "kind": ctype,
                    "title": str(meta.get("title") or cid),
                    "status": str(meta.get("status") or ""),
                    "method_kind": str(meta.get("method_kind") or ""),
                    "aliases": [str(a) for a in (meta.get("aliases") or []) if isinstance(a, str)],
                    "methods": sorted(methods),
                    "chart_types": [str(c) for c in (meta.get("chart_types") or []) if isinstance(c, str)],
                    "interfaces": sorted(interfaces),
                    "summary": str(meta.get("summary") or ""),
                    "keywords": [str(k) for k in (meta.get("keywords") or []) if isinstance(k, str)],
                }
            )
    return candidates


def check_duplicates(
    config: Config,
    *,
    kind: str,
    entry_id: str = "",
    title: str = "",
    primary_method: str = "",
    methods: list[str] | None = None,
    chart_types: list[str] | None = None,
    interfaces: list[str] | None = None,
    summary: str = "",
    keywords: list[str] | None = None,
    exclude_ids: set[str] | None = None,
    limit: int = 5,
) -> dict:
    """Compare a proposed entry against active Wiki entries across multiple structural and lexical signals."""
    if kind not in ("template", "method", "recipe"):
        raise WikiError(f"check-dup 不支持的 kind: {kind}")

    wiki_root = config.wiki_root
    target_methods = _resolve_method_ids(wiki_root, [*(methods or []), *([primary_method] if primary_method else [])])
    target_charts = {c.strip() for c in (chart_types or []) if isinstance(c, str) and c.strip()}
    target_ifaces = {i.strip() for i in (interfaces or []) if isinstance(i, str) and i.strip()}
    norm_id = _normalize_id(entry_id)
    norm_title = _normalize_title(title)
    query_grams = _text_ngrams(" ".join([title, summary, *(keywords or [])]))
    excluded = exclude_ids or set()

    matches: list[dict] = []
    for item in _iter_existing_candidates(wiki_root, kind):
        if item["id"] in excluded:
            continue
        score = 0.0
        reasons: list[str] = []

        item_norm_ids = {_normalize_id(item["id"]), *(_normalize_id(a) for a in item["aliases"])} - {""}
        if norm_id and norm_id in item_norm_ids:
            score += 0.50
            reasons.append(f"规范ID近似({item['id']})")

        item_norm_title = _normalize_title(item["title"])
        exact_title = bool(norm_title and item_norm_title and norm_title == item_norm_title)
        if exact_title:
            score += 0.60
            reasons.append("标题高度一致")

        shared_methods = sorted(target_methods & set(item["methods"]))
        if shared_methods:
            score += 0.30
            reasons.append("同方法域(" + ", ".join(shared_methods) + ")")

        shared_charts = sorted(target_charts & set(item["chart_types"]))
        if shared_charts:
            score += 0.25
            reasons.append("同图型(" + ", ".join(shared_charts) + ")")

        shared_ifaces = sorted(target_ifaces & set(item["interfaces"]))
        if shared_ifaces:
            score += 0.20
            reasons.append("同接口/输入(" + ", ".join(shared_ifaces[:3]) + ")")

        item_grams = _text_ngrams(" ".join([item["title"], item["summary"], *item["keywords"]]))
        lex_sim = _jaccard(query_grams, item_grams)
        if lex_sim >= 0.20 and not exact_title:
            score += min(0.35, round(lex_sim * 0.55, 3))
            reasons.append(f"文本语义重合({lex_sim:.0%})")

        if not reasons:
            continue
        score = min(1.0, round(score, 3))
        # A single chart-type or method-domain match alone should not clutter output as a false duplicate.
        if score < 0.38:
            continue
        severity = "high" if (score >= 0.65 or exact_title) else "medium"
        matches.append(
            {
                "id": item["id"],
                "kind": item["kind"],
                "title": item["title"],
                "status": item["status"],
                "score": score,
                "severity": severity,
                "reasons": reasons,
                "methods": item["methods"],
                "chart_types": item["chart_types"],
            }
        )

    matches.sort(key=lambda m: (-m["score"], m["kind"], m["id"]))
    top = matches[:limit]
    high_hits = [m for m in top if m["severity"] == "high"]
    return {
        "kind": kind,
        "query": {
            "id": entry_id,
            "title": title,
            "methods": sorted(target_methods),
            "chart_types": sorted(target_charts),
            "interfaces": sorted(target_ifaces),
        },
        "blocked": bool(high_hits),
        "high_count": len(high_hits),
        "candidates": top,
    }


def assert_no_high_duplicate(
    config: Config,
    *,
    kind: str,
    entry_id: str = "",
    title: str = "",
    primary_method: str = "",
    chart_types: list[str] | None = None,
    interfaces: list[str] | None = None,
    summary: str = "",
    keywords: list[str] | None = None,
    exclude_ids: set[str] | None = None,
    dedup_note: str = "",
    force: bool = False,
) -> dict:
    """Gate helper: raise WikiError on high-similarity candidates unless dedup_note or force is provided."""
    report = check_duplicates(
        config,
        kind=kind,
        entry_id=entry_id,
        title=title,
        primary_method=primary_method,
        chart_types=chart_types,
        interfaces=interfaces,
        summary=summary,
        keywords=keywords,
        exclude_ids=exclude_ids,
    )
    if report["blocked"] and not (dedup_note.strip() or force):
        lines = [
            f"- {c['kind']}/{c['id']}《{c['title']}》(score={c['score']}): {'；'.join(c['reasons'])}"
            for c in report["candidates"]
            if c["severity"] == "high"
        ]
        raise WikiError(
            "入库查重发现高相似既有条目，请优先复用或在现有条目扩展；确属不同实现/变体时请传 --dedup-note \"<差异说明>\" 继续：\n"
            + "\n".join(lines)
        )
    return report

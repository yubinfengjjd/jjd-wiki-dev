"""Paper replication showcase API helpers: `/api/papers`, `/api/papers/{id}`, and `/panel-code`."""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

from .aliases import resolve_page_ref
from .code_assets import MAX_PREVIEW_BYTES, _SKIP_DIRS, _hash, _language, _relative, _safe_existing
from .confine import _link, _restricted_link, confined
from .config import Config, read_json
from .errors import WikiError
from .pages import read_page
from .read_cache import cached_vault_value
from .panel_manifest import (
    EXCLUDED_EVIDENCE_TIERS,
    load_panel_manifest,
    manifest_path_for,
    normalize_figure_slug,
    summarize_panel_manifest,
)

_EMPTY_STATS = {
    "figures": 0,
    "panels": 0,
    "original_table": 0,
    "local_recompute": 0,
    "proxy": 0,
    "excluded_wet_lab": 0,
    "excluded_schematic": 0,
    "excluded_imaging": 0,
    "excluded_total": 0,
    "computed": 0,
    "templates": 0,
}


def _gallery_url(gallery_root: Path, entry: str, rel_file: str | None) -> str | None:
    if not entry or not isinstance(rel_file, str) or not rel_file.strip():
        return None
    rel_clean = rel_file.strip().lstrip("/")
    if not _relative(entry) or not _relative(rel_clean):
        return None
    root_resolved = gallery_root.resolve()
    target = root_resolved.joinpath(*PurePosixPath(entry).parts, *PurePosixPath(rel_clean).parts)
    if not _safe_existing(target, root_resolved) or not target.is_file():
        return None
    rel_posix = target.resolve().relative_to(root_resolved).as_posix()
    return "/files/gallery/" + quote(rel_posix, safe="/")


def _index_paper_galleries(gallery_root: Path) -> tuple[dict[str, tuple[str, dict[str, Any]]], dict[str, dict[str, Any]]]:
    by_workflow: dict[str, tuple[str, dict[str, Any]]] = {}
    by_entry: dict[str, dict[str, Any]] = {}
    root = gallery_root.resolve()
    if not root.is_dir():
        return by_workflow, by_entry
    for entry_dir in sorted(root.iterdir()):
        if not entry_dir.is_dir() or entry_dir.name.startswith(".") or not _safe_existing(entry_dir, root):
            continue
        meta_path = entry_dir / "meta.json"
        if not meta_path.is_file() or not _safe_existing(meta_path, root):
            continue
        try:
            gmeta = read_json(meta_path)
        except (WikiError, OSError, ValueError):
            continue
        if not isinstance(gmeta, dict):
            continue
        if not (isinstance(gmeta.get("figures"), list) or gmeta.get("workflow_id")):
            continue
        by_entry[entry_dir.name] = gmeta
        wf_id = str(gmeta.get("workflow_id") or "").strip()
        if wf_id and wf_id not in by_workflow:
            by_workflow[wf_id] = (entry_dir.name, gmeta)
    return by_workflow, by_entry


def _workflow_dir_confined(wiki_root: Path, method_page: Path) -> Path | None:
    """Validate unresolved `methods/<id>` directory and its ancestors against canonical `wiki_root`."""
    try:
        root_resolved = wiki_root.resolve()
        page_resolved = method_page.resolve()
        if not page_resolved.is_relative_to(root_resolved):
            return None
        workflow_dir = method_page.with_suffix("")
        if not confined(workflow_dir, wiki_root, wiki_root):
            return None
        for anc in (workflow_dir, *workflow_dir.parents):
            try:
                if anc.resolve() == root_resolved:
                    break
            except OSError:
                return None
            if _link(anc):
                return None
        if not workflow_dir.resolve().is_relative_to(root_resolved):
            return None
        return workflow_dir
    except (OSError, RuntimeError, ValueError):
        return None


def _resolve_panel_script(wiki_root: Path, method_page: Path, rel_path: str) -> Path | None:
    """Shared validator for `detail.script_available` and `/api/papers/{id}/panel-code`."""
    if not isinstance(rel_path, str):
        return None
    rel_clean = rel_path.strip().lstrip("/")
    if not _relative(rel_clean):
        return None
    parts = PurePosixPath(rel_clean).parts
    if len(parts) < 2 or parts[0] not in ("code", "source") or any(
        part.startswith(".") or part.lower() in _SKIP_DIRS for part in parts
    ):
        return None
    workflow_dir = _workflow_dir_confined(wiki_root, method_page)
    if workflow_dir is None:
        return None
    target = workflow_dir.joinpath(*parts)
    if not confined(target, workflow_dir, wiki_root) or not confined(target, wiki_root, wiki_root):
        return None
    # Reject symlinks/junctions inside the workflow directory unless they are valid restricted checkout links.
    cur = target
    while cur != workflow_dir:
        if _link(cur) and not _restricted_link(cur, wiki_root):
            return None
        cur = cur.parent
    try:
        return target if target.is_file() else None
    except OSError:
        return None


def _summarize_receipts(
    wiki_root: Path,
    method_page: Path,
    receipts_meta: dict[str, Any],
) -> dict[str, Any] | None:
    if not receipts_meta:
        return None
    entries = receipts_meta.get("panels") or receipts_meta.get("receipts") or []
    if isinstance(entries, dict):
        items = [v for v in entries.values() if isinstance(v, dict)]
    elif isinstance(entries, list):
        items = [v for v in entries if isinstance(v, dict)]
    else:
        items = []
    status_counts: dict[str, int] = {}
    hash_checked = 0
    hash_matched = 0
    hash_mismatched = 0
    script_missing = 0
    for item in items:
        st = str(item.get("status") or "unknown").strip() or "unknown"
        status_counts[st] = status_counts.get(st, 0) + 1
        sp = str(item.get("script_path") or "").strip()
        expected_sha = str(item.get("script_sha256") or "").strip().lower()
        target = _resolve_panel_script(wiki_root, method_page, sp) if sp else None
        if sp and target is None:
            script_missing += 1
        if expected_sha and target is not None:
            hash_checked += 1
            if _hash(target).lower() == expected_sha:
                hash_matched += 1
            else:
                hash_mismatched += 1
    return {
        "total": len(items),
        "generated": status_counts.get("generated", 0),
        "smoke_tested": status_counts.get("smoke_tested", 0),
        "hash_checked": hash_checked,
        "hash_matched": hash_matched,
        "hash_mismatched": hash_mismatched,
        "script_missing": script_missing,
        "status_counts": status_counts,
    }


def _iter_paper_workflows(config: Config) -> list[dict[str, Any]]:
    wiki_root = config.wiki_root.resolve()
    gallery_root = config.gallery_root.resolve()
    by_workflow, by_entry = _index_paper_galleries(gallery_root)
    methods_dir = wiki_root / "methods"
    if not methods_dir.is_dir():
        return []

    records: list[dict[str, Any]] = []
    for path in sorted(methods_dir.glob("*.md")):
        try:
            meta, _ = read_page(path)
        except (WikiError, OSError, UnicodeDecodeError):
            continue
        if meta.get("type") != "method" or meta.get("status") == "archived":
            continue
        wf_id = str(meta.get("id") or path.stem)
        mpath = manifest_path_for(config, path)
        has_manifest = mpath.is_file()
        has_gallery = wf_id in by_workflow
        if not has_manifest and not has_gallery:
            continue

        manifest_data: dict[str, Any] = {}
        manifest_error: str | None = None
        if has_manifest:
            try:
                manifest_data = load_panel_manifest(mpath)
            except WikiError as exc:
                manifest_data = {}
                manifest_error = str(exc)

        gallery_entry = str(manifest_data.get("gallery_entry") or "").strip()
        gmeta: dict[str, Any] = {}
        if gallery_entry and gallery_entry in by_entry:
            gmeta = by_entry[gallery_entry]
        elif wf_id in by_workflow:
            gallery_entry, gmeta = by_workflow[wf_id]
        elif gallery_entry and _relative(gallery_entry):
            cand = gallery_root / gallery_entry / "meta.json"
            if cand.is_file() and _safe_existing(cand, gallery_root):
                try:
                    loaded = read_json(cand)
                    if isinstance(loaded, dict):
                        gmeta = loaded
                except (WikiError, OSError, ValueError):
                    pass

        stats = summarize_panel_manifest(manifest_data) if manifest_data.get("panels") else dict(_EMPTY_STATS)
        figures_meta = gmeta.get("figures") if isinstance(gmeta.get("figures"), list) else []
        cover_url = None
        for fig in figures_meta:
            if isinstance(fig, dict):
                cover_url = _gallery_url(gallery_root, gallery_entry, fig.get("replica"))
                if cover_url:
                    break
        if not cover_url and gallery_entry:
            cover_url = _gallery_url(gallery_root, gallery_entry, "figures/fig01_replica.png")

        year = manifest_data.get("year") or gmeta.get("year")
        if year is None:
            m_year = re.search(r"\b(19|20)\d{2}\b", " ".join(str(c) for c in (meta.get("cite") or [])))
            if m_year:
                year = int(m_year.group(0))

        journal = str(manifest_data.get("journal") or gmeta.get("journal") or "").strip()
        doi = str(manifest_data.get("doi") or gmeta.get("doi") or "").strip()
        paper_id = str(manifest_data.get("paper_id") or gmeta.get("paper_id") or "").strip()

        receipts_meta, _ = _load_receipts_index(path.with_suffix(""))
        receipt_counts = _summarize_receipts(wiki_root, path, receipts_meta)

        gallery_slugs = {
            str(f.get("slug") or "").strip()
            for f in figures_meta
            if isinstance(f, dict) and str(f.get("slug") or "").strip()
        }
        manifest_figs: dict[str, dict[str, Any]] = {}
        for item in manifest_data.get("panels") or []:
            if not isinstance(item, dict):
                continue
            slug = _derive_figure_slug(item)
            if not slug:
                continue
            info = manifest_figs.setdefault(
                slug,
                {"slug": slug, "label": str(item.get("figure") or slug), "has_computed": False},
            )
            tier = str(item.get("evidence_tier") or "")
            if tier not in EXCLUDED_EVIDENCE_TIERS:
                info["has_computed"] = True
        if gallery_slugs:
            reproduced_figure_count = len(gallery_slugs)
            manifest_only_figures = [
                {"slug": slug, "label": info["label"]}
                for slug, info in manifest_figs.items()
                if slug not in gallery_slugs
            ]
        else:
            reproduced_figure_count = sum(1 for info in manifest_figs.values() if info["has_computed"])
            manifest_only_figures = [
                {"slug": slug, "label": info["label"]}
                for slug, info in manifest_figs.items()
                if not info["has_computed"]
            ]

        records.append({
            "workflow_id": wf_id,
            "path": path,
            "meta": meta,
            "manifest": manifest_data,
            "manifest_error": manifest_error,
            "gallery_entry": gallery_entry,
            "gallery_meta": gmeta,
            "cover_url": cover_url,
            "paper_id": paper_id,
            "doi": doi,
            "journal": journal,
            "year": year,
            "license": str(manifest_data.get("license") or meta.get("license") or ""),
            "upstream_repo": str(gmeta.get("upstream_repo") or ""),
            "figure_count": len(figures_meta) or stats["figures"],
            "reproduced_figure_count": reproduced_figure_count,
            "manifest_only_figures": manifest_only_figures,
            "manifest_only_figure_count": len(manifest_only_figures),
            "stats": stats,
            "has_receipts": (path.with_suffix("") / "panel-receipts.json").is_file(),
            "receipt_counts": receipt_counts,
        })
    return records


def paper_origins_by_template(config: Config) -> dict[str, list[dict[str, Any]]]:
    """Map template IDs referenced in replicated paper manifests back to their paper workflows."""
    return cached_vault_value(
        config.wiki_root,
        "paper_origins_by_template",
        lambda: _build_paper_origins_by_template(config),
        gallery_root=config.gallery_root,
    )


def _build_paper_origins_by_template(config: Config) -> dict[str, list[dict[str, Any]]]:
    mapping: dict[str, list[dict[str, Any]]] = {}
    for rec in _iter_paper_workflows(config):
        panels = rec["manifest"].get("panels")
        if not isinstance(panels, list):
            continue
        counts: dict[str, int] = {}
        for item in panels:
            if not isinstance(item, dict):
                continue
            tier = item.get("evidence_tier")
            if isinstance(tier, str) and tier in EXCLUDED_EVIDENCE_TIERS:
                continue
            tid = item.get("template_id")
            if isinstance(tid, str) and tid.strip():
                counts[tid.strip()] = counts.get(tid.strip(), 0) + 1
            for etid in item.get("extra_templates") or []:
                if isinstance(etid, str) and etid.strip():
                    counts[etid.strip()] = counts.get(etid.strip(), 0) + 1
        for tid, panel_count in counts.items():
            mapping.setdefault(tid, []).append({
                "workflow_id": rec["workflow_id"],
                "title": rec["meta"].get("title") or rec["workflow_id"],
                "paper_id": rec["paper_id"],
                "doi": rec["doi"],
                "journal": rec["journal"],
                "year": rec["year"],
                "panel_count": panel_count,
            })
    return mapping


def _find_project_page(wiki_root: Path, paper_id: str, workflow_id: str) -> str | None:
    proj_dir = wiki_root / "projects"
    if not proj_dir.is_dir():
        return None
    if paper_id and (proj_dir / f"{paper_id}.md").is_file():
        return f"projects/{paper_id}.md"
    for p in sorted(proj_dir.glob("*.md")):
        try:
            meta, body = read_page(p)
        except (WikiError, OSError, UnicodeDecodeError):
            continue
        if meta.get("slug") == paper_id or workflow_id in body:
            return p.relative_to(wiki_root).as_posix()
    return None


def list_papers(config: Config) -> list[dict[str, Any]]:
    """Return summary cards for all replicated papers in the Wiki."""
    return cached_vault_value(
        config.wiki_root,
        "papers_list",
        lambda: _build_list_papers(config),
        gallery_root=config.gallery_root,
    )


def _build_list_papers(config: Config) -> list[dict[str, Any]]:
    wiki_root = config.wiki_root.resolve()
    items: list[dict[str, Any]] = []
    for rec in _iter_paper_workflows(config):
        wf_id = rec["workflow_id"]
        meta = rec["meta"]
        items.append({
            "workflow_id": wf_id,
            "title": meta.get("title") or wf_id,
            "summary": meta.get("summary") or "",
            "paper_id": rec["paper_id"],
            "doi": rec["doi"],
            "journal": rec["journal"],
            "year": rec["year"],
            "license": rec["license"],
            "upstream_repo": rec["upstream_repo"],
            "workflow_page": f"methods/{wf_id}.md",
            "project_page": _find_project_page(wiki_root, rec["paper_id"], wf_id),
            "gallery_entry": rec["gallery_entry"],
            "cover_url": rec["cover_url"],
            "figure_count": rec["figure_count"],
            "reproduced_figure_count": rec["reproduced_figure_count"],
            "manifest_only_figures": rec["manifest_only_figures"],
            "manifest_only_figure_count": rec["manifest_only_figure_count"],
            "has_receipts": rec["has_receipts"],
            "receipt_counts": rec["receipt_counts"],
            "manifest_error": rec["manifest_error"],
            "stats": rec["stats"],
        })
    items.sort(key=lambda x: (-(int(x["year"]) if isinstance(x["year"], int) else 0), x["workflow_id"]))
    return items


def _load_template_summaries(wiki_root: Path) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    tpl_dir = wiki_root / "templates"
    if not tpl_dir.is_dir():
        return summaries
    for path in sorted(tpl_dir.glob("*.md")):
        try:
            meta, _ = read_page(path)
        except (WikiError, OSError, UnicodeDecodeError):
            continue
        if meta.get("type") != "template" or meta.get("status") == "archived":
            continue
        tid = str(meta.get("id") or path.stem)
        preview_file = path.with_suffix("") / "preview.png"
        summaries[tid] = {
            "id": tid,
            "title": meta.get("title") or tid,
            "path": path.relative_to(wiki_root).as_posix(),
            "status": meta.get("status") or "draft",
            "language": meta.get("language") or "",
            "style_tier": meta.get("style_tier"),
            "journal_style": meta.get("journal_style"),
            "chart_types": list(meta.get("chart_types") or []),
            "preview_url": f"/files/wiki/templates/{quote(tid)}/preview.png" if preview_file.is_file() else None,
        }
    return summaries


def _load_receipts_index(asset_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    rpath = asset_dir / "panel-receipts.json"
    if not rpath.is_file():
        return {}, {}
    try:
        raw = json.loads(rpath.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}, {}
    if not isinstance(raw, dict):
        return {}, {}

    index: dict[str, dict[str, Any]] = {}
    entries = raw.get("panels") or raw.get("receipts") or []
    if isinstance(entries, dict):
        for k, v in entries.items():
            if isinstance(v, dict):
                index[str(k)] = v
    elif isinstance(entries, list):
        for item in entries:
            if not isinstance(item, dict):
                continue
            pk = item.get("panel_key")
            if isinstance(pk, str) and pk.strip():
                index[pk.strip()] = item
            sp = item.get("script_path")
            if isinstance(sp, str) and sp.strip():
                index[sp.strip()] = item
    return raw, index


def _derive_panel_letter(item: dict[str, Any]) -> str:
    if isinstance(item.get("panel_letter"), str) and item["panel_letter"].strip():
        return item["panel_letter"].strip()
    pk = item.get("panel_key")
    if isinstance(pk, str) and "/" in pk:
        return pk.split("/", 1)[1].strip()
    pan = str(item.get("panel") or "").strip()
    m = re.match(r"^(?:S?\d+)([A-Za-z].*)$", pan)
    return m.group(1) if m else pan


def _derive_figure_slug(item: dict[str, Any]) -> str:
    if isinstance(item.get("figure_slug"), str) and item["figure_slug"].strip():
        return item["figure_slug"].strip()
    pk = item.get("panel_key")
    if isinstance(pk, str) and "/" in pk:
        return pk.split("/", 1)[0].strip()
    return normalize_figure_slug(str(item.get("figure") or ""))


def get_paper_detail(config: Config, workflow_id: str) -> dict[str, Any] | None:
    """Return full figure gallery + atomic panel details for a replicated paper workflow."""
    if not _relative(workflow_id):
        return None
    matches = [rec for rec in _iter_paper_workflows(config) if rec["workflow_id"] == workflow_id]
    if not matches:
        return None
    rec = matches[0]

    wiki_root = config.wiki_root.resolve()
    gallery_root = config.gallery_root.resolve()
    asset_dir = rec["path"].with_suffix("")
    gmeta = rec["gallery_meta"]
    gallery_entry = rec["gallery_entry"]

    tpl_summaries = _load_template_summaries(wiki_root)
    receipts_meta, receipts_index = _load_receipts_index(asset_dir)

    figures_out: list[dict[str, Any]] = []
    fig_by_slug: dict[str, dict[str, Any]] = {}
    for raw_fig in gmeta.get("figures") or []:
        if not isinstance(raw_fig, dict):
            continue
        slug = str(raw_fig.get("slug") or "").strip()
        if not slug:
            continue
        label = str(raw_fig.get("label") or slug)
        fig_entry = {
            "slug": slug,
            "label": label,
            "caption": str(raw_fig.get("caption") or ""),
            "is_supplementary": slug.lower().startswith("sfig") or "supp" in label.lower(),
            "declared_panels": list(raw_fig.get("panels") or []),
            "replica_url": _gallery_url(gallery_root, gallery_entry, raw_fig.get("replica")),
            "side_by_side_url": _gallery_url(gallery_root, gallery_entry, raw_fig.get("side_by_side")),
            "replica_px": list(raw_fig.get("replica_px") or []),
            "side_by_side_px": list(raw_fig.get("side_by_side_px") or []),
            "visual_review": str(raw_fig.get("visual_review") or ""),
            "manifest_only": False,
            "panels": [],
        }
        figures_out.append(fig_entry)
        fig_by_slug[slug] = fig_entry

    for item in rec["manifest"].get("panels") or []:
        if not isinstance(item, dict):
            continue
        fig_slug = _derive_figure_slug(item)
        letter = _derive_panel_letter(item)
        panel_key = str(item.get("panel_key") or (f"{fig_slug}/{letter}" if fig_slug and letter else "")).strip()
        tier = str(item.get("evidence_tier") or "")
        is_excluded = tier in EXCLUDED_EVIDENCE_TIERS

        raw_script = str(item.get("script_path") or "").strip().lstrip("/")
        script_exists = _resolve_panel_script(wiki_root, rec["path"], raw_script) is not None

        tid = item.get("template_id")
        tpl_summary = tpl_summaries.get(tid.strip()) if isinstance(tid, str) and tid.strip() else None
        extra_summaries = [
            tpl_summaries[et.strip()]
            for et in (item.get("extra_templates") or [])
            if isinstance(et, str) and et.strip() in tpl_summaries
        ]
        receipt = receipts_index.get(panel_key) or (receipts_index.get(raw_script) if raw_script else None)

        panel_entry = {
            "panel_key": panel_key,
            "figure_slug": fig_slug,
            "figure": str(item.get("figure") or fig_slug),
            "panel_letter": letter,
            "panel": str(item.get("panel") or letter),
            "evidence_tier": tier,
            "is_excluded": is_excluded,
            "description": str(item.get("description") or item.get("note") or ""),
            "note": str(item.get("note") or item.get("description") or ""),
            "script_path": raw_script,
            "script_available": script_exists,
            "code_url": (
                f"/api/papers/{quote(workflow_id, safe='')}/panel-code?path={quote(raw_script, safe='/')}"
                if raw_script else None
            ),
            "input_tables": list(item.get("input_tables") or []),
            "methods": list(item.get("methods") or []),
            "template_id": tid.strip() if isinstance(tid, str) and tid.strip() else None,
            "template": tpl_summary,
            "extra_templates": extra_summaries,
            "receipt": receipt,
        }

        if fig_slug not in fig_by_slug:
            label = str(item.get("figure") or fig_slug)
            synthetic = {
                "slug": fig_slug,
                "label": label,
                "caption": "",
                "is_supplementary": fig_slug.lower().startswith("sfig") or "supp" in label.lower(),
                "declared_panels": [],
                "replica_url": None,
                "side_by_side_url": None,
                "replica_px": [],
                "side_by_side_px": [],
                "visual_review": "",
                "manifest_only": True,
                "panels": [],
            }
            figures_out.append(synthetic)
            fig_by_slug[fig_slug] = synthetic
        fig_by_slug[fig_slug]["panels"].append(panel_entry)

    runtime_data: dict[str, Any] | None = None
    runtime_path = asset_dir / "code" / "runtime.json"
    if runtime_path.is_file():
        try:
            loaded_rt = read_json(runtime_path)
            if isinstance(loaded_rt, dict):
                runtime_data = loaded_rt
        except (WikiError, OSError, ValueError):
            pass

    receipt_counts = _summarize_receipts(wiki_root, rec["path"], receipts_meta) or {
        "total": 0,
        "generated": 0,
        "smoke_tested": 0,
        "hash_checked": 0,
        "hash_matched": 0,
        "hash_mismatched": 0,
        "script_missing": 0,
        "status_counts": {},
    }
    reproduced_figure_count = sum(1 for fig in figures_out if not fig.get("manifest_only"))
    manifest_only_figure_count = sum(1 for fig in figures_out if fig.get("manifest_only"))

    return {
        "workflow_id": workflow_id,
        "title": rec["meta"].get("title") or workflow_id,
        "summary": rec["meta"].get("summary") or "",
        "paper_id": rec["paper_id"],
        "doi": rec["doi"],
        "journal": rec["journal"],
        "year": rec["year"],
        "license": rec["license"],
        "upstream_repo": rec["upstream_repo"],
        "upstream_commit": str(gmeta.get("upstream_commit") or ""),
        "workflow_page": f"methods/{workflow_id}.md",
        "project_page": _find_project_page(wiki_root, rec["paper_id"], workflow_id),
        "gallery_entry": gallery_entry,
        "cover_url": rec["cover_url"],
        "excluded_wet_lab": list(gmeta.get("excluded_wet_lab") or []),
        "reproduced_figure_count": reproduced_figure_count,
        "manifest_only_figure_count": manifest_only_figure_count,
        "manifest_error": rec["manifest_error"],
        "stats": rec["stats"],
        "receipts_summary": {
            "present": bool(receipts_meta),
            "generated_at": receipts_meta.get("generated_at") if isinstance(receipts_meta, dict) else None,
            "count": receipt_counts["total"],
            **receipt_counts,
        },
        "runtime": runtime_data,
        "figures": figures_out,
    }


def read_paper_panel_code(config: Config, workflow_id: str, rel_path: str) -> dict[str, Any]:
    """Read a single panel or workflow script safely within `methods/<workflow_id>/(code|source)/`."""
    if not _relative(workflow_id) or not _relative(rel_path):
        raise WikiError("非法的论文或脚本路径")

    parts = PurePosixPath(rel_path).parts
    if len(parts) < 2 or parts[0] not in ("code", "source") or any(
        part.startswith(".") or part.lower() in _SKIP_DIRS for part in parts
    ):
        raise WikiError("仅允许读取工作流 code/ 或 source/ 目录下的脚本文件")

    wiki_root = config.wiki_root.resolve()
    method_page = resolve_page_ref(wiki_root, workflow_id, expected_type="method")
    if (
        method_page is None
        or not _safe_existing(method_page, wiki_root)
        or not confined(method_page, wiki_root, wiki_root)
    ):
        raise WikiError("工作流页面不存在")
    meta, _ = read_page(method_page)
    if meta.get("type") != "method" or meta.get("status") == "archived":
        raise WikiError("工作流不可用")

    mpath = manifest_path_for(config, method_page)
    if not _safe_existing(mpath, wiki_root) or not mpath.is_file():
        raise WikiError("仅允许读取已注册论文工作流的面板脚本")

    target = _resolve_panel_script(wiki_root, method_page, rel_path)
    if target is None:
        raise WikiError("脚本文件不存在")

    size = target.stat().st_size
    language = _language(target)
    if size > MAX_PREVIEW_BYTES:
        text, encoding, note = None, None, "文件超过 1 MiB 文本查看上限，请下载原文件。"
    elif language in ("binary", "unknown"):
        text, encoding, note = None, None, "二进制或未知文件类型，仅提供原字节下载。"
    else:
        raw = target.read_bytes()
        if b"\x00" in raw or any(byte < 9 or 13 < byte < 32 for byte in raw):
            text, encoding, note = None, None, "内容包含二进制控制字节。"
        else:
            try:
                text, encoding, note = raw.decode("utf-8-sig"), "utf-8", ""
            except UnicodeDecodeError:
                text, encoding, note = raw.decode("utf-8", errors="replace"), "utf-8", "包含非 UTF-8 字符，已替换显示。"

    return {
        "workflow_id": str(meta.get("id") or workflow_id),
        "path": rel_path,
        "language": language,
        "size": size,
        "sha256": _hash(target),
        "encoding": encoding,
        "text": text,
        "note": note,
    }

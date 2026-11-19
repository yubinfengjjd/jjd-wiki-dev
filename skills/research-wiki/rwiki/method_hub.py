"""Read-only Method Hub aggregation: methods, attached visualizations, render bridges, and recipes."""
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from urllib.parse import quote

from .acceptance import acceptance_stale, entry_errors
from .aliases import resolve_page_ref
from .asset_checkout import profile
from .config import Config, read_json
from .curation import excluded_paths
from .errors import WikiError
from .method_implementations import METHOD_KINDS, implementation_status
from .method_taxonomy import (
    DOMAIN_LABELS,
    _LEGACY_TAG_TO_DOMAIN,
    domains_for,
    taxonomy,
)
from .pages import read_page, section_text
from .read_cache import _snapshot, read_session
from .relations import all_relations
from .spec import load_spec

_COMPAT_ORDER = {"direct": 0, "curated": 1, "adaptable": 2, "unreviewed": 3, "candidate": 4}


def _session_ctx():
    return read_session() if _snapshot.get() is None else nullcontext()


def _section(body: str, title: str) -> str:
    try:
        return section_text(body, title)
    except WikiError:
        return ""


def template_preview_url(root: Path, meta: dict) -> str | None:
    """Return a served preview image URL for a template if a local asset file exists."""
    tid = str(meta.get("id") or "")
    if not tid:
        return None
    direct = root / "templates" / tid / "preview.png"
    if direct.is_file():
        return "/files/wiki/" + quote(f"templates/{tid}/preview.png", safe="/")
    for src in meta.get("sources") or []:
        if isinstance(src, str) and src.startswith("recipes/"):
            rid = src.removeprefix("recipes/").removesuffix(".md")
            candidate = root / "recipes" / rid / "preview.png"
            if candidate.is_file():
                return "/files/wiki/" + quote(f"recipes/{rid}/preview.png", safe="/")
    for lid in meta.get("layouts") or []:
        if isinstance(lid, str) and lid:
            candidate = root / "layouts" / lid / "thumb.png"
            if candidate.is_file():
                return "/files/wiki/" + quote(f"layouts/{lid}/thumb.png", safe="/")
    return None


def recipe_preview_url(root: Path, rid: str) -> str | None:
    candidate = root / "recipes" / rid / "preview.png"
    if candidate.is_file():
        return "/files/wiki/" + quote(f"recipes/{rid}/preview.png", safe="/")
    return None


def spec_tables_list(spec: dict) -> list[dict]:
    """Normalize spec.tables into a list preserving explicit/default `required` (default True)."""
    tables: list[dict] = []
    raw_tables = spec.get("tables")
    if not isinstance(raw_tables, dict):
        return tables
    for key, table in raw_tables.items():
        if not isinstance(table, dict):
            continue
        iface = table.get("interface")
        tables.append({
            "key": str(key),
            "interface": iface.strip() if isinstance(iface, str) else "",
            "description": str(table.get("description") or ""),
            "required": bool(table.get("required", True)),
        })
    return tables


def match_interfaces(
    tables: list[dict],
    available: set[str],
    *,
    required_pool: set[str] | None = None,
) -> tuple[str | None, list[str], list[str]]:
    """Strict full vs partial interface match (`required` defaults to True).

    Returns (match_type, matched_interfaces, missing_required_interfaces).
    When `required_pool` is given, at least one required interface must intersect `required_pool`.
    """
    required_ifaces = {t["interface"] for t in tables if t["interface"] and t.get("required", True)}
    all_ifaces = {t["interface"] for t in tables if t["interface"]}
    if not required_ifaces:
        return None, [], []
    anchor = required_pool if required_pool is not None else available
    if not (required_ifaces & anchor):
        return None, [], []
    matched = sorted(all_ifaces & available)
    missing = sorted(required_ifaces - available)
    match_type = "full" if not missing else "partial"
    return match_type, matched, missing


def _load_template_catalog(config: Config, hidden: set[str]) -> list[dict]:
    root = config.wiki_root
    catalog: list[dict] = []
    tpl_dir = root / "templates"
    if not tpl_dir.is_dir():
        return catalog
    for path in sorted(tpl_dir.glob("*.md")):
        rel_path = path.relative_to(root).as_posix()
        if rel_path in hidden:
            continue
        try:
            meta, _ = read_page(path)
        except WikiError:
            continue
        if meta.get("type") != "template" or meta.get("status") == "archived":
            continue
        asset_dir = path.with_suffix("")
        spec_file = asset_dir / "spec.json"
        if not spec_file.is_file():
            continue
        try:
            spec = load_spec(asset_dir)
        except (WikiError, OSError, ValueError, KeyError, TypeError):
            try:
                spec = read_json(spec_file)
            except (WikiError, OSError, ValueError):
                continue
        tables = spec_tables_list(spec)
        if not tables:
            continue

        primary_method_id: str | None = None
        raw_pm = meta.get("primary_method")
        if isinstance(raw_pm, str) and raw_pm.strip():
            resolved_pm = resolve_page_ref(root, raw_pm.strip(), expected_type="method")
            if resolved_pm is not None:
                primary_method_id = resolved_pm.stem
            else:
                primary_method_id = raw_pm.strip().removeprefix("methods/").removesuffix(".md")

        sources = [
            str(s).removesuffix(".md").removeprefix("recipes/")
            for s in (meta.get("sources") or [])
            if isinstance(s, str) and str(s).strip().startswith("recipes/")
        ]
        item = {
            "id": str(meta.get("id") or path.stem),
            "title": str(meta.get("title") or path.stem),
            "path": rel_path,
            "kind": "template",
            "status": str(meta.get("status") or "draft"),
            "language": str(meta.get("language") or spec.get("language") or ""),
            "license": str(meta.get("license") or ""),
            "chart_types": [str(c) for c in (meta.get("chart_types") or []) if isinstance(c, str)],
            "tables": tables,
            "sources": sources,
            "primary_method_id": primary_method_id,
            "preview_url": template_preview_url(root, meta),
        }
        if meta.get("style_tier"):
            item["style_tier"] = meta["style_tier"]
        if meta.get("journal_style"):
            item["journal_style"] = meta["journal_style"]
        catalog.append(item)
    return catalog


def _load_method_map(root: Path) -> tuple[dict[str, dict], set[str]]:
    map_path = root / "recipes" / "method-map.json"
    if not map_path.is_file():
        return {}, set()
    try:
        data = read_json(map_path)
    except (WikiError, OSError, ValueError):
        return {}, set()
    mappings = data.get("mappings") if isinstance(data.get("mappings"), dict) else {}
    unmapped = {str(x) for x in (data.get("unmapped") or []) if isinstance(x, str)}
    return mappings, unmapped


def _load_recipes_index(
    config: Config,
    hidden: set[str],
    mappings: dict[str, dict],
    unmapped_set: set[str],
    promoted_recipes: set[str] | None = None,
) -> tuple[dict[str, list[dict]], list[dict]]:
    root = config.wiki_root
    by_method: dict[str, list[dict]] = {}
    unmapped_recipes: list[dict] = []
    rec_dir = root / "recipes"
    if not rec_dir.is_dir():
        return by_method, unmapped_recipes

    promoted = promoted_recipes or set()
    for path in sorted(rec_dir.glob("*.md")):
        rel_path = path.relative_to(root).as_posix()
        if rel_path in hidden:
            continue
        try:
            meta, _ = read_page(path)
        except WikiError:
            continue
        if meta.get("type") != "recipe" or meta.get("status") == "archived":
            continue
        rid = str(meta.get("id") or path.stem)
        if rid in promoted:
            continue
        entry = mappings.get(rid) if isinstance(mappings.get(rid), dict) else {}
        methods = [str(m) for m in (entry.get("methods") or []) if isinstance(m, str) and m.strip()]
        record = {
            "id": rid,
            "title": str(meta.get("title") or rid),
            "path": rel_path,
            "kind": "recipe",
            "status": str(meta.get("status") or "draft"),
            "language": str(meta.get("language") or ""),
            "license": str(meta.get("license") or ""),
            "runner": str(meta.get("runner") or ""),
            "chart_types": [str(c) for c in (meta.get("chart_types") or []) if isinstance(c, str)],
            "tags": [str(t) for t in (meta.get("tags") or []) if isinstance(t, str)],
            "data_domains": domains_for(meta),
            "confidence": str(entry.get("confidence") or "curated"),
            "note": str(entry.get("note") or ""),
            "methods": methods,
            "preview_url": recipe_preview_url(root, rid),
        }
        if not methods or rid in unmapped_set:
            unmapped_recipes.append(record)
            continue
        for mid in methods:
            by_method.setdefault(mid, []).append(record)
    return by_method, unmapped_recipes


def _attached_visualizations(
    method_id: str,
    method_rel_path: str,
    outputs: set[str],
    render_bridges: list[dict],
    templates: list[dict],
    relations: list[dict],
    *,
    method_recipes: list[dict] | None = None,
    extra_template_ids: set[str] | None = None,
) -> dict:
    rel_by_figure: dict[str, dict] = {}
    for rel in relations:
        if rel["method"] == method_rel_path and rel.get("target_kind") == "template":
            rel_by_figure[rel["figure"]] = rel

    extra_ids = extra_template_ids or set()
    curated: list[dict] = []
    curated_ids: set[str] = set()
    for tpl in templates:
        rel = rel_by_figure.get(tpl["path"])
        is_primary = tpl["primary_method_id"] == method_id
        is_extra = tpl["id"] in extra_ids
        if rel is None and not is_primary and not is_extra:
            continue
        curated_ids.add(tpl["id"])
        # Semantic boundary: primary_method alone NEVER upgrades compatibility or verification.
        compatibility = rel["compatibility"] if rel is not None else "unreviewed"
        verification = (
            dict(rel["verification"])
            if rel is not None
            else {
                "state": "not_run",
                "scope": "仅声明所属方法，尚未在方法页 figure_relations 完成语义配对审查。",
                "evidence": [],
            }
        )
        curated.append({
            "id": tpl["id"],
            "title": tpl["title"],
            "path": tpl["path"],
            "kind": "template",
            "status": tpl["status"],
            "language": tpl["language"],
            "license": tpl.get("license", ""),
            "chart_types": tpl["chart_types"],
            "tables": tpl["tables"],
            "preview_url": tpl["preview_url"],
            "primary": is_primary,
            "compatibility": compatibility,
            "verification": verification,
            "reason": rel["reason"] if rel is not None else "",
            "adaptation": rel["adaptation"] if rel is not None else "",
            "prerequisites": list(rel["prerequisites"]) if rel is not None else [],
        })

    for rec in (method_recipes or []):
        if rec["id"] in curated_ids:
            continue
        curated_ids.add(rec["id"])
        is_ready = rec.get("status") == "ready"
        curated.append({
            "id": rec["id"],
            "title": rec["title"],
            "path": rec["path"],
            "kind": "recipe",
            "status": rec["status"],
            "language": rec["language"],
            "license": rec.get("license", ""),
            "chart_types": rec["chart_types"],
            "tables": [],
            "preview_url": rec["preview_url"],
            "primary": True,
            "compatibility": "curated",
            "verification": {
                "state": "verified" if is_ready else "not_run",
                "scope": "原样可运行模板，由方法映射挂载" if is_ready else "尚未在当前环境完成实跑验证",
                "evidence": [],
            },
            "reason": rec.get("note", ""),
            "adaptation": "",
            "prerequisites": [],
        })

    curated.sort(key=lambda item: (
        item.get("kind") != "template",
        not item["primary"],
        _COMPAT_ORDER.get(item["compatibility"], 9),
        item["id"],
    ))

    object_compatible: list[dict] = []
    if outputs:
        for tpl in templates:
            if tpl["id"] in curated_ids:
                continue
            match_type, matched, missing = match_interfaces(tpl["tables"], outputs)
            if match_type is None:
                continue
            object_compatible.append({
                "id": tpl["id"],
                "title": tpl["title"],
                "path": tpl["path"],
                "status": tpl["status"],
                "language": tpl["language"],
                "chart_types": tpl["chart_types"],
                "tables": tpl["tables"],
                "preview_url": tpl["preview_url"],
                "match_type": match_type,
                "matched_interfaces": matched,
                "missing_required_interfaces": missing,
            })
    object_compatible.sort(key=lambda item: (
        0 if item["match_type"] == "full" else 1,
        -len(item["matched_interfaces"]),
        item["id"],
    ))

    bridge_by_iface = {
        b["interface"]: b
        for b in render_bridges
        if isinstance(b, dict) and isinstance(b.get("interface"), str) and b["interface"].strip()
    }
    render_bridged: list[dict] = []
    if bridge_by_iface:
        bridge_ifaces = set(bridge_by_iface)
        combined_available = bridge_ifaces | outputs
        for tpl in templates:
            match_type, matched, missing = match_interfaces(
                tpl["tables"],
                combined_available,
                required_pool=bridge_ifaces,
            )
            if match_type is None:
                continue
            req_matched_bridges = [
                bridge_by_iface[t["interface"]]
                for t in tpl["tables"]
                if t["interface"] in bridge_by_iface and t.get("required", True)
            ]
            if not req_matched_bridges:
                continue
            lead = req_matched_bridges[0]
            render_bridged.append({
                "id": tpl["id"],
                "title": tpl["title"],
                "path": tpl["path"],
                "status": tpl["status"],
                "language": tpl["language"],
                "chart_types": tpl["chart_types"],
                "tables": tpl["tables"],
                "preview_url": tpl["preview_url"],
                "via_bridge": lead["interface"],
                "from_output": lead["from_output"],
                "extractor_note": "；".join(dict.fromkeys(b["extractor_note"] for b in req_matched_bridges)),
                "unit": lead.get("unit", ""),
                "bridges": req_matched_bridges,
                "match_type": match_type,
                "matched_interfaces": matched,
                "missing_required_interfaces": missing,
            })
    render_bridged.sort(key=lambda item: (
        0 if item["match_type"] == "full" else 1,
        -len(item["matched_interfaces"]),
        item["id"],
    ))

    all_previews: list[dict] = []
    seen_previews: set[str] = set()

    def _add_preview(item: dict, source_kind: str) -> None:
        if len(all_previews) >= 6 or item["id"] in seen_previews:
            return
        seen_previews.add(item["id"])
        all_previews.append({
            "id": item["id"],
            "title": item["title"],
            "path": item["path"],
            "preview_url": item["preview_url"],
            "source": source_kind,
            "primary": bool(item.get("primary", False)),
            "compatibility": item.get("compatibility"),
            "match_type": item.get("match_type"),
            "chart_types": item.get("chart_types", []),
            "language": item.get("language", ""),
        })

    for item in sorted(curated, key=lambda x: (x["preview_url"] is None,)):
        _add_preview(item, "curated")
    for item in sorted(render_bridged, key=lambda x: (x["preview_url"] is None,)):
        _add_preview(item, "render_bridged")
    for item in sorted(
        (x for x in object_compatible if x["match_type"] == "full"),
        key=lambda x: (x["preview_url"] is None,),
    ):
        _add_preview(item, "object_compatible")

    return {
        "curated": curated,
        "object_compatible": object_compatible,
        "render_bridged": render_bridged,
        "all_previews": all_previews,
    }


def _normalize_render_bridges(raw) -> list[dict]:
    if not isinstance(raw, list):
        return []
    bridges: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        iface = item.get("interface")
        from_output = item.get("from_output")
        note = item.get("extractor_note")
        if not (isinstance(iface, str) and iface.strip()):
            continue
        bridges.append({
            "interface": iface.strip(),
            "from_output": str(from_output or "").strip(),
            "extractor_note": str(note or "").strip(),
            "unit": str(item.get("unit") or "").strip(),
        })
    return bridges


def _method_workflow(config: Config, path: Path, meta: dict, impl_status: list[dict], sparse: bool) -> dict | None:
    """Compute workflow snapshot for a single method without scanning unrelated recipes/layouts."""
    status = meta.get("status")
    if status == "archived":
        return {"stage": "archived", "queue": None, "label": "已归档", "reason": "已归档，不进入待办。", "templates": []}
    if sparse:
        return {
            "stage": "checking",
            "queue": None,
            "label": "轻量检出 · 未核对完整证据",
            "reason": "轻量检出不据资产省略判断科学或回放失败；正式维护请切换 full。",
            "templates": [],
        }
    if status not in ("draft", "ready"):
        return None
    method_kind = meta.get("method_kind")
    if method_kind not in METHOD_KINDS:
        return {
            "stage": "method_classify",
            "queue": "agent",
            "label": "待分类",
            "reason": "旧方法尚未分类；先核对研究问题与资料类型。",
            "templates": [],
        }
    errors = entry_errors(config, path)
    if errors or (status == "ready" and acceptance_stale(path)):
        return {
            "stage": "method_work",
            "queue": "agent",
            "label": "待完善笔记",
            "reason": "；".join(errors) or "验收记录需重新核对。",
            "templates": [],
        }
    if status == "draft":
        return {
            "stage": "method_confirm",
            "queue": "confirm",
            "label": "待你确认",
            "reason": "笔记与知识关联检查已填写，待作者核对。",
            "templates": [],
        }
    if method_kind in ("workflow", "technical"):
        label = "流程资料已确认" if method_kind == "workflow" else "技术资料已确认"
        return {
            "stage": "complete",
            "queue": None,
            "label": label,
            "reason": "笔记与资料内容已确认；不作为可执行分析推荐，也不要求分析实现收据。",
            "templates": [],
        }
    verified = any(item.get("state") == "verified" for item in impl_status)
    if verified:
        return {
            "stage": "complete",
            "queue": None,
            "label": "已验证实现",
            "reason": "笔记已确认；仅实现收据中列明的分支和范围通过验证。",
            "templates": [],
        }
    return {
        "stage": "method_implementation",
        "queue": "agent",
        "label": "待验证实现" if impl_status else "待实现",
        "reason": "笔记已确认；实现尚无当前有效验证，不作为可执行分析推荐。",
        "templates": [],
    }


def _build_single_hub(
    config: Config,
    path: Path,
    meta: dict,
    body: str,
    *,
    templates: list[dict],
    relations: list[dict],
    recipes_by_method: dict[str, list[dict]],
    extra_templates_by_method: dict[str, set[str]] | None = None,
    unmapped_recipes_count: int,
    sparse: bool,
) -> dict:
    root = config.wiki_root
    rel_path = path.relative_to(root).as_posix()
    method_id = str(meta.get("id") or path.stem)
    domains = domains_for(meta)
    inputs = [str(s) for s in (meta.get("inputs") or []) if isinstance(s, str) and s.strip()]
    outputs = [str(s) for s in (meta.get("outputs") or []) if isinstance(s, str) and s.strip()]
    render_bridges = _normalize_render_bridges(meta.get("render_bridges"))
    implementations = [dict(item) for item in (meta.get("implementations") or []) if isinstance(item, dict)]
    impl_status = [] if sparse else implementation_status(path, meta)
    summary = str(meta.get("summary") or "").strip() or _section(body, "用途").strip()
    next_steps = [s for s in (meta.get("next_steps") or []) if isinstance(s, dict)]
    method_recipes = list(recipes_by_method.get(method_id, []))

    return {
        "id": method_id,
        "title": str(meta.get("title") or method_id),
        "path": rel_path,
        "status": str(meta.get("status") or "draft"),
        "summary": summary,
        "data_domains": domains,
        "data_domain_labels": [DOMAIN_LABELS[d] for d in domains if d in DOMAIN_LABELS],
        "purposes": list(dict.fromkeys(
            str(p).strip() for p in (meta.get("purposes") or []) if isinstance(p, str) and p.strip()
        )),
        "tags": [str(t) for t in (meta.get("tags") or []) if isinstance(t, str) and t.strip()],
        "keywords": [str(k) for k in (meta.get("keywords") or []) if isinstance(k, str) and k.strip()],
        "inputs": inputs,
        "outputs": outputs,
        "data_contract": dict(meta.get("data_contract") or {}) if isinstance(meta.get("data_contract"), dict) else {},
        "render_bridges": render_bridges,
        "implementations": implementations,
        "implementation_status": impl_status,
        "workflow": _method_workflow(config, path, meta, impl_status, sparse),
        "next_steps_count": len(next_steps),
        "attached_visualizations": _attached_visualizations(
            method_id,
            rel_path,
            set(outputs),
            render_bridges,
            templates,
            relations,
            method_recipes=method_recipes,
            extra_template_ids=(extra_templates_by_method or {}).get(method_id),
        ),
        "reference_recipes": method_recipes,
        "unmapped_recipes_count": unmapped_recipes_count,
    }


def _hub_context(config: Config, *, include_recipes: bool = True) -> dict:
    root = config.wiki_root
    hidden = excluded_paths(config)
    templates = _load_template_catalog(config, hidden)
    promoted_recipes: set[str] = set()
    extra_templates_by_method: dict[str, set[str]] = {}
    if include_recipes:
        mappings, unmapped_set = _load_method_map(root)
        for tpl in templates:
            pm = tpl.get("primary_method_id")
            if not pm:
                continue
            for src in tpl.get("sources") or []:
                entry = mappings.get(src) if isinstance(mappings.get(src), dict) else {}
                mapped_methods = [str(m).strip() for m in (entry.get("methods") or []) if isinstance(m, str) and m.strip()]
                if pm in mapped_methods:
                    promoted_recipes.add(src)
                    for mid in mapped_methods:
                        if mid != pm:
                            extra_templates_by_method.setdefault(mid, set()).add(tpl["id"])
        recipes_by_method, unmapped_recipes = _load_recipes_index(
            config,
            hidden,
            mappings,
            unmapped_set,
            promoted_recipes=promoted_recipes,
        )
    else:
        recipes_by_method, unmapped_recipes = {}, []
    return {
        "hidden": hidden,
        "templates": templates,
        "relations": all_relations(config, include_archived=False),
        "recipes_by_method": recipes_by_method,
        "extra_templates_by_method": extra_templates_by_method,
        "unmapped_recipes": unmapped_recipes,
        "sparse": profile(config) == "light",
    }


def build_method_hub(config: Config, method_id: str) -> dict:
    """Aggregate one analysis method's hub payload, resolving aliases via rwiki.aliases."""
    with _session_ctx():
        path = resolve_page_ref(config.wiki_root, method_id, expected_type="method")
        if path is None:
            raise WikiError(f"未找到方法页面: {method_id}")
        meta, body = read_page(path)
        if meta.get("type") != "method":
            raise WikiError(f"页面类型不是 method: {method_id}")
        if meta.get("status") == "archived":
            raise WikiError(f"方法页面已归档: {method_id}")
        if meta.get("method_kind") != "analysis":
            raise WikiError(f"方法不是 analysis 类型: {method_id}")

        ctx = _hub_context(config)
        hub = _build_single_hub(
            config,
            path,
            meta,
            body,
            templates=ctx["templates"],
            relations=ctx["relations"],
            recipes_by_method=ctx["recipes_by_method"],
            extra_templates_by_method=ctx["extra_templates_by_method"],
            unmapped_recipes_count=len(ctx["unmapped_recipes"]),
            sparse=ctx["sparse"],
        )
        hub["requested_id"] = method_id
        return hub


def _matches_domain(method_hub: dict, domain: str) -> bool:
    if domain in DOMAIN_LABELS:
        return domain in method_hub["data_domains"]
    if domain in method_hub["tags"]:
        return True
    mapped = _LEGACY_TAG_TO_DOMAIN.get(domain)
    return bool(mapped and mapped in method_hub["data_domains"])


def _matches_query(method_hub: dict, query: str) -> bool:
    words = [w for w in dict.fromkeys(query.casefold().split()) if w]
    if not words:
        return True
    viz = method_hub["attached_visualizations"]
    parts = [
        method_hub["id"],
        method_hub["title"],
        method_hub["summary"],
        *method_hub["tags"],
        *method_hub["keywords"],
        *method_hub["data_domains"],
        *method_hub["data_domain_labels"],
        *method_hub["purposes"],
        *method_hub["inputs"],
        *method_hub["outputs"],
        *(item["id"] for item in viz["curated"]),
        *(item["title"] for item in viz["curated"]),
        *(item["id"] for item in viz["render_bridged"]),
        *(item["id"] for item in viz["object_compatible"]),
        *(rec["id"] for rec in method_hub["reference_recipes"]),
        *(rec["title"] for rec in method_hub["reference_recipes"]),
    ]
    searchable = "\n".join(parts).casefold()
    return all(word in searchable for word in words)


def list_method_hubs(
    config: Config,
    *,
    domain: str = "",
    purpose: str = "",
    q: str = "",
) -> dict:
    """List all non-archived analysis method hubs with optional domain/purpose/q filters."""
    with _session_ctx():
        root = config.wiki_root
        ctx = _hub_context(config)
        tax = taxonomy(root)

        methods_dir = root / "methods"
        all_hubs: list[dict] = []
        if methods_dir.is_dir():
            for path in sorted(methods_dir.glob("*.md")):
                rel_path = path.relative_to(root).as_posix()
                if rel_path in ctx["hidden"]:
                    continue
                try:
                    meta, body = read_page(path)
                except WikiError:
                    continue
                if (
                    meta.get("type") != "method"
                    or meta.get("status") == "archived"
                    or meta.get("method_kind") != "analysis"
                ):
                    continue
                all_hubs.append(
                    _build_single_hub(
                        config,
                        path,
                        meta,
                        body,
                        templates=ctx["templates"],
                        relations=ctx["relations"],
                        recipes_by_method=ctx["recipes_by_method"],
                        extra_templates_by_method=ctx["extra_templates_by_method"],
                        unmapped_recipes_count=len(ctx["unmapped_recipes"]),
                        sparse=ctx["sparse"],
                    )
                )

        d = domain.strip()
        p = purpose.strip()
        query = q.strip()
        filtered = [
            hub for hub in all_hubs
            if (not d or _matches_domain(hub, d))
            and (not p or p in hub["purposes"])
            and (not query or _matches_query(hub, query))
        ]

        return {
            "taxonomy": tax,
            "data_domains": tax["data_domains"],
            "methods": filtered,
            "total": len(all_hubs),
            "filtered_total": len(filtered),
            "unmapped_recipes": ctx["unmapped_recipes"],
            "unmapped_recipes_count": len(ctx["unmapped_recipes"]),
        }

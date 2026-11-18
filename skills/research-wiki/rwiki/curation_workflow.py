"""Lightweight closed-loop Method-Visualization curation, mapping, audit, and native scaffolding."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .aliases import resolve_page_ref
from .config import Config
from .dedup import assert_no_high_duplicate
from .errors import WikiError
from .ingest import ensure_hubs
from .naming import (
    CHART_TYPE_SUGGESTIONS,
    naming_audit_for_page,
    title_hygiene_issues,
    validate_new_id,
)
from .pages import read_page, write_page
from .store import guarded, save


def _validate_analysis_method(wiki_root: Path, ref: str) -> str:
    target = resolve_page_ref(wiki_root, ref, expected_type="method")
    if target is None:
        raise WikiError(f"引用的分析方法不存在: {ref}")
    meta, _ = read_page(target)
    if meta.get("status") == "archived":
        raise WikiError(f"引用的分析方法已归档: {target.stem}")
    if meta.get("method_kind") != "analysis":
        kind = meta.get("method_kind") or "未分类"
        raise WikiError(f"必须绑定 method_kind=analysis 的分析方法（当前为 {kind}）: {target.stem}")
    return target.stem


def method_map_errors(config: Config) -> list[str]:
    """Validate wiki/recipes/method-map.json references and schema consistency."""
    root = config.wiki_root
    map_path = root / "recipes" / "method-map.json"
    if not map_path.is_file():
        return []
    try:
        payload = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"recipes/method-map.json JSON 解析失败: {error}"]
    if not isinstance(payload, dict):
        return ["recipes/method-map.json 根对象必须为 JSON object"]

    errors: list[str] = []
    mappings = payload.get("mappings")
    unmapped = payload.get("unmapped")
    if not isinstance(mappings, dict):
        errors.append("recipes/method-map.json 缺少对象字段 mappings")
        mappings = {}
    if not isinstance(unmapped, list) or any(not isinstance(r, str) for r in unmapped):
        errors.append("recipes/method-map.json 缺少字符串列表 unmapped")
        unmapped = []

    unmapped_set = set(unmapped)
    for rid in sorted(unmapped_set):
        if resolve_page_ref(root, rid, expected_type="recipe") is None:
            errors.append(f"recipes/method-map.json.unmapped 配方不存在: {rid}")

    for rid, entry in sorted(mappings.items()):
        if not isinstance(rid, str) or not rid.strip():
            errors.append("recipes/method-map.json.mappings 存在空键")
            continue
        if resolve_page_ref(root, rid, expected_type="recipe") is None:
            errors.append(f"recipes/method-map.json.mappings 配方不存在: {rid}")
        if not isinstance(entry, dict):
            errors.append(f"recipes/method-map.json.mappings[{rid}] 必须为对象")
            continue
        methods = entry.get("methods")
        if not isinstance(methods, list) or any(not isinstance(m, str) or not m.strip() for m in methods):
            errors.append(f"recipes/method-map.json.mappings[{rid}].methods 必须为非空字符串列表（允许为空列表）")
            continue
        if methods and rid in unmapped_set:
            errors.append(f"recipes/method-map.json 中 {rid} 同时存在于已映射 mappings 与 unmapped")
        for mid in methods:
            target = resolve_page_ref(root, mid, expected_type="method")
            if target is None:
                errors.append(f"recipes/method-map.json[{rid}] 引用了不存在的方法: {mid}")
                continue
            try:
                meta, _ = read_page(target)
            except WikiError as error:
                errors.append(f"recipes/method-map.json[{rid}] 方法不可读 {mid}: {error}")
                continue
            if meta.get("status") == "archived":
                errors.append(f"recipes/method-map.json[{rid}] 引用了已归档方法: {mid}")
            elif meta.get("method_kind") != "analysis":
                errors.append(f"recipes/method-map.json[{rid}] 只能引用 analysis 方法（{mid} 为 {meta.get('method_kind')}）")
    return errors


def infer_primary_method_for_recipe(config: Config, recipe_id: str) -> str:
    """Return canonical primary method ID if recipe_id maps unambiguously to one analysis method."""
    map_path = config.wiki_root / "recipes" / "method-map.json"
    if not map_path.is_file():
        return ""
    try:
        payload = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    entry = (payload.get("mappings") or {}).get(recipe_id)
    if not isinstance(entry, dict):
        return ""
    methods = [m.strip() for m in (entry.get("methods") or []) if isinstance(m, str) and m.strip()]
    if len(methods) != 1:
        return ""
    try:
        return _validate_analysis_method(config.wiki_root, methods[0])
    except WikiError:
        return ""


def map_method(
    config: Config,
    *,
    template_id: str | None = None,
    recipe_id: str | None = None,
    primary_method: str | None = None,
    methods: list[str] | None = None,
    unmapped: bool = False,
    note: str = "",
    confidence: str = "curated",
) -> dict:
    """Bind a template's primary_method and/or update recipes/method-map.json in one validated save."""
    if not template_id and not recipe_id:
        raise WikiError("map-method 至少需指定 --template 或 --recipe")
    root = config.wiki_root
    updated: dict = {}

    if template_id:
        if not primary_method:
            raise WikiError("更新模板主方法归属时须指定 --primary-method")
        mid = _validate_analysis_method(root, primary_method)
        tpage = resolve_page_ref(root, template_id, expected_type="template")
        if tpage is None:
            raise WikiError(f"模板不存在: {template_id}")
        meta, body = read_page(tpage)
        meta["primary_method"] = mid
        write_page(tpage, meta, body)
        updated["template"] = {"id": meta.get("id") or tpage.stem, "primary_method": mid}

    if recipe_id:
        rpage = resolve_page_ref(root, recipe_id, expected_type="recipe")
        if rpage is None:
            raise WikiError(f"配方不存在: {recipe_id}")
        rid = rpage.stem
        map_path = root / "recipes" / "method-map.json"
        if map_path.is_file():
            payload = json.loads(map_path.read_text(encoding="utf-8"))
        else:
            payload = {"schema_version": 1, "unmapped": [], "mappings": {}}
        mappings = payload.setdefault("mappings", {})
        unmapped_list = payload.setdefault("unmapped", [])

        if unmapped:
            mappings[rid] = {
                "methods": [],
                "confidence": confidence,
                "note": note or "人工标定为纯工具/未映射条目。",
            }
            if rid not in unmapped_list:
                unmapped_list.append(rid)
            updated["recipe"] = {"id": rid, "methods": [], "unmapped": True}
        else:
            raw_list = methods or ([primary_method] if primary_method else [])
            if not raw_list:
                raise WikiError("映射配方时须指定 --methods 或 --unmapped")
            resolved_methods = list(dict.fromkeys(_validate_analysis_method(root, m) for m in raw_list))
            mappings[rid] = {
                "methods": resolved_methods,
                "confidence": confidence,
                "note": note or (mappings.get(rid, {}).get("note") if isinstance(mappings.get(rid), dict) else "") or "方法域人工核定挂载。",
            }
            payload["unmapped"] = [r for r in unmapped_list if r != rid]
            updated["recipe"] = {"id": rid, "methods": resolved_methods, "unmapped": False}

        payload["unmapped"] = sorted(set(payload["unmapped"]))
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    label = template_id or recipe_id
    save(config, f"map method for {label}")
    return updated


def scaffold_native_template(
    config: Config,
    template_id: str,
    *,
    chart_type: str,
    title: str,
    primary_method: str,
    language: str = "r",
    sources: list[str] | None = None,
    tags: list[str] | None = None,
    keywords: list[str] | None = None,
    interfaces: list[str] | None = None,
    summary: str = "",
    dedup_note: str = "",
    force: bool = False,
) -> str:
    """Create a strict-named standalone native L2 template bound directly to an analysis method."""
    id_issues = validate_new_id("template", template_id)
    if id_issues:
        raise WikiError("；".join(id_issues))
    title_issues = title_hygiene_issues(title, entry_id=template_id, chart_types=[chart_type], strict_content_name=False)
    if title_issues:
        raise WikiError("；".join(title_issues))
    if language not in ("r", "python"):
        raise WikiError("language 只能是 python 或 r")

    root = config.wiki_root
    mid = _validate_analysis_method(root, primary_method)
    src_list = [s.strip() for s in (sources or []) if isinstance(s, str) and s.strip()]
    if not src_list:
        src_list = [f"methods/{mid}"]
    for src in src_list:
        raw = src.removesuffix(".md")
        if resolve_page_ref(root, raw) is None and not (root / f"{raw}.md").is_file():
            raise WikiError(f"引用的来源页不存在: {src}")

    target = root / "templates" / template_id
    page = target.with_suffix(".md")
    if target.exists() or page.exists():
        raise WikiError(f"模板页或目录已存在: {template_id}")

    exclude = {src.split("/", 1)[1].removesuffix(".md") for src in src_list if src.startswith("recipes/")}
    assert_no_high_duplicate(
        config,
        kind="template",
        entry_id=template_id,
        title=title,
        primary_method=mid,
        chart_types=[chart_type],
        interfaces=interfaces,
        summary=summary,
        keywords=keywords,
        exclude_ids=exclude,
        dedup_note=dedup_note,
        force=force,
    )

    (target / "code").mkdir(parents=True)
    (target / "example").mkdir()
    entry = "code/render.py" if language == "python" else "code/render.R"
    spec: dict = {"entry": entry, "language": language, "tables": {}, "style": {}}
    if language == "python":
        (target / "code/__init__.py").write_text("", encoding="utf-8")
        if config.function_defaults:
            spec["style"] = deepcopy(config.function_defaults)
        spec["panel"] = "code/panel.py"
        (target / "code/panel.py").write_text(
            "def draw(fig, rect, tables, style):\n    raise NotImplementedError('请实现 draw(fig, rect, tables, style)')\n",
            encoding="utf-8",
        )
        (target / entry).write_text("raise SystemExit('请实现独立渲染入口')\n", encoding="utf-8")
    else:
        (target / entry).write_text("# 原生模板入口：请读取 example/ 并在测试后 verify-template\nstop('尚未实现渲染代码')\n", encoding="utf-8", newline="\n")
    (target / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    today = datetime.now(timezone.utc).date().isoformat()
    relation_note = f"{today}：新建模板主归属方法 [[methods/{mid}]]。"
    if dedup_note.strip():
        relation_note += f"查重说明：{dedup_note.strip()}"
    if chart_type in CHART_TYPE_SUGGESTIONS:
        relation_note += f" 图型提示：建议使用规范图型 {CHART_TYPE_SUGGESTIONS[chart_type]}。"

    meta = {
        "type": "template",
        "id": template_id,
        "title": title.strip(),
        "status": "draft",
        "layouts": [],
        "sources": src_list,
        "panels": [],
        "language": language,
        "primary_method": mid,
        "tags": tags or [],
        "chart_types": [chart_type],
        "keywords": keywords or [],
        "favorite": False,
    }
    body = (
        f"# {meta['title']}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        "## 适用\n\n## 不适用\n\n"
        f"## 知识关联检查\n\n{relation_note}\n\n"
        "## 数据要求\n\n待填写 spec.json。\n\n"
        "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n"
    )
    ensure_hubs(config, meta)
    with guarded(config, page):
        write_page(page, meta, body)
        save(config, f"scaffold native template {template_id}")
    return template_id


def curate_audit(config: Config) -> dict:
    """Audit method-domain completeness, mapping health, duplicate clusters, and naming hygiene."""
    from .method_hub import list_method_hubs

    root = config.wiki_root
    hubs_payload = list_method_hubs(config)
    map_errs = method_map_errors(config)

    methods_without_viz = []
    for m in hubs_payload.get("methods", []):
        viz = m.get("attached_visualizations") or {}
        total_viz = sum(len(viz.get(k) or []) for k in ("curated", "object_compatible", "render_bridged"))
        if total_viz == 0:
            methods_without_viz.append({"id": m["id"], "title": m["title"], "purposes": m.get("purposes", [])})

    map_path = root / "recipes" / "method-map.json"
    mmap: dict = {}
    if map_path.is_file():
        try:
            mmap = json.loads(map_path.read_text(encoding="utf-8")).get("mappings") or {}
        except (OSError, ValueError):
            mmap = {}

    templates_missing_pm: list[dict] = []
    naming_issues: list[dict] = []
    clusters: dict[tuple[str, str], list[dict]] = {}

    for folder in ("templates", "methods", "interfaces"):
        directory = root / folder
        if not directory.is_dir():
            continue
        for page in sorted(directory.glob("*.md")):
            try:
                meta, _ = read_page(page)
            except WikiError:
                continue
            if meta.get("status") == "archived":
                continue
            pid = str(meta.get("id") or meta.get("slug") or page.stem)
            issues = naming_audit_for_page(meta)
            if issues:
                naming_issues.append({"page": f"{folder}/{page.name}", "id": pid, "issues": issues})
            if folder == "templates":
                pm = str(meta.get("primary_method") or "").strip()
                if not pm:
                    suggested: list[str] = []
                    for src in meta.get("sources") or []:
                        if isinstance(src, str) and src.startswith("recipes/"):
                            rid = src.split("/", 1)[1].removesuffix(".md")
                            suggested.extend((mmap.get(rid) or {}).get("methods") or [])
                    templates_missing_pm.append({
                        "id": pid,
                        "title": meta.get("title", pid),
                        "status": meta.get("status"),
                        "suggested_methods": sorted(set(suggested)),
                    })
                else:
                    for ct in meta.get("chart_types") or []:
                        clusters.setdefault((pm, ct), []).append({"id": pid, "title": meta.get("title", pid)})

    duplicate_clusters = [
        {"primary_method": pm, "chart_type": ct, "templates": items}
        for (pm, ct), items in sorted(clusters.items())
        if len(items) >= 2
    ]

    return {
        "methods_total": hubs_payload.get("total", 0),
        "method_map_errors": map_errs,
        "unmapped_recipes_count": hubs_payload.get("unmapped_recipes_count", 0),
        "unmapped_recipes": hubs_payload.get("unmapped_recipes", []),
        "templates_missing_primary_method": templates_missing_pm,
        "methods_without_viz": methods_without_viz,
        "duplicate_clusters_count": len(duplicate_clusters),
        "duplicate_clusters": duplicate_clusters,
        "naming_hygiene_count": len(naming_issues),
        "naming_hygiene_issues": naming_issues,
    }

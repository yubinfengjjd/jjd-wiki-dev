"""Load, validate, and summarize per-workflow panel coverage manifests (`panel-manifest.yaml`)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .aliases import resolve_page_ref
from .confine import confined
from .config import Config
from .errors import WikiError
from .pages import read_page

MANIFEST_FILENAME = "panel-manifest.yaml"
EXCLUDED_EVIDENCE_TIERS = frozenset({
    "excluded_wet_lab",
    "excluded_schematic",
    "excluded_imaging",
})
VALID_EVIDENCE_TIERS = frozenset({"original_table", "local_recompute", "proxy"}) | EXCLUDED_EVIDENCE_TIERS
EVIDENCE_TIERS = VALID_EVIDENCE_TIERS
VALID_TEMPLATE_DISPOSITIONS = frozenset({"paper_variant", "reuse_identical", "paper_specific_only"})


def manifest_path_for(config: Config, method_path: Path | str) -> Path:
    """Resolve the optional `panel-manifest.yaml` path for a workflow method page or ID."""
    if isinstance(method_path, Path):
        p = method_path if method_path.is_absolute() else (config.wiki_root / method_path)
    else:
        text = str(method_path).strip()
        if "/" in text or "\\" in text or text.endswith(".md"):
            p = config.wiki_root / text
        else:
            p = config.wiki_root / "methods" / text
    asset_dir = p.with_suffix("") if p.suffix == ".md" else p
    return asset_dir / MANIFEST_FILENAME


def _validate_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_safe_relative_path(value: str) -> bool:
    if not value or value.startswith("/") or "\\" in value or ":" in value:
        return False
    if any(ord(ch) < 32 for ch in value):
        return False
    parts = value.split("/")
    return all(part not in ("", ".", "..") and part == part.rstrip(" .") for part in parts)


def normalize_figure_slug(label: str) -> str:
    """Map human figure labels like 'Fig. 1' / 'Supp. Fig. 3' to canonical slugs ('fig01', 'sfig03')."""
    text = (label or "").strip()
    m_supp = re.match(r"^(?:Supp(?:lementary)?\.?\s*Fig(?:ure)?\.?|SFig)\s*S?(\d+)\b", text, re.I)
    if m_supp:
        return f"sfig{int(m_supp.group(1)):02d}"
    m_main = re.match(r"^(?:Main\s+)?Fig(?:ure)?\.?\s*(\d+)\b", text, re.I)
    if m_main:
        return f"fig{int(m_main.group(1)):02d}"
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_panel_manifest(path: Path) -> dict[str, Any]:
    """Load and structurally parse `panel-manifest.yaml`, raising `WikiError` if malformed."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise WikiError(f"panel-manifest.yaml 读取失败: {exc}") from exc
    if not isinstance(data, dict):
        raise WikiError("panel-manifest.yaml 根节点必须为映射对象")
    panels = data.get("panels")
    if not isinstance(panels, list):
        raise WikiError("panel-manifest.yaml 的 panels 必须为列表")
    return data


def panel_manifest_errors(config: Config, method_path: Path | str) -> list[str]:
    """Return validation error messages for a method's `panel-manifest.yaml` (if present)."""
    mpath = manifest_path_for(config, method_path)
    if not mpath.is_file():
        return []
    try:
        data = load_panel_manifest(mpath)
    except WikiError as exc:
        return [str(exc)]

    errors: list[str] = []
    raw_schema = data.get("schema_version")
    if "schema_version" in data:
        if isinstance(raw_schema, bool) or not isinstance(raw_schema, int) or raw_schema < 1:
            errors.append("panel-manifest.yaml 字段 schema_version 必须为大于等于 1 的整数")
    is_v2_plus = isinstance(raw_schema, int) and not isinstance(raw_schema, bool) and raw_schema >= 2
    asset_dir = mpath.parent

    for field in ("doi", "paper_id", "license"):
        if field in data and data[field] is not None and not _validate_nonempty_str(data[field]):
            errors.append(f"panel-manifest.yaml 字段 {field} 必须为非空字符串")

    seen_panels: set[tuple[str, str]] = set()
    seen_panel_keys: set[str] = set()
    for idx, item in enumerate(data["panels"]):
        if not isinstance(item, dict):
            errors.append(f"panel-manifest.yaml panels[{idx}] 必须为对象")
            continue

        panel_key = item.get("panel_key")
        has_panel_key = "panel_key" in item and panel_key is not None
        if "panel_key" in item and panel_key is not None:
            if not _validate_nonempty_str(panel_key):
                errors.append(f"panel-manifest.yaml panels[{idx}].panel_key 必须为非空字符串")
            else:
                pk_norm = panel_key.strip()
                if pk_norm in seen_panel_keys:
                    errors.append(f"panel-manifest.yaml panels[{idx}] 存在重复 panel_key: {pk_norm}")
                seen_panel_keys.add(pk_norm)

        fig_val = item.get("figure")
        pan_val = item.get("panel")
        if not has_panel_key:
            for req in ("figure", "panel"):
                if not _validate_nonempty_str(item.get(req)):
                    errors.append(f"panel-manifest.yaml panels[{idx}].{req} 必须为非空字符串")
        else:
            if "figure" in item and item.get("figure") is not None and not _validate_nonempty_str(fig_val):
                errors.append(f"panel-manifest.yaml panels[{idx}].figure 必须为非空字符串")
            if "panel" in item and item.get("panel") is not None and not _validate_nonempty_str(pan_val):
                errors.append(f"panel-manifest.yaml panels[{idx}].panel 必须为非空字符串")

        if _validate_nonempty_str(fig_val) and _validate_nonempty_str(pan_val):
            key = (fig_val.strip(), pan_val.strip())
            if key in seen_panels:
                errors.append(f"panel-manifest.yaml panels[{idx}] 存在重复面板条目: {key[0]} {key[1]}")
            seen_panels.add(key)

        for opt_str in ("figure_slug", "panel_letter"):
            if opt_str in item and item[opt_str] is not None and not _validate_nonempty_str(item[opt_str]):
                errors.append(f"panel-manifest.yaml panels[{idx}].{opt_str} 必须为非空字符串")

        if "description" in item and item["description"] is not None and not isinstance(item["description"], str):
            errors.append(f"panel-manifest.yaml panels[{idx}].description 必须为字符串")

        if "input_tables" in item and item["input_tables"] is not None:
            itables = item["input_tables"]
            if not isinstance(itables, list) or any(not _validate_nonempty_str(t) for t in itables):
                errors.append(f"panel-manifest.yaml panels[{idx}].input_tables 必须为非空字符串列表")

        tier = item.get("evidence_tier")
        is_valid_tier = isinstance(tier, str) and tier in VALID_EVIDENCE_TIERS
        if not is_valid_tier:
            errors.append(
                f"panel-manifest.yaml panels[{idx}].evidence_tier 非法: {tier!r}"
                f"（必须为 {', '.join(sorted(VALID_EVIDENCE_TIERS))}）"
            )

        is_excluded = isinstance(tier, str) and tier in EXCLUDED_EVIDENCE_TIERS

        script_path = item.get("script_path")
        if script_path is not None:
            if not _validate_nonempty_str(script_path) or not _is_safe_relative_path(script_path.strip()):
                errors.append(f"panel-manifest.yaml panels[{idx}].script_path 必须为安全的相对路径")

        if not is_excluded:
            tid = item.get("template_id")
            resolved_tpl: Path | None = None
            if tid is not None:
                if not _validate_nonempty_str(tid):
                    errors.append(f"panel-manifest.yaml panels[{idx}].template_id 必须为非空字符串")
                else:
                    resolved_tpl = resolve_page_ref(config.wiki_root, tid.strip(), expected_type="template")
                    if resolved_tpl is None:
                        errors.append(
                            f"panel-manifest.yaml panels[{idx}].template_id 引用的模板不存在: {tid}"
                        )
            extra = item.get("extra_templates")
            if extra is not None:
                if not isinstance(extra, list) or any(not _validate_nonempty_str(x) for x in extra):
                    errors.append(f"panel-manifest.yaml panels[{idx}].extra_templates 必须为非空字符串列表")
                else:
                    for etid in extra:
                        if resolve_page_ref(config.wiki_root, etid.strip(), expected_type="template") is None:
                            errors.append(
                                f"panel-manifest.yaml panels[{idx}].extra_templates 引用的模板不存在: {etid}"
                            )

            if is_v2_plus:
                if script_path is None:
                    errors.append(
                        f"panel-manifest.yaml panels[{idx}].script_path 缺失"
                        "（schema_version >= 2 的计算面板必须声明并存在实体脚本）"
                    )
                elif _validate_nonempty_str(script_path) and _is_safe_relative_path(script_path.strip()):
                    script_candidate = asset_dir / script_path.strip()
                    if not confined(script_candidate, asset_dir, config.wiki_root) or not script_candidate.is_file():
                        errors.append(
                            f"panel-manifest.yaml panels[{idx}].script_path 指向的脚本文件不存在或越界: {script_path.strip()}"
                        )

                disp = item.get("template_disposition")
                if not isinstance(disp, str) or disp not in VALID_TEMPLATE_DISPOSITIONS:
                    errors.append(
                        f"panel-manifest.yaml panels[{idx}].template_disposition 缺失或非法: {disp!r}"
                        f"（必须为 {', '.join(sorted(VALID_TEMPLATE_DISPOSITIONS))}）"
                    )
                elif disp == "paper_variant":
                    if tid is None:
                        errors.append(
                            f"panel-manifest.yaml panels[{idx}] template_disposition=paper_variant 时必须声明非空 template_id"
                        )
                    elif resolved_tpl is not None:
                        try:
                            tpl_meta, _ = read_page(resolved_tpl)
                        except WikiError as exc:
                            errors.append(
                                f"panel-manifest.yaml panels[{idx}].template_id 引用的模板不可读: {tid} ({exc})"
                            )
                        else:
                            if tpl_meta.get("status") != "ready":
                                errors.append(
                                    f"panel-manifest.yaml panels[{idx}].template_id ({tid}) 在 paper_variant 下 status 必须为 ready"
                                    f"（当前为 {tpl_meta.get('status')!r}）"
                                )
                            if not _validate_nonempty_str(tpl_meta.get("primary_method")):
                                errors.append(
                                    f"panel-manifest.yaml panels[{idx}].template_id ({tid}) 在 paper_variant 下必须声明非空 primary_method"
                                )
                            if tpl_meta.get("style_tier") not in ("default", "variant"):
                                errors.append(
                                    f"panel-manifest.yaml panels[{idx}].template_id ({tid}) 在 paper_variant 下 style_tier 必须为 default 或 variant"
                                    f"（当前为 {tpl_meta.get('style_tier')!r}）"
                                )
                            if not _validate_nonempty_str(tpl_meta.get("journal_style")):
                                errors.append(
                                    f"panel-manifest.yaml panels[{idx}].template_id ({tid}) 在 paper_variant 下必须声明非空 journal_style"
                                )
                elif disp == "reuse_identical":
                    if tid is None:
                        errors.append(
                            f"panel-manifest.yaml panels[{idx}] template_disposition=reuse_identical 时必须声明非空 template_id"
                        )
                    elif resolved_tpl is not None:
                        try:
                            tpl_meta, _ = read_page(resolved_tpl)
                        except WikiError as exc:
                            errors.append(
                                f"panel-manifest.yaml panels[{idx}].template_id 引用的模板不可读: {tid} ({exc})"
                            )
                        else:
                            if tpl_meta.get("status") == "archived":
                                errors.append(
                                    f"panel-manifest.yaml panels[{idx}].template_id ({tid}) 在 reuse_identical 下不得引用已归档（archived）模板"
                                )
                    if not _validate_nonempty_str(item.get("disposition_note")):
                        errors.append(
                            f"panel-manifest.yaml panels[{idx}] template_disposition=reuse_identical 时必须声明非空字符串 disposition_note"
                        )
                elif disp == "paper_specific_only":
                    if tid is not None:
                        errors.append(
                            f"panel-manifest.yaml panels[{idx}] template_disposition=paper_specific_only 时 template_id 必须为 None"
                        )
                    if not _validate_nonempty_str(item.get("disposition_note")):
                        errors.append(
                            f"panel-manifest.yaml panels[{idx}] template_disposition=paper_specific_only 时必须声明非空字符串 disposition_note"
                        )

        if "methods" in item and item["methods"] is not None:
            methods = item["methods"]
            if not isinstance(methods, list) or any(not _validate_nonempty_str(m) for m in methods):
                errors.append(f"panel-manifest.yaml panels[{idx}].methods 必须为非空字符串列表")
            else:
                for mid in methods:
                    if resolve_page_ref(config.wiki_root, mid.strip(), expected_type="method") is None:
                        errors.append(
                            f"panel-manifest.yaml panels[{idx}].methods 引用的方法不存在: {mid}"
                        )

    return errors


def summarize_panel_manifest(data: dict[str, Any]) -> dict[str, int]:
    """Compute figure, panel-entry, tier, and unique template coverage counts."""
    panels = [p for p in (data.get("panels") or []) if isinstance(p, dict)]
    figures: set[str] = set()
    for p in panels:
        if _validate_nonempty_str(p.get("figure")):
            figures.add(normalize_figure_slug(p["figure"]) or p["figure"].strip())
        elif _validate_nonempty_str(p.get("figure_slug")):
            figures.add(p["figure_slug"].strip())
        elif _validate_nonempty_str(p.get("panel_key")) and "/" in p["panel_key"]:
            figures.add(p["panel_key"].split("/", 1)[0].strip())

    counts = {tier: 0 for tier in VALID_EVIDENCE_TIERS}
    templates: set[str] = set()
    for p in panels:
        tier = p.get("evidence_tier")
        if isinstance(tier, str) and tier in counts:
            counts[tier] += 1
        if not (isinstance(tier, str) and tier in EXCLUDED_EVIDENCE_TIERS):
            tid = p.get("template_id")
            if _validate_nonempty_str(tid):
                templates.add(tid.strip())
            extra = p.get("extra_templates")
            if isinstance(extra, list):
                for etid in extra:
                    if _validate_nonempty_str(etid):
                        templates.add(etid.strip())
    excluded_total = (
        counts["excluded_wet_lab"]
        + counts["excluded_schematic"]
        + counts["excluded_imaging"]
    )
    return {
        "figures": len(figures),
        "panels": len(panels),
        "original_table": counts["original_table"],
        "local_recompute": counts["local_recompute"],
        "proxy": counts["proxy"],
        "excluded_wet_lab": counts["excluded_wet_lab"],
        "excluded_schematic": counts["excluded_schematic"],
        "excluded_imaging": counts["excluded_imaging"],
        "excluded_total": excluded_total,
        "computed": counts["original_table"] + counts["local_recompute"] + counts["proxy"],
        "templates": len(templates),
    }


def manifest_facts_lines(config: Config, method_path: Path | str) -> list[str]:
    """Return formatted facts bullet lines when `panel-manifest.yaml` exists and is readable."""
    mpath = manifest_path_for(config, method_path)
    if not mpath.is_file():
        return []
    try:
        data = load_panel_manifest(mpath)
    except WikiError:
        return []
    stats = summarize_panel_manifest(data)
    parts = [
        f"实测/补表 {stats['original_table']}",
        f"本地重算 {stats['local_recompute']}",
        f"代理 {stats['proxy']}",
        f"剔除湿实验 {stats['excluded_wet_lab']}",
    ]
    if stats["excluded_schematic"]:
        parts.append(f"剔除示意图 {stats['excluded_schematic']}")
    if stats["excluded_imaging"]:
        parts.append(f"剔除显微影像 {stats['excluded_imaging']}")
    return [
        f"- 面板覆盖清单：{stats['figures']} 张图 / {stats['panels']} 条面板条目"
        f"（{'、'.join(parts)}），引用 {stats['templates']} 套去重模板"
    ]

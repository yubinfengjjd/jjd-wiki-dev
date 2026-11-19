"""Load, validate, and summarize per-workflow panel coverage manifests (`panel-manifest.yaml`)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .aliases import resolve_page_ref
from .config import Config
from .errors import WikiError

MANIFEST_FILENAME = "panel-manifest.yaml"
EVIDENCE_TIERS = frozenset({"original_table", "local_recompute", "proxy", "excluded_wet_lab"})


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
    for field in ("doi", "paper_id", "license"):
        if field in data and data[field] is not None and not _validate_nonempty_str(data[field]):
            errors.append(f"panel-manifest.yaml 字段 {field} 必须为非空字符串")

    seen_panels: set[tuple[str, str]] = set()
    for idx, item in enumerate(data["panels"]):
        if not isinstance(item, dict):
            errors.append(f"panel-manifest.yaml panels[{idx}] 必须为对象")
            continue
        fig_val = item.get("figure")
        pan_val = item.get("panel")
        for req in ("figure", "panel"):
            if not _validate_nonempty_str(item.get(req)):
                errors.append(f"panel-manifest.yaml panels[{idx}].{req} 必须为非空字符串")
        if _validate_nonempty_str(fig_val) and _validate_nonempty_str(pan_val):
            key = (fig_val.strip(), pan_val.strip())
            if key in seen_panels:
                errors.append(f"panel-manifest.yaml panels[{idx}] 存在重复面板条目: {key[0]} {key[1]}")
            seen_panels.add(key)

        tier = item.get("evidence_tier")
        is_valid_tier = isinstance(tier, str) and tier in EVIDENCE_TIERS
        if not is_valid_tier:
            errors.append(
                f"panel-manifest.yaml panels[{idx}].evidence_tier 非法: {tier!r}"
                f"（必须为 {', '.join(sorted(EVIDENCE_TIERS))}）"
            )

        if tier != "excluded_wet_lab":
            tid = item.get("template_id")
            if tid is not None:
                if not _validate_nonempty_str(tid):
                    errors.append(f"panel-manifest.yaml panels[{idx}].template_id 必须为非空字符串")
                elif resolve_page_ref(config.wiki_root, tid.strip(), expected_type="template") is None:
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
    figures = {p["figure"].strip() for p in panels if _validate_nonempty_str(p.get("figure"))}
    counts = {tier: 0 for tier in EVIDENCE_TIERS}
    templates: set[str] = set()
    for p in panels:
        tier = p.get("evidence_tier")
        if isinstance(tier, str) and tier in counts:
            counts[tier] += 1
        if tier != "excluded_wet_lab":
            tid = p.get("template_id")
            if _validate_nonempty_str(tid):
                templates.add(tid.strip())
            extra = p.get("extra_templates")
            if isinstance(extra, list):
                for etid in extra:
                    if _validate_nonempty_str(etid):
                        templates.add(etid.strip())
    return {
        "figures": len(figures),
        "panels": len(panels),
        "original_table": counts["original_table"],
        "local_recompute": counts["local_recompute"],
        "proxy": counts["proxy"],
        "excluded_wet_lab": counts["excluded_wet_lab"],
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
    return [
        f"- 面板覆盖清单：{stats['figures']} 张图 / {stats['panels']} 条面板条目"
        f"（实测/补表 {stats['original_table']}、本地重算 {stats['local_recompute']}、"
        f"代理 {stats['proxy']}、剔除湿实验 {stats['excluded_wet_lab']}），"
        f"引用 {stats['templates']} 套去重模板"
    ]

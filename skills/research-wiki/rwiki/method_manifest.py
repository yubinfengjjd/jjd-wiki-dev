"""Load and validate per-workflow computational method intake manifests (`method-manifest.yaml`)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .aliases import resolve_page_ref
from .confine import confined
from .config import Config
from .errors import WikiError
from .method_implementations import implementation_status
from .pages import read_page
from .panel_manifest import MANIFEST_FILENAME as PANEL_MANIFEST_FILENAME

METHOD_MANIFEST_FILENAME = "method-manifest.yaml"
VALID_METHOD_DISPOSITIONS = frozenset({"method_impl", "reuse_impl", "paper_specific_only"})
_SAFE_STEP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def method_manifest_path_for(config: Config, method_path: Path | str) -> Path:
    """Resolve the `method-manifest.yaml` path for a workflow method page or ID."""
    if isinstance(method_path, Path):
        p = method_path if method_path.is_absolute() else (config.wiki_root / method_path)
    else:
        text = str(method_path).strip()
        if "/" in text or "\\" in text or text.endswith(".md"):
            p = config.wiki_root / text
        else:
            p = config.wiki_root / "methods" / text
    asset_dir = p.with_suffix("") if p.suffix == ".md" else p
    return asset_dir / METHOD_MANIFEST_FILENAME


def _validate_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_safe_relative_path(value: str) -> bool:
    if not value or value.startswith("/") or "\\" in value or ":" in value:
        return False
    if any(ord(ch) < 32 for ch in value):
        return False
    parts = value.split("/")
    return all(part not in ("", ".", "..") and part == part.rstrip(" .") for part in parts)


def _panel_manifest_requires_method_manifest(asset_dir: Path) -> bool:
    panel_path = asset_dir / PANEL_MANIFEST_FILENAME
    if not panel_path.is_file():
        return False
    try:
        data = yaml.safe_load(panel_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return False
    if not isinstance(data, dict):
        return False
    raw_schema = data.get("schema_version")
    return isinstance(raw_schema, int) and not isinstance(raw_schema, bool) and raw_schema >= 2


def load_method_manifest(path: Path) -> dict[str, Any]:
    """Load and structurally parse `method-manifest.yaml`, raising `WikiError` if malformed."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise WikiError(f"method-manifest.yaml 读取失败: {exc}") from exc
    if not isinstance(data, dict):
        raise WikiError("method-manifest.yaml 根节点必须为映射对象")
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise WikiError("method-manifest.yaml 的 steps 必须为列表")
    return data


def _resolve_verified_impl(
    config: Config,
    method_id: str,
    impl_id: str,
    prefix: str,
    *,
    require_slot_fields: bool,
) -> list[str]:
    errors: list[str] = []
    target = resolve_page_ref(config.wiki_root, method_id, expected_type="method")
    if target is None:
        return [f"{prefix}.method_id 引用的方法页不存在: {method_id}"]
    try:
        method_meta, _ = read_page(target)
    except WikiError as exc:
        return [f"{prefix}.method_id 引用的方法页不可读: {method_id} ({exc})"]
    if method_meta.get("type") != "method":
        return [f"{prefix}.method_id 必须指向 method 页: {method_id}"]
    if method_meta.get("status") == "archived":
        return [f"{prefix}.method_id 引用的方法页已归档: {method_id}"]
    if method_meta.get("method_kind") != "analysis":
        kind = method_meta.get("method_kind") or "未分类"
        return [f"{prefix}.method_id 必须指向 method_kind=analysis 的方法页（当前为 {kind}）: {method_id}"]

    implementations = method_meta.get("implementations")
    if not isinstance(implementations, list):
        return [f"{prefix}.implementation_id ({impl_id}) 在方法 {method_id} 中不存在（未声明 implementations）"]
    matched = next(
        (item for item in implementations if isinstance(item, dict) and item.get("id") == impl_id),
        None,
    )
    if matched is None:
        return [f"{prefix}.implementation_id ({impl_id}) 在方法 {method_id} 的 implementations 中不存在"]

    if require_slot_fields:
        if matched.get("impl_tier") not in ("default", "variant"):
            errors.append(
                f"{prefix}.implementation_id ({method_id}/{impl_id}) 在 method_impl 下 impl_tier 必须为 default 或 variant"
                f"（当前为 {matched.get('impl_tier')!r}）"
            )
        if not _validate_nonempty_str(matched.get("modality")):
            errors.append(
                f"{prefix}.implementation_id ({method_id}/{impl_id}) 在 method_impl 下必须声明非空 modality"
            )

    statuses = implementation_status(target, method_meta)
    status_item = next((st for st in statuses if st.get("id") == impl_id), None)
    actual_state = status_item.get("state") if isinstance(status_item, dict) else "not_run"
    if actual_state != "verified":
        errors.append(
            f"{prefix}.implementation_id ({method_id}/{impl_id}) 实测验证状态必须为 verified"
            f"（当前为 {actual_state!r}，请运行 rwiki verify-method {target.stem} --impl {impl_id}）"
        )
    return errors


def method_manifest_errors(config: Config, method_path: Path | str) -> list[str]:
    """Return validation error messages for a workflow's `method-manifest.yaml`."""
    mpath = method_manifest_path_for(config, method_path)
    asset_dir = mpath.parent
    if not mpath.is_file():
        if _panel_manifest_requires_method_manifest(asset_dir):
            return [
                f"panel-manifest.yaml 为 schema_version >= 2，必须同时提供 {METHOD_MANIFEST_FILENAME}"
                "（逐计算步骤声明方法入库处置 method_disposition）"
            ]
        return []

    try:
        data = load_method_manifest(mpath)
    except WikiError as exc:
        return [str(exc)]

    errors: list[str] = []
    raw_schema = data.get("schema_version")
    if not isinstance(raw_schema, int) or isinstance(raw_schema, bool) or raw_schema < 1:
        errors.append("method-manifest.yaml 字段 schema_version 必须为大于等于 1 的整数")
    for field in ("paper_id", "workflow_id"):
        if not _validate_nonempty_str(data.get(field)):
            errors.append(f"method-manifest.yaml 字段 {field} 必须为非空字符串")
    wf_val = data.get("workflow_id")
    if _validate_nonempty_str(wf_val) and wf_val.strip() != asset_dir.name:
        errors.append(
            f"method-manifest.yaml 字段 workflow_id ({wf_val.strip()}) 与当前方法页 ID ({asset_dir.name}) 不一致"
        )
    if not data["steps"]:
        errors.append("method-manifest.yaml 的 steps 至少需包含 1 条计算步骤")

    seen_step_ids: set[str] = set()
    for idx, step in enumerate(data["steps"]):
        prefix = f"method-manifest.yaml steps[{idx}]"
        if not isinstance(step, dict):
            errors.append(f"{prefix} 必须为对象")
            continue

        step_id = step.get("step_id")
        if not _validate_nonempty_str(step_id) or not _SAFE_STEP_ID.fullmatch(step_id.strip()):
            errors.append(f"{prefix}.step_id 必须为非空安全标识（字母数字开头，仅含字母数字与 ._-）")
        else:
            sid = step_id.strip()
            if sid in seen_step_ids:
                errors.append(f"{prefix} 存在重复 step_id: {sid}")
            seen_step_ids.add(sid)

        if not _validate_nonempty_str(step.get("title")):
            errors.append(f"{prefix}.title 必须为非空字符串")

        script_path = step.get("script_path")
        if not _validate_nonempty_str(script_path) or not _is_safe_relative_path(script_path.strip()):
            errors.append(f"{prefix}.script_path 必须为安全的相对路径")
        else:
            candidate = asset_dir / script_path.strip()
            if not confined(candidate, asset_dir, config.wiki_root) or not candidate.is_file():
                errors.append(f"{prefix}.script_path 指向的脚本文件不存在或越界: {script_path.strip()}")

        disp = step.get("method_disposition")
        if not isinstance(disp, str) or disp not in VALID_METHOD_DISPOSITIONS:
            errors.append(
                f"{prefix}.method_disposition 缺失或非法: {disp!r}"
                f"（必须为 {', '.join(sorted(VALID_METHOD_DISPOSITIONS))}）"
            )
            continue

        mid = step.get("method_id")
        impl_id = step.get("implementation_id")

        if disp == "method_impl":
            if not _validate_nonempty_str(mid):
                errors.append(f"{prefix} method_disposition=method_impl 时必须声明非空 method_id")
            if not _validate_nonempty_str(impl_id):
                errors.append(f"{prefix} method_disposition=method_impl 时必须声明非空 implementation_id")
            if _validate_nonempty_str(mid) and _validate_nonempty_str(impl_id):
                errors.extend(
                    _resolve_verified_impl(
                        config,
                        mid.strip(),
                        impl_id.strip(),
                        prefix,
                        require_slot_fields=True,
                    )
                )
        elif disp == "reuse_impl":
            if not _validate_nonempty_str(mid):
                errors.append(f"{prefix} method_disposition=reuse_impl 时必须声明非空 method_id")
            if not _validate_nonempty_str(impl_id):
                errors.append(f"{prefix} method_disposition=reuse_impl 时必须声明非空 implementation_id")
            if not _validate_nonempty_str(step.get("disposition_note")):
                errors.append(f"{prefix} method_disposition=reuse_impl 时必须声明非空字符串 disposition_note")
            if _validate_nonempty_str(mid) and _validate_nonempty_str(impl_id):
                errors.extend(
                    _resolve_verified_impl(
                        config,
                        mid.strip(),
                        impl_id.strip(),
                        prefix,
                        require_slot_fields=False,
                    )
                )
        elif disp == "paper_specific_only":
            if mid is not None:
                errors.append(f"{prefix} method_disposition=paper_specific_only 时 method_id 必须为 None")
            if impl_id is not None:
                errors.append(f"{prefix} method_disposition=paper_specific_only 时 implementation_id 必须为 None")
            if not _validate_nonempty_str(step.get("disposition_note")):
                errors.append(f"{prefix} method_disposition=paper_specific_only 时必须声明非空字符串 disposition_note")

    return errors

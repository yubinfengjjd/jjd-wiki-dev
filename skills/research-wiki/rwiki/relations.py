"""Explicit, reviewed method-to-figure relationships.

Only method frontmatter is authoritative. Interface equality and shared labels
never create a semantic relationship. Reading this module does not run code.
"""

import re
from collections import Counter
from copy import deepcopy

from .errors import WikiError
from .pages import read_page
from .spec import load_spec
from .read_cache import remember

COMPATIBILITIES = ("direct", "adaptable", "candidate")
VERIFICATION_STATES = ("not_run", "example", "project")
COMPATIBILITY_LABELS = {"direct": "直接可接", "adaptable": "需要适配", "candidate": "待核实"}
_FIGURE = re.compile(r"(?:templates|layouts)/[A-Za-z0-9][A-Za-z0-9_-]*\Z")
_PAGE = re.compile(r"(?:methods|templates|layouts)/[A-Za-z0-9][A-Za-z0-9_-]*(?:\.md)?\Z")


def canonical_figure(value) -> str | None:
    """Accept a Wiki figure reference and normalize the optional .md suffix."""
    if not isinstance(value, str):
        return None
    canonical = value.removesuffix(".md")
    return canonical if _FIGURE.fullmatch(canonical) else None


def _strings(value, nonempty=False) -> bool:
    return (isinstance(value, list) and (bool(value) or not nonempty)
            and all(isinstance(item, str) and item.strip() for item in value))


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _target(config, figure: str):
    path = config.wiki_root / f"{figure}.md"
    # A relation is a Wiki reference, never permission to follow an external link.
    if not path.resolve().is_relative_to(config.wiki_root.resolve()):
        raise WikiError("关系目标越出 Wiki")
    meta, _ = read_page(path)
    expected = "template" if figure.startswith("templates/") else "layout"
    if meta.get("type") != expected or meta.get("id") != path.stem:
        raise WikiError("关系目标页面类型或 id 不一致")
    statuses = (("draft", "ready", "archived") if expected == "template" else
                ("pending_signoff", "pending_template", "ready", "archived"))
    if not _text(meta.get("title")) or meta.get("status") not in statuses:
        raise WikiError("关系目标缺少有效标题或页面状态")
    if expected == "layout" and (not isinstance(meta.get("panels"), (dict, list))
                                 or len(meta["panels"]) != 1):
        raise WikiError("关系目标必须为单 panel 来源图样")
    return path, meta


def _ready_covering_template(config, layout: dict, template_id: str) -> bool:
    """True when a ready template is the callable form of this source layout."""
    template_path = config.wiki_root / "templates" / f"{template_id}.md"
    try:
        template, _ = read_page(template_path)
    except (WikiError, OSError):
        return False
    if template.get("status") != "ready" or layout.get("id") not in template.get("layouts", []):
        return False
    if len(template.get("chart_types", [])) != 1:
        return False
    letters = layout.get("template_panels", {}).get(template_id, [])
    panels = layout.get("panels", {})
    return (isinstance(panels, dict) and bool(panels) and set(letters) == set(panels)
            and all(panels[letter] == template["chart_types"][0] for letter in panels))


def _record_errors(config, record: dict, method: dict | None = None) -> list[str]:
    errors = []
    figure = canonical_figure(record.get("figure"))
    if figure is None:
        errors.append("figure 必须为 templates/<id> 或 layouts/<id>（可带 .md 后缀）")
    compatibility = record.get("compatibility")
    if compatibility not in COMPATIBILITIES:
        errors.append("compatibility 必须为 direct、adaptable 或 candidate")
    if not _text(record.get("reason")):
        errors.append("reason 必须为非空依据说明")
    if not _strings(record.get("prerequisites")):
        errors.append("prerequisites 必须为非空字符串组成的列表（可为空列表）")
    if not isinstance(record.get("adaptation"), str):
        errors.append("adaptation 必须为字符串")
    elif compatibility == "adaptable" and not record["adaptation"].strip():
        errors.append("adaptable 关系必须说明 adaptation")
    if not _strings(record.get("evidence"), nonempty=True):
        errors.append("evidence 必须为非空证据位置字符串列表")
    verification = record.get("verification")
    if not isinstance(verification, dict):
        errors.append("verification 必须为 state、scope、evidence 对象")
    else:
        state = verification.get("state")
        if state not in VERIFICATION_STATES:
            errors.append("verification.state 必须为 not_run、example 或 project")
        if not _text(verification.get("scope")):
            errors.append("verification.scope 必须说明验证范围")
        if not _strings(verification.get("evidence"), nonempty=state in ("example", "project")):
            errors.append("verification.evidence 必须为字符串列表；已运行状态需非空证据")
    if figure is not None:
        try:
            path, target = _target(config, figure)
            if compatibility == "direct":
                if target["type"] != "template":
                    errors.append("direct 只能指向可调用模板；来源图样尚待模板化")
                else:
                    # Contract/assets can be checked without importing or running the entry.
                    assets = path.with_suffix("")
                    if (not assets.resolve().is_relative_to(config.wiki_root.resolve())
                            or not (assets / "spec.json").resolve().is_relative_to(assets.resolve())):
                        raise WikiError("direct 模板资产越出 Wiki 或专属资产目录")
                    spec = load_spec(assets)  # also confines spec.entry / spec.panel to the folder
                    if target.get("status") == "draft":
                        errors.append("direct 目标模板仍为 draft；作者确认可用前用 adaptable 或 candidate")
                    if method is not None:
                        required = {table["interface"] for table in spec["tables"].values()}
                        missing = sorted(required - set(method.get("outputs") or []))
                        if missing:
                            errors.append("direct 要求模板读取的接口均为方法声明输出；缺 "
                                          + "、".join(missing) + "，否则写 adaptable")
            if target["type"] == "layout":
                covering = [tid for tid in target.get("templates", [])
                            if _ready_covering_template(config, target, tid)]
                if covering:
                    errors.append(
                        "关系指向来源 layout，但已有 ready 覆盖模板；请改指模板，layout 放 evidence: "
                        + "、".join(covering))
        except (WikiError, OSError, ValueError, TypeError, KeyError) as error:
            errors.append(f"关系目标或可调用模板无效: {error}")
    return errors


def _checked(config, meta: dict):
    records = meta.get("figure_relations", [])
    if not isinstance(records, list):
        return [], ["figure_relations 必须为列表"]
    figures = Counter(canonical_figure(record.get("figure")) or record.get("figure") for record in records
                      if isinstance(record, dict) and isinstance(record.get("figure"), str))
    checked, diagnostics = [], []
    for index, record in enumerate(records):
        prefix = f"figure_relations[{index}]"
        if not isinstance(record, dict):
            diagnostics.append(f"{prefix} 必须为对象")
            continue
        errors = _record_errors(config, record, meta)
        figure = canonical_figure(record.get("figure")) or record.get("figure")
        if isinstance(figure, str) and figures[figure] > 1:
            errors.append(f"figure 重复: {figure}")
        diagnostics.extend(f"{prefix}: {error}" for error in errors)
        if not errors:
            checked.append({**record, "figure": figure})
    return checked, diagnostics


def relation_errors(config, meta: dict) -> list[str]:
    """Return actionable diagnostics, even for malformed YAML values."""
    return _checked(config, meta)[1]


def all_relations(config, include_archived: bool = True) -> list[dict]:
    return deepcopy(remember(('relations', config.wiki_root, include_archived),
                             lambda: _collect_relations(config, include_archived)))


def _collect_relations(config, include_archived: bool) -> list[dict]:
    """Resolve valid author/agent records once; both endpoints share this shape.

    Invalid records are reported by lint and omitted here, so a dangling or
    malformed direct declaration cannot become an executable recommendation.
    Page status and invocation verification remain independent dimensions.
    """
    from .curation import excluded_paths
    hidden = excluded_paths(config)
    results = []
    for path in sorted((config.wiki_root / "methods").glob("*.md")):
        if not path.resolve().is_relative_to(config.wiki_root.resolve()):
            continue
        try:
            method, _ = read_page(path)
        except (WikiError, OSError, ValueError):
            continue
        if (method.get("type") != "method" or method.get("id") != path.stem
                or not _text(method.get("title"))
                or method.get("status") not in ("draft", "ready", "archived")):
            continue
        records, _ = _checked(config, method)
        for record in records:
            figure = record["figure"]
            _, target = _target(config, figure)
            active = (method["status"] != "archived" and target["status"] != "archived"
                      and f"{figure}.md" not in hidden)
            if not active and not include_archived:
                continue
            results.append({
                "method": path.relative_to(config.wiki_root).as_posix(),
                "figure": f"{figure}.md", "method_title": method["title"],
                "figure_title": target["title"], "method_status": method["status"],
                "figure_status": target["status"], "compatibility": record["compatibility"],
                "reason": record["reason"], "prerequisites": list(record["prerequisites"]),
                "adaptation": record["adaptation"], "evidence": list(record["evidence"]),
                "verification": {"state": record["verification"]["state"],
                                 "scope": record["verification"]["scope"],
                                 "evidence": list(record["verification"]["evidence"])},
                "target_kind": target["type"], "active": active,
            })
    return results


def relations_for(config, path: str) -> list[dict]:
    """Forward or reverse lookup by root-relative canonical or .md page path."""
    if not isinstance(path, str) or not _PAGE.fullmatch(path):
        return []
    page = path if path.endswith(".md") else f"{path}.md"
    return [record for record in all_relations(config)
            if page in (record["method"], record["figure"])]

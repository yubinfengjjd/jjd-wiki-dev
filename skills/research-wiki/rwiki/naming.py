"""Controlled naming conventions and hygiene checks for new vs. legacy Wiki entries."""
from __future__ import annotations

import re

STRICT_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BANNED_TEMPLATE_ID_TOKENS = frozenset({
    "fy",
    "figureya",
    "tmp",
    "temp",
    "copy",
    "test",
    "draft",
    "update",
    "updated",
    "plus",
})
VERSION_SEGMENT_RE = re.compile(r"(?:^|-)v\d+(?:-|$)|[a-z]v\d+$")
TITLE_NOISE_RE = re.compile(
    r"(?:figureya|ks科研|公众号|wechat|单\s*panel\s*[:：]?|^draft\s*[:：]|(?:\b|_|\s)v\d+$|\bplus\b)",
    re.I,
)
MAX_TITLE_LENGTH = 36

# Canonical chart-type recommendations for near-duplicate slugs; does not block legacy pages.
CHART_TYPE_SUGGESTIONS: dict[str, str] = {
    "dot": "dotplot",
    "ring": "pie",
    "rose": "radial-bar",
    "deg-table": "table",
}


def validate_new_id(kind: str, entry_id: str) -> list[str]:
    """Validate strict canonical slug format for newly created template/method/interface IDs."""
    if not isinstance(entry_id, str) or not entry_id:
        return [f"{kind} id 不能为空"]
    issues: list[str] = []
    if "--" in entry_id:
        issues.append(f"新建 {kind} id 不允许使用双连字符 '--' 拼接: {entry_id}（请用语义短 slug，如 bulk-de-volcano）")
    elif not STRICT_SLUG_RE.fullmatch(entry_id):
        issues.append(f"新建 {kind} id 只允许小写字母、数字与单连字符 [a-z0-9-]: {entry_id}")
    if kind == "template":
        parts = [p for p in entry_id.split("-") if p]
        bad_tokens = [p for p in parts if p in BANNED_TEMPLATE_ID_TOKENS]
        if bad_tokens:
            issues.append(
                f"新建 template id 不得包含来源/版本/临时词 ({', '.join(bad_tokens)}): {entry_id}"
            )
        if VERSION_SEGMENT_RE.search(entry_id):
            issues.append(f"新建 template id 不得包含版本号后缀 (如 v2/v3): {entry_id}")
    return issues


def title_hygiene_issues(
    title: str,
    *,
    entry_id: str = "",
    chart_types: list[str] | None = None,
    strict_content_name: bool = False,
) -> list[str]:
    """Check title formatting and detect source/version/noise pollution.

    Hard creation checks pass strict_content_name=False to block explicit noise tokens
    (FigureYa/KS科研/单panel/v2/plus/overlong) without breaking minimal synthetic callers;
    advisory/audit callers set strict_content_name=True to also flag ASCII-only placeholder titles.
    """
    issues: list[str] = []
    clean = (title or "").strip()
    if not clean:
        return ["title 不能为空"]
    if len(clean) > MAX_TITLE_LENGTH:
        issues.append(f"title 过长（{len(clean)} 字 > {MAX_TITLE_LENGTH} 字），请精炼为内容名")
    match = TITLE_NOISE_RE.search(clean)
    if match:
        issues.append(f"title 不得包含来源/版本/推广噪声 ({match.group(0).strip()}): {clean}")
    if strict_content_name:
        lowered = clean.casefold()
        if entry_id and lowered == entry_id.casefold():
            issues.append(f"title 不应直接复用英文 id ({entry_id})，建议写简明中文内容名")
        elif chart_types and any(lowered == ct.casefold() for ct in chart_types if ct):
            issues.append(f"title 不应直接复用英文图型 ({clean})，建议写简明中文内容名")
    return issues


def chart_type_suggestions(chart_types: list[str] | None) -> list[str]:
    """Return advisory canonical chart_type suggestions for near-duplicate slugs."""
    hints: list[str] = []
    for ct in chart_types or []:
        replacement = CHART_TYPE_SUGGESTIONS.get(ct)
        if replacement:
            hints.append(f"图型 '{ct}' 建议统一使用规范词 '{replacement}'")
    return hints


def naming_audit_for_page(meta: dict) -> list[str]:
    """Non-blocking hygiene audit used by check-entry warnings and curate-audit."""
    ptype = meta.get("type")
    if ptype not in ("template", "method", "interface"):
        return []
    pid = str(meta.get("id") or meta.get("slug") or "")
    issues = list(validate_new_id(ptype, pid))
    issues.extend(
        title_hygiene_issues(
            str(meta.get("title") or ""),
            entry_id=pid,
            chart_types=meta.get("chart_types") if isinstance(meta.get("chart_types"), list) else None,
            strict_content_name=True,
        )
    )
    if ptype == "template":
        issues.extend(chart_type_suggestions(meta.get("chart_types")))
    return issues

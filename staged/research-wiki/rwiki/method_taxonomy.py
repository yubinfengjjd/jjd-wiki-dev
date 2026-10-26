"""One derivation of the research-domain -> analysis-purpose directory.

Categories only make existing analysis families discoverable. They are not a
scientific-suitability gate and never grant execution: implementation receipts
and the author's note status stay independent.
"""
from pathlib import Path

# Controlled vocabulary. Adding a purpose requires updating this list, the tests,
# the rules and the migration record together.
PURPOSES = (
    '预处理与质量控制',
    '降维与聚类',
    '整合与批次校正',
    '注释与参考映射',
    '差异与功能分析',
    '轨迹与动态分析',
    '模型评价',
    '模型解释',
)
_PURPOSE_SET = frozenset(PURPOSES)


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def purpose_errors(meta: dict) -> list[str]:
    """Illegal classification is an error; a missing purpose stays a readable legacy page."""
    if not isinstance(meta, dict) or meta.get('type') != 'method':
        return []
    if 'purposes' not in meta:
        return []
    if meta.get('method_kind') != 'analysis':
        return ['purposes 只适用于 method_kind=analysis']
    purposes = meta.get('purposes')
    if not isinstance(purposes, list) or any(not _text(value) for value in purposes):
        return ['purposes 必须为字符串列表']
    unknown = [value for value in purposes if value not in _PURPOSE_SET]
    if unknown:
        return ['purposes 含非法用途: ' + '、'.join(unknown)]
    if len(set(purposes)) != len(purposes):
        return ['purposes 不得重复']
    return []


def missing_purpose(meta: dict) -> bool:
    return (isinstance(meta, dict) and meta.get('type') == 'method'
            and meta.get('method_kind') == 'analysis'
            and meta.get('status') != 'archived'
            and not meta.get('purposes'))


def _analysis_pages(root: Path) -> list[tuple[Path, dict]]:
    from .catalog import readable_pages

    return [(path, meta) for path, meta in readable_pages(root)
            if meta.get('type') == 'method' and meta.get('method_kind') == 'analysis'
            and meta.get('status') != 'archived']


def _counted(values, vocabulary=None) -> list[dict]:
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    order = list(vocabulary) if vocabulary is not None else sorted(counts, key=lambda v: (-counts[v], v))
    return [{'value': value, 'count': counts[value]} for value in order if counts.get(value)]


def taxonomy(root: Path) -> dict:
    """Vocabulary and distinct-page counts derived from current pages; nothing is persisted."""
    pages = _analysis_pages(root)
    domains = {}
    purposes = []
    unclassified = []
    for path, meta in pages:
        tags = [tag for tag in meta.get('tags') or [] if _text(tag)]
        page_purposes = [value for value in meta.get('purposes') or [] if _text(value)]
        for tag in dict.fromkeys(tags):
            domains.setdefault(tag, []).append(page_purposes)
        purposes.extend(page_purposes)
        if not page_purposes:
            unclassified.append({'id': meta.get('id', path.stem), 'title': meta.get('title', path.stem),
                                 'path': path.relative_to(root).as_posix()})
    domain_items = []
    for value, members in domains.items():
        domain_purposes = [purpose for member in members for purpose in member]
        domain_items.append({'value': value, 'count': len(members),
                             'purposes': _counted(domain_purposes, PURPOSES)})
    domain_items.sort(key=lambda item: (-item['count'], item['value']))
    return {'total': len(pages), 'domains': domain_items,
            'purposes': _counted(purposes, PURPOSES), 'unclassified': unclassified}


def select_methods(root: Path, domain: str | None = None, purpose: str | None = None) -> list[str]:
    """Intersection filter for tests/CLI; the frontend applies the same rule to the API payload."""
    selected = []
    for path, meta in _analysis_pages(root):
        if domain and domain not in (meta.get('tags') or []):
            continue
        if purpose and purpose not in (meta.get('purposes') or []):
            continue
        selected.append(path.relative_to(root).as_posix())
    return selected

"""One derivation of the research-domain -> analysis-purpose directory.

Categories only make existing analysis families discoverable. They are not a
scientific-suitability gate and never grant execution: implementation receipts
and the author's note status stay independent.
"""
from pathlib import Path

DATA_DOMAINS = (
    ('single-cell', '单细胞转录组'),
    ('spatial-omics', '空间转录组'),
    ('bulk-transcriptomics', 'Bulk 转录组'),
    ('genomics-epigenomics', '基因组与表观遗传'),
    ('clinical-prognosis', '临床与预后建模'),
    ('multi-omics', '多组学整合与泛癌'),
    ('general-viz-stats', '通用绘图与统计'),
)
DOMAIN_LABELS = dict(DATA_DOMAINS)
_DATA_DOMAIN_SET = frozenset(DOMAIN_LABELS)
_DATA_DOMAIN_ALLOWED_TYPES = frozenset(('method', 'template', 'recipe', 'scenario'))

# Conservative legacy-tag fallback when explicit `data_domains` is absent.
# Ambiguous tags (`transcriptomics`, `machine-learning`, `model-explanation-shap`, `other`)
# are intentionally unmapped so legacy pages never receive fabricated domain claims.
_LEGACY_TAG_TO_DOMAIN = {
    'single-cell': 'single-cell',
    '单细胞分析': 'single-cell',
    'spatial-omics': 'spatial-omics',
    '空间转录组': 'spatial-omics',
    'bulk-transcriptomics': 'bulk-transcriptomics',
    'genomics-epigenomics': 'genomics-epigenomics',
    'clinical-prognosis': 'clinical-prognosis',
    'survival-analysis': 'clinical-prognosis',
    '生存分析': 'clinical-prognosis',
    'diagnostic-roc': 'clinical-prognosis',
    '诊断与预测评价': 'clinical-prognosis',
    'multi-omics': 'multi-omics',
    '多组学整合': 'multi-omics',
    '多组学整合与泛癌': 'multi-omics',
    'general-viz-stats': 'general-viz-stats',
    'experimental-statistics': 'general-viz-stats',
    '实验统计': 'general-viz-stats',
}

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
    '细胞通讯与微环境',
    '变异与表观调控',
    '生存与预后建模',
    '集合与通用统计',
)
_PURPOSE_SET = frozenset(PURPOSES)


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def data_domain_errors(meta: dict) -> list[str]:
    """Validate optional `data_domains` against the 7 canonical domain slugs."""
    if not isinstance(meta, dict) or 'data_domains' not in meta:
        return []
    if meta.get('type') not in _DATA_DOMAIN_ALLOWED_TYPES:
        return ['data_domains 只适用于 method、template、recipe 或 scenario']
    domains = meta.get('data_domains')
    if not isinstance(domains, list) or any(not _text(value) for value in domains):
        return ['data_domains 必须为字符串列表']
    unknown = [value for value in dict.fromkeys(domains) if value not in _DATA_DOMAIN_SET]
    if unknown:
        return ['data_domains 含非法数据域: ' + '、'.join(unknown)]
    if len(set(domains)) != len(domains):
        return ['data_domains 不得重复']
    return []


def domains_for(meta: dict) -> list[str]:
    """Return deduplicated canonical data_domains; prefer explicit field, else conservative tag fallback."""
    if not isinstance(meta, dict):
        return []
    explicit = meta.get('data_domains')
    if isinstance(explicit, list) and explicit:
        canonical = list(dict.fromkeys(
            value for value in explicit if isinstance(value, str) and value in _DATA_DOMAIN_SET
        ))
        if canonical:
            return canonical
    tags = meta.get('tags')
    if not isinstance(tags, list):
        return []
    mapped = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        domain = _LEGACY_TAG_TO_DOMAIN.get(tag.strip())
        if domain and domain not in mapped:
            mapped.append(domain)
    return mapped


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
    from .read_cache import cached_vault_value

    return cached_vault_value(root, "method_taxonomy", lambda: _build_taxonomy(root))


def _build_taxonomy(root: Path) -> dict:
    pages = _analysis_pages(root)
    domains = {}
    canonical_domains = {slug: [] for slug, _ in DATA_DOMAINS}
    purposes = []
    unclassified = []
    seen_pages = set()
    for path, meta in pages:
        rel_path = path.relative_to(root).as_posix()
        if rel_path in seen_pages:
            continue
        seen_pages.add(rel_path)
        tags = [tag for tag in meta.get('tags') or [] if _text(tag)]
        page_purposes = list(dict.fromkeys(value for value in meta.get('purposes') or [] if _text(value)))
        for tag in dict.fromkeys(tags):
            domains.setdefault(tag, []).append(page_purposes)
        for slug in domains_for(meta):
            canonical_domains[slug].append(page_purposes)
        purposes.extend(page_purposes)
        if not page_purposes:
            unclassified.append({'id': meta.get('id', path.stem), 'title': meta.get('title', path.stem),
                                 'path': rel_path})
    domain_items = []
    for value, members in domains.items():
        domain_purposes = [purpose for member in members for purpose in member]
        domain_items.append({'value': value, 'count': len(members),
                             'purposes': _counted(domain_purposes, PURPOSES)})
    domain_items.sort(key=lambda item: (-item['count'], item['value']))
    data_domain_items = []
    for slug, label in DATA_DOMAINS:
        members = canonical_domains[slug]
        domain_purposes = [purpose for member in members for purpose in member]
        data_domain_items.append({
            'value': slug,
            'label': label,
            'count': len(members),
            'purposes': _counted(domain_purposes, PURPOSES),
        })
    return {
        'total': len(seen_pages),
        'domains': domain_items,
        'data_domains': data_domain_items,
        'domain_labels': dict(DATA_DOMAINS),
        'purposes': _counted(purposes, PURPOSES),
        'unclassified': unclassified,
    }


def select_methods(root: Path, domain: str | None = None, purpose: str | None = None) -> list[str]:
    """Intersection filter for tests/CLI; the frontend applies the same rule to the API payload."""
    selected = []
    for path, meta in _analysis_pages(root):
        if domain:
            if domain in _DATA_DOMAIN_SET:
                if domain not in domains_for(meta):
                    continue
            elif domain not in (meta.get('tags') or []):
                continue
        if purpose and purpose not in (meta.get('purposes') or []):
            continue
        selected.append(path.relative_to(root).as_posix())
    return selected

"""Research-domain -> analysis-purpose navigation; counts are distinct pages, never category sums."""
import json
import shutil

import pytest
from fastapi.testclient import TestClient

from conftest import TAXONOMY_SOURCE, write_config, write_interface
from rwiki.lint import lint
from rwiki.method_taxonomy import (
    DATA_DOMAINS,
    DOMAIN_LABELS,
    PURPOSES,
    data_domain_errors,
    domains_for,
    purpose_errors,
    select_methods,
    taxonomy,
)
from rwiki.pages import write_page
from rwiki.server import create_app
from rwiki.store import init as init_wiki


@pytest.fixture
def taxonomy_env(tmp_path):
    from rwiki.config import load_config

    (tmp_path / 'gallery').mkdir()
    shutil.copyfile(TAXONOMY_SOURCE, tmp_path / 'taxonomy.yaml')
    config_path = write_config(tmp_path / 'config.json', tmp_path / 'wiki')
    config = load_config(config_path)
    init_wiki(config)
    return config, config_path


def analysis(config, mid, tags, purposes=None, kind='analysis', status='draft'):
    path = config.wiki_root / f'methods/{mid}.md'
    meta = {
        'type': 'method', 'id': mid, 'title': mid, 'status': status, 'tags': tags,
        'inputs': [], 'outputs': [], 'source': {'kind': 'written'},
        'license': 'none', 'cite': ['fixture'], 'favorite': False, 'method_kind': kind,
        'summary': f'{mid} answers one bounded question.',
        'data_contract': {'input': 'one row per sample', 'output': 'one estimate per group'},
    }
    if purposes is not None:
        meta['purposes'] = purposes
    write_page(path, meta, f'# {mid}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n'
                          '<!-- user:start -->\n<!-- user:end -->\n')
    return path


def test_counts_are_distinct_pages_not_overlapping_category_sums(taxonomy_env):
    config, _ = taxonomy_env
    analysis(config, 'two-domains', ['单细胞分析', '转录组'], ['降维与聚类'])
    analysis(config, 'shared-purpose', ['单细胞分析'], ['降维与聚类', '模型评价'])
    report = taxonomy(config.wiki_root)
    assert report['total'] == 2
    domains = {item['value']: item for item in report['domains']}
    assert domains['单细胞分析']['count'] == 2
    assert domains['转录组']['count'] == 1
    purposes = {item['value']: item for item in report['purposes']}
    assert purposes['降维与聚类']['count'] == 2
    assert purposes['模型评价']['count'] == 1
    # 2 + 1 + 1 + 1 overlapping memberships must not be reported as 2 methods.
    assert sum(item['count'] for item in report['domains']) > report['total']
    shared = next(item for item in domains['单细胞分析']['purposes'] if item['value'] == '降维与聚类')
    assert shared['count'] == 2


def test_domain_and_purpose_intersection_and_same_page_once(taxonomy_env):
    config, _ = taxonomy_env
    a = analysis(config, 'a', ['单细胞分析', '转录组'], ['降维与聚类'])
    b = analysis(config, 'b', ['单细胞分析'], ['模型评价'])
    c = analysis(config, 'c', ['转录组'], ['降维与聚类'])
    assert select_methods(config.wiki_root, domain='单细胞分析') == [
        'methods/a.md', 'methods/b.md']
    assert select_methods(config.wiki_root, domain='单细胞分析', purpose='降维与聚类') == [
        'methods/a.md']
    assert select_methods(config.wiki_root, purpose='降维与聚类') == [
        'methods/a.md', 'methods/c.md']
    # A page with two domain tags is returned once, never once per tag.
    assert select_methods(config.wiki_root, domain='转录组', purpose='降维与聚类') == [
        'methods/a.md', 'methods/c.md']
    assert a and b and c


def test_workflow_technical_archived_and_unclassified_are_not_analysis_cards(taxonomy_env):
    config, _ = taxonomy_env
    analysis(config, 'analysis', ['单细胞分析'], ['预处理与质量控制'])
    analysis(config, 'workflow', ['单细胞分析'], ['预处理与质量控制'], kind='workflow')
    analysis(config, 'technical', ['单细胞分析'], kind='technical')
    analysis(config, 'archived', ['单细胞分析'], ['预处理与质量控制'], status='archived')
    analysis(config, 'legacy', ['单细胞分析'])
    report = taxonomy(config.wiki_root)
    assert report['total'] == 2
    assert [item['id'] for item in report['unclassified']] == ['legacy']
    assert select_methods(config.wiki_root) == ['methods/analysis.md', 'methods/legacy.md']
    assert select_methods(config.wiki_root, domain='单细胞分析', purpose='预处理与质量控制') == [
        'methods/analysis.md']


def test_purpose_vocabulary_and_errors(taxonomy_env):
    config, _ = taxonomy_env
    page = analysis(config, 'bad', ['单细胞分析'], ['降维与聚类', '自己发明的用途'])
    from rwiki.pages import read_page
    meta, _ = read_page(page)
    errors = purpose_errors(meta)
    assert any('非法' in error and '自己发明的用途' in error for error in errors)
    meta['purposes'] = '降维与聚类'
    assert purpose_errors(meta)
    meta['purposes'] = ['降维与聚类']
    assert purpose_errors(meta) == []
    meta['method_kind'] = 'technical'
    assert any('analysis' in error for error in purpose_errors(meta))
    assert '预处理与质量控制' in PURPOSES and len(PURPOSES) == 12


def test_lint_warns_missing_purpose_but_rejects_invalid_one(taxonomy_env):
    from rwiki.lint import lint
    config, _ = taxonomy_env
    analysis(config, 'legacy', ['单细胞分析'])
    report = lint(config)
    assert any('WARN methods/legacy.md' in line and 'purposes' in line for line in report)
    assert not any('ERROR methods/legacy.md' in line for line in report)
    page = analysis(config, 'bad', ['单细胞分析'], ['不存在的用途'])
    report = lint(config)
    assert any('ERROR methods/bad.md' in line and '不存在' in line for line in report)
    assert page


def test_check_entry_prompts_missing_purpose_without_failing_or_changing_status(taxonomy_env):
    from conftest import complete_sections, run_cli
    config, config_path = taxonomy_env
    page = analysis(config, 'legacy', ['单细胞分析'])
    complete_sections(page)
    result = run_cli(config_path, 'check-entry', 'legacy')
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['passed'] is True
    assert any('purposes' in warning for warning in report['warnings'])
    from rwiki.pages import read_page
    assert read_page(page)[0]['status'] == 'draft'


def test_facts_show_purposes_for_analysis_only(taxonomy_env):
    from rwiki.facts import page_facts
    from rwiki.pages import read_page
    config, _ = taxonomy_env
    page = analysis(config, 'a', ['单细胞分析'], ['模型评价'])
    facts = page_facts(config, read_page(page)[0])
    assert '- 分析用途：模型评价' in facts
    page = analysis(config, 't', ['单细胞分析'], ['模型评价'], kind='technical')
    assert '分析用途' not in page_facts(config, read_page(page)[0])


def test_taxonomy_api_is_the_same_derivation_as_the_backend(taxonomy_env):
    config, _ = taxonomy_env
    analysis(config, 'a', ['单细胞分析', '转录组'], ['降维与聚类'])
    analysis(config, 'b', ['单细胞分析'], ['模型评价'])
    analysis(config, 'legacy', ['单细胞分析'])
    analysis(config, 'technical', ['单细胞分析'], kind='technical')
    with TestClient(create_app(config)) as client:
        response = client.get('/api/method-taxonomy')
    assert response.status_code == 200
    assert response.json() == taxonomy(config.wiki_root)
    assert response.json()['total'] == 3


def test_purpose_classification_does_not_invalidate_implementation_receipt(taxonomy_env):
    import hashlib
    import json
    from conftest import complete_sections
    from rwiki.acceptance import record_acceptance
    from rwiki.method_implementations import implementation_status
    from rwiki.pages import read_page
    config, _ = taxonomy_env
    page = analysis(config, 'evidence', ['单细胞分析'], ['降维与聚类'])
    meta, body = read_page(page)
    meta['implementations'] = [{
        'id': 'run', 'title': 'Run', 'language': 'Python',
        'entrypoint': 'code/run.py:run', 'dependencies': [],
        'verification': 'verification/run.json'}]
    write_page(page, meta, body)
    code = page.with_suffix('') / 'code'
    code.mkdir(parents=True)
    (code / 'run.py').write_text('def run(x): return x\n', encoding='utf-8')
    receipt = page.with_suffix('') / 'verification/run.json'
    receipt.parent.mkdir()
    receipt.write_text(json.dumps({
        'schema_version': 1, 'implementation': 'run', 'state': 'passed',
        'scope': 'fixture', 'command': 'python fixture.py', 'checks': ['identity'],
        'environment': {'python': 'fixture'},
        'files': {p.relative_to(page.with_suffix('')).as_posix():
                  hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (page.with_suffix('') / 'code').rglob('*') if p.is_file()},
    }), encoding='utf-8')
    complete_sections(page)
    record_acceptance(config, page)
    assert implementation_status(page)[0]['state'] == 'verified'
    meta, body = read_page(page)
    meta['purposes'] = ['降维与聚类', '模型评价']
    write_page(page, meta, body)
    # Classification metadata is not algorithm input; the code receipt stays current.
    assert implementation_status(page)[0]['state'] == 'verified'


@pytest.mark.parametrize('purpose', [
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
])
def test_each_controlled_purpose_is_accepted(taxonomy_env, purpose):
    config, _ = taxonomy_env
    page = analysis(config, 'one', ['单细胞分析'], [purpose])
    from rwiki.pages import read_page
    assert purpose_errors(read_page(page)[0]) == []


def _write_analysis(
    config,
    mid,
    tags,
    purposes=None,
    data_domains=None,
    kind='analysis',
    status='draft',
    extra_meta=None,
):
    path = config.wiki_root / f'methods/{mid}.md'
    meta = {
        'type': 'method', 'id': mid, 'title': mid, 'status': status, 'tags': tags,
        'inputs': [], 'outputs': [], 'source': {'kind': 'written'},
        'license': 'none', 'cite': ['fixture'], 'favorite': False, 'method_kind': kind,
        'summary': f'{mid} answers one bounded question.',
        'data_contract': {'input': 'one row per sample', 'output': 'one estimate per group'},
    }
    if purposes is not None:
        meta['purposes'] = purposes
    if data_domains is not None:
        meta['data_domains'] = data_domains
    if extra_meta:
        meta.update(extra_meta)
    write_page(
        path,
        meta,
        f'# {mid}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n'
        '<!-- user:start -->\n<!-- user:end -->\n',
    )
    return path


def test_data_domains_and_purposes_vocabularies():
    assert DATA_DOMAINS == (
        ('single-cell', '单细胞转录组'),
        ('spatial-omics', '空间转录组'),
        ('bulk-transcriptomics', 'Bulk 转录组'),
        ('genomics-epigenomics', '基因组与表观遗传'),
        ('clinical-prognosis', '临床与预后建模'),
        ('multi-omics', '多组学整合与泛癌'),
        ('general-viz-stats', '通用绘图与统计'),
    )
    assert len(DATA_DOMAINS) == 7
    assert DOMAIN_LABELS == dict(DATA_DOMAINS)
    assert len(PURPOSES) == 12
    for new_purpose in ('细胞通讯与微环境', '变异与表观调控', '生存与预后建模', '集合与通用统计'):
        assert new_purpose in PURPOSES
        assert purpose_errors({
            'type': 'method',
            'method_kind': 'analysis',
            'purposes': [new_purpose],
        }) == []


def test_data_domain_errors_validation():
    for page_type in ('method', 'template', 'recipe', 'scenario'):
        assert data_domain_errors({'type': page_type, 'data_domains': ['single-cell', 'multi-omics']}) == []
        assert data_domain_errors({'type': page_type, 'data_domains': []}) == []
        assert data_domain_errors({'type': page_type}) == []

    for disallowed_type in ('layout', 'interface', 'project', 'source', 'chart-type'):
        errors = data_domain_errors({'type': disallowed_type, 'data_domains': ['single-cell']})
        assert errors and '只适用' in errors[0]

    assert data_domain_errors({'type': 'method', 'data_domains': 'single-cell'})
    assert data_domain_errors({'type': 'method', 'data_domains': ['']})
    assert data_domain_errors({'type': 'method', 'data_domains': [' single-cell ']})
    bad = data_domain_errors({'type': 'method', 'data_domains': ['transcriptomics']})
    assert bad and '非法数据域' in bad[0] and 'transcriptomics' in bad[0]
    dup = data_domain_errors({'type': 'method', 'data_domains': ['single-cell', 'single-cell']})
    assert dup == ['data_domains 不得重复']


def test_domains_for_prefers_explicit_and_maps_tags_conservatively():
    # Explicit data_domains takes precedence and deduplicates.
    assert domains_for({
        'data_domains': ['bulk-transcriptomics', 'single-cell', 'bulk-transcriptomics'],
        'tags': ['单细胞分析'],
    }) == ['bulk-transcriptomics', 'single-cell']

    # Empty explicit list falls back conservatively.
    assert domains_for({'data_domains': [], 'tags': ['单细胞分析', '转录组']}) == ['single-cell']

    # Ambiguous tags are never guessed into bulk-transcriptomics or clinical-prognosis.
    assert domains_for({'tags': ['转录组']}) == []
    assert domains_for({'tags': ['transcriptomics']}) == []
    assert domains_for({'tags': ['机器学习']}) == []
    assert domains_for({'tags': ['machine-learning', '模型解释与特征重要性']}) == []
    assert domains_for({'tags': ['单细胞分析', '转录组']}) == ['single-cell']

    # Explicit non-ambiguous legacy mappings deduplicate cleanly.
    assert domains_for({'tags': ['single-cell', '单细胞分析']}) == ['single-cell']
    assert domains_for({'tags': ['生存分析', '诊断与预测评价', 'diagnostic-roc']}) == ['clinical-prognosis']
    assert domains_for({'tags': ['multi-omics', '多组学整合']}) == ['multi-omics']
    assert domains_for({'tags': ['机器学习', '实验统计']}) == ['general-viz-stats']
    assert domains_for({'tags': ['experimental-statistics']}) == ['general-viz-stats']


def test_taxonomy_data_domains_dedup_empty_zeros_and_backward_compat(taxonomy_env):
    config, _ = taxonomy_env
    _write_analysis(
        config,
        'de-analysis',
        ['单细胞分析', '转录组'],
        purposes=['差异与功能分析', '细胞通讯与微环境'],
        data_domains=['single-cell', 'bulk-transcriptomics'],
    )
    _write_analysis(
        config,
        'survival-model',
        ['生存分析'],
        purposes=['生存与预后建模'],
        data_domains=['clinical-prognosis'],
    )
    # Ambiguous legacy page without explicit data_domains stays searchable & counted in total,
    # without fabricating a bulk-transcriptomics domain count.
    _write_analysis(config, 'ambiguous-rna', ['转录组'])
    _write_analysis(config, 'wf', ['单细胞分析'], ['差异与功能分析'], data_domains=['single-cell'], kind='workflow')
    _write_analysis(config, 'old', ['单细胞分析'], ['差异与功能分析'], data_domains=['single-cell'], status='archived')

    report = taxonomy(config.wiki_root)
    assert report['total'] == 3
    assert set(('total', 'domains', 'data_domains', 'domain_labels', 'purposes', 'unclassified')) <= set(report)
    assert report['domain_labels'] == dict(DATA_DOMAINS)
    assert [item['id'] for item in report['unclassified']] == ['ambiguous-rna']

    # Legacy domains preserved.
    legacy_domains = {item['value']: item for item in report['domains']}
    assert legacy_domains['单细胞分析']['count'] == 1
    assert legacy_domains['转录组']['count'] == 2

    # All 7 canonical data_domains present in order, with empty ones explicitly count: 0.
    assert [(item['value'], item['label']) for item in report['data_domains']] == list(DATA_DOMAINS)
    by_slug = {item['value']: item for item in report['data_domains']}
    assert by_slug['single-cell']['count'] == 1
    assert by_slug['single-cell']['purposes'] == [
        {'value': '差异与功能分析', 'count': 1},
        {'value': '细胞通讯与微环境', 'count': 1},
    ]
    assert by_slug['bulk-transcriptomics']['count'] == 1
    assert by_slug['clinical-prognosis']['count'] == 1
    for empty_slug in ('spatial-omics', 'genomics-epigenomics', 'multi-omics', 'general-viz-stats'):
        assert by_slug[empty_slug]['count'] == 0
        assert by_slug[empty_slug]['purposes'] == []

    with TestClient(create_app(config)) as client:
        response = client.get('/api/method-taxonomy')
    assert response.status_code == 200
    assert response.json() == report


def test_select_methods_supports_canonical_and_legacy_domains(taxonomy_env):
    config, _ = taxonomy_env
    _write_analysis(
        config,
        'cell-comm',
        ['单细胞分析', '转录组'],
        purposes=['细胞通讯与微环境'],
        data_domains=['single-cell', 'spatial-omics'],
    )
    _write_analysis(
        config,
        'legacy-sc',
        ['单细胞分析'],
        purposes=['降维与聚类'],
    )
    _write_analysis(
        config,
        'ambiguous-rna',
        ['转录组'],
        purposes=['差异与功能分析'],
    )

    assert select_methods(config.wiki_root, domain='single-cell') == [
        'methods/cell-comm.md',
        'methods/legacy-sc.md',
    ]
    assert select_methods(config.wiki_root, domain='spatial-omics') == ['methods/cell-comm.md']
    assert select_methods(config.wiki_root, domain='bulk-transcriptomics') == []
    assert select_methods(config.wiki_root, domain='转录组') == [
        'methods/ambiguous-rna.md',
        'methods/cell-comm.md',
    ]
    assert select_methods(config.wiki_root, domain='single-cell', purpose='细胞通讯与微环境') == [
        'methods/cell-comm.md',
    ]


def test_lint_validates_data_domains_and_new_purposes(taxonomy_env):
    config, _ = taxonomy_env
    _write_analysis(
        config,
        'good-method',
        ['单细胞分析'],
        purposes=['细胞通讯与微环境', '集合与通用统计'],
        data_domains=['single-cell', 'spatial-omics'],
    )
    _write_analysis(
        config,
        'bad-domain',
        ['单细胞分析'],
        purposes=['变异与表观调控'],
        data_domains=['not-a-domain'],
    )
    write_page(
        config.wiki_root / 'layouts/bad-layout.md',
        {
            'type': 'layout', 'id': 'bad-layout', 'title': 'bad-layout', 'status': 'pending_signoff',
            'gallery_entry': 'g', 'gallery_version': 1, 'language': 'python',
            'tags': ['单细胞分析'], 'data_domains': ['single-cell'],
            'chart_types': ['bar'], 'favorite': False, 'panels': {'A': 'bar'},
            'templates': [], 'template_panels': {},
        },
        '# bad-layout\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n',
    )
    report = lint(config)
    assert not any(line.startswith('ERROR methods/good-method.md:') for line in report)
    assert any(line.startswith('ERROR methods/bad-domain.md:') and 'not-a-domain' in line for line in report)
    assert any(line.startswith('ERROR layouts/bad-layout.md:') and 'data_domains' in line for line in report)


def test_lint_validates_template_primary_method(taxonomy_env):
    config, _ = taxonomy_env
    _write_analysis(
        config,
        'cell-type-annotation',
        ['单细胞分析'],
        purposes=['注释与参考映射'],
        data_domains=['single-cell'],
        extra_meta={'aliases': ['legacy-annot-method']},
    )
    _write_analysis(config, 'tech-helper', ['单细胞分析'], kind='technical')
    _write_analysis(config, 'archived-method', ['单细胞分析'], status='archived')
    write_page(
        config.wiki_root / 'recipes/src-recipe.md',
        {
            'type': 'recipe', 'id': 'src-recipe', 'title': 'src-recipe', 'status': 'draft',
            'source': {'id': 's', 'item': 'i', 'commit': 'c'}, 'license': 'MIT',
            'language': 'r', 'runner': 'knitr', 'entry': 'run.Rmd',
            'tags': ['单细胞分析'], 'chart_types': ['bar'], 'favorite': False,
        },
        '# src-recipe\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n',
    )

    def write_tmpl(tid, primary_method):
        meta = {
            'type': 'template', 'id': tid, 'title': tid, 'status': 'draft',
            'sources': ['recipes/src-recipe'], 'panels': [], 'language': 'r',
            'tags': ['单细胞分析'], 'chart_types': ['bar'], 'favorite': False,
        }
        if primary_method is not None:
            meta['primary_method'] = primary_method
        write_page(
            config.wiki_root / f'templates/{tid}.md',
            meta,
            f'# {tid}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n',
        )

    write_tmpl('ok-canonical', 'cell-type-annotation')
    write_tmpl('ok-typed-ref', 'methods/cell-type-annotation')
    write_tmpl('ok-alias', 'legacy-annot-method')
    write_tmpl('bad-missing', 'nonexistent-method')
    write_tmpl('bad-technical', 'tech-helper')
    write_tmpl('bad-archived', 'archived-method')
    write_tmpl('bad-empty', '')
    _write_analysis(
        config,
        'bad-pm-on-method',
        ['单细胞分析'],
        purposes=['注释与参考映射'],
        extra_meta={'primary_method': 'cell-type-annotation'},
    )

    report = lint(config)
    assert not any(line.startswith('ERROR templates/ok-canonical.md:') for line in report)
    assert not any(line.startswith('ERROR templates/ok-typed-ref.md:') for line in report)
    assert not any(line.startswith('ERROR templates/ok-alias.md:') for line in report)
    assert any(line.startswith('ERROR templates/bad-missing.md:') and 'primary_method' in line for line in report)
    assert any(line.startswith('ERROR templates/bad-technical.md:') and 'analysis' in line for line in report)
    assert any(line.startswith('ERROR templates/bad-archived.md:') and '已归档' in line for line in report)
    assert any(line.startswith('ERROR templates/bad-empty.md:') and 'primary_method' in line for line in report)
    assert any(line.startswith('ERROR methods/bad-pm-on-method.md:') and 'primary_method' in line for line in report)


def test_lint_validates_method_render_bridges(taxonomy_env):
    config, _ = taxonomy_env
    write_interface(
        config.wiki_root,
        'render-dotplot-long',
        {'gene': {'type': 'str', 'description': '基因名'}, 'expr': {'type': 'float', 'description': '平均表达'}},
        '点图长表',
    )
    _write_analysis(
        config,
        'ok-bridge',
        ['单细胞分析'],
        purposes=['注释与参考映射'],
        extra_meta={
            'render_bridges': [{
                'interface': 'render-dotplot-long',
                'from_output': 'scrna-annotated-cells',
                'extractor_note': '按细胞类型聚合平均表达并转为长表。',
            }],
        },
    )
    _write_analysis(
        config,
        'bad-missing-iface',
        ['单细胞分析'],
        purposes=['注释与参考映射'],
        extra_meta={
            'render_bridges': [{
                'interface': 'missing-render-iface',
                'from_output': 'scrna-annotated-cells',
                'extractor_note': '提取平均表达。',
            }],
        },
    )
    _write_analysis(
        config,
        'bad-schema',
        ['单细胞分析'],
        purposes=['注释与参考映射'],
        extra_meta={
            'render_bridges': [{
                'interface': 'render-dotplot-long',
                'from_output': '',
                'extractor_note': '提取平均表达。',
            }],
        },
    )
    _write_analysis(
        config,
        'bad-type',
        ['单细胞分析'],
        purposes=['注释与参考映射'],
        extra_meta={'render_bridges': 'not-a-list'},
    )
    write_page(
        config.wiki_root / 'recipes/src-r.md',
        {
            'type': 'recipe', 'id': 'src-r', 'title': 'src-r', 'status': 'draft',
            'source': {'id': 's', 'item': 'i', 'commit': 'c'}, 'license': 'MIT',
            'language': 'r', 'runner': 'knitr', 'entry': 'run.Rmd',
            'tags': ['单细胞分析'], 'chart_types': ['bar'], 'favorite': False,
        },
        '# src-r\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n',
    )
    write_page(
        config.wiki_root / 'templates/bad-bridge-on-tmpl.md',
        {
            'type': 'template', 'id': 'bad-bridge-on-tmpl', 'title': 'bad-bridge-on-tmpl', 'status': 'draft',
            'sources': ['recipes/src-r'], 'panels': [], 'language': 'r',
            'tags': ['单细胞分析'], 'chart_types': ['bar'], 'favorite': False,
            'render_bridges': [],
        },
        '# bad-bridge-on-tmpl\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n',
    )

    report = lint(config)
    assert not any(line.startswith('ERROR methods/ok-bridge.md:') for line in report)
    assert any(
        line.startswith('ERROR methods/bad-missing-iface.md:') and 'missing-render-iface' in line
        for line in report
    )
    assert any(line.startswith('ERROR methods/bad-schema.md:') and 'from_output' in line for line in report)
    assert any(line.startswith('ERROR methods/bad-type.md:') and 'render_bridges' in line for line in report)
    assert any(line.startswith('ERROR templates/bad-bridge-on-tmpl.md:') and 'render_bridges' in line for line in report)

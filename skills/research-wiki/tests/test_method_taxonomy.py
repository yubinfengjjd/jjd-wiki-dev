"""Research-domain -> analysis-purpose navigation; counts are distinct pages, never category sums."""
import json

import pytest
from fastapi.testclient import TestClient

from rwiki.method_taxonomy import PURPOSES, purpose_errors, select_methods, taxonomy
from rwiki.pages import write_page
from rwiki.server import create_app


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


def test_counts_are_distinct_pages_not_overlapping_category_sums(workspace):
    config, _ = workspace
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


def test_domain_and_purpose_intersection_and_same_page_once(workspace):
    config, _ = workspace
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


def test_workflow_technical_archived_and_unclassified_are_not_analysis_cards(workspace):
    config, _ = workspace
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


def test_purpose_vocabulary_and_errors(workspace):
    config, _ = workspace
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
    assert '预处理与质量控制' in PURPOSES and len(PURPOSES) == 8


def test_lint_warns_missing_purpose_but_rejects_invalid_one(workspace):
    from rwiki.lint import lint
    config, _ = workspace
    analysis(config, 'legacy', ['单细胞分析'])
    report = lint(config)
    assert any('WARN methods/legacy.md' in line and 'purposes' in line for line in report)
    assert not any('ERROR methods/legacy.md' in line for line in report)
    page = analysis(config, 'bad', ['单细胞分析'], ['不存在的用途'])
    report = lint(config)
    assert any('ERROR methods/bad.md' in line and '不存在' in line for line in report)
    assert page


def test_check_entry_prompts_missing_purpose_without_failing_or_changing_status(workspace):
    from conftest import complete_sections, run_cli
    config, config_path = workspace
    page = analysis(config, 'legacy', ['单细胞分析'])
    complete_sections(page)
    result = run_cli(config_path, 'check-entry', 'legacy')
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['passed'] is True
    assert any('purposes' in warning for warning in report['warnings'])
    from rwiki.pages import read_page
    assert read_page(page)[0]['status'] == 'draft'


def test_facts_show_purposes_for_analysis_only(workspace):
    from rwiki.facts import page_facts
    from rwiki.pages import read_page
    config, _ = workspace
    page = analysis(config, 'a', ['单细胞分析'], ['模型评价'])
    facts = page_facts(config, read_page(page)[0])
    assert '- 分析用途：模型评价' in facts
    page = analysis(config, 't', ['单细胞分析'], ['模型评价'], kind='technical')
    assert '分析用途' not in page_facts(config, read_page(page)[0])


def test_taxonomy_api_is_the_same_derivation_as_the_backend(workspace):
    config, _ = workspace
    analysis(config, 'a', ['单细胞分析', '转录组'], ['降维与聚类'])
    analysis(config, 'b', ['单细胞分析'], ['模型评价'])
    analysis(config, 'legacy', ['单细胞分析'])
    analysis(config, 'technical', ['单细胞分析'], kind='technical')
    with TestClient(create_app(config)) as client:
        response = client.get('/api/method-taxonomy')
    assert response.status_code == 200
    assert response.json() == taxonomy(config.wiki_root)
    assert response.json()['total'] == 3


def test_purpose_classification_does_not_invalidate_implementation_receipt(workspace):
    import hashlib
    import json
    from conftest import complete_sections
    from rwiki.acceptance import record_acceptance
    from rwiki.method_implementations import implementation_status
    from rwiki.pages import read_page
    config, _ = workspace
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


@pytest.mark.parametrize('purpose', ['预处理与质量控制', '降维与聚类', '整合与批次校正',
                                     '注释与参考映射', '差异与功能分析', '轨迹与动态分析',
                                     '模型评价', '模型解释'])
def test_each_controlled_purpose_is_accepted(workspace, purpose):
    config, _ = workspace
    page = analysis(config, 'one', ['单细胞分析'], [purpose])
    from rwiki.pages import read_page
    assert purpose_errors(read_page(page)[0]) == []

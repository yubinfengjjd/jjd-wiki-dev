"""Method knowledge approval never substitutes for implementation evidence."""
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from conftest import complete_sections
from rwiki.acceptance import ready_for_use, record_acceptance
from rwiki.catalog import build_index
from rwiki.methods import confirm_method, scaffold_method
from rwiki.pages import read_page, write_page
from rwiki.server import create_app
from rwiki.suggest import suggest_methods
from rwiki.workflow import workflow_snapshot


def method(config, mid='analysis', kind='analysis', verified=False):
    scaffold_method(config, mid, mid, 'MIT', written=True)
    page = config.wiki_root / f'methods/{mid}.md'
    meta, body = read_page(page)
    meta.update(cite=['Official source'], summary='A bounded research question.',
                data_contract={'input': 'One row per sample.', 'output': 'An estimate per group.'},
                implementations=[{'id': 'first', 'title': 'First implementation', 'language': 'Python',
                                  'entrypoint': 'code/first.py:run', 'dependencies': [],
                                  'verification': 'verification/first.json'},
                                 {'id': 'other', 'title': 'Other implementation', 'language': 'R',
                                  'entrypoint': 'code/other.R:run', 'dependencies': []}])
    if kind is not None:
        meta['method_kind'] = kind
    write_page(page, meta, body)
    complete_sections(page)
    code = page.with_suffix('') / 'code'
    code.mkdir(parents=True)
    (code / 'first.py').write_text('def run(x): return x\n', encoding='utf-8')
    (code / 'other.R').write_text('run <- function(x) x\n', encoding='utf-8')
    if verified:
        receipt(page)
    confirm_method(config, mid)
    return page


def receipt(page, **changes):
    asset = page.with_suffix('')
    data = {'schema_version': 1, 'implementation': 'first', 'state': 'passed',
            'scope': 'Isolated software fixture only.', 'command': 'python fixture.py',
            'checks': ['Expected identity result'], 'environment': {'python': 'fixture'},
            'files': {p.relative_to(asset).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (asset / 'code').rglob('*') if p.is_file()}}
    data.update(changes)
    target = asset / 'verification/first.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(data), encoding='utf-8')


@pytest.mark.parametrize('kind', ['workflow', 'technical', None])
def test_only_analysis_families_are_recommended(workspace, kind):
    config, _ = workspace
    page = method(config, kind=kind, verified=True)
    assert not ready_for_use(config, page)
    assert suggest_methods(config) == []
    flow = workflow_snapshot(config)[page.relative_to(config.wiki_root).as_posix()]
    assert flow['label'] != '可用'
    if kind is None:
        assert flow['label'] == '待分类'


def test_note_confirmation_without_receipt_keeps_implementation_pending(workspace):
    config, _ = workspace
    page = method(config)
    assert read_page(page)[0]['status'] == 'ready'
    assert not ready_for_use(config, page)
    assert suggest_methods(config) == []
    assert workflow_snapshot(config)['methods/analysis.md']['label'] == '待验证实现'


def test_verified_branch_does_not_promote_other_branches(workspace):
    config, _ = workspace
    page = method(config, verified=True)
    assert ready_for_use(config, page)
    candidate = suggest_methods(config)[0]
    assert [item['id'] for item in candidate['implementations']] == ['first']
    assert candidate['code_files'] == ['methods/analysis/code/first.py']
    with TestClient(create_app(config)) as client:
        detail = client.get('/api/page', params={'path': 'methods/analysis.md'}).json()
        summary = next(p for p in client.get('/api/pages').json() if p['path'] == 'methods/analysis.md')
    assert detail['implementation_status'] == summary['implementation_status']
    assert [item['state'] for item in detail['implementation_status']] == ['verified', 'not_run']
    assert 'implementation_status' not in detail['meta']


def test_code_mutation_invalidates_evidence_even_after_note_recheck(workspace):
    from rwiki.method_implementations import implementation_status
    config, _ = workspace
    page = method(config, verified=True)
    (page.with_suffix('') / 'code/other.R').write_text('run <- function(x) x * 2\n', encoding='utf-8')
    record_acceptance(config, page)
    assert implementation_status(page)[0]['state'] == 'stale'
    assert not ready_for_use(config, page)
    assert suggest_methods(config) == []


@pytest.mark.parametrize('changes', [
    {'implementation': 'other'}, {'schema_version': 2}, {'state': 'failed'},
    {'scope': ''}, {'command': ''}, {'checks': []}, {'environment': []},
    {'files': {}}, {'files': {'../outside.py': '0' * 64}},
    {'files': {'C:/outside.py': '0' * 64}}, {'files': {'code/first.py': 'bad'}},
])
def test_bad_receipts_never_grant_execution(workspace, changes):
    from rwiki.method_implementations import implementation_status
    config, _ = workspace
    page = method(config, verified=True)
    receipt(page, **changes)
    assert implementation_status(page)[0]['state'] == 'invalid'
    assert not ready_for_use(config, page)


@pytest.mark.parametrize('field,value', [
    ('entrypoint', '../outside.py:run'), ('entrypoint', 'source/original.py:run'),
    ('entrypoint', 'code/missing.py:run'), ('verification', '../receipt.json'),
    ('verification', 'C:\\receipt.json'),
])
def test_unsafe_or_missing_entry_and_receipt_paths_do_not_verify(workspace, field, value):
    from rwiki.method_implementations import implementation_status
    config, _ = workspace
    page = method(config, verified=True)
    meta, body = read_page(page)
    meta['implementations'][0][field] = value
    write_page(page, meta, body)
    assert implementation_status(page)[0]['state'] == 'invalid'
    assert not ready_for_use(config, page)


def test_index_classifies_each_method_once_and_preserves_legacy_page(workspace):
    config, _ = workspace
    for mid, kind in [('analysis', 'analysis'), ('process', 'workflow'),
                      ('source-guide', 'technical'), ('legacy', None)]:
        method(config, mid, kind)
    index = build_index(config.wiki_root)
    for heading in ['分析家族', '组合流程', '技术资料', '待分类方法']:
        assert f'## {heading}' in index
    for mid in ['analysis', 'process', 'source-guide', 'legacy']:
        assert index.count(f'[[methods/{mid}|') == 1
        assert f'[[methods/{mid}|{mid}]] — A bounded research question.' in index


def test_code_changes_do_not_revoke_author_note_confirmation(workspace):
    from rwiki.acceptance import acceptance_stale
    config, _ = workspace
    page = method(config, verified=True)
    (page.with_suffix('') / 'code/first.py').write_text('def run(x): return x * 2\n', encoding='utf-8')
    assert not acceptance_stale(page)
    assert read_page(page)[0]['status'] == 'ready'
    assert workflow_snapshot(config)['methods/analysis.md']['label'] == '待验证实现'


@pytest.mark.parametrize('kind,label', [('workflow', '流程资料已确认'), ('technical', '技术资料已确认')])
def test_ready_reference_notes_are_not_queued_for_analysis_implementation(workspace, kind, label):
    from conftest import complete_sections
    from rwiki.methods import scaffold_method
    from rwiki.pages import read_page, write_page
    config, _ = workspace
    scaffold_method(config, 'note', 'Reference note', 'MIT', written=True)
    page = config.wiki_root / 'methods/note.md'
    meta, body = read_page(page)
    meta.update(method_kind=kind, summary='Reference material, not an analysis.',
                data_contract={'input': 'Reference material.', 'output': 'Documentation.'},
                implementations=[], cite=['Fixture reference'])
    write_page(page, meta, body)
    complete_sections(page)
    confirm_method(config, 'note')
    record_acceptance(config, page)
    flow = workflow_snapshot(config)['methods/note.md']
    assert flow['label'] == label
    assert flow['queue'] is None


def test_second_source_adds_branch_without_creating_another_family(workspace):
    config, _ = workspace
    page = method(config, verified=True)
    meta, _ = read_page(page)
    assert len(meta['implementations']) == 2
    index = build_index(config.wiki_root)
    assert index.count('[[methods/analysis|analysis]]') == 1
    assert index.count('[[methods/analysis|') == 1
    candidate = suggest_methods(config)[0]
    assert [item['id'] for item in candidate['implementations']] == ['first']
    assert candidate['method_kind'] == 'analysis'


def test_code_files_expose_shared_branch_status_without_promoting_originals(workspace):
    from rwiki.code_assets import code_files
    config, _ = workspace
    page = method(config, verified=True)
    meta, body = read_page(page)
    # Both branches share one entrypoint file; only the first has a current receipt.
    meta['implementations'][1]['entrypoint'] = 'code/first.py:other'
    write_page(page, meta, body)
    source = page.with_suffix('') / 'source/original.py'
    source.parent.mkdir()
    source.write_text('# source only\n', encoding='utf-8')
    listing = code_files(config, 'methods/analysis.md')
    rows = {row['path']: row for row in listing['files']}
    shared = rows['code/first.py']
    assert {branch['id'] for branch in shared['branches']} == {'first', 'other'}
    assert {branch['state'] for branch in shared['branches']} == {'verified', 'not_run'}
    assert shared['verification']['state'] == 'mixed'
    assert 'first' in shared['verification']['scope'] and 'other' in shared['verification']['scope']
    original = rows['source/original.py']
    assert original['branches'] == [] and original['verification']['state'] == 'unknown'
    with TestClient(create_app(config)) as client:
        api_listing = client.get('/api/methods/analysis/code-files').json()
    api_shared = {row['path']: row for row in api_listing['files']}['code/first.py']
    assert {branch['id'] for branch in api_shared['branches']} == {'first', 'other'}
    assert api_shared['verification']['state'] == 'mixed'


def test_technical_source_page_cannot_keep_primary_figure_relations(workspace):
    from rwiki.lint import lint
    config, _ = workspace
    page = method(config, 'source-guide', kind='technical')
    meta, body = read_page(page)
    meta['figure_relations'] = [{'figure': 'templates/source-panel'}]
    write_page(page, meta, body)
    findings = '\n'.join(lint(config))
    assert 'workflow/technical 资料不应维护主 figure_relations' in findings


def test_lint_exposes_classification_missing_implementation_and_duplicate_families(workspace):
    from rwiki.lint import lint
    config, _ = workspace
    method(config, 'legacy', None)
    page = method(config, 'one')
    meta, body = read_page(page)
    meta['implementations'] = []
    write_page(page, meta, body)
    page2 = method(config, 'two')
    meta2, body2 = read_page(page2)
    meta2['title'] = meta['title']
    write_page(page2, meta2, body2)
    findings = '\n'.join(lint(config))
    assert 'method_kind 缺失' in findings
    assert '未声明实现' in findings
    assert '重复分析家族' in findings

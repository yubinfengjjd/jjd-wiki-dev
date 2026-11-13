"""Read-only opportunity discovery: candidates never silently become executable."""
import hashlib
import json

from rwiki.acceptance import ready_for_use
from rwiki.discovery import discover_methods
from rwiki.methods import confirm_method, scaffold_method
from rwiki.pages import read_page, write_page
from rwiki.suggest import suggest_methods
from conftest import complete_sections


def analysis(config, mid, *, verified=False, status='ready'):
    """Minimal analysis page fixture; receipts only ever seal fixture bytes."""
    scaffold_method(config, mid, mid, 'MIT', written=True)
    page = config.wiki_root / f'methods/{mid}.md'
    meta, body = read_page(page)
    meta.update(cite=['fixture source'], summary='fixture', method_kind='analysis',
                data_contract={'input': 'x', 'output': 'y'},
                implementations=[{'id': 'branch', 'title': 'Branch', 'language': 'Python',
                                  'entrypoint': 'code/run.py:run', 'dependencies': [],
                                  'verification': 'verification/branch.json'}])
    write_page(page, meta, body)
    complete_sections(page)
    code = page.with_suffix('') / 'code'
    code.mkdir(parents=True)
    (code / 'run.py').write_text('def run(x): return x\n', encoding='utf-8')
    if verified:
        asset = page.with_suffix('')
        receipt = {'schema_version': 1, 'implementation': 'branch', 'state': 'passed',
                   'scope': 'fixture', 'command': 'python run.py', 'checks': ['ok'],
                   'environment': {'python': 'fixture'},
                   'files': {p.relative_to(asset).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (asset / 'code').rglob('*') if p.is_file()}}
        (asset / 'verification').mkdir()
        (asset / 'verification/branch.json').write_text(json.dumps(receipt), encoding='utf-8')
    confirm_method(config, mid)
    if status != 'ready':
        meta, body = read_page(page)
        meta['status'] = status
        write_page(page, meta, body)
    return page


def test_ready_and_not_run_branches_reported_separately(workspace):
    config, _ = workspace
    ready_page = analysis(config, 'readyfam', verified=True)
    gap_page = analysis(config, 'gapfam', verified=False)
    result = discover_methods(config)
    candidates = {c['id']: c for c in result['candidates']}
    assert candidates['readyfam']['executable'] is True
    assert candidates['gapfam']['executable'] is False
    assert candidates['gapfam']['readiness']['not_run'] == ['branch']
    assert candidates['readyfam']['readiness']['verified'] == ['branch']
    # Library gaps are opportunities, not executable items.
    assert candidates['gapfam']['gaps']
    # suggest-methods semantics unchanged: only the ready family is returned.
    assert [c['id'] for c in suggest_methods(config)] == ['readyfam']
    assert ready_for_use(config, ready_page)
    assert not ready_for_use(config, gap_page)


def test_workflow_and_technical_never_become_candidates(workspace):
    config, _ = workspace
    page = analysis(config, 'pipe', verified=False)
    meta, body = read_page(page)
    meta['method_kind'] = 'workflow'
    write_page(page, meta, body)
    result = discover_methods(config)
    assert 'pipe' not in {c['id'] for c in result['candidates']}
    assert 'pipe' in {c['id'] for c in result['context_only']}


def test_archived_pages_are_excluded_not_promoted(workspace):
    config, _ = workspace
    page = analysis(config, 'gone', verified=True)
    meta, body = read_page(page)
    meta['status'] = 'archived'
    write_page(page, meta, body)
    result = discover_methods(config)
    assert 'gone' not in {c['id'] for c in result['candidates']}
    assert 'gone' not in {c['id'] for c in result['context_only']}
    assert result['excluded']['archived'] >= 1


def test_discovery_is_read_only_and_scoped(workspace):
    config, _ = workspace
    analysis(config, 'fam', verified=False)
    before = (config.wiki_root / 'methods/fam.md').read_bytes()
    result = discover_methods(config)
    assert (config.wiki_root / 'methods/fam.md').read_bytes() == before
    note = result['scope_note']
    # The note must carry the actual scoping semantics, not just exist.
    assert '机会' in note
    assert '不是可执行推荐' in note or '不是可执行' in note


def test_query_scores_but_does_not_reorder_truth(workspace):
    config, _ = workspace
    analysis(config, 'alpha', verified=False)
    analysis(config, 'beta', verified=True)
    result = discover_methods(config, query='beta')
    candidates = {c['id']: c for c in result['candidates']}
    assert candidates['beta']['score'] > candidates['alpha']['score']
    assert candidates['alpha']['executable'] is False
    assert candidates['beta']['executable'] is True

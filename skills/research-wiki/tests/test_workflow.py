"""Queue represents remaining actions, not every unfinished persistent status."""
import json

from fastapi.testclient import TestClient

from conftest import ENTRY_ID, run_cli, seal_replay
from rwiki.pages import read_page, write_page
from rwiki.server import create_app
from rwiki.templates import pending


def test_passed_replay_labels_keep_author_confirmation_separate(tmp_path, monkeypatch):
    from pathlib import Path
    from rwiki.config import Config
    from rwiki import workflow
    root = tmp_path / 'wiki'
    root.mkdir()
    config = Config(root, tmp_path / 'gallery', tmp_path / 'taxonomy.json',
                    Path('python'), Path('Rscript'), 8765)
    pages = []
    before = {}
    for kind in ('recipe', 'template'):
        path = root / f'{kind}s/example.md'
        path.parent.mkdir()
        path.write_text('original author material\n', encoding='utf-8')
        before[path] = path.read_bytes()
        pages.append((path, {'type': kind, 'id': 'example', 'status': 'draft'}))
    monkeypatch.setattr(workflow, 'readable_pages', lambda _: pages)
    monkeypatch.setattr(workflow, 'entry_errors', lambda *args: [])
    result = workflow.workflow_snapshot(config)
    assert result['recipes/example.md']['label'] == '原样运行通过 · 待确认'
    assert result['templates/example.md']['label'] == '回放通过 · 待确认'
    assert all(item['queue'] == 'confirm' for item in result.values())
    assert all(path.read_bytes() == data for path, data in before.items())


def single(config):
    page = config.wiki_root / f'layouts/{ENTRY_ID}.md'
    meta, body = read_page(page)
    tid = meta['templates'][0]
    meta.update(panels={'A': 'bar'}, templates=[tid], template_panels={tid: ['A']})
    write_page(page, meta, body)
    return page, tid


def state(config, tid, status, replay=False):
    page = config.wiki_root / f'templates/{tid}.md'
    meta, body = read_page(page)
    meta['status'] = status
    write_page(page, meta, body)
    target = page.with_suffix('')
    if replay:
        seal_replay(target)
    elif status == 'draft':
        (target / 'verify/verify.json').unlink(missing_ok=True)


def actions(config):
    with TestClient(create_app(config)) as client:
        records = client.get('/api/pages').json()
        detail = client.get('/api/page', params={'path': f'layouts/{ENTRY_ID}.md'}).json()
    result = {p['path']: p['workflow'] for p in records if 'workflow' in p}
    assert detail['workflow'] == result[f'layouts/{ENTRY_ID}.md']
    return result


def test_accepted_templates_do_not_leave_source_in_agent_pending(layout_workspace):
    config, config_path, _, _ = layout_workspace
    source, tid = single(config)
    before = source.read_bytes()
    assert pending(config) == []  # source status is pending_template, coverage is ready
    assert run_cli(config_path, 'pending').stdout == ''
    queue = actions(config)
    assert queue[f'layouts/{ENTRY_ID}.md']['stage'] == 'complete'
    assert queue[f'layouts/{ENTRY_ID}.md']['queue'] is None
    assert source.read_bytes() == before  # no fabricated layout verification/signoff


def test_unverified_template_owns_one_action_not_two(layout_workspace):
    config, _, _, _ = layout_workspace
    _, tid = single(config)
    state(config, tid, 'draft')
    queue = actions(config)
    assert queue[f'layouts/{ENTRY_ID}.md']['queue'] is None
    assert queue[f'templates/{tid}.md']['queue'] == 'agent'
    assert pending(config) == [ENTRY_ID]


def test_successful_replay_waits_for_author_not_agent(layout_workspace):
    config, _, _, _ = layout_workspace
    _, tid = single(config)
    state(config, tid, 'draft', replay=True)
    queue = actions(config)
    assert queue[f'layouts/{ENTRY_ID}.md']['queue'] is None
    assert queue[f'templates/{tid}.md']['queue'] == 'confirm'
    assert read_page(config.wiki_root / f'templates/{tid}.md')[0]['status'] == 'draft'
    assert pending(config) == []


def test_preview_alone_or_failed_receipt_is_still_agent_work(layout_workspace):
    config, _, _, _ = layout_workspace
    _, tid = single(config)
    state(config, tid, 'draft', replay=True)
    receipt = config.wiki_root / f'templates/{tid}/verify/verify.json'
    receipt.write_text('{"exit_code": 1}', encoding='utf-8')
    assert actions(config)[f'templates/{tid}.md']['queue'] == 'agent'
    receipt.unlink()
    assert actions(config)[f'templates/{tid}.md']['queue'] == 'agent'


def test_archive_restore_and_delete_recompute_coverage(layout_workspace):
    config, _, _, _ = layout_workspace
    _, tid = single(config)
    state(config, tid, 'archived')
    assert actions(config)[f'layouts/{ENTRY_ID}.md']['queue'] == 'agent'
    assert pending(config) == [ENTRY_ID]
    state(config, tid, 'ready')
    assert pending(config) == []
    (config.wiki_root / f'templates/{tid}.md').unlink()
    assert actions(config)[f'layouts/{ENTRY_ID}.md']['queue'] == 'agent'
    assert pending(config) == [ENTRY_ID]


def test_uncovered_panel_and_bad_mapping_are_not_hidden(layout_workspace):
    config, _, _, _ = layout_workspace
    page, tid = single(config)
    meta, body = read_page(page)
    meta['template_panels'][tid] = ['B']
    write_page(page, meta, body)
    assert pending(config) == [ENTRY_ID]
    assert actions(config)[f'layouts/{ENTRY_ID}.md']['queue'] == 'agent'


def test_reingest_preserves_accepted_template_and_source_links(layout_workspace):
    from rwiki.ingest import ingest_figure
    config, _, _, _ = layout_workspace
    page, _ = single(config)
    gallery = config.gallery_root / '2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/meta.json'
    gm = json.loads(gallery.read_text(encoding='utf-8'))
    gm['figure']['panel_map'] = {'A': 'bar'}
    gallery.write_text(json.dumps(gm), encoding='utf-8')
    meta, _ = read_page(page)
    before = meta['template_panels']
    ingest_figure(config, ENTRY_ID)
    assert read_page(page)[0]['template_panels'] == before
    assert pending(config) == []


def test_new_source_version_requires_signoff_without_retemplating(layout_workspace):
    config, _, _, _ = layout_workspace
    page, tid = single(config)
    meta, body = read_page(page)
    meta['status'] = 'pending_signoff'
    write_page(page, meta, body)
    queue = actions(config)
    assert queue[f'layouts/{ENTRY_ID}.md']['queue'] == 'signoff'
    assert queue[f'templates/{tid}.md']['queue'] is None
    assert pending(config) == []


def test_archive_restore_delete_api_refresh_same_queue_without_gallery_changes(layout_workspace):
    config, _, _, _ = layout_workspace
    _, tid = single(config)
    gallery_before = {p: p.read_bytes() for p in config.gallery_root.rglob('meta.json')}
    with TestClient(create_app(config)) as client:
        prefix = f'/api/templates/{tid}'
        assert client.post(prefix + '/archive').status_code == 200
        assert actions(config)[f'layouts/{ENTRY_ID}.md']['queue'] == 'agent'
        assert client.post(prefix + '/restore').status_code == 200
        assert pending(config) == []
        assert client.post(prefix + '/archive').status_code == 200
        plan = client.get(prefix + '/delete-plan').json()
        deleted = client.post(prefix + '/delete', json={'confirmed': True, 'revision': plan['revision']})
        assert deleted.status_code == 200, deleted.text
        assert pending(config) == [ENTRY_ID]
        source, _ = read_page(config.wiki_root / f'layouts/{ENTRY_ID}.md')
        assert source['templates'] == [] and source['template_panels'] == {}
    assert gallery_before == {p: p.read_bytes() for p in gallery_before}

"""Regression gates from the 2026-10-21 whole-flow audit."""
import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from conftest import ENTRY_ID, run_cli, seal_replay, update_gallery
from test_templates import approved, fake_template
from rwiki.acceptance import acceptance_stale, entry_errors, ready_for_use, record_acceptance
from rwiki.errors import WikiError
from rwiki.ingest import ingest_figure
from rwiki.pages import read_page, section_bounds, write_page
from rwiki.server import create_app
from rwiki.suggest import suggest
from rwiki.templates import mark_ready, verify_template
from rwiki.verification import replay_available
from rwiki.workflow import workflow_snapshot


def test_repeated_ingest_never_signs_new_version(workspace):
    config, _ = workspace
    config = replace(config, single_panel_only=True)
    gallery = next(config.gallery_root.glob('*/figures/*/meta.json'))
    gm = json.loads(gallery.read_text(encoding='utf-8'))
    gm['figure']['panel_map'] = {'A': 'bar'}
    update_gallery(config, status='approved', figure=gm['figure'])
    ingest_figure(config, ENTRY_ID)
    update_gallery(config, version=2)
    for _ in range(3):
        ingest_figure(config, ENTRY_ID)
        assert read_page(config.wiki_root / f'layouts/{ENTRY_ID}.md')[0]['status'] == 'pending_signoff'
    with TestClient(create_app(config)) as client:
        assert client.post(f'/api/layouts/{ENTRY_ID}/signoff').status_code == 200
    ingest_figure(config, ENTRY_ID)
    assert read_page(config.wiki_root / f'layouts/{ENTRY_ID}.md')[0]['signedoff_version'] == 2


def test_preview_without_replay_cannot_become_ready(fake_template):
    config, _, target = fake_template
    Image.new('RGB', (8, 8), 'white').save(target / 'preview.png')
    with pytest.raises(WikiError, match='回放'):
        mark_ready(config, target.name)
    assert read_page(target.with_suffix('.md'))[0]['status'] == 'draft'


@pytest.mark.parametrize('changed', ['code/render.py', 'code/panel.py', 'spec.json',
                                    'example/values.csv', 'interface', 'output'])
def test_replay_is_bound_to_current_inputs_and_outputs(fake_template, changed):
    config, _, target = fake_template
    verify_template(config, target.name)
    assert replay_available(target)
    if changed == 'interface':
        p = config.wiki_root / 'interfaces/values.md'
        m, b = read_page(p)
        m['columns']['value']['type'] = 'float'
        write_page(p, m, b)
    elif changed == 'output':
        (target / 'verify/figure.pdf').write_bytes(b'changed PDF')
    else:
        p = target / changed
        p.write_bytes(p.read_bytes() + b'\n')
    assert not replay_available(target)
    assert workflow_snapshot(config)[f'templates/{target.name}.md']['queue'] == 'agent'


def test_failed_rerun_invalidates_previous_success(fake_template):
    config, _, target = fake_template
    verify_template(config, target.name)
    (target / 'code/render.py').write_text("raise RuntimeError('isolated failure')\n", encoding='utf-8')
    with pytest.raises(WikiError):
        verify_template(config, target.name)
    assert not replay_available(target)
    assert json.loads((target / 'verify/verify.json').read_text())['exit_code'] != 0


def test_empty_method_is_agent_work_and_confirmation_is_rejected(workspace, tmp_path):
    from conftest import run_cli
    from rwiki.methods import scaffold_method
    config, config_path = workspace
    source = tmp_path / 'fixture.py'
    source.write_text('# fixture\n', encoding='utf-8')
    scaffold_method(config, 'blank', 'Blank note', 'none', from_path=source)
    assert workflow_snapshot(config)['methods/blank.md']['queue'] == 'agent'
    with TestClient(create_app(config)) as client:
        response = client.post('/api/methods/blank/confirm')
    assert response.status_code == 409
    assert '用途' in response.text and '知识关联检查' in response.text
    assert read_page(config.wiki_root / 'methods/blank.md')[0]['status'] == 'draft'
    pending = run_cli(config_path, 'pending', '--json')
    assert pending.returncode == 0, pending.stderr
    assert [p['path'] for p in json.loads(pending.stdout)] == ['methods/blank.md']


def test_text_only_method_with_review_can_confirm_and_records_acceptance(workspace, tmp_path):
    from conftest import complete_sections, run_cli
    from rwiki.methods import scaffold_method
    from rwiki.suggest import suggest_methods
    config, config_path = workspace
    source = tmp_path / 'native.py'
    source.write_text('# preserved source\n', encoding='utf-8')
    scaffold_method(config, 'note', 'Text note', 'none', from_path=source)
    page = config.wiki_root / 'methods/note.md'
    complete_sections(page)
    with TestClient(create_app(config)) as client:
        assert client.post('/api/methods/note/confirm').status_code == 200
    record = page.with_suffix('') / 'acceptance.json'
    assert record.is_file()
    assert '知识关联检查' in json.loads(record.read_text(encoding='utf-8'))['checks']
    assert not (page.with_suffix('') / 'code').exists()
    assert [m['id'] for m in suggest_methods(config)] == ['note']
    meta, body = read_page(page)
    write_page(page, meta, body.replace('隔离软件夹具的说明', '内容更新后的软件夹具说明', 1))
    assert workflow_snapshot(config)['methods/note.md']['queue'] == 'agent'
    assert suggest_methods(config) == []
    result = run_cli(config_path, 'check-entry', 'note', '--record')
    assert result.returncode == 0, result.stderr
    assert workflow_snapshot(config)['methods/note.md']['queue'] is None
    assert (page.with_suffix('') / 'source/native.py').read_bytes() == source.read_bytes()


def test_missing_relation_review_blocks_method_even_when_other_sections_complete(workspace, tmp_path):
    from conftest import complete_sections
    from rwiki.methods import scaffold_method, confirm_method
    from rwiki.pages import section_bounds
    config, _ = workspace
    source = tmp_path / 'fixture.py'
    source.write_text('# fixture\n', encoding='utf-8')
    scaffold_method(config, 'review', 'Review', 'none', from_path=source)
    page = config.wiki_root / 'methods/review.md'
    complete_sections(page)
    meta, body = read_page(page)
    start, end = section_bounds(body, '知识关联检查')
    write_page(page, meta, body[:start] + '\nTODO\n' + body[end:])
    with pytest.raises(WikiError, match='知识关联检查'):
        confirm_method(config, 'review')
    assert read_page(page)[0]['status'] == 'draft'


def test_legacy_pending_template_without_signed_version_requires_signoff(workspace):
    config, _ = workspace
    update_gallery(config, status='approved', version=2)
    gallery = next(config.gallery_root.glob('*/figures/*/meta.json'))
    gm = json.loads(gallery.read_text(encoding='utf-8'))
    gm['approved_version'] = 1
    gallery.write_text(json.dumps(gm, ensure_ascii=False), encoding='utf-8', newline='\n')
    ingest_figure(config, ENTRY_ID)
    page = config.wiki_root / f'layouts/{ENTRY_ID}.md'
    meta, body = read_page(page)
    meta['status'] = 'pending_template'
    meta['gallery_version'] = 2
    meta.pop('signedoff_version', None)
    write_page(page, meta, body)
    ingest_figure(config, ENTRY_ID)
    assert read_page(page)[0]['status'] == 'pending_signoff'


def test_new_page_from_legacy_approved_gallery_requires_signoff(workspace):
    config, _ = workspace
    update_gallery(config, status='approved')
    gallery = next(config.gallery_root.glob('*/figures/*/meta.json'))
    gm = json.loads(gallery.read_text(encoding='utf-8'))
    gm.pop('approved_version', None)
    gallery.write_text(json.dumps(gm, ensure_ascii=False), encoding='utf-8', newline='\n')
    ingest_figure(config, ENTRY_ID)
    assert read_page(config.wiki_root / f'layouts/{ENTRY_ID}.md')[0]['status'] == 'pending_signoff'


def test_placeholder_with_explanation_is_rejected(fake_template):
    config, _, target = fake_template
    page = target.with_suffix('.md')
    meta, body = read_page(page)
    start, end = section_bounds(body, '适用')
    write_page(page, meta, body[:start] + '\nTODO：补充数据\n' + body[end:])
    assert any('适用' in error for error in entry_errors(config, page))


def test_check_entry_reports_and_refreshes_stale_acceptance(fake_template):
    config, config_path, target = fake_template
    verify_template(config, target.name)
    mark_ready(config, target.name)
    page = target.with_suffix('.md')
    meta, body = read_page(page)
    start, end = section_bounds(body, '知识关联检查')
    write_page(page, meta, body[:start] + '\nchanged review\n' + body[end:])
    result = run_cli(config_path, 'check-entry', target.name)
    assert result.returncode == 1, result.stdout
    assert '验收记录' in result.stdout
    result = run_cli(config_path, 'check-entry', target.name, '--record')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['passed'] is True


def make_ready_layout(config, target):
    page = target.with_suffix('.md')
    Image.new('RGB', (8, 8), 'white').save(target / 'preview.png')
    seal_replay(target)
    meta, body = read_page(page)
    meta['status'] = 'ready'
    write_page(page, meta, body)
    record_acceptance(config, page)
    return page


def test_ready_layout_with_archived_template_is_agent(layout_workspace):
    config, _, target, _ = layout_workspace
    page = make_ready_layout(config, target)
    meta, _ = read_page(page)
    tid = meta['templates'][0]
    template = config.wiki_root / 'templates' / f'{tid}.md'
    tm, tb = read_page(template)
    tm['status'] = 'archived'
    tm['archived_from'] = 'ready'
    write_page(template, tm, tb)
    assert not ready_for_use(config, page)
    assert workflow_snapshot(config)[page.relative_to(config.wiki_root).as_posix()]['queue'] == 'agent'
    assert all(item['id'] != ENTRY_ID for item in suggest(config, [], None, '', 10))


def test_ready_layout_with_incomplete_template_is_agent(layout_workspace):
    config, _, target, _ = layout_workspace
    page = make_ready_layout(config, target)
    meta, _ = read_page(page)
    tid = meta['templates'][0]
    template = config.wiki_root / 'templates' / f'{tid}.md'
    tm, tb = read_page(template)
    start, end = section_bounds(tb, '适用')
    write_page(template, tm, tb[:start] + '\n' + tb[end:])
    assert not ready_for_use(config, page)
    assert workflow_snapshot(config)[page.relative_to(config.wiki_root).as_posix()]['queue'] == 'agent'


def test_mark_ready_rejects_layout_with_incomplete_template(layout_workspace):
    config, _, target, _ = layout_workspace
    page = target.with_suffix('.md')
    meta, _ = read_page(page)
    tid = meta['templates'][0]
    template = config.wiki_root / 'templates' / f'{tid}.md'
    tm, tb = read_page(template)
    start, end = section_bounds(tb, '适用')
    write_page(template, tm, tb[:start] + '\n' + tb[end:])
    with pytest.raises(WikiError, match='模板验收'):
        mark_ready(config, ENTRY_ID)


def test_ready_layout_stale_acceptance_is_agent(layout_workspace):
    config, _, target, _ = layout_workspace
    page = make_ready_layout(config, target)
    meta, body = read_page(page)
    start, end = section_bounds(body, '适用')
    write_page(page, meta, body[:start] + '\nchanged\n' + body[end:])
    assert acceptance_stale(page)
    assert not ready_for_use(config, page)
    assert workflow_snapshot(config)[page.relative_to(config.wiki_root).as_posix()]['queue'] == 'agent'


def test_source_updated_since_page_load_cannot_be_signed(ingested):
    config, _ = ingested
    update_gallery(config, version=2)
    with TestClient(create_app(config)) as client:
        response = client.post(f'/api/layouts/{ENTRY_ID}/signoff')
    assert response.status_code == 409
    assert read_page(config.wiki_root / f'layouts/{ENTRY_ID}.md')[0]['status'] == 'pending_signoff'

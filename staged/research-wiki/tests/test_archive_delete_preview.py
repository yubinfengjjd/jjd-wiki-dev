import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from conftest import ENTRY_ID
from rwiki.pages import read_page, write_page, set_block, get_block
from rwiki.server import create_app
from rwiki.lint import lint


@pytest.fixture
def deletion_web(layout_workspace):
    config, _, _, _ = layout_workspace
    write_page(config.wiki_root / 'chart-types/dot.md', {'type':'chart-type','slug':'dot','title':'dot'}, '# dot\n')
    with TestClient(create_app(config)) as client:
        tid = ENTRY_ID + '--bar'
        client.post(f'/api/templates/{tid}/archive')
        yield config, client, tid


def digest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def test_archive_preview_is_source_if_no_replay(deletion_web):
    config, client, tid = deletion_web
    (config.wiki_root / f'templates/{tid}/preview.png').unlink()
    origin = config.wiki_root / f'layouts/{ENTRY_ID}.md'
    meta, body = read_page(origin); meta['panels'] = {'A': 'bar'}; write_page(origin, meta, body)
    detail = client.get('/api/page', params={'path': f'templates/{tid}.md'}).json()
    assert detail['preview']['kind'] == 'source'
    assert client.get(detail['preview']['url']).status_code == 200
    assert '尚无回放' in detail['preview']['label']
    listed = next(p for p in client.get('/api/pages').json() if p['path'] == f'templates/{tid}.md')
    assert listed['preview'] == detail['preview']


def test_missing_preview_does_not_reference_missing_file(deletion_web):
    config, client, tid = deletion_web
    (config.wiki_root / f'templates/{tid}/preview.png').unlink()
    p = client.get('/api/page', params={'path': f'templates/{tid}.md'}).json()['preview']
    assert p['kind'] == 'none' and p['url'] is None


def test_delete_cleans_refs_assets_graph_and_records_audit(deletion_web):
    config, client, tid = deletion_web
    gallery_before = digest(config.gallery_root)
    p = config.wiki_root / 'projects/example.md'
    write_page(p, {'type':'project','slug':'example','title':'案例','templates':[tid]},
               f'# 案例\n[[templates/{tid}|模板]]\n[代码](/files/wiki/templates/{tid}/code/panel.py)\n')
    plan = client.get(f'/api/templates/{tid}/delete-plan').json()
    assert plan['affected'] and plan['asset_files'] > 0
    response = client.post(f'/api/templates/{tid}/delete', json={'confirmed':True, 'revision':plan['revision']})
    assert response.status_code == 200, response.text
    assert not (config.wiki_root / f'templates/{tid}.md').exists()
    assert not (config.wiki_root / f'templates/{tid}').exists()
    assert tid not in read_page(p)[0]['templates']
    assert 'href' not in read_page(p)[1] and '[[' not in read_page(p)[1]
    origin, _ = read_page(config.wiki_root / f'layouts/{ENTRY_ID}.md')
    assert tid not in origin['templates'] and tid not in origin['template_panels']
    layout = json.loads((config.wiki_root / f'layouts/{ENTRY_ID}/layout.json').read_text(encoding='utf-8'))
    assert all(panel['template'] != tid for panel in layout['panels'])
    assert client.get('/api/page',params={'path':f'templates/{tid}.md'}).status_code == 404
    assert not any(n['id'] == f'templates/{tid}.md' for n in client.get('/api/graph').json()['nodes'])
    audit = json.loads((config.wiki_root / response.json()['audit']).read_text(encoding='utf-8'))
    assert audit['deleted_at'] and audit['changed_pages']
    assert digest(config.gallery_root) == gallery_before
    assert not [x for x in lint(config) if x.startswith('ERROR')]


def test_delete_rejects_nonarchived_and_unconfirmed(deletion_web):
    config, client, tid = deletion_web
    other = ENTRY_ID + '--dot'
    assert client.get(f'/api/templates/{other}/delete-plan').status_code == 409
    assert client.post(f'/api/templates/{tid}/delete',json={'confirmed':False,'revision':'x'}).status_code == 422
    assert client.post(f'/api/templates/{tid}/delete',json={'confirmed':'true','revision':'x'}).status_code == 422
    assert (config.wiki_root / f'templates/{tid}.md').exists()


def test_stale_delete_plan_does_not_mutate(deletion_web):
    config, client, tid = deletion_web
    plan = client.get(f'/api/templates/{tid}/delete-plan').json()
    p = config.wiki_root / f'templates/{tid}.md'; p.write_text(p.read_text(encoding='utf-8')+'\n更新\n',encoding='utf-8')
    before = digest(config.wiki_root)
    r = client.post(f'/api/templates/{tid}/delete',json={'confirmed':True,'revision':plan['revision']})
    assert r.status_code == 409
    assert digest(config.wiki_root) == before


def test_protected_author_reference_blocks_cleanup(deletion_web):
    config, client, tid = deletion_web
    p = config.wiki_root / f'layouts/{ENTRY_ID}.md'
    meta, body = read_page(p)
    body = set_block(body,'user',f'\n保留 [[templates/{tid}]]\n')
    write_page(p,meta,body)
    r = client.get(f'/api/templates/{tid}/delete-plan')
    assert r.status_code == 409 and '作者备注' in r.text
    assert get_block(read_page(p)[1],'user') == get_block(body,'user')


def test_missing_and_traversal_targets_are_rejected(deletion_web):
    _, client, _ = deletion_web
    assert client.get('/api/templates/missing/delete-plan').status_code == 404
    assert client.get('/api/templates/%2e%2e%5cAGENTS/delete-plan').status_code == 404


def test_delete_invalidates_ready_layout(deletion_web):
    config, client, tid = deletion_web
    p = config.wiki_root / f'layouts/{ENTRY_ID}.md'
    meta, body = read_page(p); meta['status'] = 'ready'; write_page(p,meta,body)
    plan = client.get(f'/api/templates/{tid}/delete-plan').json()
    r = client.post(f'/api/templates/{tid}/delete',json={'confirmed':True,'revision':plan['revision']})
    assert r.status_code == 200, r.text
    assert read_page(p)[0]['status'] == 'pending_template'

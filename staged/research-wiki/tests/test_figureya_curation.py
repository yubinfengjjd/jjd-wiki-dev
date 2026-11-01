import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from rwiki import finder, server
from rwiki.pages import read_page, write_page


@pytest.fixture
def curated_wiki(wiki_repo, tmp_path):
    config, _, _ = wiki_repo
    config = replace(config, sources_root=tmp_path / 'snapshots')
    for sid in ('figureya', 'figureya-archive'):
        write_page(config.wiki_root / 'sources' / f'{sid}.md',
                   {'type': 'source', 'id': sid, 'title': sid, 'adapter': 'figureya',
                    'snapshot': sid, 'license': 'CC-BY-NC-SA-4.0', 'trusted': True}, '# source\n')
        target = config.wiki_root / 'sources' / sid / 'items.jsonl'
        target.parent.mkdir(parents=True, exist_ok=True)
        items = [{'id': f'{sid}:FigureYa{n}', 'source': sid, 'item': f'FigureYa{n}',
                  'title': f'chart {n}', 'inputs': [], 'requires': [], 'chart_hints': ['bar']}
                 for n in range(1, 4)]
        target.write_text('\n'.join(map(json.dumps, items)), encoding='utf-8')
        image = config.sources_root / sid / 'gallery_compress' / 'FigureYa1.webp'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'image')
    write_page(config.wiki_root / 'recipes' / 'figureya-1.md',
               {'type': 'recipe', 'id': 'figureya-1', 'title': 'promoted', 'status': 'ready',
                'source': {'id': 'figureya', 'item': 'FigureYa1'}}, '# recipe\n<!-- user:start -->author<!-- user:end -->\n')
    write_page(config.wiki_root / 'templates' / 't.md',
               {'type': 'template', 'id': 't', 'title': 'template', 'status': 'ready',
                'sources': ['recipes/figureya-1.md']}, '# template\n')
    write_page(config.wiki_root / 'scenarios' / 's.md',
               {'type': 'scenario', 'id': 's', 'title': 'scenario', 'picks': [
                   {'id': 'figureya:FigureYa1'}, {'id': 'templates/t'},
                   {'id': 'figureya-archive:FigureYa1'}]}, '# scenario\n')
    return config


def test_inventory_includes_promoted_and_independent_versions_with_local_previews(curated_wiki):
    with TestClient(server.create_app(curated_wiki)) as client:
        response = client.get('/api/figureya/curation')
        assert response.status_code == 200
        items = response.json()['items']
        assert len(items) == 6  # 3 original, including promoted, plus 3 archive versions
        promoted = next(i for i in items if i['id'] == 'figureya:FigureYa1')
        assert promoted['recipes'][0]['id'] == 'figureya-1'
        assert promoted['decision'] == 'pending'
        assert promoted['images'][0]['url'].startswith('/api/figureya/image?')
        assert client.get(promoted['images'][0]['url']).content == b'image'
        assert client.get('/api/figureya/image', params={
            'id': promoted['id'], 'path': '../secret.png'}).status_code == 404


def test_remove_restore_filters_cli_and_web_without_touching_sources_or_author_blocks(curated_wiki, monkeypatch):
    from rwiki import curation
    config = curated_wiki
    # Real persistence and Git save, without requiring complete scientific fixtures.
    monkeypatch.setattr('rwiki.facts.refresh_facts', lambda config: None)
    raw = config.wiki_root / 'sources' / 'figureya' / 'items.jsonl'
    original = raw.read_bytes()
    recipe = config.wiki_root / 'recipes' / 'figureya-1.md'
    author = recipe.read_bytes()
    stale_catalog = config.wiki_root / 'catalog.jsonl'
    stale_catalog.write_text(json.dumps({'id': 'figureya:FigureYa1', 'kind': 'item'}) + '\n', encoding='utf-8')
    with TestClient(server.create_app(config)) as client:
        before = client.get('/api/figureya/curation').json()
        result = client.post('/api/figureya/curation', json={
            'ids': ['figureya:FigureYa1'], 'decision': 'removed', 'revision': before['revision']})
        assert result.status_code == 200, result.text
        assert curation.removed_ids(config) == {'figureya:FigureYa1'}
        stale_catalog.write_text(json.dumps({'id': 'figureya:FigureYa1', 'kind': 'item'}) + '\n', encoding='utf-8')
        assert finder.record_for(config, 'figureya:FigureYa1') is None
        assert finder.record_for(config, 't') is None
        assert finder.record_for(config, 'figureya-archive:FigureYa1') is not None
        assert not any(i['id'] == 'figureya:FigureYa1' for i in finder.load_catalog(config))
        visible = client.get('/api/pages?light=true').json()
        assert not any(p['path'] in ('recipes/figureya-1.md', 'templates/t.md') for p in visible)
        assert next(p for p in visible if p['path'] == 'scenarios/s.md')['meta']['picks'] == [
            {'id': 'figureya-archive:FigureYa1'}]
        assert client.get('/api/page?path=scenarios/s.md').json()['meta']['picks'] == [
            {'id': 'figureya-archive:FigureYa1'}]
        graph = client.get('/api/graph').json()
        assert not any(p['id'] in ('recipes/figureya-1.md', 'templates/t.md') for p in graph['nodes'])
        assert not any(i['id'] == 'figureya:FigureYa1' for i in client.get('/api/source-items').json())
        # A rescan overwriting items.jsonl cannot resurrect the removed module.
        raw.write_bytes(original)
        assert curation.removed_ids(config) == {'figureya:FigureYa1'}
        assert read_page(recipe)[0]['status'] == 'ready'
        assert recipe.read_bytes() == author and raw.read_bytes() == original
        assert client.post('/api/figureya/curation', json={
            'ids': ['figureya:FigureYa2'], 'decision': 'kept', 'revision': before['revision']}).status_code == 409
        revision = client.get('/api/figureya/curation').json()['revision']
        assert client.post('/api/figureya/curation', json={
            'ids': ['figureya:FigureYa1'], 'decision': 'pending', 'revision': revision}).status_code == 200
        assert not curation.removed_ids(config)
        assert finder.record_for(config, 'figureya:FigureYa1') is not None


def test_save_failure_rolls_back_decisions_and_catalog(curated_wiki, monkeypatch):
    from rwiki import curation
    config = curated_wiki
    catalog = config.wiki_root / 'catalog.jsonl'
    catalog.write_text('original\n', encoding='utf-8')
    scenario = config.wiki_root / 'scenarios' / 's.md'
    original_scenario = scenario.read_bytes()
    ignored = config.wiki_root / '.gitignore'
    original_ignore = ignored.read_bytes()
    def fail_save(*args):
        catalog.write_text('partial save\n', encoding='utf-8')
        scenario.write_text('facts already refreshed before commit failure\n', encoding='utf-8')
        ignored.write_text('partial ignore rules\n', encoding='utf-8')
        raise RuntimeError('simulated save failure')
    monkeypatch.setattr('rwiki.store.save', fail_save)
    with pytest.raises(RuntimeError):
        curation.update(config, ['figureya:FigureYa1'], 'removed', curation.revision(config))
    assert not curation.state_file(config).exists()
    assert catalog.read_text(encoding='utf-8') == 'original\n'
    assert scenario.read_bytes() == original_scenario
    assert ignored.read_bytes() == original_ignore


def test_batch_rejects_unknown_ids_and_cross_site_writes_atomically(curated_wiki):
    from rwiki import curation
    with TestClient(server.create_app(curated_wiki)) as client:
        revision = client.get('/api/figureya/curation').json()['revision']
        payload = {'ids': ['figureya:FigureYa1', 'figureya:missing'], 'decision': 'removed', 'revision': revision}
        assert client.post('/api/figureya/curation', json=payload).status_code == 422
        assert not curation.removed_ids(curated_wiki)
        payload['ids'] = ['figureya:FigureYa1']
        assert client.post('/api/figureya/curation', json=payload,
                           headers={'Origin': 'https://foreign.example'}).status_code == 403
        assert not curation.removed_ids(curated_wiki)


def test_selection_save_reuses_reads_but_sees_new_decision(curated_wiki, monkeypatch):
    from rwiki import curation
    from rwiki.read_cache import remember
    built = []
    def save_probe(config, message):
        assert curation.removed_ids(config) == {'figureya:FigureYa1'}
        for _ in range(20):
            remember('expensive-library-scan', lambda: built.append(True))
    monkeypatch.setattr('rwiki.store.save', save_probe)
    result = curation.update(curated_wiki, ['figureya:FigureYa1'], 'removed', curation.revision(curated_wiki))
    assert len(built) == 1
    assert result['revision'] == curation.revision(curated_wiki)


def test_relation_inventory_is_built_once_per_read_session(curated_wiki, monkeypatch):
    from rwiki import relations
    from rwiki.read_cache import read_session
    config = curated_wiki
    write_page(config.wiki_root / 'methods' / 'm.md',
               {'type': 'method', 'id': 'm', 'title': 'method', 'status': 'draft'}, '# method\n')
    checked = []
    def probe(*args):
        checked.append(True)
        return [], []
    monkeypatch.setattr(relations, '_checked', probe)
    with read_session():
        relations.all_relations(config)
        relations.all_relations(config)
    assert len(checked) == 1
    with read_session():
        relations.all_relations(config)
    assert len(checked) == 2

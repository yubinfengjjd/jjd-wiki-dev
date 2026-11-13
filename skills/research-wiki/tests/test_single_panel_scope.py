from dataclasses import replace
import json

import pytest

from conftest import ENTRY_ID
from rwiki.config import load_config
from rwiki.errors import WikiError
from rwiki.ingest import ingest_figure
from rwiki.pages import read_page, write_page


def test_single_scope_rejects_group_before_creating_page(workspace):
    config, _ = workspace
    with pytest.raises(WikiError, match='一个逻辑 panel'):
        ingest_figure(replace(config, single_panel_only=True), ENTRY_ID)
    assert not list((config.wiki_root / 'layouts').glob('*.md'))


def test_single_scope_accepts_one_logical_panel(workspace):
    config, _ = workspace
    path = next(config.gallery_root.glob('*/figures/*/meta.json'))
    meta = json.loads(path.read_text(encoding='utf-8'))
    meta['figure']['panel_map'] = {'A': 'density-scatter'}
    path.write_text(json.dumps(meta), encoding='utf-8')
    ingest_figure(replace(config, single_panel_only=True), ENTRY_ID)
    page, _ = read_page(config.wiki_root / f'layouts/{ENTRY_ID}.md')
    assert page['panels'] == {'A': 'density-scatter'}


def test_archived_group_is_untouched_by_direct_and_bulk_ingest(ingested):
    config, _ = ingested
    path = config.wiki_root / f'layouts/{ENTRY_ID}.md'
    meta, body = read_page(path)
    meta.update(status='archived', archived_from=meta['status'])
    write_page(path, meta, body)
    before = path.read_bytes()
    scoped = replace(config, single_panel_only=True)
    ingest_figure(scoped, ENTRY_ID)
    ingest_figure(scoped)
    assert path.read_bytes() == before


def test_bulk_ingest_skips_group_without_creating_it(workspace):
    config, _ = workspace
    ingest_figure(replace(config, single_panel_only=True))
    assert not list((config.wiki_root / 'layouts').glob('*.md'))


def test_scope_config_rejects_string_boolean(workspace):
    _, path = workspace
    meta = json.loads(path.read_text(encoding='utf-8'))
    meta['single_panel_only'] = 'true'
    path.write_text(json.dumps(meta), encoding='utf-8')
    with pytest.raises(WikiError, match='布尔值'):
        load_config(path)

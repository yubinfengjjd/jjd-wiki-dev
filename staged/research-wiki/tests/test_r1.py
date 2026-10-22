import json

import pytest
from fastapi.testclient import TestClient

from conftest import ENTRY_ID, complete_sections, record_ready_receipt, run_cli, update_gallery
from rwiki.ingest import ingest_figure
from rwiki.pages import get_block, read_page, write_page
from rwiki.server import create_app


def test_ingest_translates_primary_secondary_and_keeps_free_tags(workspace):
    config, _ = workspace
    update_gallery(config, scenarios={'primary': ['model-explanation-shap'],
                                     'secondary': ['single-cell', 'model-explanation-shap'],
                                     'free': ['SHAP', '单细胞分析', 'SHAP']})
    ingest_figure(config, ENTRY_ID)
    meta, body = read_page(config.wiki_root / f'layouts/{ENTRY_ID}.md')
    assert meta['tags'] == ['模型解释与特征重要性', '单细胞分析', 'SHAP']
    assert 'scenarios' not in meta
    assert not (config.wiki_root / 'scenarios').exists()
    assert '单细胞分析' in get_block(body, 'facts')
    assert '[[scenarios/' not in body


@pytest.mark.parametrize('tags, expected', [
    ([' SHAP ', '模型解释', 'SHAP', ' 模型解释 ', ''], ['SHAP', '模型解释']),
    ([], []),
])
def test_tags_api_normalizes_and_persists(ingested, tags, expected):
    config, _ = ingested
    with TestClient(create_app(config)) as client:
        result = client.post(f'/api/layouts/{ENTRY_ID}/tags', json={'tags': tags})
        assert result.status_code == 200, result.text
        assert result.json()['meta']['tags'] == expected
        assert read_page(config.wiki_root / f'layouts/{ENTRY_ID}.md')[0]['tags'] == expected
        assert client.get('/api/taxonomy').status_code == 404
        assert client.post(f'/api/layouts/{ENTRY_ID}/scenarios', json={}).status_code in (404, 405)


def test_suggest_query_matches_applicability_only_not_user_text(layout_workspace):
    config, path, _, _ = layout_workspace
    page = config.wiki_root / f'templates/{ENTRY_ID}--bar.md'
    meta, body = read_page(page)
    meta['tags'] = ['自由标签']
    body = body.replace('## 适用\n', '## 适用\n\n异质性比较。\n')
    body = body.replace('<!-- user:start -->', '<!-- user:start -->私人词')
    write_page(page, meta, body)
    record_ready_receipt(config, page)  # an edited ready note is re-checked before it is recommended
    result = run_cli(path, 'suggest', '--q', '异质性比较 自由标签 私人词')
    assert result.returncode == 0, result.stderr
    items = json.loads(result.stdout)
    item = next(item for item in items if item['id'] == meta['id'])
    assert item['score'] == 2
    assert item['reasons'] == ['关键词匹配：异质性比较', '关键词匹配：自由标签']
    assert item['id'] == items[0]['id']


def test_written_without_citation_is_lint_error(workspace):
    config, path = workspace
    result = run_cli(path, 'scaffold-method', 'written-note', '--title', '方法笔记',
                     '--license', 'none', '--written')
    assert result.returncode == 0, result.stderr
    result = run_cli(path, 'lint')
    assert result.returncode == 1
    assert 'written' in result.stdout and 'cite' in result.stdout
    page = config.wiki_root / 'methods/written-note.md'
    meta, body = read_page(page)
    meta['cite'] = ['官方文档。']
    write_page(page, meta, body)
    assert run_cli(path, 'save', 'add citation').returncode == 0
    result = run_cli(path, 'lint')
    assert result.returncode == 0, result.stdout + result.stderr


def test_method_confirmation_and_return_are_draft_ready_only(workspace):
    config, path = workspace
    assert run_cli(path, 'scaffold-method', 'note', '--title', '笔记', '--license', 'none',
                   '--written').returncode == 0
    page = config.wiki_root / 'methods/note.md'
    meta, body = read_page(page)
    meta['cite'] = ['Fixture citation for a written note.']
    write_page(page, meta, body)
    complete_sections(page)
    assert run_cli(path, 'mark-ready', 'note').returncode == 0
    with TestClient(create_app(config)) as client:
        assert client.post('/api/methods/note/confirm').status_code == 409
        assert client.post('/api/methods/note/return', json={'reason': '补充步骤'}).status_code == 200
        assert client.post('/api/methods/note/return', json={'reason': '重复退回'}).status_code == 409
        assert client.post('/api/methods/note/confirm').json()['meta']['status'] == 'ready'

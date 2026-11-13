import hashlib

from fastapi.testclient import TestClient

from conftest import ENTRY_ID
from rwiki.pages import read_page, write_page
from rwiki.server import create_app


def test_crlf_page_sections_keep_offsets_and_author_bytes(tmp_path):
    from rwiki.pages import get_block, section_text, set_block
    path = tmp_path/'crlf.md'
    raw = ('---\r\ntype: method\r\n---\r\n## 输入\r\n\r\n一行一个案例。\r\n\r\n'
           '## 输出\r\n结果表\r\n<!-- user:start -->\r\n作者备注\r\n<!-- user:end -->\r\n')
    path.write_bytes(raw.encode('utf-8'))
    _, body = read_page(path)
    assert section_text(body, '输入') == '一行一个案例。'
    assert section_text(body, '输出') == '结果表'
    assert get_block(body, 'user') == '\r\n作者备注\r\n'
    assert set_block(body, 'user', get_block(body, 'user')) == body


def test_facts_refresh_preserves_author_mixed_line_endings(workspace):
    from rwiki.facts import refresh_facts
    config, _ = workspace
    path = config.wiki_root / 'methods/protected.md'
    author = '\r\n迁移笔记 [[methods/repeated-benchmark-distribution]]\r\n待作者签核，方法笔记也是draft。\n'
    write_page(path, {'type':'method','id':'protected','title':'Protected','status':'draft',
                     'inputs':[],'outputs':[],'source':{'kind':'written'},'license':'none',
                     'cite':['fixture'],'tags':[],'favorite':False},
               '<!-- facts:start -->\n<!-- facts:end -->\n<!-- user:start -->' + author + '<!-- user:end -->')
    refresh_facts(config)
    raw = path.read_bytes().split(b'<!-- user:start -->',1)[1].split(b'<!-- user:end -->',1)[0]
    assert raw == author.encode('utf-8')


def test_code_view_and_download_are_readonly_and_byte_preserving(workspace):
    config, _ = workspace
    root = config.wiki_root
    page = root / 'methods/native.md'
    write_page(page, {'type': 'method', 'id': 'native', 'title': '原生代码', 'status': 'draft',
                     'inputs': [], 'outputs': [], 'tags': [], 'source': {'kind': 'written'},
                     'license': 'none', 'cite': ['fixture'], 'favorite': False},
               '<!-- facts:start -->\n<!-- facts:end -->\n<!-- user:start -->\n<!-- user:end -->')
    source = root / 'methods/native/source/analysis.R'
    source.parent.mkdir(parents=True)
    raw = b'\xef\xbb\xbfx <- c(1, 2)\r\nprint(x)\r\n'
    source.write_bytes(raw)
    page_bytes = page.read_bytes()
    with TestClient(create_app(config)) as client:
        prefix = '/api/methods/native'
        listing = client.get(prefix + '/code-files')
        assert listing.status_code == 200
        item = next(x for x in listing.json()['files'] if x['path'].endswith('analysis.R'))
        assert item['variant'] == 'original' and item['sha256'] == hashlib.sha256(raw).hexdigest()
        params = {'variant': item['variant'], 'path': item['path']}
        viewed = client.get(prefix + '/code', params=params)
        assert viewed.status_code == 200 and 'x <- c(1, 2)' in viewed.json()['text']
        downloaded = client.get(prefix + '/code-download', params=params)
        assert downloaded.status_code == 200 and downloaded.content == raw
        assert 'attachment' in downloaded.headers['content-disposition']
        assert client.get(prefix + '/code', params={'variant': 'original', 'path': '../../AGENTS.md'}).status_code == 404
        assert client.get('/api/projects/native/code-files').status_code == 404
        assert client.post(prefix + '/code', json={}).status_code == 405
    assert source.read_bytes() == raw and page.read_bytes() == page_bytes


def test_relationship_same_in_page_reverse_and_graph(layout_workspace):
    config, _, _, _ = layout_workspace
    root = config.wiki_root
    tid = ENTRY_ID + '--bar'
    relation = {'figure': 'templates/' + tid, 'compatibility': 'direct',
                'reason': 'fixture value has the same row unit and quantity',
                'prerequisites': ['one count per row'], 'adaptation': '',
                'evidence': ['fixture input-output specification'],
                'verification': {'state': 'not_run', 'scope': 'API structure only', 'evidence': []}}
    write_page(root / 'methods/counts.md', {
        'type': 'method', 'id': 'counts', 'title': 'Counts', 'status': 'ready',
        'inputs': [], 'outputs': ['values'], 'tags': [], 'source': {'kind': 'written'},
        'license': 'none', 'cite': ['fixture'], 'favorite': False, 'figure_relations': [relation]},
        '<!-- facts:start -->\n<!-- facts:end -->\n<!-- user:start -->\n<!-- user:end -->')
    with TestClient(create_app(config)) as client:
        forward = client.get('/api/page', params={'path': 'methods/counts.md'}).json()['relations']
        reverse = client.get('/api/page', params={'path': f'templates/{tid}.md'}).json()['relations']
        assert len(forward) == 1 and forward == reverse
        assert forward[0]['verification']['state'] == 'not_run'
        assert forward == client.get('/api/relations', params={'path': 'methods/counts.md'}).json()
        edge = next(x for x in client.get('/api/graph').json()['links'] if x['kind'] == 'relation')
        assert edge['source'] == 'methods/counts.md' and edge['target'] == f'templates/{tid}.md'
        assert edge['compatibility'] == 'direct' and edge['active']
        listing = client.get('/api/pages').json()
        assert next(x for x in listing if x['path'] == 'methods/counts.md')['relations'] == forward

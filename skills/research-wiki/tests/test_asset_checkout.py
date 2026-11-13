"""Checkout absence is transport state, never a scientific result."""
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                          text=True, encoding='utf-8', check=True).stdout


@pytest.fixture
def checkout(tmp_path):
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.name', 'fixture')
    git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    root = tmp_path / 'wiki'
    page = root / 'methods/example.md'
    page.parent.mkdir(parents=True)
    page.write_text('---\ntype: method\nid: example\ntitle: 示例方法\nstatus: ready\ninputs: []\noutputs: []\n---\n# 示例方法\n', encoding='utf-8')
    asset = page.with_suffix('') / 'code/analysis.R'
    asset.parent.mkdir(parents=True)
    asset.write_text('answer <- function(x) x\n', encoding='utf-8')
    (root / 'AGENTS.md').write_text('Rules\n', encoding='utf-8')
    (page.with_suffix('') / 'runtime.json').write_text('{"schema_version":1}', encoding='utf-8')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'fixture')
    return SimpleNamespace(wiki_root=root, gallery_root=tmp_path / 'gallery',
                           work_root=tmp_path / 'work'), page, asset


def test_transport_state_distinguishes_missing_from_sparse(checkout):
    from rwiki.asset_checkout import assets_state, set_profile
    config, page, asset = checkout
    assert assets_state(config, page)['state'] == 'available'
    asset.unlink()
    assert assets_state(config, page)['state'] == 'missing'
    git(config.wiki_root.parent, 'restore', '--', 'wiki/methods/example/code/analysis.R')
    set_profile(config, 'light')
    assert page.is_file() and not asset.exists()
    assert (page.with_suffix('') / 'runtime.json').is_file()
    assert assets_state(config, page)['state'] == 'not_downloaded'


def test_explicit_fetch_then_full_preserves_wiki_bytes(checkout):
    from rwiki.asset_checkout import fetch_assets, profile, set_profile
    config, page, asset = checkout
    original = page.read_bytes()
    set_profile(config, 'light')
    assert profile(config) == 'light'
    result = fetch_assets(config, 'example')
    assert result['state'] == 'available' and asset.is_file()
    assert page.read_bytes() == original
    set_profile(config, 'full')
    assert profile(config) == 'full'
    assert git(config.wiki_root.parent, 'status', '--porcelain') == ''


def test_light_blocks_save_without_changing_files(checkout):
    from rwiki.asset_checkout import assert_writable, set_profile
    from rwiki.errors import WikiError
    config, page, _ = checkout
    set_profile(config, 'light')
    original = page.read_bytes()
    with pytest.raises(WikiError, match='完整|full'):
        assert_writable(config)
    assert page.read_bytes() == original


def test_store_save_rejects_light_before_refresh(checkout):
    from rwiki.asset_checkout import set_profile
    from rwiki.errors import WikiError
    from rwiki.store import save
    config, page, _ = checkout
    set_profile(config, 'light')
    original = page.read_bytes()
    with pytest.raises(WikiError, match='完整|full'):
        save(config, 'must not modify Wiki')
    assert page.read_bytes() == original


def test_web_light_writes_rejected_before_route_dispatch(checkout):
    from fastapi.testclient import TestClient
    from rwiki.asset_checkout import set_profile
    from rwiki.server import create_app
    config, page, _ = checkout
    set_profile(config, 'light')
    original = page.read_bytes()
    with TestClient(create_app(config)) as client:
        response = client.post('/api/methods/example/favorite', json={'value': True})
    assert response.status_code == 409
    assert 'full' in response.json()['detail']
    assert page.read_bytes() == original


def test_web_light_listing_does_not_claim_verification_failure(checkout):
    from fastapi.testclient import TestClient
    from rwiki.asset_checkout import set_profile
    from rwiki.server import create_app
    config, page, _ = checkout
    set_profile(config, 'light')
    with TestClient(create_app(config)) as client:
        response = client.get('/api/pages')
    assert response.status_code == 200
    item = response.json()[0]
    assert item['workflow']['stage'] == 'checking'
    assert item['implementation_status'] == []
    assert page.is_file()


def test_fetch_rejects_traversal_before_git_mutation(checkout):
    from rwiki.asset_checkout import fetch_assets
    from rwiki.errors import WikiError
    config, _, _ = checkout
    for entry in ('../example', '/tmp/example', 'example/../../escape'):
        with pytest.raises(WikiError):
            fetch_assets(config, entry)
    assert git(config.wiki_root.parent, 'status', '--porcelain') == ''


def test_fetch_failure_preserves_existing_downloads(checkout, monkeypatch):
    import rwiki.asset_checkout as module
    from rwiki.errors import WikiError
    config, page, asset = checkout
    module.set_profile(config, 'light')
    original = page.read_bytes()
    call = module._git
    def fail(root, *args, **kwargs):
        if args[:2] == ('sparse-checkout', 'set'):
            raise WikiError('offline fixture')
        return call(root, *args, **kwargs)
    monkeypatch.setattr(module, '_git', fail)
    with pytest.raises(WikiError, match='offline'):
        module.fetch_assets(config, 'example')
    assert page.read_bytes() == original


def test_fetch_already_present_parent_still_hydrates_declared_child(checkout):
    from rwiki.asset_checkout import fetch_assets, set_profile
    config, page, _ = checkout
    child = config.wiki_root / 'methods/child.md'
    child.write_text('---\ntype: method\nid: child\ntitle: 子条目\n---\n# 子条目\n', encoding='utf-8')
    child_code = child.with_suffix('') / 'code/main.R'
    child_code.parent.mkdir(parents=True)
    child_code.write_text('1+1')
    page.write_text(page.read_text(encoding='utf-8').replace('inputs: []', 'templates: [child]\ninputs: []'), encoding='utf-8')
    git(config.wiki_root.parent, 'add', '.')
    git(config.wiki_root.parent, 'commit', '-qm', 'dependency')
    set_profile(config, 'light')
    git(config.wiki_root.parent, 'sparse-checkout', 'add', '/wiki/methods/example/')
    assert not child_code.exists()
    fetch_assets(config, 'example')
    assert child_code.is_file()


def test_show_in_light_reports_not_checked_instead_of_invalid(checkout):
    from rwiki.asset_checkout import set_profile
    from rwiki.finder import show, format_show
    config, page, _ = checkout
    set_profile(config, 'light')
    detail = show(config, 'example')
    assert detail['evidence_state'] == 'not_checked'
    assert detail['implementations'] == []
    assert 'not_checked' in format_show(detail)

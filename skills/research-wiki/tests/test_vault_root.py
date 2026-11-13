"""vault 根的查找顺序：RWIKI_VAULT_ROOT → config.json 的 github.vault_root → DEV_ROOT.parent。"""
import json

import pytest

import conftest
from conftest import find_vault_root


def make_vault(path):
    (path / "知识库").mkdir(parents=True)
    (path / "知识库/AGENTS.md").write_text("rules", encoding="utf-8")
    return path


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """把 DEV_ROOT、配置候选都指到 tmp_path，互不干扰。"""
    dev = tmp_path / "dev"
    dev.mkdir()
    monkeypatch.delenv("RWIKI_VAULT_ROOT", raising=False)
    monkeypatch.setattr(conftest, "DEV_ROOT", dev)
    monkeypatch.setattr(conftest, "vault_config_candidates", lambda: [tmp_path / "config.json"])
    return tmp_path


def test_env_var_wins(isolated, monkeypatch):
    env_vault = make_vault(isolated / "env-vault")
    make_vault(isolated / "cfg-vault")
    (isolated / "config.json").write_text(json.dumps({"github": {"vault_root": str(isolated / "cfg-vault")}}),
                                          encoding="utf-8")
    monkeypatch.setenv("RWIKI_VAULT_ROOT", str(env_vault))
    assert find_vault_root() == env_vault


def test_env_var_pointing_nowhere_is_an_error(isolated, monkeypatch):
    monkeypatch.setenv("RWIKI_VAULT_ROOT", str(isolated / "missing"))
    with pytest.raises(pytest.fail.Exception, match="RWIKI_VAULT_ROOT"):
        find_vault_root()


def test_config_vault_root_used(isolated):
    cfg_vault = make_vault(isolated / "cfg-vault")
    (isolated / "config.json").write_text(json.dumps({"github": {"vault_root": str(cfg_vault)}}), encoding="utf-8")
    assert find_vault_root() == cfg_vault


def test_dev_parent_fallback(isolated):
    make_vault(isolated)  # DEV_ROOT.parent == isolated
    assert find_vault_root() == isolated


def test_config_beats_dev_parent(isolated):
    make_vault(isolated)
    cfg_vault = make_vault(isolated / "cfg-vault")
    (isolated / "config.json").write_text(json.dumps({"github": {"vault_root": str(cfg_vault)}}), encoding="utf-8")
    assert find_vault_root() == cfg_vault


def test_config_pointing_nowhere_falls_back(isolated):
    make_vault(isolated)
    (isolated / "config.json").write_text(json.dumps({"github": {"vault_root": str(isolated / "nope")}}),
                                          encoding="utf-8")
    assert find_vault_root() == isolated


def test_fixture_skips_when_no_vault(monkeypatch):
    monkeypatch.setattr(conftest, "find_vault_root", lambda: None)
    with pytest.raises(pytest.skip.Exception):
        conftest.vault_root.__wrapped__()


def test_none_found_returns_none(isolated):
    (isolated / "config.json").write_text("{not json", encoding="utf-8")
    assert find_vault_root() is None


def test_config_candidates_include_main_checkout():
    # 两种布局的本机 config.json 都被忽略；worktree 可回到主检出的配置。
    names = [p.as_posix() for p in conftest.vault_config_candidates()]
    assert names and all(name.endswith(("skills/research-wiki/config.json", "staged/research-wiki/config.json")) for name in names)


@pytest.mark.parametrize('via_env', [True, False])
def test_canonical_vault_detected(isolated, monkeypatch, via_env):
    root = isolated / 'canonical'
    (root / 'wiki').mkdir(parents=True)
    (root / 'wiki/AGENTS.md').write_text('rules', encoding='utf-8')
    if via_env:
        monkeypatch.setenv('RWIKI_VAULT_ROOT', str(root))
    else:
        (isolated / 'config.json').write_text(json.dumps({'github': {'vault_root': str(root)}}), encoding='utf-8')
    assert find_vault_root() == root

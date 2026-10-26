import subprocess

import pytest

from conftest import commit_file, git_run, install_test_hook, write_config
from rwiki.config import load_config
from rwiki.errors import WikiError
from rwiki.ghflow import write_meta
from rwiki.pages import write_page
from rwiki.push_guard import load_rules, parse_allow, pre_push, scan, sync_ignore

ZERO = "0" * 40


def method(root, page_id, license_id):
    write_page(root / "methods" / f"{page_id}.md", {"type": "method", "id": page_id, "license": license_id}, "")


def test_sync_ignore_is_idempotent_and_keeps_outside_bytes(tmp_path):
    root = tmp_path / "wiki"
    method(root, "scp", "GPL-3")
    method(root, "mit", "MIT")
    before, after = b"**/__pycache__/\r\n.obsidian/\r\n", b"# \xe4\xbd\x9c\xe8\x80\x85\xe8\xa1\x8c\nkeep.me"
    (root / ".gitignore").write_bytes(before)
    assert sync_ignore(root) is True
    data = (root / ".gitignore").read_bytes()
    assert data.startswith(before)
    assert b"/methods/scp/code/\n/methods/scp/source/\n" in data and b"mit" not in data
    assert sync_ignore(root) is False
    (root / ".gitignore").write_bytes(data + after)
    method(root, "mit", "AGPL-3.0")
    assert sync_ignore(root) is True
    data = (root / ".gitignore").read_bytes()
    assert data.startswith(before) and data.endswith(after)
    assert b"/methods/mit/code/" in data
    assert sync_ignore(root) is False


def test_sync_ignore_without_gpl_methods_leaves_file_alone(tmp_path):
    root = tmp_path / "wiki"
    method(root, "mit", "MIT")
    (root / ".gitignore").write_bytes(b"x\n")
    assert sync_ignore(root) is False
    assert (root / ".gitignore").read_bytes() == b"x\n"


@pytest.mark.parametrize("text", ["gallery 画廊/**  # 不允许", "gpl-path **  # 不允许", "abs-path docs/**",
                                  "abs-path docs/**  #   ", "size  # 缺 glob"])
def test_invalid_allow_rules_are_errors(git_pair, tmp_path, text):
    with pytest.raises(WikiError):
        parse_allow(text)
    (git_pair.work / ".push-guard-allow").write_text(text + "\n", encoding="utf-8")
    config = load_config(write_config(tmp_path / "c.json", tmp_path / "no-wiki"))
    with pytest.raises(WikiError, match="push-guard-allow"):
        load_rules(config, git_pair.work)


def push(work, branch):
    return subprocess.run(["git", "-C", str(work), "push", "origin", branch],
                          capture_output=True, text=True, encoding="utf-8")


def test_hook_refuses_legacy_branches(git_pair, tmp_path):
    work = git_pair.work
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki")
    rules = load_rules(load_config(config_path), work)
    sha = git_run(work, "rev-parse", "HEAD").strip()
    assert pre_push(work, "origin", f"refs/heads/legacy/master {sha} refs/heads/legacy/master {ZERO}\n", rules) == 1
    install_test_hook(work, config_path)
    git_run(work, "branch", "legacy/master")
    result = push(work, "legacy/master")
    assert result.returncode != 0 and "legacy" in result.stderr
    assert git_run(work, "ls-remote", "origin", "refs/heads/legacy/master") == ""


def test_local_gate_blocks_main_and_allows_new_long_branch(git_pair, tmp_path, monkeypatch):
    work = git_pair.work
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki")
    rules = load_rules(load_config(config_path), work)
    write_meta(work, {"protection": "local"})
    base = git_run(work, "rev-parse", "origin/main").strip()
    git_run(work, "checkout", "-q", "-b", "ingest/scp-wave3")
    assert pre_push(work, "origin", f"refs/heads/ingest/scp-wave3 {base} refs/heads/ingest/scp-wave3 {ZERO}\n",
                    rules) == 0
    newer = commit_file(work, "notes.md", "x\n")
    assert pre_push(work, "origin", f"refs/heads/main {newer} refs/heads/main {base}\n", rules) == 1
    assert pre_push(work, "origin", f"refs/heads/ingest/other {newer} refs/heads/ingest/other {ZERO}\n",
                    rules) == 1
    monkeypatch.setenv("RWIKI_BOOTSTRAP", "1")
    assert pre_push(work, "origin", f"refs/heads/main {newer} refs/heads/main {base}\n", rules) == 0
    monkeypatch.delenv("RWIKI_BOOTSTRAP")
    install_test_hook(work, config_path)
    git_run(work, "checkout", "-q", "main")
    git_run(work, "merge", "-q", "--ff-only", "ingest/scp-wave3")
    result = push(work, "main")
    assert result.returncode != 0 and "gh merge" in result.stderr
    assert git_run(work, "rev-parse", "origin/main").strip() == base
    git_run(work, "branch", "project/new", base)
    assert push(work, "project/new").returncode == 0
    # 未进入门禁模式（无元数据）的仓库照常推送 main。
    (work / ".git" / "rwiki-branches.json").unlink()
    assert push(work, "main").returncode == 0


def test_project_dir_files_are_blocked(git_pair, tmp_path):
    work = git_pair.work
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki")
    rules = load_rules(load_config(config_path), work)
    install_test_hook(work, config_path)
    git_run(work, "checkout", "-q", "-b", "task/x-P1-y")
    sha = commit_file(work, "课题/wiki-use/_project/raw.csv", "a,b\n")
    assert [(item["rule"], item["path"]) for item in scan(work, "origin/main..HEAD", rules)] == [
        ("project-data", "课题/wiki-use/_project/raw.csv")]
    assert pre_push(work, "origin", f"refs/heads/task/x-P1-y {sha} refs/heads/task/x-P1-y {ZERO}\n", rules) == 1
    result = push(work, "task/x-P1-y")
    assert result.returncode != 0 and "project-data" in result.stderr
    assert git_run(work, "ls-remote", "origin", "refs/heads/task/x-P1-y") == ""

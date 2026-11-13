import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from conftest import (commit_file, fake_repo_entry, gh_writes, git_init, git_init_bare, git_run,
                      run_wiki, write_config)
from rwiki.config import load_config
from rwiki.errors import WikiError
from rwiki.ghflow import LABELS, LEGACY_BRANCH, bootstrap, read_meta

NAMES = {"dev": "tester/jjd-wiki-dev", "vault": "tester/jjd-wiki"}


@dataclass
class Fresh:
    config: object
    config_path: Path
    repos: dict
    remotes: dict


def write_repo_files(repo, ignore):
    (repo / ".gitignore").write_text(ignore, encoding="utf-8", newline="\n")
    (repo / ".gitattributes").write_text("* -text\n", encoding="utf-8", newline="\n")
    (repo / ".push-guard-allow").write_text("", encoding="utf-8")
    (repo / ".github").mkdir()
    (repo / ".github/pull_request_template.md").write_text("## 关联 Issue\n", encoding="utf-8", newline="\n")


@pytest.fixture
def fresh(tmp_path, fake_gh, monkeypatch):
    """尚未 bootstrap 的两个仓库：都在 master 上、没有 origin；GitHub 上两仓库都不存在。"""
    monkeypatch.delenv("RWIKI_BOOTSTRAP", raising=False)
    dev = git_init(tmp_path / "dev", "master")
    commit_file(dev, "README.md", "# dev\n", "feat: 初始")
    commit_file(dev, "codex/run.jsonl", "E:\\research-wiki\\x\n", "chore: 运行记录")
    commit_file(dev, "staged/research-wiki/config.json", '{"wiki_root": "E:/w"}\n', "chore: 本机配置")
    write_repo_files(dev, "codex/\nstaged/research-wiki/config.json\n")
    git_run(dev, "add", ".gitignore", ".gitattributes", ".push-guard-allow", ".github")
    git_run(dev, "commit", "-q", "-m", "chore(repo): 仓库文件")
    vault = git_init(tmp_path / "vault", "master")
    wiki = vault / "知识库"
    for directory in ("layouts", "templates", "methods", "interfaces", "chart-types", "projects"):
        (wiki / directory).mkdir(parents=True)
    (wiki / "log.md").write_text("# 操作日志\n", encoding="utf-8", newline="\n")
    commit_file(vault, "画廊/a/meta.json", "{}\n", "save: 画廊")
    commit_file(vault, "知识库/log.md", "# 操作日志\n", "save: 日志")
    write_repo_files(vault, "/画廊/\n/开发/\n")
    remotes = {}
    for key in ("dev", "vault"):
        remotes[key] = tmp_path / f"{key}.git"
        git_init_bare(remotes[key])
    state = fake_gh.state()
    state.update(repos={}, remote_map={str(remotes[key]): NAMES[key] for key in remotes})
    fake_gh.write(state)
    (tmp_path / "gallery").mkdir()
    config_path = write_config(tmp_path / "config.json", wiki, github={
        "owner": "tester", "dev_root": str(dev), "vault_root": str(vault),
        "dev_url": str(remotes["dev"]), "vault_url": str(remotes["vault"])})
    return Fresh(load_config(config_path), config_path, {"dev": dev, "vault": vault}, remotes)


def branches(repo):
    return git_run(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()


def remote_writes(calls):
    return [call for call in calls if {"create", "add", "set", "PUT"} & set(call)]


def test_without_confirm_only_reads(fresh, fake_gh):
    result = run_wiki(fresh.repos["vault"], "--config", str(fresh.config_path), "gh", "bootstrap")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["confirm"] is False and report["blockers"] == []
    auth = report["authorization"]
    assert auth["account"] == "tester" and auth["owner"] == "tester"
    assert {key: (value["name"], value["private"], value["exists"]) for key, value in auth["repos"].items()} == {
        "dev": (NAMES["dev"], True, False), "vault": (NAMES["vault"], True, False)}
    assert auth["repos"]["dev"]["pending"] == {"mode": "replay", "commits": 4, "guard_findings": 0}
    assert auth["repos"]["vault"]["pending"]["mode"] == "snapshot"
    assert gh_writes(fake_gh) == [] and fake_gh.state()["repos"] == {}
    for repo in fresh.repos.values():
        assert branches(repo) == ["master"] and not (repo / ".git/hooks/pre-push").exists()
        assert not (repo / ".git/rwiki-branches.json").exists()


def test_confirm_builds_main_pushes_and_enters_local_gate_on_403(fresh, fake_gh):
    dev, vault = fresh.repos["dev"], fresh.repos["vault"]
    result = bootstrap(fresh.config, True, fresh.config_path)
    assert result["deploy_key"] == "created"
    for key, repo in fresh.repos.items():
        assert branches(repo) == [LEGACY_BRANCH, "main"]
        assert git_run(repo, "symbolic-ref", "HEAD").strip() == "refs/heads/main"
        assert git_run(repo, "ls-remote", "origin", "refs/heads/main").split()[0] == git_run(
            repo, "rev-parse", "main").strip()
        assert git_run(repo, "ls-remote", "origin", f"refs/heads/{LEGACY_BRANCH}") == ""
        assert "gh guard --pre-push" in (repo / ".git/hooks/pre-push").read_text(encoding="utf-8")
        assert read_meta(repo)["protection"] == "local" and result["repos"][key]["protection"] == "local"
        remote = fake_gh.state()["repos"][NAMES[key]]
        assert remote["visibility"] == "PRIVATE"
        assert {label["name"] for label in remote["labels"]} == set(LABELS)
        assert git_run(repo, "status", "--porcelain") == ""
    assert result["repos"]["dev"]["replayed"] == 4 and git_run(dev, "rev-list", "--count", "main").strip() == "4"
    assert "Legacy-Commit: " in git_run(dev, "log", "-1", "--format=%B", "main")
    assert git_run(vault, "rev-list", "--count", "main").strip() == "1"
    for path in (dev / "codex/run.jsonl", dev / "staged/research-wiki/config.json", vault / "画廊/a/meta.json"):
        assert path.is_file()
    assert not {"codex/run.jsonl", "staged/research-wiki/config.json"} & set(
        git_run(dev, "ls-tree", "-r", "--name-only", "origin/main").split())
    state = fake_gh.state()
    assert [(key["title"], key["read_only"]) for key in state["repos"][NAMES["dev"]]["deploy_keys"]] == [
        ("rwiki-vault-ci", True)]
    # gh 2.103：deploy-key add 默认只读，不传已移除的 --read-only，也不传 --allow-write。
    [added] = [call for call in fake_gh.calls() if call[:3] == ["repo", "deploy-key", "add"]]
    assert "--read-only" not in added and "--allow-write" not in added
    assert state["repos"][NAMES["vault"]]["secrets"] == ["DEV_DEPLOY_KEY"]
    # 重跑：每步先查后建，不再有远端写操作，分支不变。
    before, heads = len(fake_gh.calls()), {key: git_run(repo, "rev-parse", "main") for key, repo in fresh.repos.items()}
    again = bootstrap(fresh.config, True, fresh.config_path)
    assert again["deploy_key"] == "existing" and remote_writes(fake_gh.calls()[before:]) == []
    assert {key: git_run(repo, "rev-parse", "main") for key, repo in fresh.repos.items()} == heads
    # v2（2026-10-27）：本地门禁不再拒绝直接推送 main；hook 只做内容扫描。
    newer = commit_file(vault, "知识库/notes.md", "x\n", "docs: 直接改 main")
    pushed = subprocess.run(["git", "-C", str(vault), "push", "origin", "main"], capture_output=True, text=True,
                            encoding="utf-8")
    assert pushed.returncode == 0, pushed.stderr
    assert git_run(vault, "ls-remote", "origin", "refs/heads/main").split()[0] == newer


def test_confirm_configures_remote_protection_when_supported(fresh, fake_gh):
    fake_gh.update(protection_status=200)
    result = bootstrap(fresh.config, True, fresh.config_path)
    for key, repo in fresh.repos.items():
        assert result["repos"][key]["protection"] == "github" and read_meta(repo)["protection"] == "github"
        assert fake_gh.state()["repos"][NAMES[key]]["protected"] == ["main"]
    before = len(fake_gh.calls())
    again = bootstrap(fresh.config, True, fresh.config_path)
    assert all(value["protection"] == "github" for value in again["repos"].values())
    assert remote_writes(fake_gh.calls()[before:]) == []


def test_non_private_remote_blocks_before_any_change(fresh, fake_gh):
    state = fake_gh.state()
    state["repos"][NAMES["dev"]] = fake_repo_entry("PUBLIC")
    fake_gh.write(state)
    with pytest.raises(WikiError, match="PUBLIC"):
        bootstrap(fresh.config, True, fresh.config_path)
    for key, repo in fresh.repos.items():
        assert branches(repo) == ["master"]
        assert git_run(repo, "remote") == "" and git_run(fresh.remotes[key], "for-each-ref") == ""
    assert gh_writes(fake_gh) == []
    result = run_wiki(fresh.repos["vault"], "--config", str(fresh.config_path), "gh", "bootstrap")
    assert result.returncode == 1 and any("PUBLIC" in line for line in json.loads(result.stdout)["blockers"])


def test_missing_repo_files_abort_before_rename(fresh, fake_gh):
    (fresh.repos["vault"] / ".push-guard-allow").unlink()
    with pytest.raises(WikiError, match=r"vault.*\.push-guard-allow"):
        bootstrap(fresh.config, True, fresh.config_path)
    assert all(branches(repo) == ["master"] for repo in fresh.repos.values())
    assert gh_writes(fake_gh) == []

import shutil
from pathlib import Path

import pytest

from conftest import commit_count, git_run
from rwiki.config import load_config
from rwiki.errors import WikiError
from rwiki.ghflow import is_junction, read_meta, start_batch, start_task
from rwiki.lint import lint
from rwiki.pages import write_page
from rwiki.push_guard import sync_ignore
from rwiki.store import save
from rwiki.writer_lock import lock_path, read_lock

BATCH = "scp-wave3"


def vault_issues(gh_repos) -> list[dict]:
    return gh_repos.gh.state()["repos"]["tester/jjd-wiki"]["issues"]


def add_gpl_method(gh_repos):
    """GPL 方法页 + 托管块入库并推到 origin/main；源码只在主检出磁盘上（被忽略）。"""
    wiki, vault = gh_repos.config.wiki_root, gh_repos.vault
    (wiki / "methods/scp.md").write_text("---\ntype: method\nid: scp\ntitle: SCP\nlicense: GPL-3\n---\n# SCP\n",
                                         encoding="utf-8", newline="\n")
    sync_ignore(wiki)
    write_page(wiki / "projects/p.md", {"type": "project", "slug": "p", "title": "课题", "templates": []},
               "# 课题\n\n源码 [[methods/scp/code/run.R]]，许可 [[methods/scp/source/LICENSE.md]]\n")
    git_run(vault, "add", "-A")
    git_run(vault, "commit", "-q", "-m", "gpl method")
    git_run(vault, "push", "-q", "origin", "main")
    (wiki / "methods/scp/code").mkdir(parents=True)
    (wiki / "methods/scp/source").mkdir()
    (wiki / "methods/scp/code/run.R").write_text("x <- 1\n", encoding="utf-8")
    (wiki / "methods/scp/source/LICENSE.md").write_text("许可证文本\n", encoding="utf-8")
    assert git_run(vault, "status", "--porcelain") == ""


def test_two_agents_get_separate_worktrees_and_locks(gh_repos, monkeypatch):
    config = gh_repos.config
    start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    first = start_task(config, BATCH, "P2", "harmony", "整合 harmony", True)
    monkeypatch.setenv("RWIKI_AGENT", "claude")
    second = start_task(config, BATCH, "P3", "scvi", "整合 scvi", True)
    a, b = Path(first["checkout"]), Path(second["checkout"])
    assert a.parent == b.parent == gh_repos.worktrees and a != b
    assert a.name == "task__scp-wave3-P2-harmony"
    assert lock_path(a) != lock_path(b) != lock_path(gh_repos.vault)
    assert read_lock(a) | {"pid": 0, "timestamp": ""} == {
        "agent": "codex", "branch": "task/scp-wave3-P2-harmony", "pid": 0, "timestamp": ""}
    assert read_lock(b)["agent"] == "claude" and read_lock(gh_repos.vault) is None
    assert git_run(gh_repos.vault, "branch", "--show-current").strip() == "main"
    assert Path(first["RWIKI_WIKI_ROOT"]) == a / "知识库"
    issues = vault_issues(gh_repos)
    assert [(i["number"], i["milestone"], i["labels"]) for i in issues] == [
        (first["issue"], f"ingest/{BATCH}", ["type:ingest", "stage:P2", "status:进行中"]),
        (second["issue"], f"ingest/{BATCH}", ["type:ingest", "stage:P3", "status:进行中"])]
    assert "<!-- rwiki-task: branch=task/scp-wave3-P2-harmony batch=scp-wave3 stage=P2 -->" in issues[0]["body"]
    # 每个 Agent 只能在自己的 worktree 写入，提交带 Issue trailer。
    for agent, result, other in (("codex", first, b), ("claude", second, a)):
        monkeypatch.setenv("RWIKI_AGENT", agent)
        wiki = Path(result["RWIKI_WIKI_ROOT"])
        (wiki / f"{agent}.md").write_text(f"{agent}\n", encoding="utf-8")
        save(load_config(gh_repos.config_path, wiki), f"{agent} 写入")
        assert f"Issue: #{result['issue']}" in git_run(wiki, "log", "-1", "--format=%B")
        (other / "知识库" / f"{agent}-越权.md").write_text("x\n", encoding="utf-8")
        with pytest.raises(WikiError, match="写入锁由"):
            save(load_config(gh_repos.config_path, other / "知识库"), "越权")
        (other / "知识库" / f"{agent}-越权.md").unlink()


def test_main_checkout_carries_only_wiki_changes(gh_repos, monkeypatch):
    config, vault, fake = gh_repos.config, gh_repos.vault, gh_repos.gh
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    start_batch(config, "project", "glaucoma", "青光眼课题", "vault")
    (config.wiki_root / "log.md").write_text("# 操作日志\n作者在 Obsidian 的编辑\n", encoding="utf-8")
    (vault / "文档/说明.md").write_text("# 说明\n草稿\n", encoding="utf-8")
    with pytest.raises(WikiError) as error:
        start_task(config, "glaucoma", "P1", "survey", "文献调研", False)
    assert "文档/说明.md" in str(error.value) and "知识库/log.md" not in str(error.value)
    assert vault_issues(gh_repos) == [] and read_lock(vault) is None
    assert git_run(vault, "branch", "--list", "task/*") == ""
    git_run(vault, "checkout", "--", "文档/说明.md")
    result = start_task(config, "glaucoma", "P1", "survey", "文献调研", False)
    assert git_run(vault, "branch", "--show-current").strip() == "task/glaucoma-P1-survey"
    assert "作者在 Obsidian 的编辑" in (config.wiki_root / "log.md").read_text(encoding="utf-8")
    assert read_lock(vault)["branch"] == "task/glaucoma-P1-survey" and result["checkout"] == str(vault)
    assert "RWIKI_WIKI_ROOT" not in result
    assert read_meta(vault)["tasks"]["task/glaucoma-P1-survey"]["issue"] == result["issue"]
    count = commit_count(vault)
    save(config, "带入作者编辑")
    assert commit_count(vault) == count + 1
    assert "Issue: #1" in git_run(vault, "log", "-1", "--format=%B")
    assert len([call for call in fake.calls() if call[:2] == ["issue", "create"]]) == 1


def test_rerun_after_failure_does_not_duplicate_issue(gh_repos, monkeypatch):
    config = gh_repos.config
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    blocker = gh_repos.worktrees / "task__scp-wave3-P2-harmony"
    blocker.mkdir(parents=True)
    (blocker / "占位.txt").write_text("x\n", encoding="utf-8")
    with pytest.raises(WikiError, match="worktree"):
        start_task(config, BATCH, "P2", "harmony", "整合 harmony", True)
    assert len(vault_issues(gh_repos)) == 1
    shutil.rmtree(blocker)
    result = start_task(config, BATCH, "P2", "harmony", "整合 harmony", True)
    again = start_task(config, BATCH, "P2", "harmony", "整合 harmony", True)
    assert result == again and len(vault_issues(gh_repos)) == 1
    assert read_lock(Path(result["checkout"]))["agent"] == "codex"


def test_worktree_links_gpl_dirs_readably_and_invisibly(gh_repos, monkeypatch):
    config, vault = gh_repos.config, gh_repos.vault
    add_gpl_method(gh_repos)
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    result = start_task(config, BATCH, "P2", "harmony", "整合 harmony", True)
    checkout, wiki = Path(result["checkout"]), Path(result["RWIKI_WIKI_ROOT"])
    assert read_meta(vault)["tasks"]["task/scp-wave3-P2-harmony"]["junctions"] == [
        "知识库/methods/scp/code", "知识库/methods/scp/source"]
    assert is_junction(wiki / "methods/scp/code") and is_junction(wiki / "methods/scp/source")
    assert (wiki / "methods/scp/code/run.R").read_text(encoding="utf-8") == "x <- 1\n"
    assert git_run(checkout, "status", "--porcelain", "--ignored=no") == ""
    assert git_run(checkout, "status", "--porcelain", "--untracked-files=all") == ""
    in_worktree = lint(load_config(gh_repos.config_path, wiki))
    assert not [line for line in in_worktree if line.startswith("ERROR ") and "methods/scp/" in line]
    assert sorted(in_worktree) == sorted(lint(config))

import shutil
import subprocess
import sys
import time

import pytest

from conftest import SKILL_ROOT, git_run
from rwiki import ghflow
from rwiki.errors import WikiError
from rwiki.ghflow import merge, read_meta
from test_ghflow_merge import TASK, open_task_pr, pass_review, tree_hashes, vault_state
from test_ghflow_start_task import add_gpl_method


def interrupted_merge(gh_repos, monkeypatch, tmp_path, legacy=False):
    """PR 已在 GitHub 合并、本地收尾一步未做（模拟收尾前中断），返回 (PR 号, 检出, Issue 号, GPL 目录, 哈希)。"""
    add_gpl_method(gh_repos, legacy=legacy)
    gpl = gh_repos.config.wiki_root / "methods/scp"
    before = tree_hashes(gpl)
    # A legacy PR was prepared before the default tracking policy changed.
    with monkeypatch.context() as old_policy:
        if legacy:
            old_policy.setattr(ghflow.push_guard, "sync_ignore", lambda root: False)
        pr, checkout, issue = open_task_pr(gh_repos, monkeypatch, tmp_path)
        pass_review(gh_repos, checkout, pr, tmp_path)

    def interrupted(*_args):
        raise KeyboardInterrupt

    with monkeypatch.context() as patch:
        patch.setattr(ghflow, "after_task_merge", interrupted)
        with pytest.raises(KeyboardInterrupt):
            merge(gh_repos.config, gh_repos.vault, pr, None)
    assert vault_state(gh_repos)["prs"][0]["state"] == "MERGED"
    return pr, checkout, issue, gpl, before


def unlink_and_empty(checkout, junctions):
    """模拟 git worktree remove 半途失败：联接已删、文件与 .git 文件已删，目录与登记仍在。"""
    ghflow.unlink_gpl_dirs(checkout, junctions)
    assert not any(ghflow.is_junction(path) for path in checkout.rglob("*"))
    shutil.rmtree(checkout)


def assert_cleaned(gh_repos, pr, checkout, issue, gpl, before):
    assert git_run(gh_repos.vault, "branch", "--list", TASK) == ""
    assert checkout.as_posix() not in git_run(gh_repos.vault, "worktree", "list", "--porcelain")
    assert not checkout.exists()
    task = read_meta(gh_repos.vault)["tasks"][TASK]
    sha = vault_state(gh_repos)["prs"][0]["mergeCommit"]["oid"]
    assert (task["state"], task["pr"], task["merge_sha"]) == ("merged", pr, sha)
    assert next(item for item in vault_state(gh_repos)["issues"] if item["number"] == issue)["state"] == "CLOSED"
    assert tree_hashes(gpl) == before and len(before) == 2


def junctions_of(gh_repos):
    return read_meta(gh_repos.vault)["tasks"][TASK]["junctions"]


def test_rerun_after_worktree_dir_deleted_but_registered(gh_repos, monkeypatch, tmp_path):
    pr, checkout, issue, gpl, before = interrupted_merge(gh_repos, monkeypatch, tmp_path)
    unlink_and_empty(checkout, junctions_of(gh_repos))
    assert checkout.as_posix() in git_run(gh_repos.vault, "worktree", "list", "--porcelain")
    assert merge(gh_repos.config, gh_repos.vault, pr, None)["merged"]
    assert_cleaned(gh_repos, pr, checkout, issue, gpl, before)


def test_rerun_after_worktree_dir_left_empty_without_git_file(gh_repos, monkeypatch, tmp_path):
    pr, checkout, issue, gpl, before = interrupted_merge(gh_repos, monkeypatch, tmp_path)
    unlink_and_empty(checkout, junctions_of(gh_repos))
    (checkout / "知识库/methods").mkdir(parents=True)
    assert checkout.as_posix() in git_run(gh_repos.vault, "worktree", "list", "--porcelain")
    assert merge(gh_repos.config, gh_repos.vault, pr, None)["merged"]
    assert_cleaned(gh_repos, pr, checkout, issue, gpl, before)


def test_rerun_after_git_file_deleted_but_junctions_remain(gh_repos, monkeypatch, tmp_path):
    """worktree remove 删掉了 .git 文件与普通文件，联接还在：重跑只 rmdir 联接，GPL 源码不受影响。"""
    pr, checkout, issue, gpl, before = interrupted_merge(gh_repos, monkeypatch, tmp_path, legacy=True)
    junctions = junctions_of(gh_repos)
    assert junctions
    for path in sorted(checkout.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if any(ghflow.is_junction(parent) for parent in (path, *path.parents)):
            continue
        if path.is_file():
            path.unlink()
    assert not (checkout / ".git").exists()
    assert all(ghflow.is_junction(checkout / relative) for relative in junctions)
    assert merge(gh_repos.config, gh_repos.vault, pr, None)["merged"]
    assert_cleaned(gh_repos, pr, checkout, issue, gpl, before)


def test_upstream_misconfig_does_not_break_fast_forward(gh_repos):
    """branch.main.merge 被配成多个值时 pull --ff-only 会失败；fast_forward_main 不读它。"""
    git_run(gh_repos.vault, "config", "--add", "branch.main.merge", "refs/heads/other")
    ghflow.fast_forward_main(gh_repos.vault)
    assert git_run(gh_repos.vault, "rev-parse", "main") == git_run(gh_repos.vault, "rev-parse", "origin/main")


def test_rerun_after_branch_deleted_but_meta_not_updated(gh_repos, monkeypatch, tmp_path):
    pr, checkout, issue, gpl, before = interrupted_merge(gh_repos, monkeypatch, tmp_path)
    ghflow.unlink_gpl_dirs(checkout, junctions_of(gh_repos))
    git_run(gh_repos.vault, "worktree", "remove", str(checkout))
    git_run(gh_repos.vault, "branch", "-D", TASK)
    assert read_meta(gh_repos.vault)["tasks"][TASK].get("state") is None
    assert merge(gh_repos.config, gh_repos.vault, pr, None)["merged"]
    assert_cleaned(gh_repos, pr, checkout, issue, gpl, before)


def test_branch_not_ancestor_of_merge_commit_is_kept(gh_repos, monkeypatch, tmp_path, capsys):
    pr, checkout, issue, gpl, before = interrupted_merge(gh_repos, monkeypatch, tmp_path)
    (checkout / "文档/追加.md").write_text("# 合并后的追加提交\n", encoding="utf-8")
    git_run(checkout, "add", "文档/追加.md")
    git_run(checkout, "commit", "-q", "-m", "合并后追加")
    capsys.readouterr()
    assert merge(gh_repos.config, gh_repos.vault, pr, None)["merged"]
    assert git_run(gh_repos.vault, "branch", "--list", TASK).strip()
    err = capsys.readouterr().err
    assert "不是合并提交" in err and TASK in err
    assert not checkout.exists() and read_meta(gh_repos.vault)["tasks"][TASK]["state"] == "merged"
    assert tree_hashes(gpl) == before


def run_merge_cli(gh_repos, pr):
    return subprocess.run([sys.executable, "-X", "utf8", str(SKILL_ROOT / "wiki.py"), "--config",
                           str(gh_repos.config_path), "gh", "merge", str(pr)], cwd=gh_repos.vault,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=60)


def test_occupied_worktree_fails_fast_then_rerun_completes(gh_repos, monkeypatch, tmp_path):
    add_gpl_method(gh_repos)
    gpl = gh_repos.config.wiki_root / "methods/scp"
    before = tree_hashes(gpl)
    pr, checkout, issue = open_task_pr(gh_repos, monkeypatch, tmp_path)
    pass_review(gh_repos, checkout, pr, tmp_path)
    holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"], cwd=checkout / "知识库")
    try:
        time.sleep(0.5)
        for _ in range(2):
            started = time.monotonic()
            result = run_merge_cli(gh_repos, pr)
            assert result.returncode != 0 and time.monotonic() - started < 60
            assert checkout.name in result.stderr and "wiki.py gh merge" in result.stderr, result.stderr
            assert git_run(gh_repos.vault, "branch", "--list", TASK).strip()
            assert read_meta(gh_repos.vault)["tasks"][TASK].get("state") is None
    finally:
        holder.kill()
        holder.wait()
    assert tree_hashes(gpl) == before
    assert merge(gh_repos.config, gh_repos.vault, pr, None)["merged"]
    assert_cleaned(gh_repos, pr, checkout, issue, gpl, before)


def test_remove_worktree_error_names_directory(gh_repos, monkeypatch, tmp_path):
    pr, checkout, _ = open_task_pr(gh_repos, monkeypatch, tmp_path)
    (checkout / "未跟踪.txt").write_text("x", encoding="utf-8")
    with pytest.raises(WikiError, match="untracked") as error:
        ghflow.remove_worktree(gh_repos.vault, checkout, pr)
    assert str(checkout) in str(error.value) and (checkout / ".git").is_file()

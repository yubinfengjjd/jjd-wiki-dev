import random

import pytest

from conftest import git_run
from rwiki.errors import WikiError
from rwiki.ghflow import write_meta
from rwiki.store import save, save_policy
from rwiki.writer_lock import acquire, release

SEED = 20261104
ITERATIONS = 100
BRANCHES = ("main", "project/glaucoma", "ingest/scp-wave3", "task/scp-wave3-P2-harmony",
            "task/glaucoma-T3-umap", "master", "feature/x", "legacy-notes")


def test_save_policy_examples():
    # v2（2026-10-27）：main 与批次分支直接提交；只有 task/* 需要写入锁。
    assert [save_policy(b) for b in BRANCHES] == [
        "plain", "plain", "plain", "task", "task", "plain", "plain", "plain"]
    assert save_policy("") == "plain"


def test_save_branch_policy_and_subtree_scope(wiki_repo, monkeypatch):
    """Feature: github-structured-workflow, Property 7: save 分支策略与子树范围"""
    config, _, vault = wiki_repo
    wiki = config.wiki_root
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    write_meta(vault, {"tasks": {b: {"batch": "b", "issue": index + 1} for index, b in enumerate(BRANCHES)
                                 if b.startswith("task/")}})
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        info = f"seed={SEED} iteration={iteration}"
        branch = rng.choice(BRANCHES)
        exists = git_run(vault, "branch", "--list", branch).strip()
        git_run(vault, "checkout", "-q", *(() if exists else ("-b",)), branch)
        if branch.startswith("task/"):
            release(wiki)
            acquire(wiki, "codex", branch)
        if rng.random() < 0.8:
            (wiki / "附件").mkdir(exist_ok=True)
            (wiki / f"附件/{iteration}.txt").write_text(f"第 {iteration} 次\n", encoding="utf-8")
        if rng.random() < 0.6:
            (vault / f"文档/外部 {iteration}.md").write_text("不属于知识库\n", encoding="utf-8")
        head = git_run(vault, "rev-parse", "HEAD").strip()
        log = (wiki / "log.md").read_bytes()
        pending_wiki = git_run(vault, "status", "--porcelain", "--", "知识库").strip()
        if save_policy(branch).startswith("refuse"):
            with pytest.raises(WikiError, match="请先 start-task"):
                save(config, f"save {iteration}")
            assert git_run(vault, "rev-parse", "HEAD").strip() == head, info
            assert (wiki / "log.md").read_bytes() == log, info
            continue
        save(config, f"save {iteration}")
        new_head = git_run(vault, "rev-parse", "HEAD").strip()
        assert git_run(vault, "branch", "--show-current").strip() == branch, info
        if pending_wiki or new_head != head:
            assert new_head != head, info
            changed = git_run(vault, "-c", "core.quotePath=false", "diff-tree", "--no-commit-id", "--name-only",
                              "-r", "-z", head, new_head).split("\0")
            assert all(path.startswith("知识库/") for path in changed if path), f"{info} {changed}"
        assert git_run(vault, "status", "--porcelain", "--", "知识库").strip() == "", info
        outside = list((vault / "文档").glob("外部 *.md"))
        if outside:
            assert git_run(vault, "status", "--porcelain", "--", "文档").strip(), info

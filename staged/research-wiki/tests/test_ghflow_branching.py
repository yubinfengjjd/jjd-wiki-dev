import random

import pytest

from conftest import git_run, gh_writes
from rwiki.errors import WikiError
from rwiki.ghflow import start_batch, start_task
from test_ghflow_naming import EXAMPLES, broken_slug, slug, stage

SEED = 20261108
ITERATIONS = 120
BAD_STAGES = ("P6", "P", "p2", "T", "Px", "P2a", "t3", "阶段", "")


def refs(repo) -> str:
    return git_run(repo, "for-each-ref", "--format=%(refname) %(objectname)")


def test_illegal_names_create_no_branch_or_github_object(gh_repos, monkeypatch):
    """Feature: github-structured-workflow, Property 1: 分支命名往返与拒绝"""
    config, fake = gh_repos.config, gh_repos.gh
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    start_batch(config, "ingest", "base", "基线批次", "vault")
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        info = f"seed={SEED} iteration={iteration}"
        before = {key: refs(repo) for key, repo in (("vault", gh_repos.vault), ("dev", gh_repos.dev))}
        remote_before = git_run(gh_repos.vault, "ls-remote", "origin")
        writes = len(gh_writes(fake))
        if rng.random() < 0.1:
            kind, name, repo_key = rng.choice(("project", "ingest")), f"{slug(rng)}-{iteration}", rng.choice(
                ("vault", "dev"))
            result = start_batch(config, kind, name, f"批次 {iteration}", repo_key)
            titles = [m["title"] for m in fake.state()["repos"][f"tester/research-wiki-{repo_key}"]["milestones"]]
            assert result["branch"] == result["milestone"] == f"{kind}/{name}", info
            assert titles.count(f"{kind}/{name}") == 1, info
            continue
        case = rng.choice(("kind", "batch-name", "task-batch", "task-stage", "task-topic"))
        if case == "kind":
            call = (start_batch, config, rng.choice(("task", "Project", "feature", "")), slug(rng), "标题", "vault")
        elif case == "batch-name":
            call = (start_batch, config, rng.choice(("project", "ingest")), broken_slug(rng, slug(rng)), "标题",
                    rng.choice(("vault", "dev")))
        elif case == "task-batch":
            call = (start_task, config, broken_slug(rng, "base"), stage(rng), slug(rng), "标题", rng.random() < 0.5)
        elif case == "task-stage":
            call = (start_task, config, "base", rng.choice(BAD_STAGES), slug(rng), "标题", rng.random() < 0.5)
        else:
            call = (start_task, config, "base", stage(rng), broken_slug(rng, slug(rng)), "标题", rng.random() < 0.5)
        with pytest.raises(WikiError) as error:
            call[0](*call[1:])
        assert all(example in str(error.value) for example in EXAMPLES), f"{info} {case} {call[1:]!r}"
        after = {key: refs(repo) for key, repo in (("vault", gh_repos.vault), ("dev", gh_repos.dev))}
        assert after == before, f"{info} {case}"
        assert git_run(gh_repos.vault, "ls-remote", "origin") == remote_before, f"{info} {case}"
        assert len(gh_writes(fake)) == writes, f"{info} {case}"
        assert not gh_repos.worktrees.exists(), f"{info} {case}"

"""GitHub Flow（假 gh）：批次只是 Milestone，任务分支从 origin/main 切，PR 直接合入 main；旧批次照旧。"""
from pathlib import Path

import pytest

from conftest import commit_file, git_run, run_cli
from rwiki.errors import WikiError
from rwiki.ghflow import close_batch, finish_task, gate_decision, merge, read_meta, start_batch, start_task, write_meta
from test_ghflow_merge import (BATCH, LONG, PASSING, TASK, VAULT, merge_calls, open_task_pr, pass_review,
                               start_legacy_batch, vault_state)
from test_ghflow_tiered import edit_pr, pr_of

DEV = "tester/jjd-wiki-dev"
HEAD = "a" * 40


def repo_state(gh_repos, name: str) -> dict:
    return gh_repos.gh.state()["repos"][name]


def pr_creates(gh_repos) -> list[tuple[str, str]]:
    calls = [call for call in gh_repos.gh.calls() if call[:2] == ["pr", "create"]]
    return [(call[call.index("--base") + 1], call[call.index("--head") + 1]) for call in calls]


def long_branch_refs(gh_repos, repo: Path) -> str:
    return git_run(repo, "ls-remote", "origin", "refs/heads/ingest/*", "refs/heads/project/*")


def test_full_github_flow_merges_task_into_main(gh_repos, monkeypatch, tmp_path):
    config, vault = gh_repos.config, gh_repos.vault
    assert start_batch(config, "ingest", BATCH, "SCP 第三批", "vault") == {
        "batch": BATCH, "milestone": LONG, "repo": "vault", "flow": "github", "base": "main"}
    info = read_meta(vault)["batches"][BATCH]
    assert info["flow"] == "github" and "branch" not in info
    pr, checkout, issue = open_task_pr(gh_repos, monkeypatch, tmp_path)
    main_sha = git_run(vault, "rev-parse", "origin/main").strip()
    assert git_run(checkout, "merge-base", "HEAD", "origin/main").strip() == main_sha
    assert pr_of(gh_repos, pr)["baseRefName"] == "main"
    issued = next(item for item in vault_state(gh_repos)["issues"] if item["number"] == issue)
    assert issued["milestone"] == LONG
    with pytest.raises(WikiError, match=rf"^Milestone {LONG} 仍有未关闭 Issue") as blocked:
        close_batch(config, BATCH)
    assert f"#{issue} " in str(blocked.value)
    pass_review(gh_repos, checkout, pr, tmp_path)
    result = merge(config, vault, pr, None)
    assert (result["base"], result["branch"]) == ("main", TASK) and len(merge_calls(gh_repos)) == 1
    assert [m["state"] for m in vault_state(gh_repos)["milestones"]] == ["open"]
    closed = close_batch(config, BATCH)
    assert closed == {"batch": BATCH, "milestone": LONG, "state": "closed", "issues": [issue]}
    assert [(m["title"], m["state"]) for m in vault_state(gh_repos)["milestones"]] == [(LONG, "closed")]
    assert read_meta(vault)["batches"][BATCH]["state"] == "closed"
    # 没有长期分支：不推送、不建本地分支、没有到 main 的批次 PR。
    assert pr_creates(gh_repos) == [("main", TASK)]
    assert long_branch_refs(gh_repos, vault) == "" and git_run(vault, "branch", "--list", LONG) == ""
    assert not [call for call in gh_repos.gh.calls()
                if any(a in ("--head", "--base") and b == LONG for a, b in zip(call, call[1:]))]


def test_merge_blocks_until_pr_contains_latest_main(gh_repos, monkeypatch, tmp_path):
    config, vault = gh_repos.config, gh_repos.vault
    pr, checkout, _ = open_task_pr(gh_repos, monkeypatch, tmp_path)
    pass_review(gh_repos, checkout, pr, tmp_path)
    advanced = commit_file(vault, "文档/另一个 PR.md", "# 另一个 PR 已合入\n", "main 前进")
    git_run(vault, "push", "-q", "origin", "main")
    with pytest.raises(WikiError, match="PR 未包含最新 main") as blocked:
        merge(config, vault, pr, "先合入最新 main")
    reason = (f"PR 未包含最新 main（{advanced}）：在任务分支上 merge origin/main 后重新 finish-task，"
              "等 CI 与评审")
    assert reason in str(blocked.value) and merge_calls(gh_repos) == []
    gate = pr_of(gh_repos, pr)["comments"][-1]["body"]
    assert gate.startswith("<!-- rwiki-gate: blocked sha=") and f"- {reason}\n" in gate
    assert "先合入最新 main" in gate
    git_run(checkout, "fetch", "-q", "origin")
    git_run(checkout, "merge", "-q", "--no-edit", "origin/main")
    assert finish_task(config, checkout, None)["pr"] == pr
    edit_pr(gh_repos, pr, headRefOid=git_run(checkout, "rev-parse", "HEAD").strip())  # GitHub 随推送更新 head
    with pytest.raises(WikiError, match="评审已失效") as stale:
        merge(config, vault, pr, None)
    assert "PR 未包含最新 main" not in str(stale.value)
    pass_review(gh_repos, checkout, pr, tmp_path)
    assert merge(config, vault, pr, None)["merged"] and len(merge_calls(gh_repos)) == 1


def test_gate_decision_requires_latest_main_in_every_tier():
    for tier in ("low", "normal", "high"):
        entries = [{"body": f"<!-- codex-review: verdict=pass sha={HEAD} -->"}]
        assert gate_decision(PASSING, entries, HEAD, tier, base_current=True, base_sha="b" * 40) == (True, [])
        assert gate_decision(PASSING, entries, HEAD, tier) == (True, [])
        passed, reasons = gate_decision(PASSING, entries, HEAD, tier, ["命中 x"], base_current=False,
                                        base_sha="b" * 40)
        assert not passed and reasons[0] == f"风险档 {tier}：命中 x"
        assert reasons[1].startswith(f"PR 未包含最新 main（{'b' * 40}）"), tier


def same_batch_in_dev(gh_repos):
    """dev 也有同名批次（本检查之前建的）：dev 元数据与 Milestone。"""
    state = gh_repos.gh.state()
    state["repos"][DEV]["milestones"].append({"number": 1, "title": LONG, "description": "", "state": "open"})
    gh_repos.gh.write(state)
    write_meta(gh_repos.dev, {"batches": {BATCH: {"kind": "ingest", "milestone": 1, "title": "dev 同名",
                                                   "repo": "dev", "flow": "github"}}})


def test_same_batch_in_both_repos_needs_repo(gh_repos, monkeypatch):
    config = gh_repos.config
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    same_batch_in_dev(gh_repos)
    for call in (lambda: start_task(config, BATCH, "T1", "ghflow", "改流程", True),
                 lambda: close_batch(config, BATCH)):
        with pytest.raises(WikiError, match="--repo dev\\|vault"):
            call()
    assert repo_state(gh_repos, VAULT)["issues"] == repo_state(gh_repos, DEV)["issues"] == []
    assert not gh_repos.worktrees.exists()
    started = start_task(config, BATCH, "T1", "ghflow", "改流程", True, "dev")
    issues = repo_state(gh_repos, DEV)["issues"]
    assert [(i["number"], i["milestone"], i["labels"][0]) for i in issues] == [(started["issue"], LONG, "type:code")]
    assert repo_state(gh_repos, VAULT)["issues"] == []
    checkout = Path(started["checkout"])
    assert git_run(checkout, "rev-parse", "HEAD").strip() == git_run(gh_repos.dev, "rev-parse", "origin/main").strip()
    assert read_meta(gh_repos.dev)["tasks"][TASK.replace("P2-harmony", "T1-ghflow")]["repo"] == "dev"
    assert close_batch(config, BATCH, "vault")["state"] == "closed"
    vault_milestones = [(m["title"], m["state"]) for m in repo_state(gh_repos, VAULT)["milestones"]]
    assert vault_milestones == [(LONG, "closed")]
    assert [m["state"] for m in repo_state(gh_repos, DEV)["milestones"]] == ["open"]
    # CLI：--repo 传到 close-batch 与 start-task。
    refused = run_cli(gh_repos.config_path, "gh", "close-batch", BATCH, "--repo", "dev")
    assert refused.returncode == 1 and f"#{started['issue']} 改流程" in refused.stderr, refused.stderr
    ambiguous = run_cli(gh_repos.config_path, "gh", "start-task", BATCH, "T2", "more", "--title", "再改")
    assert ambiguous.returncode == 1 and "--repo" in ambiguous.stderr
    again = run_cli(gh_repos.config_path, "gh", "start-task", BATCH, "T2", "more", "--title", "再改",
                    "--worktree", "--repo", "dev")
    assert again.returncode == 0, again.stderr
    assert len(repo_state(gh_repos, DEV)["issues"]) == 2 and repo_state(gh_repos, VAULT)["issues"] == []


def test_start_batch_refuses_name_used_in_other_repo(gh_repos):
    config = gh_repos.config
    start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    writes = len(gh_repos.gh.calls())
    for kind in ("ingest", "project"):
        with pytest.raises(WikiError, match="换名") as error:
            start_batch(config, kind, BATCH, "dev 同名", "dev")
        assert "vault" in str(error.value)
    assert repo_state(gh_repos, DEV)["milestones"] == [] and read_meta(gh_repos.dev) == {}
    assert len(gh_repos.gh.calls()) == writes
    assert start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")["milestone"] == LONG
    assert len(repo_state(gh_repos, VAULT)["milestones"]) == 1


def test_legacy_batch_keeps_long_branch_flow(gh_repos, monkeypatch, tmp_path):
    """旧批次（元数据有 branch、没有 flow）：任务从 origin/<长期分支> 切，PR 合入长期分支，close-batch 开到 main 的 PR。"""
    config, vault = gh_repos.config, gh_repos.vault
    gh_repos.gh.update(default_checks=PASSING)
    start_legacy_batch(gh_repos, "ingest", BATCH, "SCP 第三批")
    with pytest.raises(WikiError, match="旧流程"):
        start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    git_run(vault, "switch", "-q", LONG)
    ahead = commit_file(vault, "文档/批次.md", "# 长期分支上的提交\n", "批次前进")
    git_run(vault, "push", "-q", "origin", LONG)
    git_run(vault, "switch", "-q", "main")
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    started = start_task(config, BATCH, "P2", "harmony", "整合 harmony", True)
    checkout = Path(started["checkout"])
    assert git_run(checkout, "rev-parse", "HEAD").strip() == ahead
    commit_file(checkout, "文档/任务.md", "# 任务\n", "任务提交")
    pr = finish_task(config, checkout, None)["pr"]
    assert pr_of(gh_repos, pr)["baseRefName"] == LONG
    pass_review(gh_repos, checkout, pr, tmp_path)
    assert merge(config, vault, pr, None)["base"] == LONG
    batch_pr = close_batch(config, BATCH)
    assert batch_pr["issues"] == [started["issue"]]
    assert pr_creates(gh_repos) == [(LONG, TASK), ("main", LONG)]
    assert [m["state"] for m in vault_state(gh_repos)["milestones"]] == ["open"]

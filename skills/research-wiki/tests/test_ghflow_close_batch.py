import random
import re

import pytest

from rwiki.errors import WikiError
from rwiki.ghflow import close_batch, read_meta, start_batch
from test_ghflow_merge import start_legacy_batch

SEED = 20261109
ITERATIONS = 100
BATCH, BRANCH, VAULT = "scp-wave3", "ingest/scp-wave3", "tester/jjd-wiki"


def random_issues(rng) -> list[dict]:
    return [{"number": number, "title": f"任务 {number}", "body": "", "labels": [], "comments": [],
             "state": rng.choice(("OPEN", "CLOSED")),
             "milestone": BRANCH if rng.random() < 0.8 else "ingest/other",
             "url": f"https://github.com/{VAULT}/issues/{number}"}
            for number in range(1, rng.randint(0, 6) + 1)]


def test_close_batch_opens_pr_only_when_all_issues_closed(gh_repos):
    """Feature: github-structured-workflow, Property 6: close-batch 只在全部关闭时开 PR（旧流程批次）"""
    config, fake = gh_repos.config, gh_repos.gh
    start_legacy_batch(gh_repos, "ingest", BATCH, "SCP 第三批")
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        info = f"seed={SEED} iteration={iteration}"
        state = fake.state()
        repo = state["repos"][VAULT]
        repo["issues"] = random_issues(rng)
        repo["prs"] = []
        fake.write(state)
        mine = [issue for issue in repo["issues"] if issue["milestone"] == BRANCH]
        still_open = {issue["number"] for issue in mine if issue["state"] == "OPEN"}
        if still_open:
            with pytest.raises(WikiError) as error:
                close_batch(config, BATCH)
            reported = {int(number) for number in re.findall(r"^#(\d+) ", str(error.value), re.M)}
            assert reported == still_open, info
            assert fake.state()["repos"][VAULT]["prs"] == [], info
            continue
        result = close_batch(config, BATCH)
        prs = fake.state()["repos"][VAULT]["prs"]
        assert [(pr["number"], pr["baseRefName"], pr["headRefName"]) for pr in prs] == [
            (result["pr"], "main", BRANCH)], info
        assert result["issues"] == sorted(issue["number"] for issue in mine), info
        assert all(f"- #{issue['number']} {issue['title']}" in prs[0]["body"] for issue in mine), info
        assert close_batch(config, BATCH)["pr"] == result["pr"], info
        assert len(fake.state()["repos"][VAULT]["prs"]) == 1, info


def test_github_flow_close_batch_closes_milestone_only_when_all_issues_closed(gh_repos):
    """Feature: lite-gh, Property: GitHub Flow 批次的 close-batch 只在全部关闭时关闭 Milestone、从不开 PR"""
    config, fake = gh_repos.config, gh_repos.gh
    start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        info = f"seed={SEED} iteration={iteration}"
        state = fake.state()
        repo = state["repos"][VAULT]
        repo["issues"] = random_issues(rng)
        for milestone in repo["milestones"]:
            milestone["state"] = "open"
        fake.write(state)
        mine = [issue for issue in repo["issues"] if issue["milestone"] == BRANCH]
        still_open = {issue["number"] for issue in mine if issue["state"] == "OPEN"}
        if still_open:
            with pytest.raises(WikiError) as error:
                close_batch(config, BATCH)
            reported = {int(number) for number in re.findall(r"^#(\d+) ", str(error.value), re.M)}
            assert reported == still_open, info
            assert [m["state"] for m in fake.state()["repos"][VAULT]["milestones"]] == ["open"], info
            continue
        result = close_batch(config, BATCH)
        after = fake.state()["repos"][VAULT]
        assert after["prs"] == [], info
        assert [(m["title"], m["state"]) for m in after["milestones"]] == [(BRANCH, "closed")], info
        assert result["issues"] == sorted(issue["number"] for issue in mine), info
        assert result["milestone"] == BRANCH and "pr" not in result, info
        assert close_batch(config, BATCH)["state"] == "closed", info
        assert read_meta(gh_repos.vault)["batches"][BATCH]["state"] == "closed", info
    assert not [call for call in fake.calls() if call[:2] == ["pr", "create"]]

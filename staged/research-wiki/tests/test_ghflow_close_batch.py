import random
import re

import pytest

from rwiki.errors import WikiError
from rwiki.ghflow import close_batch, start_batch

SEED = 20261109
ITERATIONS = 100
BATCH, BRANCH, VAULT = "scp-wave3", "ingest/scp-wave3", "tester/jjd-wiki"


def test_close_batch_opens_pr_only_when_all_issues_closed(gh_repos):
    """Feature: github-structured-workflow, Property 6: close-batch 只在全部关闭时开 PR"""
    config, fake = gh_repos.config, gh_repos.gh
    start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        info = f"seed={SEED} iteration={iteration}"
        state = fake.state()
        repo = state["repos"][VAULT]
        repo["issues"] = [{"number": number, "title": f"任务 {number}", "body": "", "labels": [], "comments": [],
                           "state": rng.choice(("OPEN", "CLOSED")),
                           "milestone": BRANCH if rng.random() < 0.8 else "ingest/other",
                           "url": f"https://github.com/{VAULT}/issues/{number}"}
                          for number in range(1, rng.randint(0, 6) + 1)]
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

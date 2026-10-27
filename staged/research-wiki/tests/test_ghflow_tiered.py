"""合并门禁按风险档判定（假 gh）：档位在 merge 时按 base 上的规则重算，不信 PR 上的 risk:* 标签。"""
import json

import pytest

from conftest import DEV_ROOT, commit_file, git_run
from rwiki.errors import WikiError
from rwiki.ghflow import OWNER_LABEL, finish_task, merge
from rwiki.risk import load_rules
from test_ghflow_merge import TASK, VAULT, merge_calls, open_task_pr, pass_review, vault_state


def set_rules(gh_repos, **rules):
    """规则提交到 vault 的 main 并推送；长期分支从 origin/main 建，PR 的 base 上即为这份规则。"""
    commit_file(gh_repos.vault, ".github/risk-tiers.json", json.dumps(rules), "risk rules")
    git_run(gh_repos.vault, "push", "-q", "origin", "main")


def pr_of(gh_repos, pr: int) -> dict:
    return next(item for item in vault_state(gh_repos)["prs"] if item["number"] == pr)


def edit_pr(gh_repos, pr: int, labels=(), events=(), **changes):
    state = gh_repos.gh.state()
    item = next(item for item in state["repos"][VAULT]["prs"] if item["number"] == pr)
    item.update(changes)
    item["labels"] = list(dict.fromkeys(item["labels"] + list(labels)))
    item["timeline"] = item["timeline"] + list(events)
    gh_repos.gh.write(state)


def push_commit(gh_repos, checkout, pr: int, relative: str, text: str) -> str:
    """任务分支追加一个提交并推送，PR 的 head 随之更新。"""
    sha = commit_file(checkout, relative, text, f"add {relative}")
    git_run(checkout, "push", "-q", "origin", TASK)
    edit_pr(gh_repos, pr, headRefOid=sha)
    return sha


def committed(sha: str, when: str) -> dict:
    return {"event": "committed", "sha": sha, "committer": {"date": when}}


def approved(when: str) -> dict:
    return {"event": "labeled", "label": {"name": OWNER_LABEL}, "created_at": when}


def risk_labels(gh_repos, pr: int) -> list[str]:
    return [name for name in pr_of(gh_repos, pr)["labels"] if name.startswith("risk:")]


def timeline_calls(gh_repos) -> list[list[str]]:
    return [call for call in gh_repos.gh.calls() if call[0] == "api" and "/timeline" in call[1]]


def test_low_tier_merges_without_review(gh_repos, monkeypatch, tmp_path):
    set_rules(gh_repos, high=[".github/**"], low=["知识库/**"])
    pr, _, _ = open_task_pr(gh_repos, monkeypatch, tmp_path)
    assert risk_labels(gh_repos, pr) == ["risk:low"]
    assert "- 风险档：low（全部 4 个路径命中低风险规则）" in pr_of(gh_repos, pr)["body"]  # save 另写目录、日志
    result = merge(gh_repos.config, gh_repos.vault, pr, None)
    assert result["merged"] and result["tier"] == "low" and len(merge_calls(gh_repos)) == 1


def test_normal_tier_without_review_blocks_and_comments(gh_repos, monkeypatch, tmp_path):
    set_rules(gh_repos, high=[".github/**"], low=["review/**"])
    pr, _, _ = open_task_pr(gh_repos, monkeypatch, tmp_path)
    assert risk_labels(gh_repos, pr) == ["risk:normal"]
    with pytest.raises(WikiError, match="没有 Codex 评审回帖"):
        merge(gh_repos.config, gh_repos.vault, pr, None)
    gate = pr_of(gh_repos, pr)["comments"][-1]["body"]
    assert gate.startswith("<!-- rwiki-gate: blocked sha=") and "\n- 风险档 normal：" in gate
    assert "知识库/harmony 笔记.md 未命中低风险规则" in gate and "等 4 条" in gate
    assert merge_calls(gh_repos) == []


def test_high_tier_requires_fresh_owner_label(gh_repos, monkeypatch, tmp_path):
    set_rules(gh_repos, high=["知识库/**"])
    pr, checkout, _ = open_task_pr(gh_repos, monkeypatch, tmp_path)
    assert risk_labels(gh_repos, pr) == ["risk:high"]
    head = pass_review(gh_repos, checkout, pr, tmp_path)["sha"]
    with pytest.raises(WikiError, match="没有 owner-approved 标签"):
        merge(gh_repos.config, gh_repos.vault, pr, None)
    gate = pr_of(gh_repos, pr)["comments"][-1]["body"]
    assert "\n- 风险档 high：" in gate and "命中高风险规则 知识库/**" in gate
    edit_pr(gh_repos, pr, [OWNER_LABEL], [approved("2026-10-28T01:00:00Z"), committed(head, "2026-10-28T02:00:00Z")])
    with pytest.raises(WikiError, match="已失效"):
        merge(gh_repos.config, gh_repos.vault, pr, None)
    assert merge_calls(gh_repos) == []
    edit_pr(gh_repos, pr, events=[approved("2026-10-28T03:00:00Z")])
    result = merge(gh_repos.config, gh_repos.vault, pr, None)
    assert result["merged"] and result["tier"] == "high"


def test_high_tier_without_owner_requirement_needs_review_and_ci(gh_repos, monkeypatch, tmp_path):
    set_rules(gh_repos, high=["知识库/**"], high_requires_owner=False)
    pr, checkout, _ = open_task_pr(gh_repos, monkeypatch, tmp_path)
    with pytest.raises(WikiError, match="没有 Codex 评审回帖"):
        merge(gh_repos.config, gh_repos.vault, pr, None)
    pass_review(gh_repos, checkout, pr, tmp_path)
    result = merge(gh_repos.config, gh_repos.vault, pr, None)
    assert result["merged"] and result["tier"] == "high" and timeline_calls(gh_repos) == []


def test_added_high_file_rejudges_tier_and_finish_task_updates_label(gh_repos, monkeypatch, tmp_path):
    set_rules(gh_repos, high=["文档/**"], low=["知识库/**"], high_requires_owner=False)
    pr, checkout, _ = open_task_pr(gh_repos, monkeypatch, tmp_path)
    assert risk_labels(gh_repos, pr) == ["risk:low"]
    push_commit(gh_repos, checkout, pr, "文档/新增.md", "# 新增\n")
    with pytest.raises(WikiError, match="风险档 high：文档/新增.md 命中高风险规则 文档/\\*\\*") as blocked:
        merge(gh_repos.config, gh_repos.vault, pr, None)
    assert "没有 Codex 评审回帖" in str(blocked.value)
    assert risk_labels(gh_repos, pr) == ["risk:low"] and merge_calls(gh_repos) == []
    assert finish_task(gh_repos.config, checkout, None)["pr"] == pr
    assert risk_labels(gh_repos, pr) == ["risk:high"]
    body = pr_of(gh_repos, pr)["body"]
    assert "- 风险档：high（文档/新增.md 命中高风险规则 文档/**）" in body and "风险档：low" not in body
    calls = len(gh_repos.gh.calls())
    finish_task(gh_repos.config, checkout, None)
    assert not [call for call in gh_repos.gh.calls()[calls:] if call[:2] == ["pr", "edit"]]


def test_pr_cannot_relax_its_own_rules(gh_repos, monkeypatch, tmp_path):
    set_rules(gh_repos, high=["知识库/**"])
    pr, checkout, _ = open_task_pr(gh_repos, monkeypatch, tmp_path)
    push_commit(gh_repos, checkout, pr, ".github/risk-tiers.json",
                json.dumps({"high": [], "low": ["**"], "high_requires_owner": False}))
    pass_review(gh_repos, checkout, pr, tmp_path)
    with pytest.raises(WikiError, match="没有 owner-approved 标签") as blocked:
        merge(gh_repos.config, gh_repos.vault, pr, None)
    assert "风险档 high" in str(blocked.value) and merge_calls(gh_repos) == []
    assert finish_task(gh_repos.config, checkout, None)["pr"] == pr
    assert risk_labels(gh_repos, pr) == ["risk:high"]


def test_high_requires_owner_must_be_boolean(tmp_path):
    rules = tmp_path / ".github/risk-tiers.json"
    rules.parent.mkdir()
    rules.write_text(json.dumps({"high": [], "low": []}), encoding="utf-8")
    assert load_rules(tmp_path)["high_requires_owner"] is True
    rules.write_text(json.dumps({"high": [], "low": [], "high_requires_owner": "no"}), encoding="utf-8")
    with pytest.raises(WikiError, match="high_requires_owner"):
        load_rules(tmp_path)


def test_dev_rules_waive_owner_confirmation():
    """作者 2026-10-28 明确放弃逐个确认高风险 PR；high 仍需独立评审与 CI。"""
    assert load_rules(DEV_ROOT)["high_requires_owner"] is False

import hashlib
from pathlib import Path

import pytest

from conftest import commit_file, git_run
from rwiki.config import load_config
from rwiki.errors import WikiError
from rwiki.ghflow import close_batch, finish_task, merge, read_meta, review, start_batch, start_task, write_meta
from rwiki.store import save
from rwiki.writer_lock import read_lock
from test_ghflow_start_task import add_gpl_method

BATCH, LONG, VAULT = "scp-wave3", "ingest/scp-wave3", "tester/jjd-wiki"
TASK = "task/scp-wave3-P2-harmony"
PASSING = [{"name": "pytest", "bucket": "pass"}, {"name": "guard", "bucket": "pass"}]


def vault_state(gh_repos) -> dict:
    return gh_repos.gh.state()["repos"][VAULT]


def merge_calls(gh_repos) -> list[list[str]]:
    return [call for call in gh_repos.gh.calls() if call[:2] == ["pr", "merge"]]


def start_legacy_batch(gh_repos, kind, name, title, repo_key="vault"):
    """旧流程批次（T6 之前建的）：从 origin/main 建长期分支并推送，元数据有 branch、没有 flow。"""
    repo = gh_repos.vault if repo_key == "vault" else gh_repos.dev
    start_batch(gh_repos.config, kind, name, title, repo_key)
    branch = f"{kind}/{name}"
    if not git_run(repo, "branch", "--list", branch).strip():
        git_run(repo, "branch", "--no-track", branch, "origin/main")
    git_run(repo, "push", "-q", "origin", branch)
    meta = read_meta(repo)
    info = meta["batches"][name]
    info.pop("flow", None)
    info["branch"] = branch
    write_meta(repo, meta)
    return branch


def open_task_pr(gh_repos, monkeypatch, tmp_path, worktree=True, checks=PASSING, legacy=False):
    """start-batch → start-task → save → finish-task，返回 (PR 号, 检出, Issue 号)；legacy 为旧流程批次。"""
    config = gh_repos.config
    gh_repos.gh.update(default_checks=checks)
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    if legacy:
        start_legacy_batch(gh_repos, "ingest", BATCH, "SCP 第三批")
    else:
        start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    started = start_task(config, BATCH, "P2", "harmony", "整合 harmony", worktree)
    checkout = Path(started["checkout"])
    wiki = checkout / "知识库"
    (wiki / "harmony 笔记.md").write_text("# harmony\n", encoding="utf-8")
    save(load_config(gh_repos.config_path, wiki), "harmony 方法页")
    report = tmp_path / "local-report.md"
    report.write_text("verify-template：通过（本地 R 4.5）\n", encoding="utf-8")
    finished = finish_task(config, checkout, report)
    return finished["pr"], checkout, started["issue"]


def pass_review(gh_repos, checkout, pr, tmp_path, verdict="pass"):
    findings = tmp_path / f"findings-{verdict}.md"
    findings.write_text("- 无阻断问题\n" if verdict == "pass" else "- 缺少适用范围\n", encoding="utf-8")
    return review(gh_repos.config, checkout, pr, verdict, findings)


def tree_hashes(root: Path) -> dict:
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


@pytest.mark.parametrize("legacy, base", [(False, "main"), (True, LONG)])
def test_finish_task_and_review_fill_pr_and_labels(gh_repos, monkeypatch, tmp_path, legacy, base):
    pr, checkout, issue = open_task_pr(gh_repos, monkeypatch, tmp_path, legacy=legacy)
    state = vault_state(gh_repos)
    opened = next(item for item in state["prs"] if item["number"] == pr)
    assert (opened["baseRefName"], opened["headRefName"]) == (base, TASK)
    assert f"Refs #{issue}" in opened["body"] and "verify-template：通过" in opened["body"]
    assert "harmony 方法页" in opened["body"] and "不适用" in opened["body"]
    assert git_run(gh_repos.vault, "ls-remote", "origin", TASK).split()[0] == git_run(checkout, "rev-parse", "HEAD").strip()
    labels = next(item for item in state["issues"] if item["number"] == issue)["labels"]
    assert "status:待评审" in labels and "status:进行中" not in labels
    assert finish_task(gh_repos.config, checkout, None)["pr"] == pr
    assert len(vault_state(gh_repos)["prs"]) == 1
    result = pass_review(gh_repos, checkout, pr, tmp_path, "changes")
    reviewed = next(item for item in vault_state(gh_repos)["prs"] if item["number"] == pr)
    assert reviewed["reviews"][-1]["body"].startswith(f"<!-- codex-review: verdict=changes sha={result['sha']} -->")
    assert "缺少适用范围" in reviewed["reviews"][-1]["body"]
    labels = next(item for item in vault_state(gh_repos)["issues"] if item["number"] == issue)["labels"]
    assert "status:需修改" in labels and "status:待评审" not in labels


def test_finish_task_refuses_uncommitted_tracked_changes(gh_repos, monkeypatch, tmp_path):
    config = gh_repos.config
    monkeypatch.setenv("RWIKI_AGENT", "codex")
    start_batch(config, "ingest", BATCH, "SCP 第三批", "vault")
    checkout = Path(start_task(config, BATCH, "P2", "harmony", "整合 harmony", True)["checkout"])
    (checkout / "文档/说明.md").write_text("# 说明\n未提交\n", encoding="utf-8")
    with pytest.raises(WikiError, match="文档/说明.md"):
        finish_task(config, checkout, None)
    assert git_run(gh_repos.vault, "ls-remote", "origin", TASK) == ""
    assert vault_state(gh_repos)["prs"] == []


def test_gate_failure_blocks_merge_and_records_reason(gh_repos, monkeypatch, tmp_path):
    pr, checkout, issue = open_task_pr(gh_repos, monkeypatch, tmp_path,
                                       checks=[{"name": "pytest", "bucket": "fail"}])
    with pytest.raises(WikiError, match="没有 Codex 评审回帖"):
        merge(gh_repos.config, checkout, pr, "修复 pytest 失败后重跑")
    pass_review(gh_repos, checkout, pr, tmp_path)
    with pytest.raises(WikiError, match=r"pytest\(fail\)"):
        merge(gh_repos.config, checkout, pr, None)
    with pytest.raises(WikiError, match=r"pytest\(fail\)"):
        merge(gh_repos.config, checkout, pr, None)
    state = gh_repos.gh.state()
    opened = next(item for item in state["repos"][VAULT]["prs"] if item["number"] == pr)
    gates = [comment["body"] for comment in opened["comments"]]
    head = opened["headRefOid"]
    assert len(gates) == 2 and all(body.startswith(f"<!-- rwiki-gate: blocked sha={head} -->") for body in gates)
    assert "修复 pytest 失败后重跑" in gates[0] and "待补" in gates[1]
    # CI 修好后又有新提交：先前的评审失效（merge 要按新 head 重算档位，提交须真实存在于远端）。
    opened["checks"] = PASSING
    opened["headRefOid"] = commit_file(checkout, "文档/追加.md", "# 追加\n", "追加")
    git_run(checkout, "push", "-q", "origin", TASK)
    gh_repos.gh.write(state)
    with pytest.raises(WikiError, match="评审已失效"):
        merge(gh_repos.config, checkout, pr, None)
    assert merge_calls(gh_repos) == [] and opened["state"] == vault_state(gh_repos)["prs"][0]["state"] == "OPEN"
    assert next(item for item in vault_state(gh_repos)["issues"] if item["number"] == issue)["state"] == "OPEN"
    assert read_lock(checkout)["agent"] == "codex" and checkout.is_dir()


def test_merge_cleans_up_worktree_without_touching_gpl_sources(gh_repos, monkeypatch, tmp_path):
    add_gpl_method(gh_repos)
    gpl = gh_repos.config.wiki_root / "methods/scp"
    before = tree_hashes(gpl)
    pr, checkout, issue = open_task_pr(gh_repos, monkeypatch, tmp_path)
    assert (checkout / "知识库/methods/scp/code/run.R").is_file()
    head = pass_review(gh_repos, checkout, pr, tmp_path)["sha"]
    result = merge(gh_repos.config, gh_repos.vault, pr, None)
    assert result["merged"] and result["base"] == "main"
    assert merge_calls(gh_repos) == [["pr", "merge", str(pr), "--merge", "--match-head-commit", head,
                                      "--delete-branch", "--repo", VAULT]]
    closed = next(item for item in vault_state(gh_repos)["issues"] if item["number"] == issue)
    assert closed["state"] == "CLOSED" and [l for l in closed["labels"] if l.startswith("status:")] == ["status:已验收"]
    assert f"已验收：合并于 #{pr} （{result['merge_sha']}）" in closed["body"]
    assert not checkout.exists()
    assert str(checkout.as_posix()) not in git_run(gh_repos.vault, "worktree", "list", "--porcelain")
    assert git_run(gh_repos.vault, "branch", "--list", TASK) == ""
    assert tree_hashes(gpl) == before and len(before) == 2
    task = read_meta(gh_repos.vault)["tasks"][TASK]
    assert (task["state"], task["pr"], task["merge_sha"]) == ("merged", pr, result["merge_sha"])
    calls = len(gh_repos.gh.calls())
    assert merge(gh_repos.config, gh_repos.vault, pr, None)["merged"]
    assert len(merge_calls(gh_repos)) == 1
    assert not [call for call in gh_repos.gh.calls()[calls:] if call[:2] in (["issue", "close"], ["issue", "edit"])]


def test_merge_in_main_checkout_returns_to_main(gh_repos, monkeypatch, tmp_path):
    pr, checkout, _ = open_task_pr(gh_repos, monkeypatch, tmp_path, worktree=False)
    assert checkout == gh_repos.vault and read_lock(checkout)["branch"] == TASK
    pass_review(gh_repos, checkout, pr, tmp_path)
    merge(gh_repos.config, checkout, pr, None)
    assert git_run(gh_repos.vault, "symbolic-ref", "--short", "HEAD").strip() == "main"
    assert read_lock(gh_repos.vault) is None
    assert git_run(gh_repos.vault, "branch", "--list", TASK) == ""


def test_long_branch_merge_closes_milestone(gh_repos, monkeypatch, tmp_path):
    """旧流程批次：任务 PR 合入长期分支，close-batch 开长期分支 → main 的 PR，合并后关闭 Milestone。"""
    pr, checkout, _ = open_task_pr(gh_repos, monkeypatch, tmp_path, legacy=True)
    pass_review(gh_repos, checkout, pr, tmp_path)
    assert merge(gh_repos.config, gh_repos.vault, pr, None)["base"] == LONG
    batch_pr = close_batch(gh_repos.config, BATCH)["pr"]
    pass_review(gh_repos, gh_repos.vault, batch_pr, tmp_path)
    result = merge(gh_repos.config, gh_repos.vault, batch_pr, None)
    assert result["base"] == "main" and result["branch"] == LONG
    milestone = next(m for m in vault_state(gh_repos)["milestones"] if m["title"] == LONG)
    assert milestone["state"] == "closed"
    assert git_run(gh_repos.vault, "branch", "--list", LONG) == ""
    assert read_meta(gh_repos.vault)["batches"][BATCH]["state"] == "merged"
    assert merge(gh_repos.config, gh_repos.vault, batch_pr, None)["merged"]
    assert len(merge_calls(gh_repos)) == 2
    assert len([call for call in gh_repos.gh.calls() if call[:3] == ["api", "-X", "PATCH"]]) == 1

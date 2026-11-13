import json
import shutil
import subprocess

import pytest

from conftest import commit_file, git_run, write_config
from rwiki.config import load_config
from rwiki.errors import WikiError
from rwiki.ghflow import push, require_gh, require_private
from rwiki.push_guard import load_rules


def test_missing_gh_gives_install_and_login_instructions(tmp_path, monkeypatch):
    (tmp_path / "empty").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert shutil.which("gh") is None
    with pytest.raises(WikiError) as error:
        require_gh(tmp_path)
    assert "https://cli.github.com/" in str(error.value) and "gh auth login" in str(error.value)
    assert "不会自动安装" in str(error.value)


def test_unauthenticated_gh_stops_with_login_instruction(fake_gh, tmp_path):
    fake_gh.update(authenticated=False)
    with pytest.raises(WikiError, match="gh auth login"):
        require_gh(tmp_path)
    assert [call[:2] for call in fake_gh.calls()] == [["auth", "status"]]


def test_authenticated_gh_reports_login(fake_gh, tmp_path):
    assert require_gh(tmp_path) == "tester"
    assert [call[:2] for call in fake_gh.calls()] == [["auth", "status"], ["api", "user"]]


@pytest.mark.parametrize("visibility", ["PUBLIC", "INTERNAL"])
def test_non_private_remote_refuses_push(fake_gh, git_pair, tmp_path, visibility):
    state = fake_gh.state()
    state["repos"]["tester/jjd-wiki"]["visibility"] = visibility
    fake_gh.write(state)
    work = git_pair.work
    rules = load_rules(load_config(write_config(tmp_path / "c.json", tmp_path / "no-wiki")), work)
    git_run(work, "checkout", "-q", "-b", "task/a-P1-b")
    commit_file(work, "notes.md", "x\n")
    with pytest.raises(WikiError, match=visibility):
        require_private(work)
    with pytest.raises(WikiError, match=visibility):
        push(work, "task/a-P1-b", rules)
    assert git_run(work, "ls-remote", "origin", "refs/heads/task/a-P1-b") == ""


def test_private_remote_pushes_after_guard(fake_gh, git_pair, tmp_path):
    work = git_pair.work
    rules = load_rules(load_config(write_config(tmp_path / "c.json", tmp_path / "no-wiki")), work)
    git_run(work, "checkout", "-q", "-b", "task/a-P1-b")
    sha = commit_file(work, "notes.md", "x\n")
    push(work, "task/a-P1-b", rules)
    assert git_run(work, "ls-remote", "origin", "refs/heads/task/a-P1-b").split()[0] == sha
    commit_file(work, "leak.txt", "E:\\research-wiki\\x\n")
    with pytest.raises(WikiError, match="abs-path"):
        push(work, "task/a-P1-b", rules)
    assert git_run(work, "ls-remote", "origin", "refs/heads/task/a-P1-b").split()[0] == sha


def test_gh_json_treats_empty_output_as_empty_list(tmp_path, monkeypatch):
    """真实 gh 对空列表（如 deploy-key list --json）输出空串。"""
    from rwiki import ghflow

    monkeypatch.setattr(ghflow, "gh", lambda args, cwd: "")
    assert ghflow.gh_json(["repo", "deploy-key", "list", "--json", "title"], tmp_path) == []
    monkeypatch.setattr(ghflow, "gh", lambda args, cwd: '[{"title": "x"}]')
    assert ghflow.gh_json(["repo", "deploy-key", "list", "--json", "title"], tmp_path) == [{"title": "x"}]
    monkeypatch.setattr(ghflow, "gh", lambda args, cwd: " \n")
    assert ghflow.gh_json(["secret", "list", "--json", "name"], tmp_path) == []


def run_fake(cwd, *args):
    return subprocess.run([shutil.which("gh"), *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")


DEV = "tester/jjd-wiki-dev"


def test_fake_gh_deploy_key_matches_gh_2_103(fake_gh, tmp_path):
    """假 gh 与 gh 2.103 同形：没有 --read-only（未知参数报错且不写入），默认只读，--allow-write 才可写；
    list --json 空时输出空串，有 key 时原样输出 REST 形状。"""
    from rwiki import ghflow

    key = tmp_path / "k.pub"
    key.write_text("ssh-ed25519 AAAA test\n", encoding="utf-8")
    assert run_fake(tmp_path, "repo", "deploy-key", "list", "--repo", DEV, "--json", "title").stdout == ""
    assert ghflow.gh_json(["repo", "deploy-key", "list", "--repo", DEV, "--json", "title"], tmp_path) == []
    refused = run_fake(tmp_path, "repo", "deploy-key", "add", str(key), "--repo", DEV, "--title", "a", "--read-only")
    assert refused.returncode == 1 and "unknown flag: --read-only" in refused.stderr
    assert fake_gh.state()["repos"][DEV]["deploy_keys"] == []
    for title, extra in (("ro", ()), ("rw", ("--allow-write",))):
        assert run_fake(tmp_path, "repo", "deploy-key", "add", str(key), "--repo", DEV, "--title", title,
                        *extra).returncode == 0
    listed = ghflow.gh_json(["repo", "deploy-key", "list", "--repo", DEV, "--json", "title"], tmp_path)
    assert [(item["title"], item["read_only"]) for item in listed] == [("ro", True), ("rw", False)]
    assert {"id", "key", "title", "created_at", "read_only"} <= set(listed[0])


def test_fake_gh_pr_checks_json_exits_zero_like_real_gh(fake_gh, tmp_path):
    """gh pr checks --json 只导出并退出 0；没有检查时报错退出 1；pr_checks 两种情况都只取 JSON。"""
    from rwiki import ghflow

    state = fake_gh.state()
    state["repos"][DEV]["prs"].append({"number": 7, "state": "OPEN", "headRefName": "task/a-T1-b", "checks": []})
    fake_gh.write(state)
    empty = run_fake(tmp_path, "pr", "checks", "7", "--repo", DEV, "--json", "name,bucket")
    assert empty.returncode == 1 and "no checks reported" in empty.stderr and empty.stdout == ""
    checks = [{"name": "test", "bucket": "fail"}, {"name": "lint", "bucket": "pending"}]
    state["repos"][DEV]["prs"][0]["checks"] = checks
    fake_gh.write(state)
    exported = run_fake(tmp_path, "pr", "checks", "7", "--repo", DEV, "--json", "name,bucket")
    assert exported.returncode == 0 and json.loads(exported.stdout) == checks
    assert run_fake(tmp_path, "pr", "checks", "7", "--repo", DEV).returncode == 1


def test_fake_gh_rejects_unknown_flags(fake_gh, tmp_path):
    for args, flag in ((("pr", "merge", "1", "--repo", DEV, "--no-such"), "unknown flag: --no-such"),
                       (("issue", "list", "--repo", DEV, "-Z"), "unknown shorthand flag: 'Z' in -Z")):
        result = run_fake(tmp_path, *args)
        assert result.returncode == 1 and flag in result.stderr

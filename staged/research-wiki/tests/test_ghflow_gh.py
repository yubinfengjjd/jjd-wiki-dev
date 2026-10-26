import shutil

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
    state["repos"]["tester/research-wiki-vault"]["visibility"] = visibility
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

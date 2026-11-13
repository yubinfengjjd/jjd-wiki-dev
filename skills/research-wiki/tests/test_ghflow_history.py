import os
import subprocess

from conftest import git_init, git_init_bare, git_run, write_config
from rwiki.ghflow import (LEGACY_BRANCH, ignored_paths, install_hook, replay_filtered, snapshot_files,
                          snapshot_orphan, switch_to_main, tracked_files)

IGNORED = ("codex/", "staged/research-wiki/config.json", "/画廊/")


def commit_as(repo, files, message, name, email, date):
    """以指定作者与时间提交；files 的值为 None 表示删除。"""
    for relative, data in files.items():
        target = repo / relative
        if data is None:
            git_run(repo, "rm", "-q", "--", relative)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        git_run(repo, "add", "-f", "--", relative)
    env = {**os.environ, "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_AUTHOR_DATE": date,
           "GIT_COMMITTER_NAME": "提交者", "GIT_COMMITTER_EMAIL": "committer@localhost", "GIT_COMMITTER_DATE": date}
    git_run(repo, "commit", "-q", "-m", message, env=env)
    return git_run(repo, "rev-parse", "HEAD").strip()


def legacy_repo(tmp_path):
    """旧 master：被跟踪的 codex/、config.json、画廊/，后来才加入忽略规则；含一个合并提交。"""
    repo = git_init(tmp_path / "repo", "master")
    shas = [commit_as(repo, {"README.md": b"# dev\r\n", "codex/run.jsonl": b"E:\\research-wiki\\x\n",
                             "staged/research-wiki/config.json": b'{"wiki_root": "E:/w"}\n'},
                      "feat: 初始\n\n正文第一行\n正文第二行", "作者甲", "a@localhost", "1700000000 +0800")]
    git_run(repo, "branch", "side")
    shas.append(commit_as(repo, {"画廊/a/meta.json": b"{}\n", "docs/说明.md": b"x\n"}, "docs: 说明",
                          "作者乙", "b@localhost", "1700003600 -0500"))
    git_run(repo, "switch", "-q", "side")
    shas.append(commit_as(repo, {"codex/prompt.txt": b"p\n", "src/a.py": b"print(1)\n"}, "feat(side): 侧枝",
                          "作者丙", "c@localhost", "1700007200 +0000"))
    git_run(repo, "switch", "-q", "master")
    git_run(repo, "merge", "-q", "--no-ff", "-m", "merge: 合并侧枝", "side")
    shas.append(git_run(repo, "rev-parse", "HEAD").strip())
    shas.append(commit_as(repo, {".gitignore": "\n".join(IGNORED).encode() + b"\n", "docs/说明.md": None},
                          "chore(repo): 忽略规则", "作者甲", "a@localhost", "1700010800 +0800"))
    return repo, shas


def log_fields(repo, rev):
    return git_run(repo, "log", "-1", "--date=raw", "--format=%an|%ae|%ad|%cn|%ce|%cd", rev).strip()


def test_replay_drops_ignored_paths_and_keeps_metadata(tmp_path):
    repo, shas = legacy_repo(tmp_path)
    dropped = lambda paths: ignored_paths(repo, paths)
    assert replay_filtered(repo, "master", "main", dropped) == len(shas)
    replayed = git_run(repo, "rev-list", "--reverse", "--topo-order", "main").split()
    originals = git_run(repo, "rev-list", "--reverse", "--topo-order", "master").split()
    assert len(replayed) == len(originals) == len(shas)
    for new, old in zip(replayed, originals):
        files = tracked_files(repo, new)
        assert not ignored_paths(repo, files) and not any(path.startswith(("codex/", "画廊/")) for path in files)
        assert set(files) == set(tracked_files(repo, old)) - ignored_paths(repo, tracked_files(repo, old))
        for path in files:
            assert git_run(repo, "rev-parse", f"{new}:{path}") == git_run(repo, "rev-parse", f"{old}:{path}")
        assert log_fields(repo, new) == log_fields(repo, old)
        message = git_run(repo, "log", "-1", "--format=%B", new)
        assert message.startswith(git_run(repo, "log", "-1", "--format=%B", old).rstrip("\n"))
        trailers = subprocess.run(["git", "interpret-trailers", "--parse"], input=message, capture_output=True,
                                  text=True, encoding="utf-8", check=True).stdout
        assert f"Legacy-Commit: {old}" in trailers
        old_parents = git_run(repo, "log", "-1", "--format=%P", old).split()
        new_parents = git_run(repo, "log", "-1", "--format=%P", new).split()
        assert new_parents == [replayed[originals.index(parent)] for parent in old_parents]
    assert git_run(repo, "status", "--porcelain") == "" and git_run(repo, "symbolic-ref", "--short", "HEAD") == "master\n"


def test_snapshot_is_single_commit_of_filtered_worktree(tmp_path):
    repo, _ = legacy_repo(tmp_path)
    (repo / ".gitattributes").write_bytes(b"* -text\n")
    (repo / "新文件.md").write_bytes(b"untracked\r\n")
    (repo / "codex/extra.log").write_bytes(b"ignored\n")
    sha = snapshot_orphan(repo, "main")
    assert git_run(repo, "rev-list", "main").split() == [sha]
    assert git_run(repo, "log", "-1", "--format=%P", sha).strip() == ""
    files = tracked_files(repo, "main")
    assert files == snapshot_files(repo) and "新文件.md" in files
    assert not any(path.startswith(("codex/", "画廊/")) or path.endswith("config.json") for path in files)
    blob = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", f"{sha}:新文件.md"],
                          capture_output=True, check=True).stdout
    assert blob == b"untracked\r\n"


def test_switch_to_main_keeps_previously_tracked_ignored_files(tmp_path):
    repo, _ = legacy_repo(tmp_path)
    kept = ["codex/prompt.txt", "codex/run.jsonl", "staged/research-wiki/config.json", "画廊/a/meta.json"]
    before = {path: (repo / path).read_bytes() for path in kept}
    replay_filtered(repo, "master", "main", lambda paths: ignored_paths(repo, paths))
    git_run(repo, "branch", "-m", "master", LEGACY_BRANCH)
    assert switch_to_main(repo) == len(kept)
    assert git_run(repo, "symbolic-ref", "HEAD").strip() == "refs/heads/main"
    assert {path: (repo / path).read_bytes() for path in kept} == before
    assert git_run(repo, "status", "--porcelain", "-uall") == ""
    assert not set(kept) & set(tracked_files(repo))


def test_installed_hook_refuses_legacy_branches(tmp_path):
    repo, _ = legacy_repo(tmp_path)
    remote = tmp_path / "remote.git"
    git_init_bare(remote)
    git_run(repo, "remote", "add", "origin", str(remote))
    git_run(repo, "branch", "-m", "master", LEGACY_BRANCH)
    hook = install_hook(repo, write_config(tmp_path / "c.json", tmp_path / "no-wiki"))
    assert hook == repo / ".git" / "hooks" / "pre-push" and "gh guard --pre-push" in hook.read_text(encoding="utf-8")
    result = subprocess.run(["git", "-C", str(repo), "push", "origin", LEGACY_BRANCH], capture_output=True,
                            text=True, encoding="utf-8")
    assert result.returncode != 0 and "legacy" in result.stderr
    assert git_run(repo, "ls-remote", "origin") == ""

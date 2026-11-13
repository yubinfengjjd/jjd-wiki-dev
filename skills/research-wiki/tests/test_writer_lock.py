import pytest

from conftest import git_run
from rwiki.errors import WikiError
from rwiki.writer_lock import acquire, lock_path, read_lock, release, require_holder


def test_each_worktree_has_its_own_lock(git_pair, tmp_path):
    work = git_pair.work
    other = tmp_path / "wt"
    git_run(work, "worktree", "add", "-q", "-b", "task/b-P1-t", str(other))
    main_lock, worktree_lock = lock_path(work), lock_path(other)
    assert main_lock == (work / ".git" / "rwiki-writer.lock").resolve()
    assert worktree_lock.parent.parent.name == "worktrees"
    assert main_lock != worktree_lock
    acquire(work, "codex", "main")
    acquire(other, "claude", "task/b-P1-t")
    assert read_lock(work)["agent"] == "codex" and read_lock(other)["agent"] == "claude"


def test_reentry_conflict_and_release(git_pair):
    work = git_pair.work
    first = acquire(work, "codex", "task/b-P1-t")
    assert set(first) == {"agent", "branch", "pid", "timestamp"}
    assert acquire(work, "codex", "task/b-P1-t") == first
    with pytest.raises(WikiError, match="codex.*task/b-P1-t"):
        acquire(work, "claude", "task/b-P1-t")
    with pytest.raises(WikiError, match="codex.*task/b-P1-t"):
        acquire(work, "codex", "task/b-P2-t")
    require_holder(work, "codex", "task/b-P1-t")
    with pytest.raises(WikiError, match="codex"):
        require_holder(work, "claude", "task/b-P1-t")
    release(work)
    assert read_lock(work) is None
    with pytest.raises(WikiError, match="start-task"):
        require_holder(work, "codex", "task/b-P1-t")
    assert acquire(work, "claude", "task/b-P1-t")["agent"] == "claude"

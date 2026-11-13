"""按 worktree 的写入锁：<git-dir>/rwiki-writer.lock。

pid 只作信息，不做存活判断；遗留锁由用户手工删除。
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .errors import WikiError
from .store import git

LOCK_NAME = "rwiki-writer.lock"


def lock_path(wiki_root: Path) -> Path:
    return Path(git(wiki_root, "rev-parse", "--absolute-git-dir").strip()) / LOCK_NAME


def read_lock(wiki_root: Path) -> dict | None:
    path = lock_path(wiki_root)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def acquire(wiki_root: Path, agent: str, branch: str) -> dict:
    path = lock_path(wiki_root)
    data = {"agent": agent, "branch": branch, "pid": os.getpid(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        held = read_lock(wiki_root)
        if held["agent"] == agent and held["branch"] == branch:
            return held
        raise WikiError(f"写入锁已由 {held['agent']} 持有（分支 {held['branch']}）：{path}") from None
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False)
    return data


def require_holder(wiki_root: Path, agent: str | None, branch: str) -> None:
    held = read_lock(wiki_root)
    if held is None:
        raise WikiError(f"当前工作树没有写入锁（分支 {branch}），请先 wiki.py gh start-task")
    if held["agent"] != agent or held["branch"] != branch:
        raise WikiError(f"写入锁由 {held['agent']} 持有（分支 {held['branch']}），"
                        f"当前 Agent {agent or '（未设置 RWIKI_AGENT）'} 在分支 {branch} 上不能写入")


def release(wiki_root: Path) -> None:
    lock_path(wiki_root).unlink(missing_ok=True)

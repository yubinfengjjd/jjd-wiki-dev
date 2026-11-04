import os
import shutil
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .catalog import build_index
from .config import Config
from .errors import WikiError
from .process import run


def git(wiki_root: Path, *args: str) -> str:
    return run(["git", "-C", str(wiki_root), *args], wiki_root).stdout


def current_branch(wiki_root: Path) -> str:
    """git < 2.22 lacks ``branch --show-current``; symbolic-ref covers older gits and unborn HEAD."""
    try:
        return git(wiki_root, "branch", "--show-current").strip()
    except WikiError:
        pass
    try:
        return git(wiki_root, "symbolic-ref", "--short", "HEAD").strip()
    except WikiError:
        return git(wiki_root, "rev-parse", "--abbrev-ref", "HEAD").strip()


@contextmanager
def guarded(config: Config, *paths: Path):
    """Restore the listed files (plus index and log) if the block, including save, fails.

    A write request either commits or leaves its own files as they were; derived
    facts on other pages are recomputed by the next save.
    """
    root = config.wiki_root
    watched = {Path(p) for p in paths} | {root / "index.md", root / "log.md"}
    saved = {p: p.read_bytes() if p.is_file() else None for p in watched}
    try:
        yield
    except BaseException:
        for path, data in saved.items():
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        raise


PAGES_SHOWN = 20


def save_policy(branch: str) -> str:
    """v2（2026-10-27）：main 与批次分支直接提交；task/* 仍需写入锁与分支元数据。"""
    if branch.startswith("task/"):
        return "task"
    return "plain"


def trailers(issue: int | None, agent: str | None, pages: list[str]) -> str:
    lines = [f"Issue: #{issue}"] if issue is not None else []
    if agent:
        lines.append(f"Agent: {agent}")
    shown = ", ".join(pages[:PAGES_SHOWN])
    if len(pages) > PAGES_SHOWN:
        shown += f" … (+{len(pages) - PAGES_SHOWN})"
    lines.append(f"Pages: {shown}")
    return "\n".join(lines)


def save(config: Config, message: str) -> None:
    from . import push_guard, writer_lock
    from .facts import refresh_facts

    root = config.wiki_root
    branch = current_branch(root)
    policy = save_policy(branch)
    agent = os.environ.get("RWIKI_AGENT")
    issue = None
    if policy == "task":
        from .ghflow import read_meta
        writer_lock.require_holder(root, agent, branch)
        task = read_meta(root).get("tasks", {}).get(branch)
        if task is None:
            raise WikiError(f"任务分支 {branch} 没有分支元数据，请用 wiki.py gh start-task 创建")
        issue = task["issue"]
    refresh_facts(config)
    (root / "index.md").write_text(build_index(root), encoding="utf-8", newline="\n")
    from .finder import write_catalog
    write_catalog(config)
    # Every git mutation is pathspec-scoped to ``.`` — the working dir is
    # wiki_root, so ``.`` means the wiki subtree only. When the wiki lives
    # inside a larger repository, unrelated staged/index changes and untracked
    # sibling planning/maintenance work stay untouched and uncommitted; no
    # reset/clean/stash is ever used to hide them. A standalone wiki repo
    # behaves exactly as before (``.`` == the whole repo).
    scope = "."
    # 作者 2026-11-02：清理旧许可排除块，使知识源码与公开资源默认提交。
    push_guard.sync_ignore(root)
    push_guard.assert_no_sensitive_changes(root)
    if not git(root, "status", "--porcelain", "--", scope).strip():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with (root / "log.md").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"\n## [{timestamp}] {message}\n")
    git(root, "add", "-A", "--", scope)
    body = []
    if policy == "task" or agent:
        pages = git(root, "-c", "core.quotePath=false", "diff", "--cached", "--name-only", "-z",
                    "--relative", "--", scope).split("\0")
        body = ["-m", trailers(issue, agent, [page for page in pages if page])]
    git(root, "-c", "user.name=research-wiki", "-c", "user.email=research-wiki@localhost",
        "commit", "-m", message, *body, "--", scope)


def init(config: Config) -> None:
    root = config.wiki_root
    assets = Path(__file__).resolve().parents[1] / "assets"
    if root.exists() and any(root.iterdir()):
        for filename in ("AGENTS.md", "CLAUDE.md"):
            shutil.copyfile(assets / filename, root / filename)
        save(config, "update rules")
        return
    # v2 directories (sources/, recipes/, scenarios/) are created when their first page is written.
    for directory in ("layouts", "templates", "methods", "interfaces", "chart-types", "projects"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    for filename in ("AGENTS.md", "CLAUDE.md"):
        shutil.copyfile(assets / filename, root / filename)
    # verify/ holds the replay receipts and outputs that ready entries depend on: keep them in git.
    (root / ".gitignore").write_text("**/__pycache__/\n", encoding="utf-8", newline="\n")
    (root / "log.md").write_text("# 操作日志\n", encoding="utf-8", newline="\n")
    git(root, "init")
    save(config, "init")

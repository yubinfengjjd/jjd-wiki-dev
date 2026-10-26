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
    """main 与长期分支拒绝写入；task/* 需要写入锁；其他分支（未迁移仓库、测试仓库）保持原行为。"""
    if branch == "main":
        return "refuse-main"
    if branch.startswith(("project/", "ingest/")):
        return "refuse-long"
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
    branch = git(root, "branch", "--show-current").strip()
    policy = save_policy(branch)
    # 拒绝发生在刷新 facts、写 log.md 与 git add 之前；调用方已写的页面由 guarded() 还原。
    if policy.startswith("refuse"):
        kind = "主分支" if policy == "refuse-main" else "长期分支"
        raise WikiError(f"{branch} 是{kind}，不直接写入知识库：请先 start-task"
                        "（wiki.py gh start-task <批次> <阶段> <主题> --title …）创建任务分支")
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
    # Every git mutation is pathspec-scoped to ``.`` — the working dir is
    # wiki_root, so ``.`` means the wiki subtree only. When the wiki lives
    # inside a larger repository, unrelated staged/index changes and untracked
    # sibling planning/maintenance work stay untouched and uncommitted; no
    # reset/clean/stash is ever used to hide them. A standalone wiki repo
    # behaves exactly as before (``.`` == the whole repo).
    scope = "."
    # 新的 GPL 方法目录必须先进 .gitignore 托管块，否则 add -A 会把源码提交进去。
    push_guard.sync_ignore(root)
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
    for directory in ("layouts", "templates", "methods", "interfaces", "chart-types", "projects"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    for filename in ("AGENTS.md", "CLAUDE.md"):
        shutil.copyfile(assets / filename, root / filename)
    # verify/ holds the replay receipts and outputs that ready entries depend on: keep them in git.
    (root / ".gitignore").write_text("**/__pycache__/\n", encoding="utf-8", newline="\n")
    (root / "log.md").write_text("# 操作日志\n", encoding="utf-8", newline="\n")
    git(root, "init")
    save(config, "init")

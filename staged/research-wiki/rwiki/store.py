import shutil
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .catalog import build_index
from .config import Config
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


def save(config: Config, message: str) -> None:
    from .facts import refresh_facts

    root = config.wiki_root
    refresh_facts(config)
    (root / "index.md").write_text(build_index(root), encoding="utf-8", newline="\n")
    if not git(root, "status", "--porcelain").strip():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with (root / "log.md").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"\n## [{timestamp}] {message}\n")
    git(root, "add", "-A")
    git(root, "-c", "user.name=research-wiki", "-c", "user.email=research-wiki@localhost",
        "commit", "-m", message)


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

import shutil
from datetime import datetime, timezone
from pathlib import Path

from .catalog import build_index
from .config import Config
from .process import run


def git(wiki_root: Path, *args: str) -> str:
    return run(["git", "-C", str(wiki_root), *args], wiki_root).stdout


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
    (root / ".gitignore").write_text("templates/*/verify/\nlayouts/*/verify/\n**/__pycache__/\n", encoding="utf-8", newline="\n")
    (root / "log.md").write_text("# 操作日志\n", encoding="utf-8", newline="\n")
    git(root, "init")
    save(config, "init")

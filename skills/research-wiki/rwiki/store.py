import os
import shutil
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, RLock

from .catalog import build_index
from .config import Config
from .errors import WikiError
from .process import run
from .read_cache import invalidate_cache


_WRITE_LOCKS: dict[str, RLock] = {}
_WRITE_LOCKS_GUARD = Lock()
_INCREMENTAL_SAVE: ContextVar[tuple[set[Path], set[str]] | None] = ContextVar("rwiki_incremental_save", default=None)


@contextmanager
def incremental_save_scope(only_refresh_paths: set[Path], deleted_pages: set[str]):
    """Scope save() inside this block to refresh facts & catalog only for the touched pages."""
    token = _INCREMENTAL_SAVE.set((only_refresh_paths, deleted_pages))
    try:
        yield
    finally:
        _INCREMENTAL_SAVE.reset(token)


def vault_write_lock(root: Path) -> RLock:
    """Process-wide re-entrant write lock for one canonical vault root.

    Every mutation path (server ``finish``, deletion, ``save``) shares it, so a
    plan computed under the lock cannot be overtaken by another in-process writer.
    """
    key = os.path.normcase(os.path.abspath(str(Path(root).resolve())))
    with _WRITE_LOCKS_GUARD:
        lock = _WRITE_LOCKS.get(key)
        if lock is None:
            lock = _WRITE_LOCKS[key] = RLock()
        return lock


def staged_paths(wiki_root: Path) -> set[str] | None:
    """Wiki-relative paths currently staged in the Git index (None outside Git)."""
    try:
        out = git(wiki_root, "-c", "core.quotePath=false", "diff", "--cached", "--name-only",
                  "-z", "--relative", "--", ".")
    except (WikiError, OSError):
        return None
    return {name for name in out.split("\0") if name}


def head_revision(wiki_root: Path) -> str | None:
    try:
        return git(wiki_root, "rev-parse", "-q", "--verify", "HEAD").strip() or None
    except (WikiError, OSError):
        return None


def unstage_new(wiki_root: Path, before: set[str] | None) -> None:
    """Unstage everything a failed save staged, leaving earlier staging untouched."""
    if before is None:
        return
    after = staged_paths(wiki_root)
    if not after:
        return
    added = sorted(after - before)
    for start in range(0, len(added), 100):
        chunk = added[start:start + 100]
        try:
            git(wiki_root, "reset", "-q", "--", *chunk)
        except (WikiError, OSError):
            for name in chunk:
                try:
                    git(wiki_root, "reset", "-q", "--", name)
                except (WikiError, OSError):
                    pass


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
    watched = {Path(p) for p in paths} | {root / "index.md", root / "log.md", root / "catalog.jsonl"}
    with vault_write_lock(root):
        saved = {p: p.read_bytes() if p.is_file() else None for p in watched}
        staged_before = staged_paths(root) if (root / ".git").exists() or _in_git(root) else None
        head_before = head_revision(root) if staged_before is not None else None
        try:
            yield
        except BaseException:
            committed = staged_before is not None and head_revision(root) != head_before
            if not committed:
                for path, data in saved.items():
                    if data is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(data)
                unstage_new(root, staged_before)
            invalidate_cache(root)
            raise


def _in_git(root: Path) -> bool:
    return any((parent / ".git").exists() for parent in (Path(root).resolve(), *Path(root).resolve().parents))


PAGES_SHOWN = 20


def save_policy(branch: str) -> str:
    """单人仓库直接提交到当前分支，不再要求写入锁或 ghflow 任务元数据。"""
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


def save(config: Config, message: str, *, only_refresh_paths: set[Path] | None = None,
         deleted_pages: set[str] | None = None) -> None:
    if only_refresh_paths is None and deleted_pages is None:
        scoped = _INCREMENTAL_SAVE.get()
        if scoped is not None:
            only_refresh_paths, deleted_pages = scoped
    with vault_write_lock(config.wiki_root):
        _save(config, message, only_refresh_paths=only_refresh_paths, deleted_pages=deleted_pages)


def _normalize_incremental_scope(
    root: Path,
    only_refresh_paths: set[Path] | None,
    deleted_pages: set[str] | None,
) -> tuple[set[Path] | None, set[str] | None]:
    """Validate and expand incremental save scope, falling back to full rebuild when cross-page facts may go stale."""
    if only_refresh_paths is None and deleted_pages is None:
        return None, None

    resolved_root = root.resolve()
    normalized_deleted = {
        str(dp).replace("\\", "/").lstrip("/")
        for dp in (deleted_pages or ())
        if str(dp).strip()
    }
    normalized_paths: set[Path] | None = None
    changed_rels: set[str] = set()
    if only_refresh_paths is not None:
        normalized_paths = set()
        for raw_p in only_refresh_paths:
            p = Path(raw_p)
            resolved_p = p.resolve() if p.is_absolute() else (resolved_root / p).resolve()
            if not resolved_p.is_relative_to(resolved_root):
                raise WikiError(f"only_refresh_paths 越出知识库目录: {raw_p}")
            normalized_paths.add(resolved_p)
            changed_rels.add(resolved_p.relative_to(resolved_root).as_posix())

    # Changes to sources/ or deletions of sources/interfaces/recipes can alter cross-page L0 items or many derived facts.
    if (
        any(rel.startswith(("sources/", "interfaces/")) for rel in changed_rels)
        or any(dp.startswith(("sources/", "interfaces/", "recipes/")) for dp in normalized_deleted)
    ):
        return None, None

    # Deleting a template or method can leave stale reverse links in interface/method/scenario/layout facts blocks.
    if normalized_paths is not None and any(
        dp.startswith(("templates/", "methods/", "layouts/")) for dp in normalized_deleted
    ):
        from .facts import FACT_DIRS

        deleted_stems = {Path(dp).stem for dp in normalized_deleted}
        needles = {dp.removesuffix(".md") for dp in normalized_deleted} | deleted_stems
        iface_dir = resolved_root / "interfaces"
        if iface_dir.is_dir():
            for iface_page in sorted(iface_dir.glob("*.md")):
                normalized_paths.add(iface_page.resolve())
        for folder in FACT_DIRS:
            folder_path = resolved_root / folder
            if not folder_path.is_dir():
                continue
            for candidate in sorted(folder_path.glob("*.md")):
                rcand = candidate.resolve()
                if rcand in normalized_paths:
                    continue
                try:
                    raw_text = rcand.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if any(needle and needle in raw_text for needle in needles):
                    normalized_paths.add(rcand)

    return normalized_paths, (normalized_deleted or None)


def _save(config: Config, message: str, *, only_refresh_paths: set[Path] | None = None,
          deleted_pages: set[str] | None = None) -> None:
    from .asset_checkout import assert_writable
    assert_writable(config)
    from . import push_guard
    from .facts import refresh_facts
    from .finder import write_catalog
    from .read_cache import read_session

    root = config.wiki_root
    agent = os.environ.get("RWIKI_AGENT")
    eff_refresh, eff_deleted = _normalize_incremental_scope(root, only_refresh_paths, deleted_pages)
    with read_session():
        if eff_refresh is None:
            refresh_facts(config)
        else:
            refresh_facts(config, only_paths=eff_refresh)
        index_text = build_index(root)
        if not (root / "index.md").is_file() or (root / "index.md").read_text(encoding="utf-8") != index_text:
            (root / "index.md").write_text(index_text, encoding="utf-8", newline="\n")
        if eff_refresh is None and eff_deleted is None:
            write_catalog(config)
        else:
            write_catalog(config, changed_paths=eff_refresh, deleted_pages=eff_deleted)
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
        invalidate_cache(root)
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with (root / "log.md").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"\n## [{timestamp}] {message}\n")
    git(root, "add", "-A", "--", scope)
    body = []
    if agent:
        pages = git(root, "-c", "core.quotePath=false", "diff", "--cached", "--name-only", "-z",
                    "--relative", "--", scope).split("\0")
        body = ["-m", trailers(None, agent, [page for page in pages if page])]
    git(root, "-c", "user.name=research-wiki", "-c", "user.email=research-wiki@localhost",
        "commit", "-m", message, *body, "--", scope)
    invalidate_cache(root)


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

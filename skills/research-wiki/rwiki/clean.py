"""Safe cleanup of expired scratch, test, and probe artifacts across workspace roots."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .config import Config

# Never touch runtime libraries, upstream source caches, active projects, or studio data.
PROTECTED_ENV_NAMES = frozenset({
    "R-lib",
    "R-lib-scp",
    "bio-python",
    "pip-cache",
    "sources",
    "projects",
    "worktrees",
    "papers",
})

PROTECTED_RWIKI_WORK_NAMES = frozenset({
    "runs",
    "search",
    "studio_outputs",
    "studio_uploads",
})

RETIRED_WORK_PREFIXES = (
    "codex-scp-",
    "devin-probe-",
    "kiro-scp-",
    "CLAUDE-SCP-",
)

RETIRED_WORK_EXACT = frozenset({
    "modernization-v3",
    "finalize_ring.py",
    "Rplots.pdf",
    "portability",
    "figureya",
    "ring-entry",
    "ring-gallery-corrected",
    "ring-src",
})

RETIRED_RWIKI_PREFIXES = (
    "dependency-catalog-",
    "deps-install-",
    "github-handoff-",
    "local-omics-",
    "remote-validation-",
)


def _is_broken_link(path: Path) -> bool:
    try:
        os.lstat(path)
    except OSError:
        return False
    return not path.exists()


def _entry_size(path: Path) -> int:
    if _is_broken_link(path) or path.is_symlink():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file() and not item.is_symlink():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def _remove_path(path: Path) -> None:
    if path.is_symlink() or _is_broken_link(path):
        try:
            path.unlink()
        except OSError:
            path.rmdir()
        return
    if path.is_file():
        path.unlink()
        return
    if path.is_dir():
        def _onerror(func, target, _exc_info):
            os.chmod(target, 0o700)
            func(target)
        shutil.rmtree(path, onerror=_onerror)


def _collect_candidates(
    config: Config,
    *,
    include_backups: bool = False,
    include_caches: bool = False,
) -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []
    rwiki_work = config.work_root
    work_dir = rwiki_work.parent if (rwiki_work is not None and rwiki_work.name == "rwiki") else rwiki_work
    env_root = (
        config.sources_root.parent
        if config.sources_root is not None
        else (work_dir.parent if work_dir is not None else None)
    )

    if env_root is not None and env_root.is_dir():
        tmp_dir = env_root / "tmp"
        if tmp_dir.is_dir():
            for child in sorted(tmp_dir.iterdir()):
                candidates.append((child, "env_tmp"))

        for child in sorted(env_root.iterdir()):
            if child.name in PROTECTED_ENV_NAMES:
                continue
            if child.name.startswith("t06-ui-"):
                candidates.append((child, "ui_smoke_profile"))
            elif include_backups and child.name in ("skill-backup", "audit", "maintenance"):
                candidates.append((child, "historical_backup"))

        if work_dir is not None and work_dir.is_dir():
            for child in sorted(work_dir.iterdir()):
                if child.name == "rwiki":
                    continue
                if (
                    child.name in RETIRED_WORK_EXACT
                    or child.name.startswith(RETIRED_WORK_PREFIXES)
                    or _is_broken_link(child)
                ):
                    candidates.append((child, "retired_probe_work"))

        if rwiki_work is not None and rwiki_work.is_dir():
            for child in sorted(rwiki_work.iterdir()):
                if child.name in PROTECTED_RWIKI_WORK_NAMES:
                    continue
                if child.name == "empty-r-user-lib" or child.name.startswith(RETIRED_RWIKI_PREFIXES):
                    candidates.append((child, "retired_rwiki_scratch"))

    if include_caches:
        vault_root = config.wiki_root.parent
        dev_root_raw = (config.github or {}).get("dev_root")
        roots = [vault_root]
        if dev_root_raw:
            roots.append(Path(dev_root_raw))
        for root in roots:
            for cache_name in (".pytest_cache", "Rplots.pdf"):
                target = root / cache_name
                if target.exists() or _is_broken_link(target):
                    candidates.append((target, "repo_cache"))

    # Deduplicate preserving order
    seen: set[Path] = set()
    unique: list[tuple[Path, str]] = []
    for path, category in candidates:
        if path not in seen:
            seen.add(path)
            unique.append((path, category))
    return unique


def clean_workspace(
    config: Config,
    *,
    apply: bool = False,
    include_backups: bool = False,
    include_caches: bool = False,
) -> dict:
    """Inspect or remove disposable scratch, smoke profiles, and retired probes safely."""
    targets = _collect_candidates(
        config,
        include_backups=include_backups,
        include_caches=include_caches,
    )
    items: list[dict] = []
    removed = 0
    failed: list[dict] = []
    total_bytes = 0

    for path, category in targets:
        size = _entry_size(path)
        total_bytes += size
        entry = {
            "path": str(path),
            "category": category,
            "bytes": size,
            "removed": False,
        }
        if apply:
            try:
                _remove_path(path)
                entry["removed"] = not (path.exists() or _is_broken_link(path))
                if entry["removed"]:
                    removed += 1
            except OSError as error:
                failed.append({"path": str(path), "error": str(error)})
        items.append(entry)

    return {
        "mode": "apply" if apply else "dry_run",
        "total_candidates": len(items),
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "removed_count": removed,
        "failed": failed,
        "items": items[:120],
        "items_truncated": max(0, len(items) - 120),
    }

"""Request-local read snapshots and thread-safe process-level Vault snapshot cache."""
from __future__ import annotations

import os
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Callable

_snapshot = ContextVar("rwiki_read_snapshot", default=None)

_LOCK = RLock()
_PAGE_CACHE_MAX = 4096
_PAGE_CACHE: OrderedDict[tuple[str, int, int, int], tuple[dict, str]] = OrderedDict()
_VAULT_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_GLOBAL_GEN = 0

_FINGERPRINT_DIRS = (
    "layouts",
    "templates",
    "methods",
    "interfaces",
    "chart-types",
    "projects",
    "sources",
    "recipes",
    "scenarios",
)
_SUBDIR_FILES = (
    "spec.json",
    "acceptance.json",
    "layout.json",
    "preview.png",
    "thumb.png",
    "panel-manifest.yaml",
    "panel-receipts.json",
    "runtime.json",
    "source.json",
)
_VERIFY_FILES = ("verify.json", "figure.png", "figure.pdf", "figure.svg")


@contextmanager
def read_session():
    if _snapshot.get() is not None:
        yield
        return
    token = _snapshot.set({})
    try:
        yield
    finally:
        _snapshot.reset(token)


def remember(key, build):
    snapshot = _snapshot.get()
    if snapshot is None:
        return build()
    if key not in snapshot:
        snapshot[key] = build()
    return snapshot[key]


def page_cache_get_or_load(path: Path, loader: Callable[[], tuple[dict, str]]) -> tuple[dict, str]:
    """Thread-safe process-level page parse cache keyed by (resolved_path, mtime_ns, ctime_ns, size)."""
    resolved = path.resolve()
    stamp = resolved.stat()
    key = (str(resolved), stamp.st_mtime_ns, stamp.st_ctime_ns, stamp.st_size)
    with _LOCK:
        cached = _PAGE_CACHE.get(key)
        if cached is not None:
            _PAGE_CACHE.move_to_end(key)
            return deepcopy(cached[0]), cached[1]
    meta, body = loader()
    with _LOCK:
        _PAGE_CACHE[key] = (deepcopy(meta), body)
        _PAGE_CACHE.move_to_end(key)
        while len(_PAGE_CACHE) > _PAGE_CACHE_MAX:
            _PAGE_CACHE.popitem(last=False)
    return deepcopy(meta), body


def invalidate_page_cache(path: Path) -> None:
    """Drop all cached entries for a specific page path."""
    target = os.path.normcase(str(path.resolve()))
    with _LOCK:
        stale = [k for k in _PAGE_CACHE if os.path.normcase(k[0]) == target]
        for k in stale:
            _PAGE_CACHE.pop(k, None)


def _scan_tree_mtimes(base: str, out: list[tuple[str, int, int]]) -> None:
    """Collect (path, mtime_ns, size) for files under code/ or example/ directories."""
    if not os.path.isdir(base):
        return
    try:
        dir_st = os.stat(base)
        out.append((base, dir_st.st_mtime_ns, 0))
        with os.scandir(base) as it:
            for entry in sorted(it, key=lambda e: e.name):
                if entry.name == "__pycache__" or entry.name.startswith("."):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    _scan_tree_mtimes(entry.path, out)
                elif entry.is_file(follow_symlinks=False):
                    if entry.name.endswith((".pyc", ".pyo")):
                        continue
                    st = entry.stat(follow_symlinks=False)
                    out.append((entry.path, st.st_mtime_ns, st.st_size))
    except OSError:
        pass


def vault_fingerprint(root: Path, gallery_root: Path | None = None) -> tuple:
    """Lightweight stat-only fingerprint across wiki_root (and optional gallery_root)."""
    resolved = str(root.resolve())
    items: list[tuple[str, int, int]] = []
    for d in _FINGERPRINT_DIRS:
        dp = os.path.join(resolved, d)
        if not os.path.isdir(dp):
            continue
        try:
            dst = os.stat(dp)
            items.append((d, dst.st_mtime_ns, 0))
            with os.scandir(dp) as it:
                entries = sorted(it, key=lambda e: e.name)
            for entry in entries:
                if entry.is_file(follow_symlinks=False) and entry.name.endswith(".md"):
                    st = entry.stat(follow_symlinks=False)
                    items.append((f"{d}/{entry.name}", st.st_mtime_ns, st.st_size))
                elif entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                    sub_prefix = f"{d}/{entry.name}"
                    try:
                        sdst = entry.stat(follow_symlinks=False)
                        items.append((sub_prefix, sdst.st_mtime_ns, 0))
                    except OSError:
                        pass
                    for fname in _SUBDIR_FILES:
                        fp = os.path.join(entry.path, fname)
                        if os.path.isfile(fp):
                            st = os.stat(fp)
                            items.append((f"{sub_prefix}/{fname}", st.st_mtime_ns, st.st_size))
                    vdir = os.path.join(entry.path, "verify")
                    if d in ("methods", "recipes"):
                        # Implementation receipts and run history: every file counts.
                        _scan_tree_mtimes(vdir, items)
                    elif os.path.isdir(vdir):
                        for vname in _VERIFY_FILES:
                            vp = os.path.join(vdir, vname)
                            if os.path.isfile(vp):
                                st = os.stat(vp)
                                items.append((f"{sub_prefix}/verify/{vname}", st.st_mtime_ns, st.st_size))
                    if d == "templates":
                        _scan_tree_mtimes(os.path.join(entry.path, "code"), items)
                        _scan_tree_mtimes(os.path.join(entry.path, "example"), items)
                        _scan_tree_mtimes(os.path.join(entry.path, "verification"), items)
                    elif d == "methods":
                        # In-place code edits change verified evidence; stat every file.
                        _scan_tree_mtimes(os.path.join(entry.path, "code"), items)
                        _scan_tree_mtimes(os.path.join(entry.path, "verification"), items)
                    elif d == "recipes":
                        _scan_tree_mtimes(os.path.join(entry.path, "source"), items)
                        _scan_tree_mtimes(os.path.join(entry.path, "repair"), items)
        except OSError:
            continue

    for extra_rel in ("sources/figureya-curation.json", "recipes/method-map.json"):
        ep = os.path.join(resolved, extra_rel)
        if os.path.isfile(ep):
            try:
                st = os.stat(ep)
                items.append((extra_rel, st.st_mtime_ns, st.st_size))
            except OSError:
                pass

    if gallery_root is not None:
        gal_resolved = str(gallery_root.resolve())
        if os.path.isdir(gal_resolved):
            try:
                gst = os.stat(gal_resolved)
                items.append(("__gallery__", gst.st_mtime_ns, 0))
                with os.scandir(gal_resolved) as it:
                    for entry in sorted(it, key=lambda e: e.name):
                        if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                            # Entry/figures directory mtimes track referenced image appearance.
                            for sub in ("", "figures"):
                                sp = os.path.join(entry.path, sub) if sub else entry.path
                                if os.path.isdir(sp):
                                    sst = os.stat(sp)
                                    items.append((f"__gallery__/{entry.name}/{sub}", sst.st_mtime_ns, 0))
                            mp = os.path.join(entry.path, "meta.json")
                            if os.path.isfile(mp):
                                st = os.stat(mp)
                                items.append((f"__gallery__/{entry.name}/meta.json", st.st_mtime_ns, st.st_size))
            except OSError:
                pass
    return tuple(items)


def cached_vault_value(
    root: Path,
    name: str,
    builder: Callable[[], Any],
    *,
    extra_key: Any = None,
    gallery_root: Path | None = None,
    copy_result: bool = True,
) -> Any:
    """Return a cached vault computation if the vault fingerprint matches; recompute safely otherwise."""
    root_key = os.path.normcase(str(root.resolve()))
    gal_key = os.path.normcase(str(gallery_root.resolve())) if gallery_root is not None else ""
    fp = remember(("vault-fingerprint", root_key, gal_key), lambda: vault_fingerprint(root, gallery_root))
    entry_key = (name, extra_key)
    # Gallery-aware and wiki-only reads have different fingerprints: give each its
    # own bucket so alternating /api/pages and /api/graph never evict each other.
    bucket_key = (root_key, gal_key)
    with _LOCK:
        bucket = _VAULT_CACHE.get(bucket_key)
        if bucket is not None and bucket["fp"] == fp:
            if entry_key in bucket["entries"]:
                cached = bucket["entries"][entry_key]
                return deepcopy(cached) if copy_result else cached
            gen_before = bucket["gen"]
        else:
            gen_before = (bucket["gen"] + 1) if bucket is not None else (_GLOBAL_GEN + 1)
            _VAULT_CACHE[bucket_key] = {"gen": gen_before, "fp": fp, "entries": {}}

    value = builder()
    stored = deepcopy(value) if copy_result else value
    with _LOCK:
        bucket = _VAULT_CACHE.get(bucket_key)
        if bucket is not None and bucket["gen"] == gen_before and bucket["fp"] == fp:
            bucket["entries"][entry_key] = stored
    return deepcopy(stored) if copy_result else stored


def invalidate_cache(root: Path | None = None) -> None:
    """Invalidate process-level vault and page caches for `root` (or all roots if None)."""
    global _GLOBAL_GEN
    snap = _snapshot.get()
    if snap is not None:
        for k in [k for k in snap if isinstance(k, tuple) and k and k[0] == "vault-fingerprint"]:
            snap.pop(k, None)
    with _LOCK:
        _GLOBAL_GEN += 1
        if root is None:
            _VAULT_CACHE.clear()
            _PAGE_CACHE.clear()
            return
        root_norm = os.path.normcase(str(root.resolve()))
        for bucket_key, bucket in _VAULT_CACHE.items():
            if bucket_key[0] != root_norm:
                continue
            bucket["gen"] += 1
            bucket["fp"] = None
            bucket["entries"].clear()
        prefix = root_norm.rstrip("\\/") + os.sep
        stale_pages = [
            k for k in _PAGE_CACHE
            if os.path.normcase(k[0]) == root_norm or os.path.normcase(k[0]).startswith(prefix)
        ]
        for k in stale_pages:
            _PAGE_CACHE.pop(k, None)


def backlinks_index(root: Path) -> dict[str, list[dict[str, Any]]]:
    """Process-level cached reverse-link index keyed by vault-relative POSIX target path."""
    resolved_root = root.resolve()

    def build() -> dict[str, list[dict[str, Any]]]:
        from .catalog import readable_pages
        from .links import extract_links, resolve
        from .pages import read_page

        index: dict[str, list[dict[str, Any]]] = {}
        for other_raw, _ in readable_pages(resolved_root):
            other = other_raw.resolve()
            if not other.is_relative_to(resolved_root):
                continue
            try:
                other_meta, other_body = read_page(other)
            except Exception:
                continue
            other_rel = other.relative_to(resolved_root).as_posix()
            other_entry = {
                "path": other_rel,
                "title": other_meta["title"],
                "type": other_meta["type"],
            }
            seen_targets: set[str] = set()
            for raw_target in extract_links(other_body):
                try:
                    target = resolve(resolved_root, raw_target).resolve()
                except (OSError, RuntimeError, ValueError):
                    continue
                if target == other or not target.is_relative_to(resolved_root):
                    continue
                target_rel = target.relative_to(resolved_root).as_posix()
                if target_rel in seen_targets:
                    continue
                seen_targets.add(target_rel)
                index.setdefault(target_rel, []).append(other_entry)
        for items in index.values():
            items.sort(key=lambda item: item["title"])
        return index

    return cached_vault_value(resolved_root, "backlinks_index", build, copy_result=False)

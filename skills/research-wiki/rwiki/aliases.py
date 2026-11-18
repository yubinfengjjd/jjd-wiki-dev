"""Type-aware canonical ID and legacy alias resolution with path confinement."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Sequence

from .confine import confined
from .errors import WikiError
from .pages import read_page
from .read_cache import remember

ALIAS_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")

DIR_TO_TYPE: dict[str, str] = {
    "templates": "template",
    "methods": "method",
    "recipes": "recipe",
    "layouts": "layout",
    "scenarios": "scenario",
    "interfaces": "interface",
    "chart-types": "chart-type",
    "projects": "project",
    "sources": "source",
}
TYPE_TO_DIR: dict[str, str] = {page_type: folder for folder, page_type in DIR_TO_TYPE.items()}
SCAN_DIRS: tuple[str, ...] = tuple(DIR_TO_TYPE.keys())


def _has_unsafe_chars(value: str) -> bool:
    return (
        not value
        or "\\" in value
        or ":" in value
        or any(ord(char) < 32 for char in value)
    )


def _is_safe_token(token: str) -> bool:
    return (
        isinstance(token, str)
        and not _has_unsafe_chars(token)
        and "/" not in token
        and token not in (".", "..")
        and not token.startswith(".")
        and token == token.rstrip(" .")
    )


def _split_safe_rel_path(rel_path: str) -> list[str] | None:
    if (
        not isinstance(rel_path, str)
        or _has_unsafe_chars(rel_path)
        or rel_path.startswith("/")
        or rel_path.endswith("/")
        or Path(rel_path).anchor
    ):
        return None
    parts = rel_path.split("/")
    for part in parts:
        if not part or part in (".", "..") or part.startswith(".") or part != part.rstrip(" ."):
            return None
    return parts


def _confined_file(path: Path, base: Path, wiki_root: Path) -> Path | None:
    try:
        if not path.is_file():
            return None
        resolved_root = wiki_root.resolve()
        resolved_base = base.resolve()
        resolved_path = path.resolve()
        if resolved_path.is_relative_to(resolved_base) and resolved_base.is_relative_to(resolved_root):
            return resolved_path
        if confined(path, base, wiki_root):
            return Path(os.path.abspath(path))
    except (OSError, RuntimeError, ValueError):
        return None
    return None


def _build_index(
    wiki_root: Path,
) -> tuple[dict[tuple[str, str], Path], set[str], set[tuple[str, str]]]:
    alias_map: dict[tuple[str, str], Path] = {}
    canonical_names: set[str] = set()
    ambiguous_aliases: set[tuple[str, str]] = set()

    for folder in SCAN_DIRS:
        expected_type = DIR_TO_TYPE[folder]
        folder_dir = wiki_root / folder
        if not folder_dir.is_dir():
            continue
        for page_path in sorted(folder_dir.glob("*.md")):
            confined_page = _confined_file(page_path, folder_dir, wiki_root)
            if confined_page is None:
                continue
            canonical_names.add(page_path.stem)
            try:
                meta, _ = read_page(confined_page)
            except (WikiError, OSError, UnicodeDecodeError):
                continue
            page_type = meta.get("type")
            if isinstance(page_type, str) and page_type in TYPE_TO_DIR:
                ptype = page_type
            else:
                ptype = expected_type
            declared_id = meta.get("id") or meta.get("slug")
            if isinstance(declared_id, str) and declared_id.strip():
                canonical_names.add(declared_id.strip())
            aliases = meta.get("aliases")
            if not isinstance(aliases, list):
                continue
            for raw_alias in aliases:
                if not isinstance(raw_alias, str) or not ALIAS_PATTERN.fullmatch(raw_alias):
                    continue
                key = (ptype, raw_alias)
                if key in alias_map and alias_map[key] != confined_page:
                    ambiguous_aliases.add(key)
                else:
                    alias_map[key] = confined_page

    return alias_map, canonical_names, ambiguous_aliases


def _alias_index(
    wiki_root: Path,
) -> tuple[dict[tuple[str, str], Path], set[str], set[tuple[str, str]]]:
    root = Path(wiki_root).resolve()
    return remember(("alias-index", root), lambda: _build_index(root))


def resolve_page_ref(
    root: Path,
    ref: str,
    *,
    expected_type: str | None = None,
    expected_types: Sequence[str] | None = None,
) -> Path | None:
    """Resolve a canonical ID, typed relative path, or legacy alias to a confined page path."""
    if not isinstance(ref, str) or not ref or ref != ref.strip() or _has_unsafe_chars(ref):
        return None
    wiki_root = Path(root).resolve()

    if "/" in ref:
        parts = _split_safe_rel_path(ref)
        if parts is None or len(parts) != 2:
            return None
        folder, leaf = parts
        if folder not in DIR_TO_TYPE:
            return None
        inferred_type = DIR_TO_TYPE[folder]
        if expected_type is not None and inferred_type != expected_type:
            return None
        if expected_types is not None and inferred_type not in expected_types:
            return None
        if leaf.endswith(".md"):
            stem = leaf[:-3]
        elif "." in leaf:
            return None
        else:
            stem = leaf
        if not _is_safe_token(stem):
            return None
        target_types: tuple[str, ...] = (inferred_type,)
    else:
        if expected_type is not None:
            if expected_type not in TYPE_TO_DIR:
                return None
            target_types = (expected_type,)
        elif expected_types is not None:
            target_types = tuple(ptype for ptype in expected_types if ptype in TYPE_TO_DIR)
            if not target_types:
                return None
        else:
            target_types = tuple(TYPE_TO_DIR.keys())
        if ref.endswith(".md"):
            stem = ref[:-3]
        elif "." in ref:
            return None
        else:
            stem = ref
        if not _is_safe_token(stem):
            return None

    # Canonical files on disk always win in caller-specified type precedence order.
    for ptype in target_types:
        folder = TYPE_TO_DIR[ptype]
        candidate = wiki_root / folder / f"{stem}.md"
        confined_page = _confined_file(candidate, wiki_root / folder, wiki_root)
        if confined_page is not None:
            return confined_page

    if not ALIAS_PATTERN.fullmatch(stem):
        return None

    alias_map, canonical_names, ambiguous_aliases = _alias_index(wiki_root)
    if stem in canonical_names:
        return None

    matches: list[Path] = []
    for ptype in target_types:
        key = (ptype, stem)
        if key in ambiguous_aliases:
            return None
        target = alias_map.get(key)
        if target is not None:
            matches.append(target)

    if len(matches) == 1:
        return matches[0]
    return None


def resolve_asset_subpath(root: Path, rel_path: str) -> Path | None:
    """Resolve `<kind>/<id_or_alias>/<subpath...>` to a confined existing asset file."""
    parts = _split_safe_rel_path(rel_path)
    if parts is None or len(parts) < 3:
        return None
    folder, entry_ref, *subparts = parts
    if folder not in DIR_TO_TYPE or not _is_safe_token(entry_ref):
        return None

    wiki_root = Path(root).resolve()
    direct_dir = wiki_root / folder / entry_ref
    direct_file = direct_dir.joinpath(*subparts)
    confined_direct = _confined_file(direct_file, direct_dir, wiki_root)
    if confined_direct is not None:
        return confined_direct

    page_path = resolve_page_ref(wiki_root, entry_ref, expected_type=DIR_TO_TYPE[folder])
    if page_path is None:
        return None

    asset_dir = page_path.with_suffix("")
    candidate = asset_dir.joinpath(*subparts)
    return _confined_file(candidate, asset_dir, wiki_root)


def alias_errors(
    meta: dict,
    page_path: Path,
    seen_aliases: dict[tuple[str, str], str],
    canonical_ids: dict[tuple[str, str], str],
) -> list[str]:
    """Validate optional `aliases` frontmatter for format, duplicates, cycles, and ID collisions."""
    if "aliases" not in meta:
        return []
    raw_aliases = meta.get("aliases")
    if not isinstance(raw_aliases, list):
        return ["aliases 必须为字符串列表"]

    page_type = str(meta.get("type") or DIR_TO_TYPE.get(page_path.parent.name, ""))
    owner = page_path.as_posix()
    own_id = str(meta.get("id") or meta.get("slug") or page_path.stem)

    errors: list[str] = []
    seen_local: set[str] = set()
    for item in raw_aliases:
        if not isinstance(item, str) or not item.strip():
            errors.append("aliases 元素必须为非空字符串")
            continue
        if any(token in item for token in ("..", "/", "\\", ":")) or not ALIAS_PATTERN.fullmatch(item):
            errors.append(
                f"alias 非法（需匹配 [A-Za-z0-9][A-Za-z0-9_-]* 且不含路径分隔符）: {item}"
            )
            continue
        if item in seen_local:
            errors.append(f"页内 aliases 重复: {item}")
            continue
        seen_local.add(item)

        if item == own_id or item == page_path.stem:
            errors.append(f"alias 不能与本页规范 id 相同: {item}")
            continue

        if (page_type, item) in canonical_ids:
            errors.append(f"alias 与同类型页面规范 id 冲突: {item} ({canonical_ids[(page_type, item)]})")
            continue

        cross = [
            (ctype, cowner)
            for (ctype, cid), cowner in canonical_ids.items()
            if cid == item and ctype != page_type
        ]
        if cross:
            ctype, cowner = cross[0]
            errors.append(f"alias 与 {ctype} 页面规范 id 冲突: {item} ({cowner})")
            continue

        prev_owner = seen_aliases.get((page_type, item))
        if prev_owner is not None and prev_owner != owner:
            errors.append(f"alias 与同类型其他页面重复: {item} ({prev_owner})")
            continue
        seen_aliases[(page_type, item)] = owner

    return errors

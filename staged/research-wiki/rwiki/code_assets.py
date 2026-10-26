"""Read-only access to existing code; nothing in this module imports asset code.

Public paths are opaque names returned by ``code_files``. Wiki assets use
``source/...`` or ``code/...``; a template's gallery originals use
``gallery/<layout-id>/original_code/...``. An optional entry-local
``code-manifest.json`` may contain ``{"files": [{"variant": "original",
"path": "source/main.py", "language": "python", "source": "...",
"encoding": "gb18030", "verification": {"state": "not_run"}}]}``.
Its paths describe already discovered files, never additional filesystem roots.
Gallery manifests use paths local to their gallery entry, without the public
``gallery/<layout-id>/`` prefix. Hashes and sizes are always measured from bytes.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .config import Config
from .errors import WikiError
from .pages import read_page


MAX_PREVIEW_BYTES = 1024 * 1024
_KINDS = {"methods": "method", "layouts": "layout", "templates": "template"}
_SKIP_DIRS = {"__pycache__", "node_modules", "venv", "env", "cache", "caches"}
_SKIP_NAMES = {"article.html", "source.md", "manifest.json", "code-manifest.json"}
_LANGUAGES = {".py": "python", ".pyi": "python", ".r": "r", ".rmd": "r",
              ".ipynb": "json", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
              ".toml": "toml", ".txt": "text", ".ini": "ini", ".cfg": "ini",
              ".conf": "text", ".csv": "csv", ".tsv": "text", ".xml": "xml",
              ".html": "html", ".htm": "html", ".js": "javascript", ".ts": "typescript",
              ".css": "css", ".sh": "bash", ".bat": "batch", ".ps1": "powershell",
              ".sql": "sql", ".c": "c", ".h": "c", ".cpp": "cpp", ".jl": "julia",
              ".m": "matlab", ".tex": "latex"}
_BINARY = {".bin", ".pkl", ".pickle", ".rds", ".rdata", ".zip", ".gz", ".pdf",
           ".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".exe", ".dll", ".so"}
_ALIASES = {"py": "python", "rscript": "r", "yml": "yaml", "plain": "text",
            "plaintext": "text", "js": "javascript", "shell": "bash"}


@dataclass
class _Asset:
    file: Path
    variant: str
    path: str
    language: str
    source: str
    generated: bool = False
    encoding: str | None = None
    verification: dict = field(default_factory=lambda: {
        "state": "unknown", "scope": "未提供执行验证记录", "evidence": []})


def _relative(value: str) -> bool:
    """Reject Windows and POSIX path tricks on every host, before normalization."""
    return (isinstance(value, str) and bool(value) and not value.startswith("/")
            and "\\" not in value and ":" not in value
            and not any(ord(char) < 32 for char in value)
            and all(part not in ("", ".", "..") and part == part.rstrip(" .")
                    for part in value.split("/")))


def _link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _confined(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return False


def _safe_existing(path: Path, root: Path) -> bool:
    if not _confined(path, root):
        return False
    # Even an in-root directory link can create cycles or unexpected aliases.
    for parent in (path, *path.parents):
        if parent == root:
            break
        if _link(parent):
            return False
    return True


def _page(config: Config, page_path: str) -> tuple[Path, dict]:
    if not _relative(page_path):
        raise WikiError("代码页面路径无效")
    parts = PurePosixPath(page_path).parts
    if len(parts) != 2 or parts[0] not in _KINDS or not parts[1].endswith(".md"):
        raise WikiError("只接受 methods、layouts、templates 的实际页面")
    root = config.wiki_root.resolve()
    target = root.joinpath(*parts)
    if not _safe_existing(target, root) or not target.is_file():
        raise WikiError("代码页面不存在")
    meta, _ = read_page(target)
    if meta.get("type") != _KINDS[parts[0]] or meta.get("id") != target.stem:
        raise WikiError("代码页面类型或标识不符")
    return target, meta


def _json(path: Path, boundary: Path):
    if (not _safe_existing(path, boundary) or not path.is_file()
            or path.stat().st_size > MAX_PREVIEW_BYTES):
        return None
    try:
        return json.loads(path.read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _walk(root: Path, boundary: Path):
    if not _safe_existing(root, boundary) or not root.is_dir():
        return
    try:
        children = sorted(root.iterdir())
    except OSError:
        return
    for path in children:
        name = path.name.lower()
        if name.startswith(".") or not _safe_existing(path, boundary):
            continue
        if path.is_dir():
            if name not in _SKIP_DIRS:
                yield from _walk(path, boundary)
        elif (path.is_file() and name not in _SKIP_NAMES
              and not name.startswith("readme") and path.suffix.lower() not in
              {".md", ".rst", ".pyc", ".pyo"}):
            yield path


def _language(path: Path) -> str:
    extension = path.suffix.lower()
    if extension == ".txt" and len(path.suffixes) > 1:
        hint = path.suffixes[-2].lstrip(".").lower()
        if hint in set(_LANGUAGES.values()) | {"makefile"}:
            return hint
    if path.name.lower() == "makefile":
        return "makefile"
    return _LANGUAGES.get(extension, "binary" if extension in _BINARY else "unknown")


def _metadata(asset: _Asset, row: dict, *, legacy: bool = False) -> None:
    if not isinstance(row, dict):
        return
    language = row.get("language") or row.get("original_language")
    fence = row.get("original_fence_language") or row.get("fence_language")
    language = language or fence
    if isinstance(language, str) and re.fullmatch(r"[\w+.-]{1,40}", language):
        if asset.file.suffix.lower() == ".txt" or asset.language == "unknown":
            asset.language = _ALIASES.get(language.lower(), language.lower())
    if fence:
        asset.source += f"；原始 fence 标签：{str(fence)[:80]}（未核实语法）"
    source = row.get("source")
    # A descriptive manifest cannot turn generated reconstruction into author code.
    if isinstance(source, str) and source.strip() and not asset.generated:
        asset.source += f"；清单来源说明（未经独立核验）：{source[:2000]}"
    if isinstance(row.get("encoding"), str) and row["encoding"].lower().replace("-", "") == "gb18030":
        asset.encoding = "gb18030"
    verification = row.get("verification")
    if isinstance(verification, dict):
        state = verification.get("state")
        if isinstance(state, str):
            asset.verification = {"state": state[:80],
                                  "scope": str(verification.get("scope", ""))[:4000],
                                  "evidence": verification.get("evidence", []),
                                  "basis": "清单声明，查看接口未独立执行验证"}
    elif legacy and (row.get("executed") is False
                     or row.get("execution") == "archived_only"):
        asset.verification = {"state": "not_run", "scope": "来源清单记录仅归档、未执行",
                              "evidence": []}


def _group(assets: list[_Asset], owner: Path, folder: str, boundary: Path,
           variant: str, source: str, prefix: str = "", generated: bool = False) -> None:
    root = owner / folder
    descriptors = _json(owner / "code-manifest.json", boundary)
    rows = descriptors.get("files", []) if isinstance(descriptors, dict) else []
    indexed = {(row.get("variant"), row.get("path")): row for row in rows
               if isinstance(row, dict) and isinstance(row.get("path"), str)
               and _relative(row["path"]) and isinstance(row.get("variant"), str)} if isinstance(rows, list) else {}
    legacy = _json(root / "manifest.json", boundary)
    blocks = legacy.get("blocks", []) if isinstance(legacy, dict) else legacy
    native = {row["file"]: row for row in blocks if isinstance(row, dict)
              and isinstance(row.get("file"), str) and _relative(row["file"])} if isinstance(blocks, list) else {}
    for path in _walk(root, boundary):
        rel = path.relative_to(root).as_posix()
        if not _relative(rel):
            continue
        local = f"{folder}/{rel}"
        historical = any(word in path.name.lower() for word in
                         ("reconstruction", "reconstructed", "replica"))
        is_generated = generated or historical
        label = source
        if historical and not generated:
            label = "归档的历史重建/复刻代码（生成；非作者原版；复用未验证）"
        entry = _Asset(path.resolve(), variant, prefix + local, _language(path), label,
                       generated=is_generated)
        _metadata(entry, native.get(rel, {}), legacy=True)
        _metadata(entry, indexed.get((variant, local), {}))
        assets.append(entry)


def _gallery(config: Config, meta: dict) -> tuple[Path, dict] | None:
    relative = meta.get("gallery_entry")
    if not _relative(relative):
        source = meta.get("source")
        if isinstance(source, dict):
            relative = source.get("gallery_entry")
    if not _relative(relative):
        return None
    boundary = config.gallery_root.resolve()
    entry = boundary.joinpath(*PurePosixPath(relative).parts)
    info = _json(entry / "meta.json", boundary)
    # A method may point at a gallery entry whose id differs from its own id;
    # gallery ids are <post>__<figure>, while the pointer is <post>/figures/<figure>.
    parts = PurePosixPath(relative).parts
    derived = (f"{parts[-3]}__{parts[-1]}"
               if len(parts) >= 3 and parts[-2] == "figures" else None)
    expected = {meta.get("id"), PurePosixPath(relative).name, derived}
    if not isinstance(info, dict) or info.get("id", meta.get("id")) not in expected:
        return None
    return entry, info


def _gallery_originals(assets: list[_Asset], config: Config, meta: dict,
                       prefix: str = "") -> None:
    result = _gallery(config, meta)
    if result is None:
        return
    root, gallery = result
    source = "画廊来源归档（原始版本分类；作者身份及完整性未核实）"
    provenance = gallery.get("original_code_provenance")
    if provenance == "example_not_target":
        source += "；来源示例，非目标图生成代码"
    elif provenance == "archived_only":
        source += "；仅归档，不代表可直接运行"
    elif isinstance(provenance, str):
        source += f"；来源标记：{provenance[:100]}"
    _group(assets, root, "original_code", config.gallery_root.resolve(), "original",
           source, prefix)


def _discover(config: Config, page_path: str) -> list[_Asset]:
    page, meta = _page(config, page_path)
    assets: list[_Asset] = []
    boundary = config.wiki_root.resolve()
    owner = page.with_suffix("")
    if meta["type"] in ("method", "template"):
        _group(assets, owner, "source", boundary, "original",
               "Wiki 来源归档（原始版本分类；不据目录名推定作者原版或完整算法）")
        _group(assets, owner, "code", boundary, "reusable",
               "Wiki 复用/改造代码；具体实现与验证范围以条目和记录为准")
    if meta["type"] == "method":
        # Methods from a gallery entry share the immutable raw archive there;
        # do not require a second copy under methods/<id>/source/.
        source_meta = meta.get("source")
        relative = source_meta.get("gallery_entry") if isinstance(source_meta, dict) else None
        prefix = f"gallery/{PurePosixPath(relative).name}/" if _relative(relative) else ""
        _gallery_originals(assets, config, meta, prefix)
    if meta["type"] == "layout":
        _gallery_originals(assets, config, meta)
        gallery = _gallery(config, meta)
        if gallery is not None:
            _group(assets, gallery[0], "code", config.gallery_root.resolve(), "reusable",
                   "画廊复刻/重建代码（生成；非作者原版；复用未验证）", generated=True)
    if meta["type"] == "template":
        origins = meta.get("layouts", [])
        for origin in sorted(set(value for value in origins if isinstance(value, str))) if isinstance(origins, list) else []:
            try:
                _, layout = _page(config, f"layouts/{origin}.md")
            except (WikiError, UnicodeError):
                continue
            _gallery_originals(assets, config, layout, f"gallery/{origin}/")
    return sorted(assets, key=lambda item: (item.variant != "original", item.path))


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decode(asset: _Asset, size: int) -> tuple[str | None, str | None, str]:
    if size > MAX_PREVIEW_BYTES:
        return None, None, "文件超过 1 MiB 文本查看上限，请下载原文件。"
    if asset.language in ("binary", "unknown"):
        return None, None, "二进制或未知文件类型，仅提供原字节下载。"
    raw = asset.file.read_bytes()
    if b"\x00" in raw or any(byte < 9 or 13 < byte < 32 for byte in raw):
        return None, None, "内容包含二进制控制字节，仅提供原字节下载。"
    encodings = ["utf-8-sig"] if raw.startswith(b"\xef\xbb\xbf") else ["utf-8"]
    coding = re.search(br"^[ \t\f]*\#.*?coding[:=]\s*([-\w.]+)",
                       b"\n".join(raw.splitlines()[:2]), re.M)
    declared_gb = (asset.language == "python" and coding is not None
                   and coding.group(1).lower().replace(b"-", b"") == b"gb18030")
    if asset.encoding == "gb18030" or declared_gb:
        encodings.append("gb18030")
    for encoding in encodings:
        try:
            return raw.decode(encoding), encoding, "只读原文；未执行、导入或渲染代码。"
        except UnicodeDecodeError:
            continue
    return None, None, "无法可靠确认文本编码；未作替换解码，请下载原文件。"


def _selected(config: Config, page_path: str, variant: str, path: str) -> _Asset:
    if variant not in ("original", "reusable") or not _relative(path):
        raise WikiError("代码版本或文件路径无效")
    for asset in _discover(config, page_path):
        if asset.variant == variant and asset.path == path:
            return asset
    raise WikiError("代码文件不存在或不在此条目的资产清单中")


def _implementation_branches(page: Path, meta: dict) -> dict[str, list[dict]]:
    """Map entrypoint files to their declared branches; never infer a branch from a helper file."""
    if meta.get("type") != "method":
        return {}
    from .method_implementations import implementation_status
    result: dict[str, list[dict]] = {}
    items = meta.get("implementations", [])
    if not isinstance(items, list):
        return result
    statuses = implementation_status(page, meta)
    for item, status in zip(items, statuses):
        if not isinstance(item, dict):
            continue
        entry = str(item.get("entrypoint", "")).partition(":")[0]
        if not entry:
            continue
        result.setdefault(entry, []).append({
            "id": item.get("id", ""),
            "title": item.get("title", ""),
            "state": status.get("state", "invalid"),
            "scope": status.get("scope", ""),
            "runtime": status.get("runtime"),
            "receipt": f"methods/{meta.get('id')}/{item['verification']}"
                       if item.get("verification") else "",
        })
    return result


def _branch_verification(branches: list[dict]) -> dict:
    states = {branch["state"] for branch in branches}
    state = "verified" if states == {"verified"} else "mixed" if len(states) > 1 else next(iter(states))
    scope = "；".join(
        f"{branch['id']}（{branch['title']}）：{branch['state']} — {branch['scope'] or '未声明验证范围'}"
        for branch in branches)
    evidence = [branch["receipt"] for branch in branches if branch.get("receipt")]
    return {"state": state, "scope": scope[:4000], "evidence": evidence,
            "basis": "由 implementation_status 按入口分支派生；不核对外部已安装依赖"}


def code_files(config: Config, page_path: str) -> dict:
    """List only existing entry-owned assets and explicitly linked gallery code."""
    page, meta = _page(config, page_path)
    branches_by_file = _implementation_branches(page, meta)
    files = []
    for asset in _discover(config, page_path):
        size = asset.file.stat().st_size
        text, _, _ = _decode(asset, size)
        branches = branches_by_file.get(asset.path, []) if asset.variant == "reusable" else []
        verification = _branch_verification(branches) if branches else asset.verification
        files.append({"variant": asset.variant, "path": asset.path, "language": asset.language,
                      "size": size, "sha256": _hash(asset.file), "text": text is not None,
                      "source": asset.source, "verification": verification,
                      "branches": branches})
    note = ("只读代码资产；原始版本保持来源清单状态，复用版按入口分支派生实现收据。"
            "共享文件列出其全部分支；文本查看上限 1 MiB。"
            if files else "暂无可查看的代码资产；未生成代码。")
    runtime = None
    if meta.get("type") == "template":
        from .runtime_contract import runtime_facts
        runtime = runtime_facts(page.with_suffix(''), meta['id'], 'template')
    return {"files": files, "note": note, "runtime": runtime}


def read_code(config: Config, page_path: str, variant: str, path: str) -> dict:
    """Return strict text decoding, or an explicit original-download fallback."""
    asset = _selected(config, page_path, variant, path)
    size = asset.file.stat().st_size
    text, encoding, note = _decode(asset, size)
    return {"path": asset.path, "variant": asset.variant, "language": asset.language,
            "text": text, "encoding": encoding, "note": note,
            "sha256": _hash(asset.file), "size": size}


def code_file(config: Config, page_path: str, variant: str, path: str) -> Path:
    """Return the confined existing file for an original-byte FileResponse."""
    return _selected(config, page_path, variant, path).file

"""v2 来源登记（2026-10-27）：上游库 = 来源页 + 固定 commit 的本地快照 + L0 目录。

- 来源页 `sources/<id>.md` 记 URL、commit、许可证、适配器、是否白名单；作者备注在 user 区块。
- 快照是 `config.sources_root/<snapshot>` 下的 git 部分克隆（blob 按需取、稀疏检出），不进 Wiki。
- L0 目录 `sources/<id>/items.jsonl` 由适配器从快照生成，一行一个上游条目；不复制上游代码。
"""
import json
import os
import re
import subprocess
from pathlib import Path

from .config import Config
from .errors import WikiError
from .pages import read_page, write_page

# License classification is preserved; knowledge is tracked by default (author policy 2026-11-02).
RESTRICTED_LICENSE = re.compile(r"^(?:(?:A|L)?GPL|CC-BY(?:-[A-Z]+)*-(?:NC|SA|ND))", re.I)
SOURCE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


def restricted_license(value) -> bool:
    return isinstance(value, str) and bool(RESTRICTED_LICENSE.match(value.strip()))


def source_page(config: Config, source_id: str) -> Path:
    return config.wiki_root / "sources" / f"{source_id}.md"


def load_source(config: Config, source_id: str) -> tuple[dict, str]:
    page = source_page(config, source_id)
    if not page.is_file():
        raise WikiError(f"来源未登记: {source_id}（先 source add）")
    meta, body = read_page(page)
    if meta.get("type") != "source":
        raise WikiError(f"不是来源页: {page}")
    return meta, body


def snapshot_dir(config: Config, meta: dict) -> Path:
    if config.sources_root is None:
        raise WikiError("配置缺少 sources_root（上游快照目录，不在 Wiki 内）")
    return config.sources_root / meta["snapshot"]


def items_path(config: Config, source_id: str) -> Path:
    return config.wiki_root / "sources" / source_id / "items.jsonl"


def read_items(config: Config, source_id: str) -> list[dict]:
    path = items_path(config, source_id)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_items(config: Config, source_id: str, items: list[dict]) -> Path:
    path = items_path(config, source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                   for item in sorted(items, key=lambda value: value["item"]))
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def find_item(config: Config, source_id: str, item: str) -> dict:
    for record in read_items(config, source_id):
        if record["item"] == item:
            return record
    raise WikiError(f"来源 {source_id} 的目录中没有条目 {item}（先 source scan）")


def add_source(config: Config, source_id: str, *, title: str, url: str, license: str, adapter: str,
               trusted: bool, cite: list[str], notice: str = "") -> Path:
    from .adapters import ADAPTERS
    from .store import guarded, save

    if not SOURCE_ID.match(source_id):
        raise WikiError("来源 id 用小写字母、数字与连字符")
    if adapter not in ADAPTERS:
        raise WikiError(f"未知适配器 {adapter}；可用：{'、'.join(sorted(ADAPTERS))}")
    page = source_page(config, source_id)
    if page.exists():
        raise WikiError(f"来源已登记: {source_id}")
    meta = {"type": "source", "id": source_id, "title": title, "url": url, "commit": "",
            "license": license, "license_notice": notice, "cite": cite, "adapter": adapter,
            "trusted": trusted, "snapshot": source_id, "tags": [], "keywords": [], "summary": ""}
    body = (f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
            "## 这是什么\n\n## 怎么用\n\n"
            "- 检索：`wiki.py find <关键词>`；L0 条目可直接 `wiki.py use <来源>:<条目> --project <课题>`。\n"
            f"- 升级为 L1 配方：`wiki.py promote {source_id} <条目>…`，再 `wiki.py run <配方 id>`。\n\n"
            "## 许可与引用\n\n## 知识关联检查\n\n<!-- user:start -->\n<!-- user:end -->\n")
    with guarded(config, page):
        write_page(page, meta, body)
        save(config, f"source add {source_id}")
    return page


def _git(directory: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", "-c", "core.longpaths=true", "-C", str(directory), *args],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if check and result.returncode:
        raise WikiError(f"git {' '.join(args)} 失败: {result.stderr.strip()[-800:]}")
    return result.stdout


def _git_dir(target: Path) -> Path:
    value = Path(_git(target, "rev-parse", "--git-dir").strip())
    return value if value.is_absolute() else target / value


def _sparse_set(target: Path, patterns: list[str]) -> None:
    """git <2.25 lacks ``sparse-checkout``; use the classic info/sparse-checkout file."""
    try:
        _git(target, "sparse-checkout", "set", "--no-cone", *patterns)
        return
    except WikiError:
        pass
    _git(target, "config", "core.sparseCheckout", "true")
    info = _git_dir(target) / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "sparse-checkout").write_text("\n".join(patterns) + "\n", encoding="utf-8", newline="\n")
    _git(target, "read-tree", "-mu", "HEAD")


def _sparse_list(target: Path) -> list[str]:
    try:
        out = _git(target, "sparse-checkout", "list")
    except WikiError:
        path = _git_dir(target) / "info" / "sparse-checkout"
        out = path.read_text(encoding="utf-8") if path.is_file() else ""
    return [line for line in out.splitlines() if line.strip()]


def _clone(target: Path, url: str) -> None:
    """git <2.19 lacks ``clone --filter``; fall back to a plain shallow clone."""
    try:
        _git(target.parent, "clone", "--filter=blob:none", "--no-checkout", "--depth", "1",
             url, target.name)
        return
    except WikiError:
        pass
    import shutil

    if target.exists():
        shutil.rmtree(target)
    _git(target.parent, "clone", "--no-checkout", "--depth", "1", url, target.name)


def fetch_source(config: Config, source_id: str, items: list[str] | None = None,
                 update: bool = False) -> dict:
    """Create or extend the partial sparse clone; returns {'commit', 'snapshot', 'added'}.

    Base patterns come from the adapter (metadata only); `items` adds whole item
    directories minus bulky reports. A snapshot that moved away from the recorded
    commit is refused unless `update` is given, so recipes stay reproducible.
    """
    from .adapters import ADAPTERS
    from .store import guarded, save

    meta, body = load_source(config, source_id)
    adapter = ADAPTERS[meta["adapter"]]
    target = snapshot_dir(config, meta)
    if not (target / ".git").exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        _clone(target, meta["url"])
        _git(target, "config", "core.longpaths", "true")
        _sparse_set(target, adapter.BASE_PATTERNS)
        _git(target, "checkout")
    patterns = _sparse_list(target)
    added = []
    for item in items or []:
        if not (target / item).is_dir() and not _git(target, "ls-tree", "-d", "HEAD", "--", item).strip():
            raise WikiError(f"上游没有条目目录: {item}")
        for pattern in adapter.item_patterns(item):
            if pattern not in patterns:
                patterns.append(pattern)
                added.append(pattern)
    if added:
        _sparse_set(target, patterns)
    commit = _git(target, "rev-parse", "HEAD").strip()
    if meta.get("commit") and meta["commit"] != commit and not update:
        raise WikiError(f"快照 commit {commit[:12]} 与来源页记录 {meta['commit'][:12]} 不同；"
                        "确认要更新时加 --update")
    if meta.get("commit") != commit:
        page = source_page(config, source_id)
        meta["commit"] = commit
        with guarded(config, page):
            write_page(page, meta, body)
            save(config, f"source fetch {source_id} {commit[:12]}")
    return {"commit": commit, "snapshot": meta["snapshot"], "added": added}


def scan_source(config: Config, source_id: str) -> dict:
    """Rebuild the L0 catalog from the snapshot; promoted items keep their recipe link."""
    from .adapters import ADAPTERS
    from .store import save

    meta, _ = load_source(config, source_id)
    adapter = ADAPTERS[meta["adapter"]]
    target = snapshot_dir(config, meta)
    if not target.is_dir():
        raise WikiError(f"快照不存在：先 source fetch {source_id}")
    commit = _git(target, "rev-parse", "HEAD").strip()
    items = adapter.scan(target, source_id, commit, meta)
    write_items(config, source_id, items)
    save(config, f"source scan {source_id}: {len(items)} items")
    return {"items": len(items), "commit": commit}

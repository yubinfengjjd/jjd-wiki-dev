"""Create method notes and record author confirmation."""

import re
import shutil
from pathlib import Path

from .config import Config
from .errors import WikiError
from .pages import read_page, write_page


def scaffold_method(config: Config, id: str, title: str, license: str,
                    from_entry: str | None = None, from_path: Path | None = None,
                    url: str | None = None, commit: str | None = None,
                    written: bool = False) -> None:
    if not re.fullmatch(r"[a-z0-9-]+", id):
        raise WikiError("方法 id 只允许 [a-z0-9-]")
    if not title.strip() or not license.strip():
        raise WikiError("方法 title 和 license 必须为非空字符串")
    if sum((from_entry is not None, from_path is not None, written)) != 1:
        raise WikiError("须选择 from_entry、from_path 或 written 一种来源")
    if (url is None) != (commit is None) or (url is not None and from_path is None):
        raise WikiError("repo 来源须同时提供 from_path、url 和 commit")
    if url is not None and (not url.strip() or not commit.strip()):
        raise WikiError("repo url 和 commit 必须为非空字符串")
    target = config.wiki_root / "methods" / id
    page = target.with_suffix(".md")
    if target.exists() or page.exists():
        raise WikiError(f"方法页或目录已存在: {id}")
    if written:
        source_meta = {"kind": "written"}
    else:
        if from_entry is not None:
            from .ingest import entry_path

            gallery = entry_path(config, from_entry)
            source = gallery / "original_code"
            source_meta = {"kind": "post", "gallery_entry": gallery.relative_to(config.gallery_root).as_posix()}
        else:
            source = Path(from_path).resolve()
            source_meta = ({"kind": "repo", "url": url, "commit": commit} if url is not None
                           else {"kind": "project", "path": str(source)})
        if not source.exists():
            raise WikiError(f"方法来源不存在: {source}")
        if source.is_dir():
            shutil.copytree(source, target / "source")
        else:
            (target / "source").mkdir(parents=True)
            shutil.copyfile(source, target / "source" / source.name)
    meta = {"type": "method", "id": id, "title": title, "status": "draft",
            "tags": [], "inputs": [], "outputs": [], "source": source_meta,
            "license": license, "cite": [], "favorite": False}
    body = (f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
            + "".join(f"## {heading}\n\n" for heading in
                      ("用途", "适用", "不适用", "输入", "怎么做", "代码", "输出", "使用记录"))
            + "<!-- user:start -->\n<!-- user:end -->\n")
    write_page(page, meta, body)
    from .store import save

    save(config, f"scaffold method {id}")


def confirm_method(config: Config, id: str) -> None:
    page = config.wiki_root / "methods" / f"{id}.md"
    meta, body = read_page(page)
    if meta["status"] != "draft":
        raise WikiError(f"方法必须为 draft: {id} ({meta['status']})")
    meta["status"] = "ready"
    write_page(page, meta, body)

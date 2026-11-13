import re
from pathlib import Path

from .config import Config, read_json
from .errors import WikiError
from .pages import read_page, write_page


def validate_columns(columns: dict) -> None:
    if not isinstance(columns, dict) or not columns:
        raise WikiError("interface.columns 必须为非空对象")
    for column, definition in columns.items():
        if not isinstance(column, str) or not column.strip():
            raise WikiError("interface.columns 列名必须为非空字符串")
        if not isinstance(definition, dict) or definition.get("type") not in ("float", "int", "str"):
            raise WikiError(f"interface.columns.{column}.type 非法")
        description = definition.get("description")
        if not isinstance(description, str) or not description.strip():
            raise WikiError(f"interface.columns.{column}.description 必须为非空字符串")
        if "required" in definition and not isinstance(definition["required"], bool):
            raise WikiError(f"interface.columns.{column}.required 必须为布尔值")


def load_interface(wiki_root: Path, slug: str) -> dict:
    if not isinstance(slug, str) or re.fullmatch(r"[a-z0-9-]+", slug) is None:
        raise WikiError(f"interface.slug 非法: {slug}")
    meta, _ = read_page(wiki_root / "interfaces" / f"{slug}.md")
    if meta.get("type") != "interface" or meta.get("slug") != slug:
        raise WikiError(f"接口 type 或 slug 不一致: {slug}")
    if not isinstance(meta.get("title"), str) or not meta["title"].strip():
        raise WikiError(f"interface.title 必须为非空字符串: {slug}")
    validate_columns(meta.get("columns"))
    return meta


def add_interface(config: Config, slug: str, title: str, columns_path: Path) -> None:
    if not isinstance(slug, str) or re.fullmatch(r"[a-z0-9-]+", slug) is None:
        raise WikiError(f"interface.slug 非法: {slug}")
    path = config.wiki_root / "interfaces" / f"{slug}.md"
    if path.exists():
        raise WikiError(f"接口已存在: {slug}")
    if not isinstance(title, str) or not title.strip():
        raise WikiError("interface.title 必须为非空字符串")
    columns = read_json(columns_path)
    validate_columns(columns)
    meta = {"type": "interface", "slug": slug, "title": title, "columns": columns}
    body = (f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
            "## 含义\n\n<!-- user:start -->\n<!-- user:end -->\n")
    write_page(path, meta, body)
    from .store import save

    save(config, f"add interface {slug}")

import re
from pathlib import Path

import yaml

from .errors import WikiError


def parse_page(text: str) -> tuple[dict, str, str | None]:
    newline = "\r\n" if text.startswith("---\r\n") else "\n"
    opening, closing = "---" + newline, newline + "---" + newline
    if not text.startswith(opening) or closing not in text[len(opening):]:
        return {}, text, "frontmatter 缺失或未闭合"
    header, body = text[len(opening):].split(closing, 1)
    try:
        meta = yaml.safe_load(header)
    except yaml.YAMLError as error:
        return {}, body, f"frontmatter YAML 无法解析: {error}"
    if not isinstance(meta, dict):
        return {}, body, "frontmatter 必须为映射"
    return meta, body, None


def read_page(path: Path) -> tuple[dict, str]:
    if not path.is_file():
        raise WikiError(f"页面不存在: {path}")
    # Author blocks are protected bytes, including their line endings.
    # Universal newline conversion would silently alter them during facts refresh.
    with path.open(encoding="utf-8", newline="") as stream:
        meta, body, error = parse_page(stream.read())
    if error:
        raise WikiError(f"{path}: {error}")
    return meta, body


def visual_path(root: Path, entry_id: str) -> Path:
    for kind in ("templates", "layouts", "methods"):
        path = root / kind / f"{entry_id}.md"
        if path.is_file():
            return path
    raise WikiError(f"模板、版式或方法页不存在: {entry_id}")


def write_page(path: Path, meta: dict, body: str) -> None:
    header = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{header}---\n{body}", encoding="utf-8", newline="\n")


def block_error(body: str, name: str) -> str | None:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    if body.count(start) != 1 or body.count(end) != 1:
        return f"{name} 区块标记缺失或重复"
    if body.index(start) > body.index(end):
        return f"{name} 区块标记顺序颠倒"
    return None


def block_bounds(body: str, name: str) -> tuple[int, int]:
    error = block_error(body, name)
    if error:
        raise WikiError(error)
    return body.index(f"<!-- {name}:start -->") + len(f"<!-- {name}:start -->"), body.index(f"<!-- {name}:end -->")


def get_block(body: str, name: str) -> str:
    start, end = block_bounds(body, name)
    return body[start:end]


def set_block(body: str, name: str, text: str) -> str:
    start, end = block_bounds(body, name)
    return body[:start] + text + body[end:]


def section_bounds(body: str, title: str) -> tuple[int, int]:
    # Ignore headings inside the author's block while retaining original offsets.
    start, end = block_bounds(body, "user")
    agent_body = body[:start] + re.sub(r"[^\n]", " ", body[start:end]) + body[end:]
    section = re.search(rf"^## {re.escape(title)}[ \t]*\r?\n(.*?)(?=^## |\Z)",
                        agent_body, re.M | re.S)
    if section is None:
        raise WikiError(f"缺少{title}节")
    content_start, content_end = section.span(1)
    user_marker = body.index("<!-- user:start -->")
    if content_start <= user_marker < content_end:
        content_end = user_marker
    return content_start, content_end


def section_text(body: str, title: str) -> str:
    start, end = section_bounds(body, title)
    return body[start:end].strip()

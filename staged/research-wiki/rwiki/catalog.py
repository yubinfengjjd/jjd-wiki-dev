from pathlib import Path

from .errors import WikiError
from .pages import read_page

LAYOUT_STATUSES = ("pending_signoff", "pending_template", "ready", "archived")
TEMPLATE_STATUSES = ("draft", "ready", "archived")
METHOD_STATUSES = ("draft", "ready", "archived")
PAGE_DIRS = ("layouts", "templates", "methods", "interfaces", "chart-types", "projects")


def page_paths(wiki_root: Path) -> list[Path]:
    return sorted(path for directory in PAGE_DIRS
                  for path in (wiki_root / directory).glob("*.md"))


def render_index(wiki_root: Path, pages: list[tuple[Path, dict]]) -> str:
    lines = ["<!-- 由 wiki.py 生成，不要手改 -->", "", "# 目录", ""]

    def append_pages(selected: list[tuple[Path, dict]]) -> None:
        for path, meta in sorted(selected, key=lambda item: item[1]["title"]):
            target = path.relative_to(wiki_root).with_suffix("").as_posix()
            summary = ' '.join(str(meta.get('summary') or '').split())
            lines.append(f"- [[{target}|{meta['title']}]]" + (f" — {summary}" if summary else ''))
        lines.append("")

    for title, kind, statuses in (("版式", "layout", LAYOUT_STATUSES),
                                  ("模板", "template", TEMPLATE_STATUSES)):
        lines.extend([f"## {title}", ""])
        for status in statuses:
            lines.extend([f"### {status}", ""])
            append_pages([(path, meta) for path, meta in pages
                          if meta.get("type") == kind and meta.get("status") == status])
    for title, method_kind in (("分析家族", "analysis"), ("组合流程", "workflow"),
                               ("技术资料", "technical"), ("待分类方法", None)):
        lines.extend([f"## {title}", ""])
        for status in (*METHOD_STATUSES, None):
            selected = [(path, meta) for path, meta in pages if meta.get('type') == 'method'
                        and (meta.get('method_kind') == method_kind if method_kind else
                             meta.get('method_kind') not in ('analysis', 'workflow', 'technical'))
                        and (meta.get('status') == status if status else meta.get('status') not in METHOD_STATUSES)]
            if selected:
                lines.extend([f"### {status or '状态待核对'}", ""])
                append_pages(selected)
    for title, page_type in (("接口", "interface"), ("图型", "chart-type"), ("课题", "project")):
        lines.extend([f"## {title}", ""])
        append_pages([(path, meta) for path, meta in pages if meta.get("type") == page_type])
    return "\n".join(lines).rstrip() + "\n"


def readable_pages(wiki_root: Path) -> list[tuple[Path, dict]]:
    """Pages whose frontmatter parses and names a title; lint reports the rest."""
    result = []
    for path in page_paths(wiki_root):
        try:
            meta = read_page(path)[0]
        except (WikiError, OSError, UnicodeDecodeError):
            continue
        if isinstance(meta.get("title"), str):
            result.append((path, meta))
    return result


def build_index(wiki_root: Path) -> str:
    return render_index(wiki_root, readable_pages(wiki_root))

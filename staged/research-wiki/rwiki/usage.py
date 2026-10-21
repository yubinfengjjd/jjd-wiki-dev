import re
from datetime import date

from .config import Config
from .errors import WikiError
from .pages import read_page, section_bounds, section_text, visual_path, write_page
from .store import save
from .templates import ready_page


def append_record(body: str, title: str, line: str) -> str:
    _, end = section_bounds(body, title)
    return body[:end] + line + "\n\n" + body[end:]


def record_use(config: Config, entry_id: str, slug: str, title: str,
               output: str, note: str | None, method_id: str | None = None) -> None:
    if re.fullmatch(r"[a-z0-9-]+", slug) is None:
        raise WikiError("project slug 只允许 [a-z0-9-]，且不能为空")
    if method_id is not None:
        method_page = config.wiki_root / "methods" / f"{method_id}.md"
        method_meta, method_body = read_page(method_page)
        if method_meta["status"] != "ready":
            raise WikiError(f"方法必须为 ready: {method_id}")
    template_meta, template_body = ready_page(config, entry_id)
    page = visual_path(config.wiki_root, entry_id)
    kind = page.parent.name
    template_records = section_text(template_body, "使用记录")
    project = config.wiki_root / "projects" / f"{slug}.md"
    if project.exists():
        project_meta, project_body = read_page(project)
    else:
        project_meta = {"type": "project", "slug": slug, "title": title, "templates": []}
        project_body = f"# {title}\n\n## 使用的模板\n\n<!-- user:start -->\n<!-- user:end -->\n"
    project_records = section_text(project_body, "使用的模板")
    if entry_id not in project_meta["templates"]:
        project_meta["templates"].append(entry_id)
    if method_id is not None and method_id not in project_meta.setdefault("methods", []):
        project_meta["methods"].append(method_id)
    today = date.today().isoformat()
    prefix = rf"^- \d{{4}}-\d{{2}}-\d{{2}} \[\[{kind}/{re.escape(entry_id)}\|.*\]\]，输出 `{re.escape(output)}`"
    suffix = (f"；方法 [[methods/{method_id}|{method_meta['title']}]]"
              if method_id is not None else "")
    existing = re.search(prefix + re.escape(suffix) + r"(?:；(?!方法 \[\[methods/).*)?$", project_records, re.M)
    if existing is None:
        line = f"- {today} [[{kind}/{entry_id}|{template_meta['title']}]]，输出 `{output}`"
        line += suffix
        if note:
            line += f"；{note}"
        project_body = append_record(project_body, "使用的模板", line)
    linked_project = re.search(rf"^- \d{{4}}-\d{{2}}-\d{{2}} \[\[projects/{re.escape(slug)}\|.*\]\]$",
                               template_records, re.M)
    if linked_project is None:
        template_body = append_record(template_body, "使用记录", f"- {today} [[projects/{slug}|{title}]]")
    write_page(project, project_meta, project_body)
    write_page(page, template_meta, template_body)
    if method_id is not None:
        linked = re.search(rf"^- \d{{4}}-\d{{2}}-\d{{2}} \[\[projects/{re.escape(slug)}\|.*\]\]$",
                           section_text(method_body, "使用记录"), re.M)
        if linked is None:
            method_body = append_record(method_body, "使用记录", f"- {today} [[projects/{slug}|{title}]]")
        write_page(method_page, method_meta, method_body)
    save(config, f"use {entry_id} in {slug}")

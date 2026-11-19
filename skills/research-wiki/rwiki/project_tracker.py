"""Lightweight Markdown stepwise project tracker (`wiki/projects/<id>.md`)."""
from __future__ import annotations

import re
from pathlib import Path

from .config import Config
from .errors import WikiError
from .pages import read_page, write_page

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
STEP_HEADING_RE = re.compile(
    r"^###\s+(?:Step|Stage)\s+(\d+)(?:\s*[（(][^）)]*[）)])?\s*[:：]\s*(.+?)\s*$",
    re.M,
)


def _projects_dir(config: Config) -> Path:
    return config.wiki_root / "projects"


def _validate_id(project_id: str) -> str:
    pid = project_id.strip()
    if not SLUG_RE.fullmatch(pid):
        raise WikiError(f"课题 ID 非法（仅允许小写字母、数字、连字符和下划线）: {project_id}")
    return pid


def parse_steps(body: str) -> list[dict]:
    """Parse `### Step N：...` sections with the 3-line stepwise card fields."""
    matches = list(STEP_HEADING_RE.finditer(body))
    steps: list[dict] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        chunk = body[start:end]
        # Stop before HTML comment markers or next level-2 heading
        stop = re.search(r"^(?:##\s|<!--\s*user:)", chunk, re.M)
        if stop:
            chunk = chunk[:stop.start()]

        def _extract(*labels: str) -> str:
            for label in labels:
                m = re.search(rf"^[ \t]*-[ \t]*\*\*【{re.escape(label)}】\*\*[ \t]*[:：][ \t]*(.+?)[ \t]*$", chunk, re.M)
                if m:
                    return m.group(1).strip()
            return ""

        steps.append({
            "step": int(match.group(1)),
            "title": match.group(2).strip(),
            "templates": _extract("所用模版", "所用模板", "所用分析方法与可切换模板"),
            "observation": _extract("观察结果与排坑", "原文结论与本地小规模边界", "原文结论与本地代理边界", "原文结论与本地回放边界", "发表补表实测与湿实验排除边界", "发表补表实测与本地回放边界"),
            "next_branch": _extract("触发下一步", "触发下一步分叉"),
        })
    return steps


def _project_dict(config: Config, path: Path, meta: dict, body: str) -> dict:
    slug = str(meta.get("slug") or path.stem)
    return {
        "id": slug,
        "slug": slug,
        "title": str(meta.get("title") or slug),
        "path": path.relative_to(config.wiki_root).as_posix(),
        "meta": meta,
        "steps": parse_steps(body),
        "body": body,
    }


def list_projects(config: Config) -> list[dict]:
    """List all non-template project pages under `wiki/projects/*.md`."""
    directory = _projects_dir(config)
    if not directory.is_dir():
        return []
    projects: list[dict] = []
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("_"):
            continue
        try:
            meta, body = read_page(path)
        except WikiError:
            continue
        if meta.get("type") != "project":
            continue
        projects.append(_project_dict(config, path, meta, body))
    return projects


def get_project(config: Config, project_id: str) -> dict:
    pid = _validate_id(project_id)
    path = _projects_dir(config) / f"{pid}.md"
    if not path.is_file():
        raise WikiError(f"课题页不存在: {pid}")
    meta, body = read_page(path)
    return _project_dict(config, path, meta, body)


def add_project_step(
    config: Config,
    project_id: str,
    *,
    title: str,
    templates: str | list[str] = "",
    observation: str = "",
    next_branch: str = "",
    project_title: str | None = None,
    commit: bool = False,
) -> dict:
    """Append a 3-line stepwise card (`### Step N：...`) to `wiki/projects/<id>.md`."""
    pid = _validate_id(project_id)
    step_title = title.strip()
    if not step_title:
        raise WikiError("步骤标题不能为空")

    directory = _projects_dir(config)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{pid}.md"
    if path.is_file():
        meta, body = read_page(path)
    else:
        heading = (project_title or pid).strip()
        meta = {"type": "project", "slug": pid, "title": heading, "templates": []}
        body = f"# {heading}\n\n## 课题步进记录\n\n<!-- user:start -->\n<!-- user:end -->\n"

    existing = parse_steps(body)
    step_num = (max(item["step"] for item in existing) + 1) if existing else 1

    if isinstance(templates, list):
        tpl_items = [str(item).strip() for item in templates if str(item).strip()]
        tpl_text = "、".join(tpl_items)
    else:
        tpl_text = str(templates).strip()
        tpl_items = [part.strip(" `") for part in re.split(r"[,，、;；]+", tpl_text) if part.strip(" `")]

    recorded_tpls = meta.setdefault("templates", [])
    if isinstance(recorded_tpls, list):
        for item in tpl_items:
            if item not in recorded_tpls and (config.wiki_root / "templates" / f"{item}.md").is_file():
                recorded_tpls.append(item)

    block = (
        f"### Step {step_num}：{step_title}\n"
        f"- **【所用模版】**：{tpl_text or '待补充'}\n"
        f"- **【观察结果与排坑】**：{observation.strip() or '待补充'}\n"
        f"- **【触发下一步】**：{next_branch.strip() or '待确定'}\n"
    )
    marker = "<!-- user:start -->"
    if marker in body:
        idx = body.index(marker)
        prefix = body[:idx].rstrip()
        new_body = f"{prefix}\n\n{block}\n{body[idx:]}"
    else:
        new_body = f"{body.rstrip()}\n\n{block}"

    write_page(path, meta, new_body)
    if commit and (config.wiki_root / ".git").exists():
        from .store import save
        save(config, f"project {pid}: step {step_num}")
    return _project_dict(config, path, meta, new_body)

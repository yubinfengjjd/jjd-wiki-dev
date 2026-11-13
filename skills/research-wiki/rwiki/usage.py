import json
import re
from datetime import date
from pathlib import Path

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


def _verified_current_run(project_root: Path, run_id: str) -> dict:
    """Proof that ``run_id`` is a completed run whose recorded evidence is still
    verifiably current — the only evidence allowed to back a successful-use
    record. Delegates to the shared ``run_evidence_failures`` provenance check
    (receipt structure/identity, actual code provenance, receipt↔artifact↔bytes
    hash agreement, material input fingerprints, computed artifact freshness)
    so use/reuse/check guard the same facts. Failed/not-run/missing/stale/
    unverifiable runs raise WikiError."""
    from . import project_state as ps
    root = Path(project_root)
    state = ps.load_project(root)
    run = state['runs'].get(run_id)
    if run is None:
        raise WikiError(f'run 未登记: {run_id}')
    report = ps.check_project(root)
    failures = ps.run_evidence_failures(state, root, run_id, report=report)
    if failures:
        raise WikiError(f'run {run_id} 不能登记为成功使用：' + '；'.join(failures))
    receipt_path = ps.state_dir(root) / run['receipt']
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    return {'state': state, 'run': run, 'receipt': receipt,
            'project_id': state['project_id'], 'revision': state['revision']}


def record_method_use(config: Config, method_id: str, slug: str, title: str, *,
                      project_root: Path, run_id: str, note: str | None = None) -> None:
    """Register a *successful analysis-only* method use — no figure is invented.

    Requires a verified-current completed run (see ``_verified_current_run``);
    a failed/not-run/stale/unverifiable run can never become a formal
    successful-use record. The association lives on the project page's
    ``使用的方法`` section and the method's ``使用记录`` — template/figure
    pages are untouched.
    """
    if re.fullmatch(r"[a-z0-9-]+", slug) is None:
        raise WikiError("project slug 只允许 [a-z0-9-]，且不能为空")
    method_page = config.wiki_root / "methods" / f"{method_id}.md"
    if not method_page.is_file():
        raise WikiError(f"方法页不存在: {method_id}")
    method_meta, method_body = read_page(method_page)
    if method_meta["status"] != "ready":
        raise WikiError(f"方法必须为 ready: {method_id}")
    proof = _verified_current_run(Path(project_root), run_id)
    # The run must be bound to *this* canonical family and a concrete
    # implementation branch the page actually declares — a ready page alone
    # never proves this run used it, and titles are not identities.
    task = proof['state']['tasks'].get(proof['run']['task']) or {}
    if task.get('family_id') != method_id:
        raise WikiError(
            f'运行 {run_id} 的任务绑定家族为 {task.get("family_id") or "未绑定"}，'
            f'不是 {method_id}；不据标题或臆测归属登记使用')
    declared_impls = {impl.get('id') for impl in method_meta.get('implementations') or []
                      if isinstance(impl, dict)}
    impl_id = task.get('implementation_id')
    if impl_id is None or impl_id not in declared_impls:
        raise WikiError(
            f'运行 {run_id} 绑定实现 {impl_id or "未绑定"} 不在方法页声明的实现'
            f' {sorted(declared_impls) or "（无）"} 中；缺少具体分支证据不登记')
    project = config.wiki_root / "projects" / f"{slug}.md"
    if project.exists():
        project_meta, project_body = read_page(project)
    else:
        project_meta = {"type": "project", "slug": slug, "title": title,
                        "templates": [], "methods": []}
        project_body = (f"# {title}\n\n## 使用的模板\n\n## 使用的方法\n\n"
                        "<!-- user:start -->\n<!-- user:end -->\n")
    if "## 使用的方法" not in project_body:
        project_body = project_body.replace("<!-- user:start -->",
                                            "## 使用的方法\n\n<!-- user:start -->", 1)
    if method_id not in project_meta.setdefault("methods", []):
        project_meta["methods"].append(method_id)
    today = date.today().isoformat()
    records = section_text(project_body, "使用的方法")
    line = (f"- {today} [[methods/{method_id}|{method_meta['title']}]]，"
            f"分析运行 `{run_id}`（任务 `{proof['run']['task']}`，"
            f"实现 `{impl_id}`，{proof['project_id']}@r{proof['revision']}）；"
            "仅分析登记，无配图")
    if note:
        line += f"；{note}"
    exists = re.search(
        rf"^- \d{{4}}-\d{{2}}-\d{{2}} \[\[methods/{re.escape(method_id)}\|.*\]\]，"
        rf"分析运行 `{re.escape(run_id)}`", records, re.M)
    if exists is None:
        project_body = append_record(project_body, "使用的方法", line)
    write_page(project, project_meta, project_body)
    linked = re.search(rf"^- \d{{4}}-\d{{2}}-\d{{2}} \[\[projects/{re.escape(slug)}\|.*\]\]（分析 `{re.escape(run_id)}`）$",
                       section_text(method_body, "使用记录"), re.M)
    if linked is None:
        method_body = append_record(
            method_body, "使用记录",
            f"- {today} [[projects/{slug}|{title}]]（分析 `{run_id}`）")
    write_page(method_page, method_meta, method_body)
    save(config, f"use method {method_id} in {slug} (run {run_id})")

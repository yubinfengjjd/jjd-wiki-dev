import csv
import json
import shutil
from pathlib import Path

from .config import Config, read_json
from .errors import WikiError
from .ingest import ensure_hubs, layout_facts
from .interfaces import load_interface
from .pages import read_page, section_bounds, set_block, visual_path, write_page
from .process import run
from .spec import check_data, load_spec, requirements_markdown
from .store import save
from .verification import record_preview


def pending(config: Config) -> list[str]:
    ids = []
    for path in sorted((config.wiki_root / "layouts").glob("*.md")):
        meta, _ = read_page(path)
        if meta["status"] == "pending_template":
            ids.append(meta["id"])
    return ids


def require_pending(meta: dict) -> None:
    if meta["status"] != "pending_template":
        raise WikiError(f"页面必须为 pending_template: {meta['id']} ({meta['status']})")


def ready_page(config: Config, entry_id: str) -> tuple[dict, str]:
    path = visual_path(config.wiki_root, entry_id)
    meta, body = read_page(path)
    if meta["status"] != "ready":
        raise WikiError(f"页面必须为 ready: {entry_id} ({meta['status']})")
    return meta, body


def infer_type(values: list[str]) -> str:
    for name, convert in (("int", int), ("float", float)):
        try:
            for value in values:
                convert(value)
        except ValueError:
            continue
        return name
    return "str"


def scaffold_template(config: Config, entry_id: str, chart_type: str, panels: list[str]) -> None:
    page = config.wiki_root / "layouts" / f"{entry_id}.md"
    meta, body = read_page(page)
    require_pending(meta)
    tid = f"{entry_id}--{chart_type}"
    target = config.wiki_root / "templates" / tid
    template_page = target.with_suffix(".md")
    if target.exists() or template_page.exists():
        raise WikiError(f"模板页或目录已存在: {tid}")
    check_panels(meta, chart_type, panels)
    gallery = read_json(config.gallery_root / meta["gallery_entry"] / "meta.json")
    (target / "code").mkdir(parents=True)
    (target / "example").mkdir()
    (target / "code/__init__.py").write_text("", encoding="utf-8")
    tables = {}
    for source in sorted((config.gallery_root / meta["gallery_entry"] / "data").glob("*.csv")):
        shutil.copyfile(source, target / "example" / source.name)
        with source.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            columns = {column: {"type": infer_type([row[column] for row in rows]), "description": "待作者确认"}
                       for column in reader.fieldnames}
        matches = []
        for path in sorted((config.wiki_root / "interfaces").glob("*.md")):
            interface = load_interface(config.wiki_root, path.stem)
            if set(interface["columns"]) == set(columns):
                matches.append(path.stem)
        print(json.dumps({"file": source.name, "columns": columns, "interfaces": matches,
                          "filename_convention": "<interface>.csv",
                          "next_step": "选择或新建接口后，将 example 中此 CSV 改名为 <interface>.csv；原文件暂保留。"},
                         ensure_ascii=False))
        tables[source.stem] = {"interface": "", "description": ""}
    language = gallery["language"]
    entry = "code/render.py" if language == "python" else "code/render.R"
    spec = {"entry": entry, "language": language, "tables": tables, "style": {}}
    if language == "python":
        spec["panel"] = "code/panel.py"
    (target / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    title = f"{chart_type} · {meta['title']}"
    template_meta = {"type": "template", "id": tid, "title": title, "status": "draft",
                     "layouts": [entry_id], "panels": panels, "language": language,
                     "tags": meta["tags"], "chart_types": [chart_type], "favorite": False}
    template_body = (f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
                     "## 适用\n\n## 不适用\n\n## 数据要求\n\n模板化后生成。\n\n"
                     "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n")
    ensure_hubs(config, template_meta)
    write_page(template_page, template_meta, template_body)
    meta["templates"].append(tid)
    meta["template_panels"][tid] = panels
    body = set_block(body, "facts", layout_facts(config, meta))
    write_page(page, meta, body)
    save(config, f"scaffold template {tid}")


def check_panels(meta: dict, chart_type: str, panels: list[str]) -> None:
    if not panels or len(set(panels)) != len(panels):
        raise WikiError("panels 必须非空且字母不重复")
    for letter in panels:
        if letter not in meta["panels"]:
            raise WikiError(f"panels 字母不在版式中: {letter}")
        if meta["panels"][letter] != chart_type:
            raise WikiError(f"panels.{letter} 图型不等于 {chart_type}")
    for tid, covered in meta["template_panels"].items():
        if set(covered) & set(panels):
            raise WikiError(f"panels 已被模板覆盖: {tid}")


def attach_template(config: Config, layout_id: str, template_id: str, panels: list[str]) -> None:
    page = config.wiki_root / "layouts" / f"{layout_id}.md"
    meta, body = read_page(page)
    require_pending(meta)
    template_page = config.wiki_root / "templates" / f"{template_id}.md"
    tm, tb = read_page(template_page)
    if tm["status"] != "ready":
        raise WikiError(f"复用模板必须为 ready: {template_id}")
    if len(tm["chart_types"]) != 1:
        raise WikiError(f"panel 模板必须只有一种图型: {template_id}")
    check_panels(meta, tm["chart_types"][0], panels)
    if template_id in meta["templates"]:
        raise WikiError(f"版式已引用模板: {template_id}")
    meta["templates"].append(template_id)
    meta["template_panels"][template_id] = panels
    if layout_id not in tm["layouts"]:
        tm["layouts"].append(layout_id)
    body = set_block(body, "facts", layout_facts(config, meta))
    write_page(template_page, tm, tb)
    write_page(page, meta, body)
    save(config, f"attach {template_id} to {layout_id}")


def layout_ready_errors(config: Config, meta: dict) -> list[str]:
    errors = []
    covered = []
    if set(meta["template_panels"]) != set(meta["templates"]):
        errors.append("template_panels 的模板键必须等于 templates")
    for tid in meta["templates"]:
        path = config.wiki_root / "templates" / f"{tid}.md"
        if not path.is_file():
            errors.append(f"模板不存在: {tid}")
            continue
        template, _ = read_page(path)
        if template["status"] != "ready":
            errors.append(f"模板尚未 ready: {tid}")
        covered.extend(meta["template_panels"].get(tid, []))
    if set(covered) != set(meta["panels"]) or len(covered) != len(set(covered)):
        errors.append("模板面板必须无重复且完整覆盖版式 panels")
    if not (config.wiki_root / "layouts" / meta["id"] / "preview.png").is_file():
        errors.append(f"缺少 preview.png: {meta['id']}")
    return errors


def render(config: Config, entry_id: str, data_dir: Path, out_dir: Path,
           style: Path | None = None) -> None:
    target = config.wiki_root / "templates" / entry_id
    spec = load_spec(target)
    check_data(spec, data_dir)
    if style is not None:
        overrides = read_json(style)
        if not isinstance(overrides, dict):
            raise WikiError(f"style 必须为对象: {style}")
        unknown = overrides.keys() - spec["style"].keys()
        if unknown:
            raise WikiError(f"未知 style 键: {', '.join(sorted(unknown))}")
    executable = config.python_exe if spec["language"] == "python" else config.rscript_exe
    command = [str(executable), spec["entry"], "--data", str(data_dir.resolve()),
               "--out", str(out_dir.resolve())]
    if style is not None:
        command.extend(["--style", str(style.resolve())])
    out_dir.mkdir(parents=True, exist_ok=True)
    # A previous run's files must not satisfy this run's output check.
    for extension in ("png", "pdf", "svg"):
        (out_dir / f"figure.{extension}").unlink(missing_ok=True)
    run(command, target)
    missing = [f"figure.{ext}" for ext in ("png", "pdf", "svg")
               if not (out_dir / f"figure.{ext}").is_file()]
    if missing:
        raise WikiError(f"模板缺少输出文件: {', '.join(missing)}")


def verify_template(config: Config, entry_id: str) -> None:
    target = config.wiki_root / "templates" / entry_id
    out = target / "verify"
    example_style = target / "example/style.json"
    render(config, entry_id, target / "example", out,
           example_style if example_style.is_file() else None)
    record_preview(target)
    save(config, f"verify {entry_id}")


def mark_ready(config: Config, entry_id: str) -> None:
    page = visual_path(config.wiki_root, entry_id)
    if page.parent.name == "methods":
        from .methods import confirm_method

        confirm_method(config, entry_id)
        save(config, f"ready {entry_id}")
        return
    meta, body = read_page(page)
    target = page.with_suffix("")
    if page.parent.name == "layouts":
        require_pending(meta)
        errors = layout_ready_errors(config, meta)
        if errors:
            raise WikiError("；".join(errors))
    else:
        if meta["status"] != "draft":
            raise WikiError(f"模板必须为 draft: {entry_id} ({meta['status']})")
        spec = load_spec(target)
        if not (target / "preview.png").is_file():
            raise WikiError(f"缺少 preview.png: {entry_id}")
        start, end = section_bounds(body, "数据要求")
        body = body[:start] + "\n" + requirements_markdown(spec) + "\n" + body[end:]
        heading_end = body.index("\n") + 1
        body = body[:heading_end] + f"\n![[templates/{entry_id}/preview.png]]\n" + body[heading_end:]
    meta["status"] = "ready"
    write_page(page, meta, body)
    save(config, f"ready {entry_id}")

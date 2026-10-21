import re

from .catalog import LAYOUT_STATUSES, TEMPLATE_STATUSES, METHOD_STATUSES, page_paths, render_index
from .config import Config, read_json
from .errors import WikiError
from .links import extract_links, resolve
from .layouts import load_layout
from .pages import block_error, get_block, parse_page
from .interfaces import load_interface
from .spec import load_spec
from .facts import page_facts
from .templates import layout_ready_errors

REQUIRED = {
    "layout": ("type", "id", "title", "status", "gallery_entry", "gallery_version",
               "language", "tags", "chart_types", "favorite", "panels", "templates", "template_panels"),
    "template": ("type", "id", "title", "status", "layouts", "panels",
                 "language", "tags", "chart_types", "favorite"),
    "chart-type": ("type", "slug", "title"),
    "project": ("type", "slug", "title", "templates"),
    "method": ("type", "id", "title", "status", "tags", "inputs", "outputs", "source", "license", "cite", "favorite"),
    "interface": ("type", "slug", "title", "columns"),
}


def metadata_errors(meta: dict) -> list[str]:
    page_type = meta.get("type")
    if page_type not in REQUIRED:
        return ["type 缺失或未知"]
    errors = [f"缺少必需键 {key}" for key in REQUIRED[page_type] if key not in meta]
    if page_type not in ("layout", "template", "method"):
        return errors
    status = meta.get("status")
    statuses = {"layout": LAYOUT_STATUSES, "template": TEMPLATE_STATUSES, "method": METHOD_STATUSES}[page_type]
    if status not in statuses:
        errors.append(f"status 非法: {status}")
    if status == "archived" and "archived_from" not in meta:
        errors.append("缺少必需键 archived_from")
    if page_type == "method":
        source = meta.get("source")
        fields = {"post": ("gallery_entry",), "project": ("path",), "repo": ("url", "commit"), "written": ()}
        if not isinstance(source, dict) or source.get("kind") not in ("post", "project", "repo", "written"):
            errors.append("source.kind 必须为 post、project、repo 或 written")
        elif any(not isinstance(source.get(key), str) or not source[key].strip() for key in fields[source["kind"]]):
            errors.append("source 缺少来源字段")
        if not isinstance(meta.get("license"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", meta["license"]):
            errors.append("license 必须为 SPDX 标识或 none")
        if not isinstance(meta.get("cite"), list) or any(not isinstance(cite, str) for cite in meta["cite"]):
            errors.append("cite 必须为文献字符串列表")
        elif isinstance(source, dict) and source.get("kind") == "written" and not any(cite.strip() for cite in meta["cite"]):
            errors.append("source.kind written 时 cite 必须非空")
        for key in ("inputs", "outputs"):
            if not isinstance(meta.get(key), list) or any(not isinstance(slug, str) or not slug.strip() for slug in meta[key]):
                errors.append(f"{key} 必须为接口 slug 字符串列表")
        if not isinstance(meta.get("favorite"), bool):
            errors.append("favorite 必须为布尔值")
    if not isinstance(meta.get("tags"), list) or any(not isinstance(tag, str) for tag in meta["tags"]):
        errors.append("tags 必须为字符串列表")
    return errors


def asset_diagnostics(config: Config, path, meta: dict) -> list[tuple[str, str]]:
    target = path.with_suffix("")
    try:
        if meta["type"] == "interface":
            load_interface(config.wiki_root, path.stem)
        elif meta["type"] == "method":
            for slug in meta["inputs"] + meta["outputs"]:
                load_interface(config.wiki_root, slug)
        elif meta["type"] == "template" and (target / "spec.json").is_file():
            load_spec(target)
    except WikiError as error:
        return [("ERROR", f"接口或 spec.json: {error}")]
    return []


def layout_diagnostics(config: Config, meta: dict) -> list[tuple[str, str]]:
    diagnostics = []
    entry = config.gallery_root / meta["gallery_entry"] / "meta.json"
    if not entry.is_file():
        diagnostics.append(("ERROR", "画廊 meta.json 不存在"))
    else:
        gallery = read_json(entry)
        status, approved = meta["status"], gallery["status"] == "approved"
        if approved and status == "pending_signoff":
            diagnostics.append(("ERROR", "画廊 approved，页面仍为 pending_signoff"))
        if status in ("pending_template", "ready") and not approved:
            diagnostics.append(("ERROR", f"页面为 {status}，画廊不是 approved"))
        if gallery["version"] > meta["gallery_version"]:
            diagnostics.append(("WARN", "画廊 version 大于 gallery_version，需重新收录"))
    return diagnostics


def visual_diagnostics(config: Config, path, meta: dict, body: str,
                       valid_metadata: dict) -> list[tuple[str, str]]:
    diagnostics = layout_diagnostics(config, meta) if meta["type"] == "layout" else []
    target = path.with_suffix("")
    if meta["status"] == "ready":
        if not (target / "preview.png").is_file():
            diagnostics.append(("ERROR", "ready 页面缺少 preview.png"))
        if meta["type"] == "template" and not (target / "spec.json").is_file():
            diagnostics.append(("ERROR", "ready 模板缺少 spec.json"))
        if meta["type"] == "layout" and all(
                config.wiki_root / "templates" / f"{tid}.md" in valid_metadata
                for tid in meta["templates"]):
            diagnostics.extend(("ERROR", error) for error in layout_ready_errors(config, meta))
    if meta["type"] == "layout" and (target / "layout.json").is_file():
        # A bad layout.json is one finding among others, not a reason to stop the report.
        try:
            load_layout(target)
        except WikiError as error:
            diagnostics.append(("ERROR", f"layout.json: {error}"))
    own_list, other_list, directory = (("templates", "layouts", "templates") if meta["type"] == "layout"
                                       else ("layouts", "templates", "layouts"))
    for entry_id in meta[own_list]:
        other_path = config.wiki_root / directory / f"{entry_id}.md"
        if not other_path.is_file():
            diagnostics.append(("ERROR", f"引用的{'模板' if directory == 'templates' else '版式'}不存在: {entry_id}"))
            continue
        # The referenced page's own schema diagnostics are already in the report.
        if other_path not in valid_metadata:
            continue
        other = valid_metadata[other_path]
        if meta["id"] not in other.get(other_list, []):
            diagnostics.append(("ERROR", f"{entry_id}.{other_list} 未包含 {meta['id']}"))
    applicable = re.search(r"^## 适用\s*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    if meta["status"] in ("pending_template", "ready") and (not applicable or not applicable[1].strip()):
        diagnostics.append(("WARN", "适用节为空"))
    return diagnostics


def lint(config: Config) -> list[str]:
    root = config.wiki_root
    diagnostics = []
    valid_pages = []
    derived_pages = []
    parsed_pages = []

    def report(level: str, path, message: str) -> None:
        diagnostics.append(f"{level} {path.relative_to(root).as_posix()}: {' '.join(message.splitlines())}")

    for path in page_paths(root):
        meta, body, parse_error = parse_page(path.read_text(encoding="utf-8"))
        errors = [parse_error] if parse_error else metadata_errors(meta)
        for error in errors:
            report("ERROR", path, error)
        if not errors:
            valid_pages.append((path, meta))
        parsed_pages.append((path, meta, body, errors))

    valid_metadata = dict(valid_pages)
    for path, meta, body, errors in parsed_pages:
        if not errors:
            if meta["type"] in ("layout", "template", "method", "interface"):
                findings = asset_diagnostics(config, path, meta)
                for level, message in findings:
                    report(level, path, message)
                if not findings:
                    derived_pages.append((path, meta, body))
            if meta["type"] in ("layout", "template"):
                for level, message in visual_diagnostics(config, path, meta, body, valid_metadata):
                    report(level, path, message)
            elif meta["type"] == "project":
                for entry_id in meta["templates"]:
                    if not any((root / kind / f"{entry_id}.md").is_file() for kind in ("templates", "layouts")):
                        report("ERROR", path, f"引用的模板页不存在: {entry_id}")
                for method_id in meta.get("methods", []):
                    if not (root / "methods" / f"{method_id}.md").is_file():
                        report("ERROR", path, f"引用的方法页不存在: {method_id}")
        for name in ("user", "facts"):
            if meta.get("type") in ("layout", "template", "method", "interface") or f"<!-- {name}:" in body:
                error = block_error(body, name)
                if error:
                    report("ERROR", path, error)
        for target in extract_links(body):
            if not resolve(root, target).exists():
                report("ERROR", path, f"断链或嵌入目标不存在: {target}")
    # A canonical relation graph requires valid pages, assets, references and blocks.
    if not any(line.startswith("ERROR ") for line in diagnostics):
        for path, meta, body in derived_pages:
            if get_block(body, "facts") != page_facts(config, meta):
                report("WARN", path, "facts 与资产不一致，请运行 save")
    index = root / "index.md"
    actual_index = index.read_text(encoding="utf-8") if index.exists() else ""
    for target in extract_links(actual_index):
        if not resolve(root, target).exists():
            report("ERROR", index, f"断链或嵌入目标不存在: {target}")
    if actual_index != render_index(root, valid_pages):
        report("WARN", index, "index.md 与页面不一致，请运行 save")
    return diagnostics

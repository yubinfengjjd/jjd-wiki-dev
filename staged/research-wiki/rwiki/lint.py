import re
import subprocess
from pathlib import Path

from .catalog import LAYOUT_STATUSES, METHOD_STATUSES, STATUSES, TEMPLATE_STATUSES, page_paths, render_index
from .config import Config, read_json
from .errors import WikiError
from .links import extract_links, resolve
from .layouts import load_layout
from .pages import block_error, get_block, parse_page, section_text
from .interfaces import load_interface
from .spec import load_spec
from .facts import page_facts
from .templates import layout_ready_errors
from .relations import relation_errors

REQUIRED = {
    "layout": ("type", "id", "title", "status", "gallery_entry", "gallery_version",
               "language", "tags", "chart_types", "favorite", "panels", "templates", "template_panels"),
    "template": ("type", "id", "title", "status", "panels",
                 "language", "tags", "chart_types", "favorite"),
    "chart-type": ("type", "slug", "title"),
    "project": ("type", "slug", "title", "templates"),
    "method": ("type", "id", "title", "status", "tags", "inputs", "outputs", "source", "license", "cite", "favorite"),
    "interface": ("type", "slug", "title", "columns"),
    # v2 (2026-10-27)
    "source": ("type", "id", "title", "url", "commit", "license", "adapter", "trusted", "snapshot"),
    "recipe": ("type", "id", "title", "status", "source", "license", "language", "runner", "entry",
               "tags", "chart_types", "favorite"),
    "scenario": ("type", "id", "title", "picks"),
}


def _string_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def metadata_errors(meta: dict, vocabulary: frozenset[str] | None = None) -> list[str]:
    from .tags import tag_errors

    def finish(found: list[str]) -> list[str]:
        found.extend(tag_errors(meta, vocabulary))
        return found

    page_type = meta.get("type")
    if page_type not in REQUIRED:
        return ["type 缺失或未知"]
    errors = [f"缺少必需键 {key}" for key in REQUIRED[page_type] if key not in meta]
    if page_type == "source":
        from .adapters import ADAPTERS
        if meta.get("adapter") not in ADAPTERS:
            errors.append(f"未知适配器: {meta.get('adapter')}")
        if not isinstance(meta.get("trusted"), bool):
            errors.append("trusted 必须为布尔值")
        return finish(errors)
    if page_type == "scenario":
        if not isinstance(meta.get("picks"), list):
            errors.append("picks 必须为列表")
        return finish(errors)
    if page_type not in ("layout", "template", "method", "recipe"):
        return finish(errors)
    status = meta.get("status")
    statuses = {"layout": LAYOUT_STATUSES, "template": TEMPLATE_STATUSES, "method": METHOD_STATUSES,
                "recipe": STATUSES}[page_type]
    if status not in statuses:
        errors.append(f"status 非法: {status}")
    if status == "archived" and "archived_from" not in meta:
        errors.append("缺少必需键 archived_from")
    if page_type == "recipe":
        source = meta.get("source")
        if not isinstance(source, dict) or any(not isinstance(source.get(key), str) or not source[key].strip()
                                               for key in ("id", "item", "commit")):
            errors.append("source 必须含 id、item、commit")
        if not _string_list(meta.get("chart_types", [])):
            errors.append("chart_types 必须为字符串列表")
        if not isinstance(meta.get("license"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", meta["license"]):
            errors.append("license 必须为 SPDX 标识或 none")
    if page_type == "template":
        layouts, sources = meta.get("layouts", []), meta.get("sources", [])
        valid = isinstance(layouts, list) and isinstance(sources, list) and _string_list(layouts + sources)
        if not valid or not (layouts or sources):
            # v2: provenance is a gallery layout or another Wiki page (e.g. recipes/<id>).
            errors.append("模板必须记录来源：layouts（历史版式）或 sources（如 recipes/<id>）；不能新建无来源模板")
    if page_type == "method":
        from .method_implementations import implementation_metadata_errors
        from .method_taxonomy import purpose_errors
        errors.extend(implementation_metadata_errors(meta))
        errors.extend(purpose_errors(meta))
        if meta.get("method_kind") in ("workflow", "technical") and meta.get("figure_relations"):
            errors.append("workflow/technical 资料不应维护主 figure_relations；迁往真正的分析家族")
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
    return finish(errors)


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


GALLERY_MISSING = "画廊 meta.json 不存在"


def layout_diagnostics(config: Config, meta: dict) -> list[tuple[str, str]]:
    diagnostics = []
    entry = config.gallery_root / meta["gallery_entry"] / "meta.json"
    if not entry.is_file():
        diagnostics.append(("ERROR", GALLERY_MISSING))
    else:
        gallery = read_json(entry)
        status, approved = meta["status"], gallery["status"] == "approved"
        signed = meta.get('signedoff_version')
        if approved and status == "pending_signoff" and (
                signed == gallery['version'] or gallery.get('approved_version') == gallery['version']):
            diagnostics.append(("ERROR", "画廊 approved，页面仍为 pending_signoff"))
        if status in ('pending_template', 'ready') and 'signedoff_version' in meta and signed != gallery['version']:
            diagnostics.append(('ERROR', '来源当前版本尚未签核'))
        if status in ("pending_template", "ready") and not approved:
            diagnostics.append(("ERROR", f"页面为 {status}，画廊不是 approved"))
        if gallery["version"] > meta["gallery_version"]:
            diagnostics.append(("WARN", "画廊 version 大于 gallery_version，需重新收录"))
    return diagnostics


def adaptable_interface_diagnostics(config: Config, path, meta: dict, body: str) -> list[tuple[str, str]]:
    """An adaptable relation must name the template interfaces it adapts."""
    findings = []
    records = meta.get("figure_relations", [])
    if not isinstance(records, list):
        return findings
    for record in records:
        if not isinstance(record, dict) or record.get("compatibility") != "adaptable":
            continue
        figure = record.get("figure")
        if not isinstance(figure, str) or not figure.startswith("templates/"):
            continue
        target = config.wiki_root / figure.removesuffix(".md")
        try:
            spec = load_spec(target)
        except (WikiError, OSError, ValueError, KeyError, TypeError):
            continue
        missing = [table["interface"] for table in spec.get("tables", {}).values()
                   if isinstance(table, dict) and table.get("interface")
                   and table["interface"] not in body]
        if missing:
            findings.append(("WARN", f"适配关系 {figure} 的模板读取接口未在正文说明: "
                                      + "、".join(missing)))
    return findings


NO_FIGURE_NOTE = "无图原因"


def figureless_method_diagnostics(config: Config, meta: dict, body: str) -> list[tuple[str, str]]:
    """A ready method with outputs but no template at all must say why in its review section."""
    outputs = set(meta.get("outputs") or [])
    if not outputs:
        return []
    from .facts import declarations, table_interfaces
    structural = [tid for tid, (tm, spec) in declarations(config.wiki_root, "templates").items()
                  if tm.get("status") != "archived" and table_interfaces(spec)
                  and table_interfaces(spec) <= outputs]
    related = [r for r in meta.get("figure_relations") or []
               if isinstance(r, dict) and str(r.get("figure", "")).startswith("templates/")]
    if structural or related:
        return []
    try:
        review = section_text(body, "知识关联检查")
    except WikiError:
        review = ""
    if NO_FIGURE_NOTE in review:
        return []
    return [("WARN", f"方法输出接口没有结构匹配模板，也没有语义模板关系；请在知识关联检查写“{NO_FIGURE_NOTE}：…”")]


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
    if meta["type"] == "template":
        for value in meta.get("sources") or []:
            if not (config.wiki_root / f"{str(value).removesuffix('.md')}.md").is_file():
                diagnostics.append(("ERROR", f"引用的来源页不存在: {value}"))
    for entry_id in meta.get(own_list) or []:
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


def lint(config: Config, ci: bool = False) -> list[str]:
    """ci=True：因被 git 忽略（GPL 托管块、画廊、维护记录）而缺失的引用报告为 LOCAL-ONLY。"""
    from .tags import load_vocabulary

    root = config.wiki_root
    diagnostics = []
    try:
        vocabulary = load_vocabulary(config)
        vocab_error = None
    except WikiError as error:
        # Keep walking pages, but the run cannot pass without the controlled vocabulary.
        vocabulary = None
        vocab_error = str(error)
    valid_pages = []
    derived_pages = []
    parsed_pages = []
    gpl_missing = []
    if ci:
        from .push_guard import restricted_dirs
        gpl_missing = [root / d for d in restricted_dirs(root) if not (root / d).exists()]

    def local_only(missing) -> bool:
        # 目录以 `/` 结尾传给 check-ignore，目录型忽略规则才会匹配不存在的路径。
        return not Path(missing).exists() and subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", "--", str(missing)],
            capture_output=True).returncode == 0

    def method_missing(path):
        """方法、配方与派生模板的检查依赖其限制性许可源码目录；CI 检出中这些目录被忽略而缺失。"""
        asset = path.with_suffix("")
        return next((f"{d}/" for d in gpl_missing if d.is_relative_to(asset)), None)

    def report(level: str, path, message: str, missing=None) -> None:
        if ci and level == "ERROR" and missing is not None and local_only(missing):
            level = "LOCAL-ONLY"
        diagnostics.append(f"{level} {path.relative_to(root).as_posix()}: {' '.join(message.splitlines())}")

    for path in page_paths(root):
        meta, body, parse_error = parse_page(path.read_text(encoding="utf-8"))
        errors = [parse_error] if parse_error else metadata_errors(meta, vocabulary)
        if not parse_error and meta.get("type") == "method":
            errors.extend(relation_errors(config, meta))
        elif "figure_relations" in meta:
            errors.append("figure_relations 只能在 method 页声明；图端关系由方法页反向计算")
        for error in errors:
            report("ERROR", path, error)
        if not errors:
            valid_pages.append((path, meta))
        parsed_pages.append((path, meta, body, errors))

    valid_metadata = dict(valid_pages)
    families = {}
    for path, meta, body, errors in parsed_pages:
        if meta.get('type') == 'method':
            from .method_implementations import implementation_status
            if not meta.get('method_kind'):
                report('WARN', path, 'method_kind 缺失：旧页待分类，不参与分析推荐')
            from .method_taxonomy import missing_purpose
            if missing_purpose(meta):
                report('WARN', path, 'purposes 缺失：请按分析用途分类；旧页仍可读，但不进入用途筛选')
            if meta.get('method_kind') == 'analysis' and meta.get('status') != 'archived':
                name = ''.join(str(meta.get('title', '')).casefold().split())
                if name in families:
                    report('ERROR', path, f'重复分析家族：标题与 {families[name]} 相同，须人工核对范围')
                families[name] = path.relative_to(root).as_posix()
                if not meta.get('implementations'):
                    report('WARN', path, '未声明实现：笔记可确认，实现仍待实现')
            for item in implementation_status(path, meta):
                if item['state'] != 'verified':
                    report('WARN', path, f"实现 {item['id']}：{item['state']}；当前不能推荐执行")
                runtime = item.get('runtime') or {}
                if runtime.get('declared') and runtime.get('dependency_match') is False:
                    report('WARN', path, f"实现 {item['id']}：页面 dependencies 与 runtime.json 不一致，"
                                          "展示以 runtime.json 为准")
            from .runtime_contract import lint_manifest
            for message in lint_manifest(path.with_suffix(''), path.stem, 'method'):
                report('WARN', path, message)
        if not errors:
            if meta["type"] == "interface":
                try:
                    meaning = section_text(body, "含义")
                except WikiError:
                    meaning = ""
                if not meaning.strip():
                    report("WARN", path, "含义为空：写明一行代表什么、单位以及与相近接口的区别")
            if meta["type"] == "method" and meta.get("status") == "ready":
                for level, message in (adaptable_interface_diagnostics(config, path, meta, body)
                                       + figureless_method_diagnostics(config, meta, body)):
                    report(level, path, message)
            if meta["type"] in ("layout", "template", "method", "interface", "recipe", "source", "scenario"):
                findings = asset_diagnostics(config, path, meta)
                for level, message in findings:
                    report(level, path, message, method_missing(path))
                if not findings:
                    derived_pages.append((path, meta, body))
            if meta["type"] in ("layout", "template"):
                for level, message in visual_diagnostics(config, path, meta, body, valid_metadata):
                    report(level, path, message,
                           config.gallery_root / meta["gallery_entry"] / "meta.json"
                           if message == GALLERY_MISSING else None)
                if meta["type"] == "template":
                    from .runtime_contract import lint_manifest
                    for message in lint_manifest(path.with_suffix(''), meta['id'], 'template'):
                        report('WARN', path, message)
            elif meta["type"] == "project":
                for entry_id in meta["templates"]:
                    if not any((root / kind / f"{entry_id}.md").is_file() for kind in ("templates", "layouts")):
                        report("ERROR", path, f"引用的模板页不存在: {entry_id}")
                for method_id in meta.get("methods", []):
                    if not (root / "methods" / f"{method_id}.md").is_file():
                        report("ERROR", path, f"引用的方法页不存在: {method_id}")
            if meta["type"] == "scenario":
                from .finder import record_for
                from .curation import visible_picks
                for pick in visible_picks(config, meta.get("picks") or []):
                    value = str(pick.get("id") if isinstance(pick, dict) else pick)
                    key = value if ":" in value else value.split("/", 1)[-1].removesuffix(".md")
                    if record_for(config, key) is None:
                        report("ERROR", path, f"场景首选条目不存在或已归档: {value}")
            if (meta['type'] in ('method', 'template', 'layout', 'recipe')
                    and meta.get('status') not in ('archived', 'pending_signoff')):
                from .acceptance import entry_errors, acceptance_stale
                for message in entry_errors(config, path):
                    report('ERROR' if meta['status'] == 'ready' else 'WARN', path, f'入库验收: {message}',
                           method_missing(path))
                if meta['status'] == 'ready' and acceptance_stale(path):
                    report('ERROR', path, '入库验收记录已过期，请核对后 check-entry --record',
                           method_missing(path))
        for name in ("user", "facts"):
            if meta.get("type") in ("layout", "template", "method", "interface", "recipe", "source", "scenario") \
                    or f"<!-- {name}:" in body:
                error = block_error(body, name)
                if error:
                    report("ERROR", path, error)
        for target in extract_links(body):
            if not resolve(root, target).exists():
                report("ERROR", path, f"断链或嵌入目标不存在: {target}", resolve(root, target))
    # A canonical relation graph requires valid pages, assets, references and blocks.
    # LOCAL-ONLY 表示本地资产缺失，facts 无法在此检出中重算。
    if not any(line.startswith(("ERROR ", "LOCAL-ONLY ")) for line in diagnostics):
        for path, meta, body in derived_pages:
            if get_block(body, "facts") != page_facts(config, meta):
                report("WARN", path, "facts 与资产不一致，请运行 save")
    index = root / "index.md"
    actual_index = index.read_text(encoding="utf-8") if index.exists() else ""
    for target in extract_links(actual_index):
        if not resolve(root, target).exists():
            report("ERROR", index, f"断链或嵌入目标不存在: {target}", resolve(root, target))
    # Malformed metadata still belongs in the directory; lint reports its problems separately.
    from .catalog import readable_pages
    if actual_index != render_index(root, readable_pages(root)):
        report("WARN", index, "index.md 与页面不一致，请运行 save")
    if vocab_error:
        diagnostics.append(f"ERROR taxonomy: {vocab_error}")
    from .finder import CATALOG, render_catalog
    catalog = root / CATALOG
    if (catalog.read_text(encoding="utf-8") if catalog.is_file() else "") != render_catalog(config):
        report("WARN", catalog, "catalog.jsonl 与页面不一致，请运行 save")
    return diagnostics

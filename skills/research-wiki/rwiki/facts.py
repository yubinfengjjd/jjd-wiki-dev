"""Rebuild derived page facts from frontmatter and asset declarations."""

from urllib.parse import quote

from .config import Config, read_json
from .errors import WikiError
from .interfaces import load_interface
from .pages import read_page, set_block, write_page
from .relations import COMPATIBILITY_LABELS, all_relations, relations_for


def declarations(root, kind: str) -> dict:
    """Readable method metas, or template metas with their spec; broken pages are lint's job."""
    result = {}
    for path in sorted((root / kind).glob("*.md")):
        try:
            meta = read_page(path)[0]
            if kind == "methods":
                if isinstance(meta.get("outputs"), list) and isinstance(meta.get("inputs"), list):
                    result[path.stem] = (meta, meta)
            elif (path.with_suffix("") / "spec.json").is_file():
                spec = read_json(path.with_suffix("") / "spec.json")
                if isinstance(spec, dict) and isinstance(spec.get("tables"), dict):
                    result[path.stem] = (meta, spec)
        except WikiError:
            continue
    return result


def table_interfaces(spec: dict) -> set[str]:
    return {table["interface"] for table in spec["tables"].values() if table["interface"]}


def input_interfaces(method: dict) -> set[str]:
    return set(method["inputs"])


def page_link(kind: str, meta: dict, status: bool = False) -> str:
    key = meta["slug"] if kind == "interfaces" else meta["id"]
    return f"[[{kind}/{key}|{meta['title']}]]" + (f"（{meta['status']}）" if status else "")


def interface_link(root, slug: str) -> str:
    return page_link("interfaces", load_interface(root, slug))


def relationship_facts(config: Config, path: str) -> str:
    """The same authored record is presented from either endpoint."""
    lines = ["\n- 方法配图关系（语义审查）："]
    for relation in relations_for(config, path):
        other = "figure" if path.startswith("methods/") else "method"
        target = relation[other].removesuffix(".md")
        label = relation[f"{other}_title"]
        status = relation[f"{other}_status"]
        verification = relation["verification"]
        reference = "；来源图样参考，执行时另查关联模板" if relation["target_kind"] == "layout" else ""
        archived = "；已归档，不推荐" if not relation["active"] else ""
        lines.append(f"  - [[{target}|{label}]]（{status}）："
                     f"{COMPATIBILITY_LABELS[relation['compatibility']]}（{relation['compatibility']}）"
                     f"{reference}{archived}；调用验证：{verification['state']}；范围：{verification['scope']}")
        lines.append(f"    - 依据：{relation['reason']}；前提：{'；'.join(relation['prerequisites']) or '无额外声明'}"
                     f"；适配：{relation['adaptation'] or '无格式适配声明'}")
        lines.append(f"    - 关系证据：{'；'.join(relation['evidence'])}；运行证据："
                     f"{'；'.join(verification['evidence']) or '无'}")
    if len(lines) == 1:
        lines.append("  - 暂无已记录关系；接口或标签相同不代表语义已核实。")
    return "\n".join(lines) + "\n"


def source_links(root, values) -> list[str]:
    """v2 template provenance: `recipes/<id>` (or other page paths) instead of a gallery layout."""
    links = []
    for value in values or []:
        path = root / f"{str(value).removesuffix('.md')}.md"
        title = read_page(path)[0]["title"] if path.is_file() else value
        links.append(f"[[{str(value).removesuffix('.md')}|{title}]]")
    return links


def template_facts(config: Config, meta: dict) -> str:
    root = config.wiki_root
    layouts = [page_link("layouts", read_page(root / "layouts" / f"{lid}.md")[0])
               for lid in meta.get("layouts") or []] + source_links(root, meta.get("sources"))
    charts = " · ".join(f"[[chart-types/{slug}]]" for slug in meta["chart_types"])
    spec_path = root / "templates" / meta["id"] / "spec.json"
    interfaces, compatible = [], []
    if spec_path.is_file():
        spec = read_json(spec_path)
        interfaces = [interface_link(root, table["interface"]) if table["interface"] else "未声明"
                      for table in spec["tables"].values()]
        required = table_interfaces(spec)
        if required and all(table["interface"] for table in spec["tables"].values()):
            compatible = [page_link("methods", mm, True) for mm, method in declarations(root, "methods").values()
                          if mm["status"] != "archived" and required <= set(method["outputs"])]
    panels = f"- 面板（来源版式）：{'、'.join(meta['panels'])}\n" if meta.get("layouts") else ""
    license_line = f"- 许可证：{meta['license']}\n" if meta.get("license") else ""
    return (f"\n- 来源：{' · '.join(layouts)}\n"
            f"{panels}- 语言：{meta['language']}\n{license_line}"
            f"- 标签：{'、'.join(meta['tags'])}\n- 图型：{charts}\n"
            f"- 输入接口：{' · '.join(interfaces) or '未声明'}\n"
            f"- 接口结构匹配的分析方法（仅结构候选，未核实语义）：{' · '.join(compatible) or '暂无'}\n"
            + relationship_facts(config, f"templates/{meta['id']}.md"))


def method_facts(config: Config, meta: dict) -> str:
    root = config.wiki_root
    source = meta["source"]
    if source["kind"] == "post":
        lid = source["gallery_entry"].replace("/figures/", "__")
        layout = root / "layouts" / f"{lid}.md"
        origin = page_link("layouts", read_page(layout)[0]) if layout.is_file() else lid
    elif source["kind"] == "repo":
        origin = f"{source['url']}（{source['commit']}）"
    elif source["kind"] == "written":
        origin = "依据文献 / 官方文档编写"
    else:
        origin = source["path"]
    outputs = set(meta["outputs"])
    figures = []
    for tm, spec in declarations(root, "templates").values():
        required = table_interfaces(spec)
        if (tm["status"] != "archived" and required and required <= outputs
                and all(table["interface"] for table in spec["tables"].values())):
            figures.append(page_link("templates", tm, True))
    next_methods = [page_link("methods", mm, True)
                    for mm, method in declarations(root, "methods").values()
                    if mm["status"] != "archived"
                    and input_interfaces(method) and input_interfaces(method) <= outputs]
    code_files = [f"[{path.relative_to(root).as_posix()}](/files/wiki/{quote(path.relative_to(root).as_posix(), safe='/')})"
                  for path in sorted((root / "methods" / meta["id"] / "code").rglob("*"))
                  if path.is_file() and "__pycache__" not in path.parts
                  and path.suffix.lower() not in (".pyc", ".pyo")]
    license_text = "仅供个人研究参考" if meta["license"] == "none" else meta["license"]
    lines = [
        f"\n- 来源：{origin}", f"- 许可证：{license_text}",
        f"- 引用：{'；'.join(meta['cite']) or '无'}", f"- 标签：{'、'.join(meta['tags'])}",
        f"- 输入接口：{' · '.join(interface_link(root, slug) for slug in meta['inputs']) or '未声明'}",
        f"- 输出接口：{' · '.join(interface_link(root, slug) for slug in meta['outputs']) or '未声明'}",
        f"- 接口结构匹配的图（仅结构候选，未核实语义）：{' · '.join(figures) or '暂无'}",
        f"- 接口结构匹配的下一步方法（仅结构候选，未核实语义）：{' · '.join(next_methods) or '暂无'}",
        f"- 代码模板：{' · '.join(code_files) or '无'}",
    ]
    if meta.get("method_kind") == "analysis":
        lines.insert(4, f"- 分析用途：{'、'.join(meta.get('purposes') or []) or '未分类'}")
    return "\n".join(lines) + "\n" + relationship_facts(config, f"methods/{meta['id']}.md")


def interface_facts(config: Config, meta: dict) -> str:
    slug = meta["slug"]
    methods = declarations(config.wiki_root, "methods")
    templates = declarations(config.wiki_root, "templates")
    live = lambda pairs: [(m, d) for m, d in pairs if m.get("status") != "archived"]
    producers = [page_link("methods", mm) for mm, method in live(methods.values()) if slug in method["outputs"]]
    readers = [page_link("methods", mm) for mm, method in live(methods.values()) if slug in input_interfaces(method)]
    figures = [page_link("templates", tm) for tm, spec in live(templates.values()) if slug in table_interfaces(spec)]
    lines = ["\n| 列 | 类型 | 必需 | 含义 |", "|---|---|---|---|"]
    for name, column in meta["columns"].items():
        required = "必需" if column.get("required", True) else "可选"
        lines.append(f"| {name} | {column['type']} | {required} | {column['description']} |")
    lines.extend(["", f"- 产出方法：{' · '.join(producers) or '无'}",
                  f"- 读取方法：{' · '.join(readers) or '无'}",
                  f"- 使用的模板：{' · '.join(figures) or '无'}"])
    # A method whose declared outputs are empty can still feed a template that reads
    # this interface, but only through an explicit adaptation. Showing that link here
    # keeps the interface page from claiming "无" while the figure side says otherwise.
    reading_templates = {tm["id"] for tm, spec in live(templates.values())
                         if slug in table_interfaces(spec)}
    related = {}
    for record in all_relations(config):
        figure = record["figure"].removesuffix(".md")
        if (not record["active"] or record["compatibility"] == "direct"
                or not figure.startswith("templates/")
                or figure.split("/", 1)[1] not in reading_templates):
            continue
        previous = related.get(record["method"])
        if previous is None or record["compatibility"] == "adaptable":
            related[record["method"]] = record
    if related:
        links = [f"[[{path.removesuffix('.md')}|{record['method_title']}]]（{record['compatibility']}）"
                 for path, record in sorted(related.items())]
        lines.append("- 经模板关联的方法（经读取该接口的模板；不是 direct，按方法页准备数据）："
                     + " · ".join(links))
    return "\n".join(lines) + "\n"


def source_facts(config: Config, meta: dict) -> str:
    from .sources import read_items
    items = read_items(config, meta["id"])
    recipes = []
    for path in sorted((config.wiki_root / "recipes").glob("*.md")):
        try:
            other = read_page(path)[0]
        except WikiError:
            continue
        if (other.get("source") or {}).get("id") == meta["id"]:
            recipes.append(f"[[recipes/{other['id']}|{other['title']}]]（{other.get('status')}）")
    tags = {}
    for item in items:
        for tag in item.get("tags") or []:
            tags[tag] = tags.get(tag, 0) + 1
    return (f"\n- 上游：{meta['url']} · commit `{str(meta.get('commit') or '未获取')[:12]}`\n"
            f"- 许可证：{meta['license']}；白名单：{'是（按需获取不再询问）' if meta.get('trusted') else '否（获取前先问作者）'}\n"
            f"- 适配器：{meta['adapter']}；快照：`<sources_root>/{meta['snapshot']}`（不进 Wiki）\n"
            f"- L0 目录：{len(items)} 项（`sources/{meta['id']}/items.jsonl`）；"
            f"自动领域分布：{'、'.join(f'{tag} {count}' for tag, count in sorted(tags.items(), key=lambda kv: -kv[1]))}\n"
            f"- L1 配方：{len(recipes)} 个{'：' + ' · '.join(recipes) if recipes else ''}\n")


def scenario_facts(config: Config, meta: dict) -> str:
    from .finder import record_for
    from .curation import visible_picks
    lines = ["\n| 条目 | 级别 | 状态 | 说明 |", "|---|---|---|---|"]
    for pick in visible_picks(config, meta.get("picks") or []):
        value = pick.get("id") if isinstance(pick, dict) else pick
        note = pick.get("note", "") if isinstance(pick, dict) else ""
        key = str(value) if ":" in str(value) else str(value).split("/", 1)[-1].removesuffix(".md")
        record = record_for(config, key)
        if record is None:
            lines.append(f"| {value} | — | 不存在或已归档 | {note} |")
            continue
        link = f"[[{record['page'].removesuffix('.md')}|{record['title']}]]" if record["kind"] != "item" \
            else f"`{record['id']}`"
        state = record.get("status") or "-"
        if record["kind"] == "recipe":
            state += f" · 运行 {record['run']}"
        elif record.get("usable"):
            state += " · 可用"
        lines.append(f"| {link} | {record['level']} | {state} | {note} |")
    return "\n".join(lines) + "\n"


def page_facts(config: Config, meta: dict) -> str:
    if meta["type"] == "layout":
        from .ingest import layout_facts

        return layout_facts(config, meta) + relationship_facts(config, f"layouts/{meta['id']}.md")
    if meta["type"] == "interface":
        return interface_facts(config, meta)
    if meta["type"] == "method":
        return method_facts(config, meta)
    if meta["type"] == "recipe":
        from .recipes import recipe_facts
        return recipe_facts(config, meta)
    if meta["type"] == "source":
        return source_facts(config, meta)
    if meta["type"] == "scenario":
        return scenario_facts(config, meta)
    return template_facts(config, meta)


FACT_DIRS = ("layouts", "templates", "methods", "interfaces", "recipes", "sources", "scenarios")


def refresh_facts(config: Config) -> None:
    # Render every page before writing any, so a failure leaves no half-refreshed set.
    # A page that cannot be read or rendered is skipped here and reported by lint,
    # instead of blocking every save in the Wiki.
    updates = []
    for kind in FACT_DIRS:
        for path in sorted((config.wiki_root / kind).glob("*.md")):
            try:
                meta, body = read_page(path)
                updates.append((path, meta, set_block(body, "facts", page_facts(config, meta))))
            except (WikiError, KeyError, TypeError, ValueError, OSError):
                continue
    for path, meta, body in updates:
        write_page(path, meta, body)

"""Rebuild derived page facts from frontmatter and asset declarations."""

from urllib.parse import quote

from .config import Config, read_json
from .interfaces import load_interface
from .pages import read_page, set_block, write_page


def declarations(root, kind: str) -> dict:
    if kind == "methods":
        return {path.stem: (meta, meta) for path in sorted((root / kind).glob("*.md"))
                for meta in [read_page(path)[0]]}
    return {path.stem: (read_page(path)[0], read_json(path.with_suffix("") / "spec.json"))
            for path in sorted((root / kind).glob("*.md"))
            if (path.with_suffix("") / "spec.json").is_file()}


def table_interfaces(spec: dict) -> set[str]:
    return {table["interface"] for table in spec["tables"].values() if table["interface"]}


def input_interfaces(method: dict) -> set[str]:
    return set(method["inputs"])


def page_link(kind: str, meta: dict, status: bool = False) -> str:
    key = meta["slug"] if kind == "interfaces" else meta["id"]
    return f"[[{kind}/{key}|{meta['title']}]]" + (f"（{meta['status']}）" if status else "")


def interface_link(root, slug: str) -> str:
    return page_link("interfaces", load_interface(root, slug))


def template_facts(config: Config, meta: dict) -> str:
    root = config.wiki_root
    layouts = [page_link("layouts", read_page(root / "layouts" / f"{lid}.md")[0])
               for lid in meta["layouts"]]
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
    return (f"\n- 来源版式：{' · '.join(layouts)}\n"
            f"- 面板（来源版式）：{'、'.join(meta['panels'])}\n- 语言：{meta['language']}\n"
            f"- 标签：{'、'.join(meta['tags'])}\n- 图型：{charts}\n"
            f"- 输入接口：{' · '.join(interfaces) or '未声明'}\n"
            f"- 可接的分析方法：{' · '.join(compatible) or '暂无'}\n")


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
                  if path.is_file()]
    license_text = "仅供个人研究参考" if meta["license"] == "none" else meta["license"]
    return "\n".join([
        f"\n- 来源：{origin}", f"- 许可证：{license_text}",
        f"- 引用：{'；'.join(meta['cite']) or '无'}", f"- 标签：{'、'.join(meta['tags'])}",
        f"- 输入接口：{' · '.join(interface_link(root, slug) for slug in meta['inputs']) or '未声明'}",
        f"- 输出接口：{' · '.join(interface_link(root, slug) for slug in meta['outputs']) or '未声明'}",
        f"- 可接的图：{' · '.join(figures) or '暂无'}",
        f"- 可接的下一步方法：{' · '.join(next_methods) or '暂无'}",
        f"- 代码模板：{' · '.join(code_files) or '无'}",
    ]) + "\n"


def interface_facts(config: Config, meta: dict) -> str:
    slug = meta["slug"]
    methods = declarations(config.wiki_root, "methods")
    templates = declarations(config.wiki_root, "templates")
    producers = [page_link("methods", mm) for mm, method in methods.values() if slug in method["outputs"]]
    readers = [page_link("methods", mm) for mm, method in methods.values() if slug in input_interfaces(method)]
    figures = [page_link("templates", tm) for tm, spec in templates.values() if slug in table_interfaces(spec)]
    lines = ["\n| 列 | 类型 | 含义 |", "|---|---|---|"]
    for name, column in meta["columns"].items():
        lines.append(f"| {name} | {column['type']} | {column['description']} |")
    lines.extend(["", f"- 产出方法：{' · '.join(producers) or '无'}",
                  f"- 读取方法：{' · '.join(readers) or '无'}",
                  f"- 使用的模板：{' · '.join(figures) or '无'}"])
    return "\n".join(lines) + "\n"


def page_facts(config: Config, meta: dict) -> str:
    if meta["type"] == "layout":
        from .ingest import layout_facts

        return layout_facts(config, meta)
    if meta["type"] == "interface":
        return interface_facts(config, meta)
    if meta["type"] == "method":
        return method_facts(config, meta)
    return template_facts(config, meta)


def refresh_facts(config: Config) -> None:
    for kind in ("layouts", "templates", "methods", "interfaces"):
        for path in sorted((config.wiki_root / kind).glob("*.md")):
            meta, body = read_page(path)
            body = set_block(body, "facts", page_facts(config, meta))
            write_page(path, meta, body)

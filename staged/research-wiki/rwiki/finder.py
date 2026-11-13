"""v2 检索与调用（2026-10-27）：catalog.jsonl、find、show、use。

任何 agent 只靠这几条命令就能从“研究场景”走到“课题里的可运行副本”：
find 按场景/图型/关键词排序，show 给出用途、输入、许可与下一步，use 把代码复制进课题。
catalog.jsonl 由 save 重建，一行一个条目（L0 目录项、L1 配方、L2 模板/方法、场景）。
"""
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .adapters import required_packages
from .config import Config
from .errors import WikiError
from .pages import read_page, section_text
from .curation import excluded_paths, filter_records, removed_ids

CATALOG = "catalog.jsonl"
KIND_ORDER = {"scenario": 0, "template": 1, "recipe": 2, "method": 3, "item": 4}
HEADER_LIMIT = 30


def _section(body: str, title: str) -> str:
    try:
        return section_text(body, title)
    except WikiError:
        return ""


def _line(text: str, limit: int = 160) -> str:
    text = " ".join(line.strip("-* ").strip() for line in text.splitlines()
                    if line.strip() and not line.lstrip().startswith(("|", "<!--", "![[")))
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _usable(config: Config, path: Path, meta: dict) -> bool:
    from .acceptance import ready_for_use
    try:
        return bool(ready_for_use(config, path, meta))
    except (WikiError, OSError, KeyError, TypeError, ValueError):
        return False


def _template_record(config: Config, path: Path, meta: dict, body: str) -> dict:
    from .spec import load_spec
    try:
        spec = load_spec(path.with_suffix(""))
        interfaces = sorted({table["interface"] for table in spec["tables"].values() if table.get("interface")})
    except (WikiError, OSError, KeyError, TypeError, ValueError):
        interfaces = []
    return {"id": meta["id"], "kind": "template", "level": "L2", "title": meta["title"],
            "status": meta.get("status"), "usable": _usable(config, path, meta),
            "summary": _line(meta.get("summary") or _section(body, "适用")),
            "not_for": _line(_section(body, "不适用")),
            "chart_types": meta.get("chart_types") or [], "tags": meta.get("tags") or [],
            "keywords": meta.get("keywords") or [], "inputs": interfaces, "language": meta.get("language"),
            "license": meta.get("license", ""), "page": f"templates/{meta['id']}.md",
            "use": f"wiki.py use {meta['id']} --project <课题目录>  # 或 wiki.py render {meta['id']} "
                   "--data <数据目录> --out <输出目录> [--bindings bindings.json]"}


def _recipe_record(config: Config, path: Path, meta: dict, body: str) -> dict:
    from .recipes import current_run
    receipt = current_run(config, path)
    source = meta.get("source") or {}
    return {"id": meta["id"], "kind": "recipe", "level": "L1", "title": meta["title"],
            "status": meta.get("status"), "usable": _usable(config, path, meta),
            "run": receipt["state"] if receipt else "none",
            "run_scope": receipt.get("scope") if receipt else None,
            "missing_packages": (receipt or {}).get("missing_packages", []),
            "summary": _line(_section(body, "用途")), "scenario": _line(_section(body, "适用")),
            "not_for": _line(_section(body, "不适用")),
            "chart_types": meta.get("chart_types") or [], "tags": meta.get("tags") or [],
            "keywords": meta.get("keywords") or [],
            "inputs": [entry["file"] for entry in meta.get("inputs") or []],
            "requires": required_packages(meta.get("packages") or {}), "language": meta.get("language"),
            "license": meta.get("license", ""), "source": f"{source.get('id')}:{source.get('item')}",
            "page": f"recipes/{meta['id']}.md", "use": f"wiki.py use {meta['id']} --project <课题目录>"}


def _method_record(config: Config, path: Path, meta: dict, body: str) -> dict:
    usable = _usable(config, path, meta)
    return {"id": meta["id"], "kind": "method", "level": "L2" if usable else "note", "title": meta["title"],
            "status": meta.get("status"), "usable": usable, "method_kind": meta.get("method_kind"),
            "summary": _line(meta.get("summary") or _section(body, "用途")),
            "not_for": _line(_section(body, "不适用")), "purposes": meta.get("purposes") or [],
            "chart_types": [], "tags": meta.get("tags") or [], "keywords": meta.get("keywords") or [],
            "inputs": meta.get("inputs") or [], "outputs": meta.get("outputs") or [],
            "license": meta.get("license", ""), "page": f"methods/{meta['id']}.md",
            "use": f"wiki.py show {meta['id']}"}


def _scenario_record(meta: dict, body: str) -> dict:
    return {"id": meta["id"], "kind": "scenario", "level": "-", "title": meta["title"],
            "summary": _line(meta.get("summary") or _section(body, "什么时候用")),
            "picks": meta.get("picks") or [], "chart_types": [], "tags": meta.get("tags") or [],
            "keywords": meta.get("keywords") or [], "page": f"scenarios/{meta['id']}.md",
            "use": f"wiki.py show {meta['id']}"}


def _item_record(item: dict, source: dict) -> dict:
    return {"id": item["id"], "kind": "item", "level": "L0", "title": item["title"], "status": "catalog",
            "usable": False, "run": "none", "summary": item.get("requirement") or item.get("requirement_en", ""),
            "scenario": item.get("scenario") or item.get("scenario_en", ""),
            "chart_types": item.get("chart_hints") or [], "tags": item.get("tags") or [],
            "keywords": item.get("keywords") or [], "inputs": [entry["file"] for entry in item.get("inputs") or []],
            "requires": item.get("requires") or [], "language": item.get("language"),
            "license": source.get("license", ""), "source": item["id"], "thumb": item.get("thumb_url", ""),
            "page": f"sources/{source['id']}.md", "use": f"wiki.py use {item['id']} --project <课题目录>"}


def catalog_records(config: Config) -> list[dict]:
    from .catalog import readable_pages
    from .sources import read_items

    records, promoted, sources = [], set(), {}
    for path, meta in readable_pages(config.wiki_root):
        kind = meta.get("type")
        if meta.get("status") == "archived" or kind not in ("recipe", "template", "method", "scenario", "source"):
            continue
        try:
            if kind == "source":
                sources[meta["id"]] = meta
                continue
            body = read_page(path)[1]
            if kind == "recipe":
                records.append(_recipe_record(config, path, meta, body))
                source = meta.get("source") or {}
                promoted.add(f"{source.get('id')}:{source.get('item')}")
            elif kind == "template":
                records.append(_template_record(config, path, meta, body))
            elif kind == "method":
                records.append(_method_record(config, path, meta, body))
            else:
                records.append(_scenario_record(meta, body))
        except (WikiError, OSError, KeyError, TypeError, ValueError):
            continue
    for source_id, meta in sorted(sources.items()):
        for item in read_items(config, source_id):
            if item["id"] not in promoted:
                records.append(_item_record(item, meta))
    return sorted(filter_records(config, records), key=lambda record: (KIND_ORDER.get(record["kind"], 9), record["id"]))


def record_for(config: Config, entry_id: str) -> dict | None:
    """Catalog record of one id (page id or `<source>:<item>`); None when absent or archived."""
    try:
        if entry_id in removed_ids(config):
            return None
        if ":" in entry_id:
            from .sources import find_item, load_source
            source_id, item = entry_id.split(":", 1)
            return _item_record(find_item(config, source_id, item), load_source(config, source_id)[0])
        path = _page(config, entry_id)
        if path.relative_to(config.wiki_root).as_posix() in excluded_paths(config):
            return None
        meta, body = read_page(path)
        if meta.get("status") == "archived":
            return None
        builder = {"recipe": _recipe_record, "template": _template_record, "method": _method_record}.get(meta["type"])
        return builder(config, path, meta, body) if builder else None
    except (WikiError, OSError, KeyError, TypeError, ValueError):
        return None


def render_catalog(config: Config) -> str:
    return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                   for record in catalog_records(config))


def write_catalog(config: Config) -> None:
    path = config.wiki_root / CATALOG
    text = render_catalog(config)
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")


def load_catalog(config: Config) -> list[dict]:
    path = config.wiki_root / CATALOG
    if not path.is_file():
        return catalog_records(config)
    return filter_records(config, [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])


# ---------------------------------------------------------------- find

def find(config: Config, query: str, kind: str | None = None, level: str | None = None,
         runnable: bool = False, limit: int = 10, scope: str = "knowledge") -> list[dict]:
    from .search import search
    return search(config, query, kind=kind, level=level, runnable=runnable, limit=limit, scope=scope)["results"]


def format_find(results: list[dict]) -> str:
    if not results:
        return "没有匹配条目。换个说法（图型名、分析名、英文名）或用 --json 查看 catalog 字段。"
    lines = []
    for record in results:
        state = record["level"]
        if record["kind"] == "recipe":
            state += f" · {record['status']} · 运行 {record['run']}"
        elif record["kind"] in ("template", "method"):
            state += f" · {record['status']}" + (" · 可用" if record.get("usable") else "")
        elif record["kind"] == "item":
            state += " · 目录项（未在 Wiki 运行）"
        lines.append(f"[{state}] {record['id']}  {record['title']}  （{'；'.join(record['why'])}）")
        summary = record.get("summary") or record.get("scenario") or ""
        if summary:
            lines.append(f"    {summary[:120]}")
        extra = []
        if record.get("inputs"):
            extra.append("输入 " + "、".join(record["inputs"][:4]))
        if record.get("missing_packages"):
            extra.append("缺包 " + "、".join(record["missing_packages"][:6]))
        if extra:
            lines.append("    " + "；".join(extra))
        lines.append(f"    → {record['use']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- show

PAGE_KINDS = ("recipes", "templates", "methods", "scenarios", "sources", "interfaces", "chart-types", "projects", "layouts")


def _page(config: Config, entry_id: str) -> Path:
    for kind in PAGE_KINDS:
        path = config.wiki_root / kind / f"{entry_id}.md"
        if path.is_file():
            return path
    raise WikiError(f"没有条目 {entry_id}（L0 目录项写成 <来源>:<条目>，如 figureya:FigureYa59volcanoV2）")


def show(config: Config, entry_id: str) -> dict:
    if ":" in entry_id:
        from .sources import find_item, load_source
        source_id, item = entry_id.split(":", 1)
        source, _ = load_source(config, source_id)
        record = find_item(config, source_id, item)
        recipe = config.wiki_root / "recipes" / f"{record['recipe']}.md"
        return {"kind": "item", "level": "L0", "record": record, "license": source.get("license"),
                "license_notice": source.get("license_notice", ""),
                "upstream": f"{source['url'].rstrip('/')}/tree/{record['commit']}/{item}",
                "promoted": f"recipes/{record['recipe']}.md" if recipe.is_file() else None,
                "next": [f"wiki.py use {entry_id} --project <课题目录>",
                         f"wiki.py promote {source_id} {item}   # 升级为 L1 配方并原样运行"]}
    path = _page(config, entry_id)
    meta, body = read_page(path)
    kind = meta["type"]
    sections = {title: _section(body, title) for title in
                {"recipe": ("用途", "适用", "不适用", "输入", "怎么用", "输出"),
                 "template": ("适用", "不适用", "数据要求"),
                 "layout": ("适用", "不适用", "知识关联检查"),
                 "method": ("用途", "适用", "不适用", "输入", "怎么做", "代码", "输出"),
                 "scenario": ("什么时候用", "首选组合", "注意"),
                 "source": ("这是什么", "怎么用", "许可与引用"),
                 "interface": ("含义",),
                 "chart-type": ("回答什么问题", "什么时候选它", "什么时候不要用", "与相近图型怎么区分", "常见误用"),
                 "project": ("用途", "使用记录")}.get(kind, ())}
    result = {"kind": kind, "path": path.relative_to(config.wiki_root).as_posix(), "meta": meta,
              "sections": {key: value for key, value in sections.items() if value}}
    from .asset_checkout import assets_state, profile
    transport = assets_state(config, path)
    result.update(asset_availability=transport['state'], asset_details=transport)
    sparse = profile(config) == 'light'
    if sparse:
        result['evidence_state'] = 'not_checked'
    if kind == "recipe":
        from .recipes import current_run, license_notice
        receipt = current_run(config, path) if profile(config) != 'light' else None
        result["last_run"] = {key: receipt.get(key) for key in
                              ("state", "scope", "started_at", "duration_s", "missing_packages", "error",
                               "missing_outputs")} if receipt else None
        result["license_notice"] = license_notice(meta.get("license", ""))
        if profile(config) == 'light':
            result['evidence_state'] = 'not_checked'
        result["next"] = [f"wiki.py use {entry_id} --project <课题目录>", "wiki.py run --dir <副本目录>"]
    elif kind == "template":
        from .interfaces import load_interface
        from .spec import load_spec
        spec = load_spec(path.with_suffix(""))
        tables = {}
        for key, table in spec["tables"].items():
            columns = load_interface(config.wiki_root, table["interface"])["columns"] if table.get("interface") else {}
            tables[key] = {"interface": table.get("interface"), "required": table.get("required", True),
                           "columns": {name: {"type": column["type"], "required": column.get("required", True),
                                              "description": column["description"]}
                                       for name, column in columns.items()}}
        result["tables"] = tables
        result["usable"] = False if sparse else _usable(config, path, meta)
        result["next"] = [f"wiki.py use {entry_id} --project <课题目录>",
                          f"wiki.py render {entry_id} --data <数据目录> --out <输出目录> --bindings <bindings.json>"]
    elif kind == "method":
        from .method_implementations import implementation_status
        result["implementations"] = [{key: item.get(key) for key in ("id", "state", "entrypoint")}
                                     for item in ([] if sparse else implementation_status(path, meta))]
        result["usable"] = False if sparse else _usable(config, path, meta)
    return result


def format_show(detail: dict) -> str:
    if detail["kind"] == "item":
        record = detail["record"]
        lines = [f"{record['id']}  [L0 目录项 · 未在 Wiki 运行]", f"许可：{detail['license']}",
                 f"用途：{record.get('requirement') or record.get('requirement_en') or '—'}",
                 f"场景：{record.get('scenario') or record.get('scenario_en') or '—'}",
                 "输入：" + ("；".join(f"{entry['file']}" for entry in record.get("inputs", [])) or "—"),
                 "依赖：" + ("、".join(record.get("requires", [])) or "—"),
                 f"上游：{detail['upstream']}"]
        if detail.get("promoted"):
            lines.append(f"已升级为配方：{detail['promoted']}")
        lines += [f"→ {command}" for command in detail["next"]]
        return "\n".join(lines)
    meta = detail["meta"]
    head = f"{meta.get('id', meta.get('slug'))}  {meta['title']}  [{detail['kind']} · {meta.get('status', '-')}]"
    lines = [head]
    if detail.get('evidence_state') == 'not_checked':
        lines.append('资产：' + str(detail.get('asset_availability')) + '；轻量检出尚未核对完整证据（not_checked），不表示验证失败。')
    if detail.get("license_notice"):
        lines.append(f"许可：{detail['license_notice']}")
    for title, text in detail["sections"].items():
        lines.append(f"## {title}\n{text}")
    if detail.get("last_run"):
        run = detail["last_run"]
        lines.append(f"最近运行：{run['state']}（{run['scope']}，{run['started_at']}，{run['duration_s']} 秒）"
                     + (f"；缺包 {'、'.join(run['missing_packages'])}" if run.get("missing_packages") else "")
                     + (f"；错误 {run['error'][:200]}" if run.get("error") and run["state"] != "pass" else ""))
    elif detail["kind"] == "recipe" and detail.get('evidence_state') != 'not_checked':
        lines.append("最近运行：尚无当前原字节的运行收据")
    if detail.get("tables"):
        for key, table in detail["tables"].items():
            columns = "、".join(f"{name}{'' if column['required'] else '（可选）'}"
                               for name, column in table["columns"].items())
            lines.append(f"表 {key} → 接口 {table['interface']}：{columns}")
    if detail.get("implementations"):
        lines.append("实现：" + "；".join(f"{item['id']}={item['state']}" for item in detail["implementations"]))
    lines.append(f"页面：{detail['path']}")
    lines += [f"→ {command}" for command in detail.get("next", [])]
    return "\n".join(lines)


# ---------------------------------------------------------------- use

def _header(path: Path) -> list[str]:
    if path.suffix.lower() not in (".csv", ".txt", ".tsv") or path.stat().st_size > 200 * 2 ** 20:
        return []
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        line = stream.readline()
    delimiter = "\t" if line.count("\t") > line.count(",") else ","
    return next(csv.reader([line], delimiter=delimiter), [])[:HEADER_LIMIT]


def _destination(project: Path, name: str) -> Path:
    destination = project / "wiki-use" / name
    if destination.exists():
        raise WikiError(f"{destination} 已存在；换 --name 或先移走旧副本")
    return destination


def _check_project(config: Config, project: Path) -> Path:
    project = project.resolve()
    if project == config.wiki_root or project.is_relative_to(config.wiki_root):
        raise WikiError("课题目录不能在知识库内；课题数据与成图留在课题目录")
    if not project.is_dir():
        raise WikiError(f"课题目录不存在: {project}")
    return project


def _write_use_note(destination: Path, title: str, origin: dict, notice: str, inputs: list[dict],
                    commands: list[str], extra: list[str]) -> None:
    lines = [f"# {title}", "", f"> {notice}", "",
             f"- 来自科研知识库：`{origin['id']}`（{origin['level']}）；来源 {origin.get('upstream') or origin.get('page')}",
             f"- 入口：`{origin.get('entry', '')}`；复制时间 {origin['copied_at']}", ""]
    lines += ["## 运行", ""] + [f"- `{command}`" for command in commands] + [""]
    if inputs:
        lines += ["## 换成课题数据", "",
                  "替换下列文件，保持文件名、列名与格式；参数在入口文件的参数设置段改。改统计逻辑、阈值含义或分组定义前先问作者。",
                  "", "| 输入文件 | 列（示例文件表头） | 说明 |", "|---|---|---|"]
        for entry in inputs:
            path = destination / entry["file"]
            columns = "、".join(_header(path)) if path.is_file() else "（副本里没有这个文件）"
            lines.append(f"| `{entry['file']}` | {columns or '—'} | {entry.get('note', '')[:120]} |")
        lines.append("")
    lines += extra
    (destination / "RWIKI-USE.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


def use(config: Config, entry_id: str, project: Path, name: str | None = None) -> dict:
    from .recipes import HARNESS, license_notice, tree_hashes

    project = _check_project(config, project)
    if ':' not in entry_id:
        from .asset_checkout import fetch_assets
        fetch_assets(config, entry_id)
    copied_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if ":" in entry_id:
        from .sources import fetch_source, find_item, load_source, snapshot_dir
        from .adapters import ADAPTERS
        source_id, item = entry_id.split(":", 1)
        source, _ = load_source(config, source_id)
        if not source.get("trusted"):
            raise WikiError(f"来源 {source_id} 不在白名单（trusted: false）：先问作者是否获取上游代码")
        record = find_item(config, source_id, item)
        fetch_source(config, source_id, [item])
        directory = snapshot_dir(config, source) / item
        destination = _destination(project, name or ADAPTERS[source["adapter"]].recipe_id(item))
        shutil.copytree(directory, destination, ignore=shutil.ignore_patterns("*.html", ".git"))
        entry = Path(record["rmd"]).name if record.get("rmd") else ""
        origin = {"id": entry_id, "kind": "item", "level": "L0", "entry": entry, "packages": record["packages"],
                  "outputs": record.get("outputs", []), "license": source.get("license"),
                  "upstream": f"{source['url'].rstrip('/')}/tree/{record['commit']}/{item}",
                  "commit": record["commit"], "copied_at": copied_at}
        title, inputs = record["title"], record.get("inputs", [])
        notice = license_notice(source.get("license", ""), source.get("license_notice", ""))
        commands = [f'wiki.py run --dir "{destination}"']
        extra = ["L0 目录项：Wiki 里没有运行过这个模块；首次运行若缺包，列出包名问作者。"]
    else:
        path = _page(config, entry_id)
        meta, _ = read_page(path)
        kind = meta["type"]
        destination = _destination(project, name or entry_id)
        if kind == "recipe":
            from .recipes import integrity_errors
            errors = integrity_errors(path)
            if errors:
                raise WikiError("；".join(errors) + f"（可先 wiki.py restore {entry_id}）")
            shutil.copytree(path.with_suffix("") / "source", destination)
            source = meta.get("source") or {}
            origin = {"id": entry_id, "kind": "recipe", "level": "L1", "entry": Path(meta["entry"]).name,
                      "packages": meta.get("packages") or {}, "outputs": meta.get("outputs") or [],
                      "license": meta.get("license"), "page": f"recipes/{entry_id}.md",
                      "upstream": f"{source.get('url', '').rstrip('/')}/tree/{source.get('commit')}/{source.get('item')}",
                      "commit": source.get("commit"), "copied_at": copied_at}
            title, inputs = meta["title"], meta.get("inputs") or []
            notice = license_notice(meta.get("license", ""))
            commands = [f'wiki.py run --dir "{destination}"',
                        f"或用课题自己的 R：在副本目录 Rscript -e \"knitr::knit('{origin['entry']}')\""
                        "（先自行处理 install_dependencies.R）"]
            extra = []
        elif kind == "template":
            from .interfaces import load_interface
            from .spec import load_spec
            target = path.with_suffix("")
            spec = load_spec(target)
            destination.mkdir(parents=True)
            for folder in ("code", "example"):
                if (target / folder).is_dir():
                    shutil.copytree(target / folder, destination / folder,
                                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for filename in ("spec.json", "runtime.json"):
                if (target / filename).is_file():
                    shutil.copyfile(target / filename, destination / filename)
            bindings = {"tables": {}}
            for key, table in spec["tables"].items():
                columns = load_interface(config.wiki_root, table["interface"])["columns"]
                bindings["tables"][key] = {"file": f"{table['interface']}.csv",
                                           "columns": {column: column for column in columns}}
            (destination / "bindings.draft.json").write_text(
                json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            origin = {"id": entry_id, "kind": "template", "level": "L2", "entry": spec["entry"],
                      "license": meta.get("license", ""), "page": f"templates/{entry_id}.md", "copied_at": copied_at}
            title, inputs = meta["title"], []
            notice = license_notice(meta.get("license") or "", "许可见模板页与 runtime.json 的 source.license。")
            commands = [f'wiki.py render {entry_id} --data <课题数据目录> --out <输出目录> --bindings '
                        f'"{destination / "bindings.json"}"']
            extra = ["## 列映射", "",
                     "`bindings.draft.json` 的 `columns` 是“内部字段 → 课题列”。把右侧改成课题表的列名、`file` 改成课题文件名，"
                     "另存为 `bindings.json`。含义/单位/粒度不清先问作者；不在映射里补值、换算或聚合。", "",
                     "示例数据在 `example/`，代码副本在 `code/`（课题环境独立调用时用）。"]
        elif kind == "method":
            target = path.with_suffix("")
            if not (target / "code").is_dir():
                raise WikiError(f"方法 {entry_id} 没有可复制的 code/（文字笔记）；读页面后在课题里自己实现前先问作者")
            shutil.copytree(target / "code", destination / "code", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            if (target / "runtime.json").is_file():
                shutil.copyfile(target / "runtime.json", destination / "runtime.json")
            origin = {"id": entry_id, "kind": "method", "level": "L2", "entry": "",
                      "license": meta.get("license", ""), "page": f"methods/{entry_id}.md", "copied_at": copied_at}
            title, inputs = meta["title"], []
            notice = license_notice(meta.get("license") or "")
            commands = [f"按 {origin['page']} 的“代码/怎么做”在课题环境调用 code/ 中的入口函数"]
            extra = []
        else:
            raise WikiError(f"{kind} 页面不能 use；用 show 查看")
    origin["files"] = {name: digest for name, digest in tree_hashes(destination).items() if name not in HARNESS}
    (destination / "rwiki-origin.json").write_text(json.dumps(origin, ensure_ascii=False, indent=2) + "\n",
                                                   encoding="utf-8", newline="\n")
    _write_use_note(destination, title, origin, notice, inputs, commands, extra)
    missing = []
    packages = origin.get("packages")
    if packages:
        from .recipes import missing_packages
        try:
            missing = missing_packages(config, required_packages(packages))
        except WikiError:
            missing = ["（未能检查：Rscript 不可用）"]
    return {"copy": str(destination), "level": origin["level"], "license": origin.get("license"),
            "missing_packages_in_wiki_r": missing, "next": commands, "note": "见副本里的 RWIKI-USE.md"}

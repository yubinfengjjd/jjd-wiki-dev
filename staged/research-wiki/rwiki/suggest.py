from decimal import Decimal, ROUND_HALF_UP

from .catalog import page_paths
from .config import Config
from .errors import WikiError

from .pages import get_block, read_page, section_text
from .spec import load_spec


def column_score(tables: dict, columns: str) -> tuple[float, list[str]]:
    supplied = {column.strip().casefold() for column in columns.split(",")}
    coverage = Decimal(0)
    reasons = []
    for name, table in tables.items():
        covered = [column for column in table["columns"] if column.casefold() in supplied]
        missing = [column for column in table["columns"] if column.casefold() not in supplied]
        coverage += Decimal(len(covered)) / len(table["columns"])
        reasons.append(f"列覆盖（{name}）：覆盖 {'、'.join(covered) or '无'}；缺少 {'、'.join(missing) or '无'}")
    score = (coverage / len(tables) * 4).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return float(score), reasons


def suggest(config: Config, chart_types: list[str],
            columns: str | None, query: str, limit: int) -> list[dict]:
    if limit < 0:
        raise WikiError("--limit 不能为负数")
    results = []
    for path in page_paths(config.wiki_root):
        meta, body = read_page(path)
        if meta["type"] not in ("layout", "template") or meta["status"] != "ready":
            continue
        target = path.with_suffix("")
        if meta["type"] == "template":
            spec = load_spec(target)
            tables, style_keys = spec["tables"], list(spec["style"])
        else:
            specs = {tid: load_spec(config.wiki_root / "templates" / tid) for tid in meta["templates"]}
            tables = {f"{tid}/{name}": table for tid, spec in specs.items() for name, table in spec["tables"].items()}
            style_keys = list(dict.fromkeys(key for spec in specs.values() for key in spec["style"]))
        applicable = section_text(body, "适用")
        note = get_block(body, "user").strip()
        reasons = []
        score = 0
        for slug in chart_types:
            if slug in meta["chart_types"]:
                score += 2
                reasons.append(f"图型匹配：{slug}")
        if columns is not None:
            points, details = column_score(tables, columns)
            score += points
            reasons.extend(details)
        searchable = "\n".join([meta["title"], *meta["tags"], applicable]).casefold()
        for word in dict.fromkeys(query.casefold().split()):
            if word in searchable:
                score += 1
                reasons.append(f"关键词匹配：{word}")
        item = {"id": meta["id"], "kind": meta["type"], "title": meta["title"], "score": score,
                        "reasons": reasons, "page": path.relative_to(config.wiki_root).as_posix(),
                        "preview": str((target / "preview.png").resolve()),
                        "applicable": applicable, "not_applicable": section_text(body, "不适用"),
                        "note": note, "tables": tables, "style_keys": style_keys}
        if meta["type"] == "layout":
            item["templates"] = meta["templates"]
        results.append(item)
    return sorted(results, key=lambda item: (-item["score"], item["title"]))[:limit]


def suggest_pipeline(config: Config, figure: str | None = None, query: str = "") -> list[dict]:
    methods = []
    for path in sorted((config.wiki_root / "methods").glob("*.md")):
        meta, body = read_page(path)
        if meta["status"] == "ready":
            methods.append((meta, body))
    groups = []
    for path in sorted((config.wiki_root / "templates").glob("*.md")):
        template, body = read_page(path)
        if template["status"] != "ready" or (figure is not None and template["id"] != figure):
            continue
        spec = load_spec(path.with_suffix(""))
        required = {table["interface"] for table in spec["tables"].values()}
        candidates = []
        for meta, method_body in methods:
            if not required <= set(meta["outputs"]):
                continue
            score, reasons = 0, []
            applicable = section_text(method_body, "适用")
            searchable = "\n".join([meta["title"], *meta["tags"], applicable,
                                    template["title"], *template["tags"], section_text(body, "适用")]).casefold()
            for word in dict.fromkeys(query.casefold().split()):
                if word in searchable:
                    score += 1
                    reasons.append(f"关键词匹配：{word}")
            code_files = [p.relative_to(config.wiki_root).as_posix()
                          for p in sorted((config.wiki_root / "methods" / meta["id"] / "code").rglob("*"))
                          if p.is_file()]
            candidates.append({"id": meta["id"], "title": meta["title"], "tags": meta["tags"],
                               "score": score, "reasons": reasons, "applicable": applicable,
                               "not_applicable": section_text(method_body, "不适用"),
                               "license": meta["license"], "code_files": code_files})
        groups.append({"id": template["id"], "title": template["title"], "interfaces": sorted(required),
                       "methods": sorted(candidates, key=lambda item: (-item["score"], item["title"], item["id"]))})
    return sorted(groups, key=lambda group: (-max((m["score"] for m in group["methods"]), default=0),
                                           group["title"], group["id"]))

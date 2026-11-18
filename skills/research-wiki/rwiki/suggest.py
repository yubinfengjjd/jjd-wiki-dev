from decimal import Decimal, ROUND_HALF_UP

from .catalog import page_paths
from .config import Config
from .errors import WikiError
from .interfaces import load_interface

from .pages import get_block, read_page, section_text
from .spec import load_spec
from .relations import all_relations
from .acceptance import ready_for_use
from .curation import excluded_paths


DISCOVERY_NOTE = "关键词与列覆盖仅为检索线索；需由课题 agent 核对研究目的、每行单位、量纲和方法前提。"


def _section(body: str, title: str) -> str:
    try:
        return section_text(body, title)
    except WikiError:
        return ""


def _code_context(config: Config, path) -> dict:
    from .code_assets import code_files

    inventory = code_files(config, path.relative_to(config.wiki_root).as_posix())
    files = inventory["files"]
    return {"available": bool(files),
            "has_original": any(item["variant"] == "original" for item in files),
            "has_reusable": any(item["variant"] == "reusable" for item in files),
            "files": files, "note": inventory.get("note", ""),
            "execution_note": "文件存在或复用版不证明可运行；验证范围见各文件记录。"}


def _reusable_files(config: Config, path) -> list[str]:
    return [item.relative_to(config.wiki_root).as_posix()
            for item in sorted((path.with_suffix("") / "code").rglob("*"))
            if item.is_file() and "__pycache__" not in item.parts
            and item.suffix.lower() not in (".pyc", ".pyo")]


def _requirements(config: Config, slugs: list[str]) -> dict:
    requirements = {}
    for slug in slugs:
        try:
            interface = load_interface(config.wiki_root, slug)
            requirements[slug] = {"interface": slug, "title": interface["title"],
                                  "columns": interface["columns"]}
        except WikiError as error:
            requirements[slug] = {"interface": slug, "columns": {}, "error": str(error)}
    return requirements


def _method_candidate(config: Config, path, meta: dict, body: str, query: str,
                      columns: str | None, relations: list[dict]) -> dict:
    from .method_implementations import verified_implementations, implementation_status
    implementations = verified_implementations(path, meta)
    branch_files = [path.with_suffix('').joinpath(item['entrypoint'].partition(':')[0]).relative_to(
        config.wiki_root).as_posix() for item in implementations]
    requirements = _requirements(config, meta["inputs"])
    applicable = _section(body, "适用")
    searchable = "\n".join([meta["title"], *meta["tags"], applicable,
                             _section(body, "用途"), _section(body, "输入")]).casefold()
    score, reasons = 0, []
    for word in dict.fromkeys(query.casefold().split()):
        if word in searchable:
            score += 1
            reasons.append(f"关键词匹配：{word}")
    if columns is not None:
        points, details = column_score(requirements, columns)
        score += points
        reasons.extend(details)
    declared = meta.get("prerequisites", [])
    prerequisites = [item for item in declared if isinstance(item, str)] if isinstance(declared, list) else []
    prerequisites = list(dict.fromkeys([*prerequisites, *(prerequisite for relation in relations
                                                        for prerequisite in relation["prerequisites"])]))
    return {"id": meta["id"], "kind": "method", "title": meta["title"],
            "page": path.relative_to(config.wiki_root).as_posix(), "status": meta["status"],
            "tags": meta["tags"], "score": score, "reasons": reasons,
            "purpose": _section(body, "用途"), "applicable": applicable,
            "not_applicable": _section(body, "不适用"), "input": _section(body, "输入"),
            "inputs": meta["inputs"], "outputs": meta["outputs"],
            "input_requirements": requirements, "prerequisites": prerequisites,
            "relations": relations, "license": meta["license"],
            "method_kind": meta.get('method_kind'), "data_contract": meta.get('data_contract'),
            "implementations": implementations,
            "implementation_status": [item for item in implementation_status(path, meta) if item['state'] == 'verified'],
            "code_files": branch_files, "code_status": _code_context(config, path),
            "project_readiness": "requires_project_review", "discovery_note": DISCOVERY_NOTE}


def suggest_methods(config: Config, query: str = "", columns: str | None = None,
                    limit: int = 3) -> list[dict]:
    """Discover confirmed notes, including notes with no figure or matching columns.

    This is inventory discovery, not scientific inference or permission to run.
    Preconditions/materials must be assessed against the current project by its agent.
    """
    if limit < 0:
        raise WikiError("--limit 不能为负数")
    relations = all_relations(config, include_archived=False)
    results = []
    for path in sorted((config.wiki_root / "methods").glob("*.md")):
        meta, body = read_page(path)
        if not ready_for_use(config, path, meta):
            continue
        linked = [record for record in relations
                  if record["method"] == path.relative_to(config.wiki_root).as_posix()]
        results.append(_method_candidate(config, path, meta, body, query, columns, linked))
    return sorted(results, key=lambda item: (-item["score"], item["title"], item["id"]))[:limit]


def column_score(tables: dict, columns: str) -> tuple[float, list[str]]:
    supplied = {column.strip().casefold() for column in columns.split(",")}
    coverage = Decimal(0)
    reasons = []
    if not tables:
        return 0, ["未声明可比较的输入列；仍保留候选，需核对实际材料与前提"]
    for name, table in tables.items():
        covered = [column for column in table["columns"] if column.casefold() in supplied]
        missing = [column for column in table["columns"] if column.casefold() not in supplied]
        coverage += Decimal(len(covered)) / len(table["columns"]) if table["columns"] else Decimal(0)
        reasons.append(f"列覆盖（{name}）：覆盖 {'、'.join(covered) or '无'}；缺少 {'、'.join(missing) or '无'}")
    score = (coverage / len(tables) * 4).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return float(score), reasons


def suggest(config: Config, chart_types: list[str],
            columns: str | None, query: str, limit: int) -> list[dict]:
    if limit < 0:
        raise WikiError("--limit 不能为负数")
    results = []
    relations = all_relations(config, include_archived=False)
    hidden = excluded_paths(config)
    for path in page_paths(config.wiki_root):
        if path.relative_to(config.wiki_root).as_posix() in hidden:
            continue
        meta, body = read_page(path)
        if meta["type"] not in ("layout", "template") or not ready_for_use(config, path, meta):
            continue
        if getattr(config, "single_panel_only", False) and meta["type"] == "layout" and len(meta["panels"]) != 1:
            continue
        target = path.with_suffix("")
        if meta["type"] == "template":
            spec = load_spec(target)
            tables, style_keys = spec["tables"], list(spec["style"])
        else:
            from .aliases import resolve_page_ref
            try:
                specs = {
                    tid: load_spec(
                        (resolve_page_ref(config.wiki_root, tid, expected_type="template")
                         or (config.wiki_root / "templates" / f"{tid}.md")).with_suffix("")
                    )
                    for tid in meta["templates"]
                }
            except (WikiError, OSError, ValueError, KeyError, TypeError):
                # A layout whose callable template cannot be loaded is not a
                # valid recommendation; skip it instead of failing the query.
                continue
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
        linked = [relation for relation in relations if relation["figure"] == item["page"]
                  and relation["method_status"] == "ready"]
        item.update(relations=linked,
                    prerequisites=list(dict.fromkeys(prerequisite for relation in linked
                                                      for prerequisite in relation["prerequisites"])),
                    code_status=_code_context(config, path), discovery_note=DISCOVERY_NOTE)
        results.append(item)
    return sorted(results, key=lambda item: (-item["score"], item["title"]))[:limit]


def suggest_pipeline(config: Config, figure: str | None = None, query: str = "") -> list[dict]:
    hidden = excluded_paths(config)
    methods = []
    for path in sorted((config.wiki_root / "methods").glob("*.md")):
        meta, body = read_page(path)
        if ready_for_use(config, path, meta):
            methods.append((path, meta, body))
    relations = all_relations(config, include_archived=False)
    groups = []
    for path in sorted((config.wiki_root / "templates").glob("*.md")):
        if path.relative_to(config.wiki_root).as_posix() in hidden:
            continue
        template, body = read_page(path)
        if not ready_for_use(config, path, template) or (
            figure is not None and figure not in (template["id"], *(template.get("aliases") or []))
        ):
            continue
        spec = load_spec(path.with_suffix(""))
        required = {table["interface"] for table in spec["tables"].values()}
        candidates = []
        figure_path = path.relative_to(config.wiki_root).as_posix()
        figure_relations = [relation for relation in relations
                            if relation["figure"] == figure_path and relation["method_status"] == "ready"]
        for method_path, meta, method_body in methods:
            method_page = method_path.relative_to(config.wiki_root).as_posix()
            relation = next((record for record in figure_relations if record["method"] == method_page), None)
            structural = bool(required) and required <= set(meta["outputs"])
            if not structural and relation is None:
                continue
            score, reasons = 0, []
            applicable = section_text(method_body, "适用")
            searchable = "\n".join([meta["title"], *meta["tags"], applicable,
                                    template["title"], *template["tags"], section_text(body, "适用")]).casefold()
            for word in dict.fromkeys(query.casefold().split()):
                if word in searchable:
                    score += 1
                    reasons.append(f"关键词匹配：{word}")
            candidate = _method_candidate(config, method_path, meta, method_body, "", None,
                                          [relation] if relation else [])
            candidate.update(score=score, reasons=reasons, structural_match=structural,
                             match_basis="reviewed_relation" if relation else "interface_structure",
                             compatibility=relation["compatibility"] if relation else None,
                             verification=relation["verification"] if relation else None)
            if not relation:
                candidate["match_note"] = "仅接口结构匹配，语义与课题前提尚待核实；不代表直接可接。"
            candidates.append(candidate)
        groups.append({"id": template["id"], "kind": "template", "page": figure_path,
                       "title": template["title"], "interfaces": sorted(required),
                       "relations": figure_relations, "code_status": _code_context(config, path),
                       "discovery_note": DISCOVERY_NOTE,
                       "methods": sorted(candidates, key=lambda item: (-item["score"], item["title"], item["id"]))})
    return sorted(groups, key=lambda group: (-max((m["score"] for m in group["methods"]), default=0),
                                           group["title"], group["id"]))


def _locate_node(config: Config, node_id: str):
    from .aliases import resolve_page_ref

    resolved = resolve_page_ref(
        config.wiki_root,
        node_id,
        expected_types=("method", "interface", "template", "recipe", "scenario"),
    )
    if resolved is not None:
        return resolved
    raise WikiError(f"未找到节点页面: {node_id}")


def _normalize_next_step(item: dict) -> dict:
    def _str_list(val) -> list[str]:
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        if isinstance(val, str) and val.strip():
            return [val.strip()]
        return []

    return {
        "direction": str(item.get("direction") or item.get("title") or "下一步方向"),
        "when": str(item.get("when") or item.get("condition") or ""),
        "analysis_templates": _str_list(item.get("analysis_templates") or item.get("methods")),
        "intermediate_interface": str(item.get("intermediate_interface") or item.get("interface") or ""),
        "viz_templates": _str_list(item.get("viz_templates") or item.get("templates")),
    }


def suggest_next_steps(config: Config, node_id: str, query: str = "") -> dict:
    """Return structured downstream bioinformatics directions and structural interface matches."""
    from .catalog import readable_pages
    from .facts import declarations, input_interfaces, table_interfaces

    path = _locate_node(config, node_id)
    meta, body = read_page(path)
    kind = meta.get("type", "")
    canonical_id = str(meta.get("id") or meta.get("slug") or path.stem)
    title = meta.get("title", canonical_id)

    raw_steps = meta.get("next_steps")
    next_steps: list[dict] = []
    if isinstance(raw_steps, list):
        for entry in raw_steps:
            if isinstance(entry, dict):
                next_steps.append(_normalize_next_step(entry))
    elif kind == "scenario" and isinstance(meta.get("steps"), list):
        for entry in meta["steps"]:
            if isinstance(entry, dict):
                next_steps.append(_normalize_next_step(entry))

    outputs: set[str] = set()
    if kind == "method":
        outputs = {str(s) for s in (meta.get("outputs") or []) if isinstance(s, str) and s.strip()}
    elif kind == "interface":
        outputs = {str(meta.get("slug") or canonical_id)}
    elif kind == "template":
        spec_path = path.with_suffix("") / "spec.json"
        if spec_path.is_file():
            try:
                spec = load_spec(path.with_suffix(""))
                outputs = table_interfaces(spec)
            except (WikiError, OSError, ValueError, KeyError, TypeError):
                outputs = set()

    structural_matches: list[dict] = []
    if outputs:
        for tid, (tm, spec) in declarations(config.wiki_root, "templates").items():
            if tm.get("status") == "archived":
                continue
            req = table_interfaces(spec)
            if req and req & outputs:
                preview_file = config.wiki_root / "templates" / tid / "preview.png"
                structural_matches.append({
                    "id": tid,
                    "kind": "template",
                    "type": "template",
                    "title": tm.get("title", tid),
                    "status": tm.get("status"),
                    "interfaces": sorted(req),
                    "inputs": sorted(req),
                    "path": f"templates/{tid}.md",
                    "page": f"templates/{tid}.md",
                    "preview": f"/files/wiki/templates/{tid}/preview.png" if preview_file.is_file() else None,
                })
        for mid, (mm, method_meta) in declarations(config.wiki_root, "methods").items():
            if mm.get("status") == "archived" or mid == canonical_id:
                continue
            ins = input_interfaces(method_meta)
            if ins and ins & outputs:
                structural_matches.append({
                    "id": mid,
                    "kind": "method",
                    "type": "method",
                    "title": mm.get("title", mid),
                    "status": mm.get("status"),
                    "interfaces": sorted(ins),
                    "inputs": sorted(ins),
                    "outputs": list(method_meta.get("outputs") or []),
                    "path": f"methods/{mid}.md",
                    "page": f"methods/{mid}.md",
                })
    # Also attach any scenario step links if node_id appears in playbook scenarios
    if not next_steps:
        for spath, smeta in readable_pages(config.wiki_root):
            if smeta.get("type") != "scenario" or not isinstance(smeta.get("steps"), list):
                continue
            steps = smeta["steps"]
            for idx, st in enumerate(steps):
                if not isinstance(st, dict):
                    continue
                if st.get("id") in (canonical_id, node_id) or st.get("method_id") in (canonical_id, node_id):
                    for nxt in steps[idx + 1:]:
                        if isinstance(nxt, dict) and (nxt.get("parent") == st.get("id") or idx + 1 == steps.index(nxt)):
                            next_steps.append(_normalize_next_step(nxt))
                    break

    words = [w for w in dict.fromkeys(query.casefold().split()) if w]
    if words:
        def _matches(text: str) -> bool:
            low = text.casefold()
            return any(w in low for w in words)

        filtered_steps = [
            step for step in next_steps
            if _matches(" ".join([
                step["direction"], step["when"], step["intermediate_interface"],
                *step["analysis_templates"], *step["viz_templates"],
            ]))
        ]
        if filtered_steps:
            next_steps = filtered_steps
        filtered_matches = [
            m for m in structural_matches
            if _matches(" ".join([m["id"], m["title"], *m.get("interfaces", [])]))
        ]
        if filtered_matches:
            structural_matches = filtered_matches

    return {
        "node_id": canonical_id,
        "requested_id": node_id,
        "kind": kind,
        "title": title,
        "page": path.relative_to(config.wiki_root).as_posix(),
        "outputs": sorted(outputs),
        "next_steps": next_steps,
        "structural_matches": structural_matches,
    }


def format_next_steps(payload: dict) -> str:
    lines = [f"{payload['node_id']}  {payload['title']}  [{payload['kind']}]"]
    if payload.get("outputs"):
        lines.append("输出中间表：" + "、".join(payload["outputs"]))
    steps = payload.get("next_steps") or []
    if steps:
        lines.append("下一步分析方向：")
        for idx, step in enumerate(steps, 1):
            lines.append(f"  {idx}. {step['direction']}")
            if step["when"]:
                lines.append(f"     触发条件：{step['when']}")
            if step["intermediate_interface"]:
                lines.append(f"     标准中间表：{step['intermediate_interface']}")
            if step["analysis_templates"]:
                lines.append(f"     推荐分析模版：{', '.join(step['analysis_templates'])}")
            if step["viz_templates"]:
                lines.append(f"     配套可视化模版：{', '.join(step['viz_templates'])}")
    else:
        lines.append("暂无显式 next_steps 声明。")
    matches = payload.get("structural_matches") or []
    if matches:
        lines.append("接口结构匹配下游条目：")
        for m in matches:
            lines.append(f"  - [{m['kind']}] {m['id']}  {m['title']} ({', '.join(m.get('interfaces', []))})")
    return "\n".join(lines)

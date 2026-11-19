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
        required = {table["interface"] for table in spec["tables"].values() if table.get("interface")}
        all_interfaced = bool(required) and all(table.get("interface") for table in spec["tables"].values())
        candidates = []
        figure_path = path.relative_to(config.wiki_root).as_posix()
        figure_relations = [relation for relation in relations
                            if relation["figure"] == figure_path and relation["method_status"] == "ready"]
        for method_path, meta, method_body in methods:
            method_page = method_path.relative_to(config.wiki_root).as_posix()
            relation = next((record for record in figure_relations if record["method"] == method_page), None)
            structural = all_interfaced and required <= set(meta["outputs"])
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

    analysis_refs = _str_list(item.get("analysis_templates") or item.get("methods"))
    method_id = str(item.get("method_id") or "").strip()
    if method_id and method_id not in analysis_refs and f"methods/{method_id}" not in analysis_refs:
        analysis_refs.append(f"methods/{method_id}")

    raw_viz = _str_list(item.get("viz_templates") or item.get("templates"))
    viz_refs: list[str] = []
    for ref in raw_viz:
        clean = ref.removesuffix(".md")
        if clean.startswith(("methods/", "recipes/")):
            if ref not in analysis_refs:
                analysis_refs.append(ref)
        elif clean.startswith("scenarios/"):
            continue
        else:
            viz_refs.append(ref)

    return {
        "direction": str(item.get("direction") or item.get("title") or "下一步方向"),
        "when": str(item.get("when") or item.get("condition") or ""),
        "analysis_templates": analysis_refs,
        "intermediate_interface": str(item.get("intermediate_interface") or item.get("interface") or ""),
        "viz_templates": viz_refs,
        "requires": _str_list(item.get("requires")),
        "subtree": str(item.get("subtree") or "").strip(),
    }


def _resolve_branch_targets(
    config: Config,
    analysis_refs: list[str],
    viz_refs: list[str],
    hidden: set[str],
    rel_compat_by_figure: dict[str, str],
) -> tuple[list[dict], list[dict], list[dict]]:
    from .aliases import resolve_page_ref
    from .method_hub import recipe_preview_url, template_preview_url
    from .method_taxonomy import domains_for

    root = config.wiki_root
    next_methods: list[dict] = []
    reference_recipes: list[dict] = []
    viz_templates: list[dict] = []
    seen_methods: set[str] = set()
    seen_recipes: set[str] = set()
    seen_viz: set[str] = set()

    for ref in analysis_refs:
        resolved = resolve_page_ref(root, ref, expected_types=("method", "recipe"))
        if resolved is None:
            clean = ref.removesuffix(".md")
            if clean.startswith("recipes/"):
                rid = clean.split("/", 1)[1]
                if rid not in seen_recipes:
                    seen_recipes.add(rid)
                    reference_recipes.append({
                        "id": rid,
                        "title": rid,
                        "path": f"recipes/{rid}.md",
                        "status": "missing",
                        "exists": False,
                    })
            else:
                mid = clean.split("/", 1)[-1]
                if mid not in seen_methods:
                    seen_methods.add(mid)
                    next_methods.append({
                        "id": mid,
                        "title": mid,
                        "path": f"methods/{mid}.md",
                        "status": "missing",
                        "exists": False,
                    })
            continue
        rel_path = resolved.relative_to(root).as_posix()
        if rel_path in hidden:
            continue
        try:
            rmeta, _ = read_page(resolved)
        except WikiError:
            continue
        if rmeta.get("status") == "archived":
            continue
        rtype = rmeta.get("type")
        if rtype == "method":
            if rmeta.get("method_kind") in ("technical", "workflow"):
                continue
            mid = str(rmeta.get("id") or resolved.stem)
            if mid in seen_methods:
                continue
            seen_methods.add(mid)
            next_methods.append({
                "id": mid,
                "title": str(rmeta.get("title") or mid),
                "path": rel_path,
                "status": str(rmeta.get("status") or "draft"),
                "method_kind": rmeta.get("method_kind"),
                "summary": str(rmeta.get("summary") or ""),
                "data_domains": domains_for(rmeta),
                "purposes": list(rmeta.get("purposes") or []),
                "exists": True,
            })
        elif rtype == "recipe":
            rid = str(rmeta.get("id") or resolved.stem)
            if rid in seen_recipes:
                continue
            seen_recipes.add(rid)
            reference_recipes.append({
                "id": rid,
                "title": str(rmeta.get("title") or rid),
                "path": rel_path,
                "status": str(rmeta.get("status") or "draft"),
                "language": str(rmeta.get("language") or ""),
                "chart_types": list(rmeta.get("chart_types") or []),
                "preview_url": recipe_preview_url(root, rid),
                "exists": True,
            })

    for ref in viz_refs:
        resolved = resolve_page_ref(root, ref, expected_type="template")
        if resolved is None:
            tid = ref.removesuffix(".md").split("/", 1)[-1]
            if tid and tid not in seen_viz:
                seen_viz.add(tid)
                viz_templates.append({
                    "id": tid,
                    "title": tid,
                    "path": f"templates/{tid}.md",
                    "status": "missing",
                    "compatibility": "unreviewed",
                    "preview_url": None,
                    "exists": False,
                })
            continue
        rel_path = resolved.relative_to(root).as_posix()
        if rel_path in hidden:
            continue
        try:
            tmeta, _ = read_page(resolved)
        except WikiError:
            continue
        if tmeta.get("status") == "archived":
            continue
        tid = str(tmeta.get("id") or resolved.stem)
        if tid in seen_viz:
            continue
        seen_viz.add(tid)
        viz_entry = {
            "id": tid,
            "title": str(tmeta.get("title") or tid),
            "path": rel_path,
            "status": str(tmeta.get("status") or "draft"),
            "language": str(tmeta.get("language") or ""),
            "chart_types": list(tmeta.get("chart_types") or []),
            "preview_url": template_preview_url(root, tmeta),
            "compatibility": rel_compat_by_figure.get(rel_path, "unreviewed"),
            "exists": True,
        }
        if tmeta.get("style_tier"):
            viz_entry["style_tier"] = str(tmeta["style_tier"])
        if tmeta.get("journal_style"):
            viz_entry["journal_style"] = str(tmeta["journal_style"])
        viz_templates.append(viz_entry)

    return next_methods, reference_recipes, viz_templates


def suggest_next_steps(config: Config, node_id: str, query: str = "") -> dict:
    """Return structured downstream bioinformatics directions and structural interface matches."""
    from .catalog import readable_pages
    from .facts import declarations, input_interfaces, table_interfaces
    from .method_hub import (
        _attached_visualizations,
        _hub_context,
        _normalize_render_bridges,
        _session_ctx,
        match_interfaces,
        spec_tables_list,
        template_preview_url,
    )
    from .method_taxonomy import domains_for

    with _session_ctx():
        root = config.wiki_root
        hidden = excluded_paths(config)
        path = _locate_node(config, node_id)
        meta, _ = read_page(path)
        kind = meta.get("type", "")
        canonical_id = str(meta.get("id") or meta.get("slug") or path.stem)
        page_rel = path.relative_to(root).as_posix()
        title = meta.get("title", canonical_id)

        raw_steps = meta.get("next_steps")
        branch_pairs: list[tuple[dict, dict]] = []
        if isinstance(raw_steps, list):
            for entry in raw_steps:
                if isinstance(entry, dict):
                    branch_pairs.append((entry, _normalize_next_step(entry)))
        elif kind == "scenario" and isinstance(meta.get("steps"), list):
            for entry in meta["steps"]:
                if isinstance(entry, dict):
                    branch_pairs.append((entry, _normalize_next_step(entry)))

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

        # Playbook scenario fallback when node has no explicit next_steps
        if not branch_pairs:
            for _, smeta in readable_pages(root):
                if smeta.get("type") != "scenario" or not isinstance(smeta.get("steps"), list):
                    continue
                steps = smeta["steps"]
                for idx, st in enumerate(steps):
                    if not isinstance(st, dict):
                        continue
                    if st.get("id") in (canonical_id, node_id) or st.get("method_id") in (canonical_id, node_id):
                        for nxt in steps[idx + 1:]:
                            if isinstance(nxt, dict) and (nxt.get("parent") == st.get("id") or idx + 1 == steps.index(nxt)):
                                branch_pairs.append((nxt, _normalize_next_step(nxt)))
                        break

        hub_ctx = _hub_context(config, include_recipes=True)
        relations = hub_ctx["relations"]
        rel_compat_by_figure = {
            rel["figure"]: rel["compatibility"]
            for rel in relations
            if rel["method"] == page_rel
        }

        if kind == "method" and meta.get("status") != "archived" and meta.get("method_kind") == "analysis":
            attached_visualizations = _attached_visualizations(
                canonical_id,
                page_rel,
                outputs,
                _normalize_render_bridges(meta.get("render_bridges")),
                hub_ctx["templates"],
                relations,
                method_recipes=hub_ctx["recipes_by_method"].get(canonical_id, []),
                extra_template_ids=hub_ctx.get("extra_templates_by_method", {}).get(canonical_id),
            )
        else:
            attached_visualizations = {
                "curated": [],
                "object_compatible": [],
                "render_bridged": [],
                "all_previews": [],
            }

        data_contract_out = ""
        if isinstance(meta.get("data_contract"), dict):
            data_contract_out = str(meta["data_contract"].get("output") or "").strip()
        default_required_obj = data_contract_out or (", ".join(sorted(outputs)) if outputs else "")

        curated_branches: list[dict] = []
        compat_rank = {"direct": 0, "adaptable": 1}
        for idx, (raw_entry, norm_step) in enumerate(branch_pairs, 1):
            next_methods, reference_recipes, _ = _resolve_branch_targets(
                config,
                norm_step["analysis_templates"],
                [],
                hidden,
                rel_compat_by_figure,
            )
            branch_compat = dict(rel_compat_by_figure)
            branch_method_paths = {m["path"] for m in next_methods if m.get("exists") and m.get("path")}
            for rel in relations:
                if rel["method"] in branch_method_paths:
                    fig = rel["figure"]
                    new_c = rel["compatibility"]
                    cur_c = branch_compat.get(fig)
                    if cur_c is None or compat_rank.get(new_c, 9) < compat_rank.get(cur_c, 9):
                        branch_compat[fig] = new_c
            _, _, viz_templates = _resolve_branch_targets(
                config,
                [],
                norm_step["viz_templates"],
                hidden,
                branch_compat,
            )
            hypothesis = str(raw_entry.get("hypothesis") or "").strip() or norm_step["when"] or norm_step["direction"]
            required_obj = str(raw_entry.get("required_object") or "").strip() or default_required_obj
            curated_branches.append({
                "branch_id": str(raw_entry.get("branch_id") or raw_entry.get("id") or f"branch-{idx}"),
                "direction": norm_step["direction"],
                "when": norm_step["when"],
                "hypothesis": hypothesis,
                "required_object": required_obj,
                "produced_interface": norm_step["intermediate_interface"],
                "requires": norm_step["requires"],
                "subtree": norm_step["subtree"],
                "next_methods": next_methods,
                "reference_recipes": reference_recipes,
                "viz_templates": viz_templates,
            })

        structural_matches: list[dict] = []
        object_compatible_candidates: list[dict] = []
        if outputs:
            tpl_decls = declarations(root, "templates")
            method_decls = declarations(root, "methods")

            for tid, (tm, spec) in tpl_decls.items():
                tpath = f"templates/{tid}.md"
                if tm.get("status") == "archived" or tpath in hidden:
                    continue
                req = table_interfaces(spec)
                if req and req & outputs:
                    preview_url = template_preview_url(root, tm)
                    structural_matches.append({
                        "id": tid,
                        "kind": "template",
                        "type": "template",
                        "title": tm.get("title", tid),
                        "status": tm.get("status"),
                        "interfaces": sorted(req),
                        "inputs": sorted(req),
                        "path": tpath,
                        "page": tpath,
                        "preview": preview_url,
                    })
                    tables = spec_tables_list(spec)
                    match_type, matched, missing = match_interfaces(tables, outputs)
                    if match_type is not None:
                        object_compatible_candidates.append({
                            "id": tid,
                            "kind": "template",
                            "title": tm.get("title", tid),
                            "path": tpath,
                            "status": tm.get("status"),
                            "source": "object_inferred",
                            "match_type": match_type,
                            "shared_interfaces": matched,
                            "missing_required_interfaces": missing,
                            "language": tm.get("language", ""),
                            "chart_types": list(tm.get("chart_types") or []),
                            "preview_url": preview_url,
                            "downstream_viz": [],
                        })

            for mid, (mm, method_meta) in method_decls.items():
                mpath = f"methods/{mid}.md"
                if mm.get("status") == "archived" or mid == canonical_id or mpath in hidden:
                    continue
                if mm.get("method_kind") in ("technical", "workflow"):
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
                        "path": mpath,
                        "page": mpath,
                    })
                    if mm.get("method_kind") == "analysis":
                        req_ins = {s for s in ins if isinstance(s, str) and s.strip()}
                        match_type = "full" if req_ins <= outputs else "partial"
                        shared = sorted(req_ins & outputs)
                        missing = sorted(req_ins - outputs)
                        m_outputs = {
                            str(s) for s in (mm.get("outputs") or []) if isinstance(s, str) and s.strip()
                        }
                        m_viz = _attached_visualizations(
                            mid,
                            mpath,
                            m_outputs,
                            _normalize_render_bridges(mm.get("render_bridges")),
                            hub_ctx["templates"],
                            relations,
                        )
                        object_compatible_candidates.append({
                            "id": mid,
                            "kind": "method",
                            "title": mm.get("title", mid),
                            "path": mpath,
                            "status": mm.get("status"),
                            "source": "object_inferred",
                            "match_type": match_type,
                            "shared_interfaces": shared,
                            "missing_required_interfaces": missing,
                            "data_domains": domains_for(mm),
                            "purposes": list(mm.get("purposes") or []),
                            "downstream_viz": m_viz["all_previews"],
                        })

        object_compatible_candidates.sort(key=lambda item: (
            0 if item["match_type"] == "full" else 1,
            0 if item["kind"] == "method" else 1,
            -len(item["shared_interfaces"]),
            item["id"],
        ))

        next_steps = [norm for _, norm in branch_pairs]
        words = [w for w in dict.fromkeys(query.casefold().split()) if w]
        if words:
            def _matches(text: str) -> bool:
                low = text.casefold()
                return any(w in low for w in words)

            filtered_pairs = [
                (idx, norm, branch)
                for idx, (norm, branch) in enumerate(zip(next_steps, curated_branches))
                if _matches(" ".join([
                    norm["direction"], norm["when"], norm["intermediate_interface"],
                    branch["hypothesis"], *norm["analysis_templates"], *norm["viz_templates"],
                ]))
            ]
            if filtered_pairs:
                next_steps = [norm for _, norm, _ in filtered_pairs]
                curated_branches = [branch for _, _, branch in filtered_pairs]
            filtered_matches = [
                m for m in structural_matches
                if _matches(" ".join([m["id"], m["title"], *m.get("interfaces", [])]))
            ]
            if filtered_matches:
                structural_matches = filtered_matches
            filtered_candidates = [
                c for c in object_compatible_candidates
                if _matches(" ".join([
                    c["id"], c["title"], c["match_type"],
                    *c.get("shared_interfaces", []), *c.get("missing_required_interfaces", []),
                ]))
            ]
            if filtered_candidates:
                object_compatible_candidates = filtered_candidates

        current_node = {
            "id": canonical_id,
            "requested_id": node_id,
            "kind": kind,
            "title": title,
            "path": page_rel,
            "status": meta.get("status"),
            "data_domains": domains_for(meta),
            "purposes": list(meta.get("purposes") or []) if kind == "method" else [],
            "inputs": list(meta.get("inputs") or []) if kind == "method" else [],
            "outputs": sorted(outputs),
        }

        agent_guidance = (
            "下游分支均为可选科研决策，无固定线性顺序；"
            "请结合课题假设选择 curated_branches，或对照 object_compatible_candidates 的 full/partial 接口匹配，"
            "并在调用模板前核对方法前提与 figure_relations 适配说明。"
        )

        return {
            "schema_version": 2,
            "node_id": canonical_id,
            "requested_id": node_id,
            "kind": kind,
            "title": title,
            "page": page_rel,
            "outputs": sorted(outputs),
            "current_node": current_node,
            "decision_mode": "multi_branch_optional",
            "agent_guidance": agent_guidance,
            "curated_branches": curated_branches,
            "object_compatible_candidates": object_compatible_candidates,
            "attached_visualizations": attached_visualizations,
            "next_steps": next_steps,
            "structural_matches": structural_matches,
        }


def format_next_steps(payload: dict) -> str:
    lines = [f"{payload['node_id']}  {payload['title']}  [{payload['kind']}]"]
    if payload.get("outputs"):
        lines.append("输出中间表：" + "、".join(payload["outputs"]))
    if payload.get("agent_guidance"):
        lines.append(f"分支决策提示（{payload.get('decision_mode', 'multi_branch_optional')}）：{payload['agent_guidance']}")

    branches = payload.get("curated_branches")
    steps = payload.get("next_steps") or []
    if branches:
        lines.append("下一步分析方向（可选分支）：")
        for idx, branch in enumerate(branches, 1):
            lines.append(f"  {idx}. {branch['direction']}")
            if branch.get("when"):
                lines.append(f"     触发条件：{branch['when']}")
            if branch.get("hypothesis") and branch["hypothesis"] != branch.get("when"):
                lines.append(f"     分析假设：{branch['hypothesis']}")
            if branch.get("requires"):
                lines.append("     多上游汇合前提：" + " + ".join(branch["requires"]))
            if branch.get("subtree"):
                lines.append(f"     专题子分支树：{branch['subtree']}")
            if branch.get("produced_interface"):
                lines.append(f"     标准中间表：{branch['produced_interface']}")
            if branch.get("next_methods"):
                lines.append("     推荐分析模版：" + ", ".join(m["id"] for m in branch["next_methods"]))
            if branch.get("reference_recipes"):
                lines.append("     参考源码配方：" + ", ".join(r["id"] for r in branch["reference_recipes"]))
            if branch.get("viz_templates"):
                def _fmt_viz(v: dict) -> str:
                    parts = []
                    if v.get("style_tier"):
                        parts.append(v["style_tier"])
                    parts.append(v.get("compatibility", "unreviewed"))
                    return f"{v['id']}({', '.join(parts)})"
                lines.append("     配套可视化模版：" + ", ".join(_fmt_viz(v) for v in branch["viz_templates"]))
    elif steps:
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

    candidates = payload.get("object_compatible_candidates")
    matches = payload.get("structural_matches") or []
    if candidates:
        lines.append("接口结构匹配下游候选（仅接口推断，不代表语义已审查）：")
        for c in candidates:
            shared = ", ".join(c.get("shared_interfaces", []))
            missing = c.get("missing_required_interfaces") or []
            miss_note = f"；缺必需接口: {', '.join(missing)}" if missing else ""
            lines.append(f"  - [{c['kind']}] {c['id']}  {c['title']} [{c['match_type']}] ({shared}){miss_note}")
    elif matches:
        lines.append("接口结构匹配下游条目：")
        for m in matches:
            lines.append(f"  - [{m['kind']}] {m['id']}  {m['title']} ({', '.join(m.get('interfaces', []))})")
    return "\n".join(lines)

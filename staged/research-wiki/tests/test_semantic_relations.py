"""Software fixtures establish relationship behavior, not scientific validity."""

import copy
import hashlib
import json
import sys

import pytest

from conftest import run_cli, complete_sections, record_ready_receipt, seal_replay
from rwiki.config import load_config
from rwiki.deletion import delete_archived, prepare
from rwiki.facts import page_facts, refresh_facts
from rwiki.lint import lint
from rwiki.pages import get_block, read_page, write_page
from rwiki.relations import all_relations, relation_errors, relations_for
from rwiki.spec import check_data, load_spec
from rwiki.errors import WikiError


def body(title):
    return (f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
            "## 用途\n\n检验夹具。\n\n## 适用\n\n合成软件测试。\n\n"
            "## 不适用\n\n不能据此断言临床有效。\n\n## 输入\n\n模型与逐条结果。\n\n"
            "## 怎么做\n\n## 代码\n\n## 输出\n\n## 使用记录\n\n"
            "<!-- user:start -->\n作者原始备注 <literal>\n<!-- user:end -->\n")


def relation(figure, compatibility="direct", **changes):
    record = {"figure": figure, "compatibility": compatibility,
              "reason": "逐条结果与图样编码相符；这是人工审查的测试声明。",
              "prerequisites": ["每行代表同一种验证单位"],
              "adaptation": "明确列映射和长宽表整理" if compatibility == "adaptable" else "",
              "evidence": ["methods/m-a#输出", f"{figure}#数据要求"],
              "verification": {"state": "not_run", "scope": "仅审查语义，尚未调用", "evidence": []}}
    record.update(changes)
    return record


def update(config, page, **changes):
    path = config.wiki_root / page
    meta, text = read_page(path)
    meta.update(changes)
    write_page(path, meta, text)


@pytest.fixture
def semantic_wiki(tmp_path):
    root = tmp_path / "wiki"
    root.mkdir()
    for directory in ("methods", "templates", "layouts", "interfaces", "projects", "chart-types"):
        (root / directory).mkdir()
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text('{"scenarios": {}}', encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"wiki_root": str(root), "gallery_root": str(tmp_path / "gallery"),
                                      "taxonomy": str(taxonomy), "python_exe": sys.executable,
                                      "rscript_exe": "unused", "port": 8765, "single_panel_only": True}),
                           encoding="utf-8")
    config = load_config(config_path)
    for slug, column in (("source-values", "source_metric"), ("plot-values", "plot_metric")):
        write_page(root / f"interfaces/{slug}.md", {"type": "interface", "slug": slug,
                   "title": slug, "columns": {column: {"type": "float", "description": "明确的逐条量"}}}, body(slug))
    for fid, interface in (("f-a", "source-values"), ("f-b", "plot-values")):
        assets = root / "templates" / fid
        (assets / "code").mkdir(parents=True)
        for filename in ("render.py", "panel.py", "__init__.py"):
            (assets / "code" / filename).write_text("# fixture only; never executed\n", encoding="utf-8")
        (assets / "preview.png").write_bytes(b"fixture")
        (assets / "spec.json").write_text(json.dumps({"entry": "code/render.py", "panel": "code/panel.py",
            "language": "python", "tables": {"results": {"interface": interface, "description": "逐条量"}},
            "style": {}}), encoding="utf-8")
        write_page(root / f"templates/{fid}.md", {"type": "template", "id": fid, "title": fid,
            "status": "ready", "language": "python", "layouts": [f"src-{fid}"], "panels": ["A"],
            "chart_types": ["value"], "tags": ["same-label"], "favorite": False}, body(fid))
        complete_sections(root / f'templates/{fid}.md')
        seal_replay(assets)
    # Each callable template has its own replicated, signed single-panel source (D044).
    for name, title, templates in (("ref", "另一来源", []), ("src-f-a", "f-a 来源", ["f-a"]),
                                   ("src-f-b", "f-b 来源", ["f-b"])):
        gallery = config.gallery_root / f"{name}-post/figures/{name}"
        gallery.mkdir(parents=True)
        (gallery / "meta.json").write_text(json.dumps({"status": "approved", "version": 1,
            "post": {"title": title, "account": None, "publish_date": None, "url": None},
            "data_provenance": "synthetic fixture", "code_provenance": "fixture"}), encoding="utf-8")
        if name == "ref":
            continue
        write_page(root / f"layouts/{name}.md", {"type": "layout", "id": name, "title": title,
            "status": "pending_template", "gallery_entry": f"{name}-post/figures/{name}", "gallery_version": 1,
            "language": "python", "panels": {"A": "value"}, "templates": templates,
            "template_panels": {templates[0]: ["A"]}, "chart_types": ["value"], "tags": [],
            "favorite": False}, body(title))
        complete_sections(root / f"layouts/{name}.md")
    write_page(root / "layouts/ref.md", {"type": "layout", "id": "ref", "title": "来源参考",
        "status": "pending_template", "gallery_entry": "ref-post/figures/ref", "gallery_version": 1,
        "language": "python", "panels": {"A": "dot"}, "templates": [], "template_panels": {},
        "chart_types": [], "tags": ["same-label"], "favorite": False}, body("来源参考"))
    for mid, outputs in (("m-a", ["source-values"]), ("m-b", ["plot-values"]),
                         ("m-c", ["source-values"]), ("no-figure", [])):
        write_page(root / f"methods/{mid}.md", {"type": "method", "id": mid, "title": mid,
            "status": "ready", "inputs": ["source-values"], "outputs": outputs,
            "tags": ["same-label"], "source": {"kind": "project", "path": f"independent-source/{mid}"},
            "license": "none", "cite": [], "favorite": False}, body(mid))
    update(config, "methods/m-a.md", figure_relations=[relation("templates/f-a"),
        relation("templates/f-b", "adaptable"), relation("layouts/ref", "candidate")])
    update(config, "methods/m-b.md", figure_relations=[relation("templates/f-b")])
    for page in (root / 'methods').glob('*.md'):
        complete_sections(page)
    for page in (*(root / 'methods').glob('*.md'), *(root / 'templates').glob('*.md')):
        record_ready_receipt(config, page)
    return config, config_path


def test_method_relation_to_layout_with_ready_template_is_rejected(semantic_wiki):
    config, _ = semantic_wiki
    update(config, 'layouts/ref.md', templates=['f-a'],
           template_panels={'f-a': ['A']}, panels={'A': 'value'})
    update(config, 'templates/f-a.md', layouts=['ref'], chart_types=['value'])
    method_meta, _ = read_page(config.wiki_root / 'methods/m-a.md')
    errors = relation_errors(config, method_meta)
    assert any('layout' in error and '模板' in error for error in errors), errors
    assert all(record['target_kind'] != 'layout'
               for record in all_relations(config)
               if record['method'] == 'methods/m-a.md')


def test_adaptable_relation_requires_read_interfaces_in_body(semantic_wiki):
    config, _ = semantic_wiki
    assert any(line.startswith("WARN methods/m-a.md:") and "plot-values" in line
               for line in lint(config))
    page = config.wiki_root / "methods/m-a.md"
    meta, body = read_page(page)
    write_page(page, meta, body + "\n模板读取接口：plot-values\n")
    remaining = [line for line in lint(config)
                 if line.startswith("WARN methods/m-a.md:") and "plot-values" in line]
    assert not remaining, remaining


def test_many_to_many_and_cross_source_resolve_identically(semantic_wiki):
    config, _ = semantic_wiki
    records = all_relations(config)
    assert len(records) == 4
    assert {r["figure"] for r in relations_for(config, "methods/m-a.md")} == {
        "templates/f-a.md", "templates/f-b.md", "layouts/ref.md"}
    reverse = relations_for(config, "templates/f-b")
    assert {r["method"] for r in reverse} == {"methods/m-a.md", "methods/m-b.md"}
    assert all(r in records for r in reverse)
    expected = {"method", "figure", "method_title", "figure_title", "method_status", "figure_status",
                "compatibility", "reason", "prerequisites", "adaptation", "evidence", "verification",
                "target_kind", "active"}
    assert all(set(r) == expected for r in records)
    assert records[0]["verification"]["state"] == "not_run"
    assert relations_for(config, "methods/m-c.md") == []  # equal output interface/labels cannot infer semantics
    assert relations_for(config, "../outside") == []


def test_page_facts_include_both_states_both_directions_and_layout_notice(semantic_wiki):
    config, _ = semantic_wiki
    before = {p: get_block(read_page(p)[1], "user") for p in config.wiki_root.rglob("*.md")}
    refresh_facts(config)
    for page in ("methods/m-a.md", "templates/f-b.md"):
        facts = get_block(read_page(config.wiki_root / page)[1], "facts")
        assert "需要适配（adaptable）" in facts
        assert "调用验证：not_run" in facts and "仅审查语义，尚未调用" in facts
        assert "每行代表同一种验证单位" in facts
    facts = page_facts(config, read_page(config.wiki_root / "methods/m-c.md")[0])
    assert "接口结构匹配的图（仅结构候选，未核实语义）" in facts
    assert "[[templates/f-a|" in facts and "direct" not in facts
    ref = page_facts(config, read_page(config.wiki_root / "layouts/ref.md")[0])
    assert "来源图样参考，执行时另查关联模板" in ref and "candidate" in ref
    assert all(get_block(read_page(p)[1], "user") == note for p, note in before.items())


@pytest.mark.parametrize("changes, needle", [
    ({"figure": "methods/m-b"}, "figure"), ({"figure": "templates/../escape"}, "figure"),
    ({"figure": "templates/f-a.md.md"}, "figure"), ({"figure": ["templates/f-a"]}, "figure"),
    ({"figure": "templates/missing"}, "页面不存在"), ({"figure": "layouts/ref"}, "direct"),
    ({"compatibility": "ready"}, "compatibility"), ({"compatibility": []}, "compatibility"),
    ({"reason": " "}, "reason"), ({"reason": {}}, "reason"),
    ({"prerequisites": "model"}, "prerequisites"), ({"prerequisites": [{}]}, "prerequisites"),
    ({"adaptation": None}, "adaptation"), ({"compatibility": "adaptable", "adaptation": ""}, "adaptation"),
    ({"evidence": []}, "evidence"), ({"evidence": [""]}, "evidence"),
    ({"verification": None}, "verification"),
    ({"verification": {"state": [], "scope": "test", "evidence": []}}, "verification.state"),
    ({"verification": {"state": "not_run", "scope": "", "evidence": []}}, "verification.scope"),
    ({"verification": {"state": "project", "scope": "test", "evidence": []}}, "verification.evidence"),
    ({"verification": {"state": "example", "scope": "test", "evidence": "log"}}, "verification.evidence"),
])
def test_lint_relationship_malformed_values_do_not_abort(semantic_wiki, changes, needle):
    config, _ = semantic_wiki
    record = relation("templates/f-a")
    record.update(changes)
    update(config, "methods/m-a.md", figure_relations=[record])
    diagnostics = lint(config)
    assert any(line.startswith("ERROR methods/m-a.md:") and needle in line for line in diagnostics)
    assert not any(r["method"] == "methods/m-a.md" for r in all_relations(config))


@pytest.mark.parametrize("records, needle", [(None, "必须为列表"), ({}, "必须为列表"),
                                             ([None, [], 1], "必须为对象")])
def test_lint_top_level_malformed_relations(semantic_wiki, records, needle):
    config, _ = semantic_wiki
    update(config, "methods/m-a.md", figure_relations=records)
    assert any(needle in line for line in lint(config))


def test_duplicates_and_missing_callable_assets_are_not_promised_direct(semantic_wiki):
    config, _ = semantic_wiki
    record = relation("templates/f-a")
    alternate_spelling = copy.deepcopy(record)
    alternate_spelling["figure"] += ".md"
    update(config, "methods/m-a.md", figure_relations=[record, alternate_spelling])
    assert any("重复" in error for error in relation_errors(config, read_page(config.wiki_root / "methods/m-a.md")[0]))
    assert relations_for(config, "methods/m-a") == []
    update(config, "methods/m-a.md", figure_relations=[record])
    (config.wiki_root / "templates/f-a/code/render.py").unlink()
    assert relations_for(config, "templates/f-a") == []
    assert any("spec.entry" in line for line in lint(config))


def test_optional_md_input_resolves_to_single_canonical_page_suffix(semantic_wiki):
    config, _ = semantic_wiki
    update(config, "methods/m-a.md", figure_relations=[relation("templates/f-a.md")])
    records = relations_for(config, "methods/m-a.md")
    assert len(records) == 1 and records[0]["figure"] == "templates/f-a.md"
    assert not relation_errors(config, read_page(config.wiki_root / "methods/m-a.md")[0])


def test_archived_endpoint_is_retained_as_history_excluded_from_discovery(semantic_wiki):
    from rwiki.suggest import suggest, suggest_methods, suggest_pipeline

    config, _ = semantic_wiki
    update(config, "templates/f-b.md", status="archived", archived_from="ready")
    assert len(all_relations(config)) == 4 and len(all_relations(config, include_archived=False)) == 2
    assert all(not r["active"] for r in relations_for(config, "templates/f-b"))
    assert all(r["figure"] != "templates/f-b.md" for item in suggest_methods(config, limit=10) for r in item["relations"])
    assert "f-b" not in {item["id"] for item in suggest(config, [], None, "", 10)}
    assert "f-b" not in {item["id"] for item in suggest_pipeline(config)}
    update(config, "methods/m-a.md", status="archived", archived_from="ready")
    assert all_relations(config, include_archived=False) == []
    assert "m-a" not in {item["id"] for item in suggest_methods(config, limit=10)}


def test_discovery_keeps_methods_without_figures_or_matching_column_names(semantic_wiki):
    from rwiki.suggest import suggest_methods, suggest_pipeline

    config, config_path = semantic_wiki
    methods = suggest_methods(config, columns="entirely_different_name", limit=10)
    assert {item["id"] for item in methods} == {"m-a", "m-b", "m-c", "no-figure"}
    isolated = next(item for item in methods if item["id"] == "no-figure")
    assert isolated["relations"] == [] and isolated["code_files"] == []
    assert not isolated["code_status"]["available"]
    method = next(item for item in methods if item["id"] == "m-a")
    assert method["prerequisites"] == ["每行代表同一种验证单位"]
    assert method["input_requirements"]["source-values"]["columns"]
    assert method["project_readiness"] == "requires_project_review"
    assert method["score"] == 0 and "缺少 source_metric" in method["reasons"][0]
    group = suggest_pipeline(config, "f-b")[0]
    candidates = {item["id"]: item for item in group["methods"]}
    assert set(candidates) == {"m-a", "m-b"}
    assert candidates["m-a"]["compatibility"] == "adaptable" and not candidates["m-a"]["structural_match"]
    assert candidates["m-b"]["compatibility"] == "direct"
    structural = {item["id"]: item for item in suggest_pipeline(config, "f-a")[0]["methods"]}["m-c"]
    assert structural["match_basis"] == "interface_structure" and structural["compatibility"] is None
    assert structural["verification"] is None
    run = run_cli(config_path, "suggest-methods", "--columns", "different", "--limit", "10")
    assert run.returncode == 0, run.stderr
    assert {item["id"] for item in json.loads(run.stdout)} == {item["id"] for item in methods}
    assert run_cli(config_path, "suggest-methods", "--limit", "-1").returncode == 1


def test_same_columns_do_not_replace_strict_execution_input_checks(semantic_wiki, tmp_path):
    config, _ = semantic_wiki
    data = tmp_path / "project-copy"
    data.mkdir()
    (data / "source-values.csv").write_text("different_column\n1\n", encoding="utf-8")
    with pytest.raises(WikiError, match="缺列.*source_metric"):
        check_data(load_spec(config.wiki_root / "templates/f-a"), data)


def test_deletion_removes_relation_metadata_and_audits_counts_without_touching_author(semantic_wiki, monkeypatch):
    config, _ = semantic_wiki
    update(config, "methods/m-b.md", figure_relations=[relation("templates/f-b.md")])
    update(config, "templates/f-b.md", status="archived", archived_from="ready")
    refresh_facts(config)
    root = config.wiki_root
    before = {page: get_block(read_page(page)[1], "user") for page in root.rglob("*.md")}
    gallery_before = {page: hashlib.sha256(page.read_bytes()).hexdigest()
                      for page in config.gallery_root.rglob("*") if page.is_file()}
    plan = prepare(config, root / "templates/f-b.md")[0]
    assert plan["figure_relations_removed"] == 2
    assert {page["path"]: page["figure_relations_removed"] for page in plan["affected"]
            if page["figure_relations_removed"]} == {
        "methods/m-a.md": 1, "methods/m-b.md": 1}
    monkeypatch.setattr("rwiki.deletion.save", lambda *_: None)
    result = delete_archived(config, root / "templates/f-b.md", plan["revision"])
    assert result["deleted"] and result["figure_relations_removed"] == 2
    audit = json.loads((root / result["audit"]).read_text(encoding="utf-8"))
    assert audit["figure_relations_removed"] == 2
    assert {"methods/m-a.md", "methods/m-b.md"} <= {item["path"] for item in audit["changed_pages"]}
    assert all(r["figure"] != "templates/f-b.md" for r in all_relations(config))
    assert read_page(root / "methods/m-b.md")[0]["figure_relations"] == []
    assert all(get_block(read_page(p)[1], "user") == note for p, note in before.items() if p.exists())
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in gallery_before.items())


def test_verification_evidence_is_not_page_status_or_code_existence(semantic_wiki):
    config, _ = semantic_wiki
    verification = {"state": "example", "scope": "只回放了隔离合成示例", "evidence": ["fixture/run.log"]}
    update(config, "methods/m-a.md", figure_relations=[relation("templates/f-a", verification=verification)])
    update(config, "methods/m-a.md", status="draft")
    resolved = relations_for(config, "methods/m-a")[0]
    assert resolved["method_status"] == "draft" and resolved["compatibility"] == "direct"
    assert resolved["verification"] == verification and resolved["active"]


def test_code_inventory_is_actual_and_legacy_code_list_excludes_cache(semantic_wiki):
    from rwiki.suggest import suggest_methods

    config, _ = semantic_wiki
    assets = config.wiki_root / "methods/no-figure"
    (assets / "source").mkdir(parents=True)
    (assets / "source/original.r").write_bytes(b"# native snippet\n")
    (assets / "code/__pycache__").mkdir(parents=True)
    (assets / "code/run.py").write_text("# reusable fixture; no execution evidence\n", encoding="utf-8")
    (assets / "code/__pycache__/run.pyc").write_bytes(b"cache")
    record_ready_receipt(config, assets.with_suffix(".md"))  # new code assets are re-checked before recommending
    candidate = next(item for item in suggest_methods(config, limit=10) if item["id"] == "no-figure")
    assert candidate["code_files"] == ["methods/no-figure/code/run.py"]
    assert candidate["code_status"]["has_original"] and candidate["code_status"]["has_reusable"]
    assert len(candidate["code_status"]["files"]) == 2
    assert all(item["verification"]["state"] == "unknown" for item in candidate["code_status"]["files"])
    facts = page_facts(config, read_page(assets.with_suffix(".md"))[0])
    assert "__pycache__" not in facts and "run.pyc" not in facts and "code/run.py" in facts

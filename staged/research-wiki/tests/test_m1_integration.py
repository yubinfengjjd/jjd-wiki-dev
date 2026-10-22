"""Cross-module contracts for frontmatter methods, tags and derived relationships."""

import json
import re
import sys

import pytest

from conftest import run_cli, complete_sections, record_ready_receipt, seal_replay
from rwiki.config import load_config
from rwiki.pages import get_block, read_page, set_block, write_page
from rwiki.store import init, save


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def page_body(title, applicable="", unsuitable="", note="author note"):
    return (f"# {title}\n\n<!-- facts:start -->\nBROKEN FACTS\n<!-- facts:end -->\n\n"
            f"## 用途\n\n{title}\n\n## 适用\n\n{applicable}\n\n"
            f"## 不适用\n\n{unsuitable}\n\n## 输入\n\n## 怎么做\n\n## 代码\n\n"
            f"## 输出\n\n## 使用记录\n\n<!-- user:start -->\n{note}\n<!-- user:end -->\n")


@pytest.fixture
def tiny_wiki(tmp_path):
    config_path = tmp_path / "config.json"
    taxonomy = tmp_path / "taxonomy.json"
    write_json(taxonomy, {"scenarios": {}})
    write_json(config_path, {
        "wiki_root": str(tmp_path / "wiki"), "gallery_root": str(tmp_path / "gallery"),
        "taxonomy": str(taxonomy), "python_exe": sys.executable,
        "rscript_exe": "unused-rscript", "port": 8765,
    })
    config = load_config(config_path)
    config.gallery_root.mkdir()
    init(config)
    root = config.wiki_root
    for slug, columns in {
        "feature-importance": {"feature": {"type": "str", "description": "特征"},
                               "importance": {"type": "float", "description": "重要性"}},
        "sample-scores": {"sample": {"type": "str", "description": "样本"},
                          "score": {"type": "float", "description": "评分"}},
    }.items():
        write_page(root / f"interfaces/{slug}.md", {
            "type": "interface", "slug": slug, "title": slug, "columns": columns,
        }, page_body(slug))
    for method_id, inputs, output, applicable in (
        ("rank-a", [], "feature-importance", "marker ranking"),
        ("rank-b", [], "feature-importance", "stable ranking"),
        ("score-c", ["feature-importance"], "sample-scores", "sample scoring"),
    ):
        directory = root / "methods" / method_id
        (directory / "code").mkdir(parents=True)
        (directory / "code/run.py").write_text("# optional template\n", encoding="utf-8")
        write_page(root / f"methods/{method_id}.md", {
            "type": "method", "id": method_id, "title": method_id, "status": "ready",
            "tags": ["单细胞"] if method_id == "rank-a" else ["组织"],
            "inputs": inputs, "outputs": [output],
            "source": {"kind": "project", "path": "source"}, "license": "MIT",
            "cite": [], "favorite": False,
        }, page_body(method_id, applicable, f"avoid {method_id}"))
    directory = root / "templates/rank-plot"
    (directory / "code").mkdir(parents=True)
    for filename in ("__init__.py", "render.py", "panel.py"):
        (directory / "code" / filename).write_text("# minimal template\n", encoding="utf-8")
    (directory / "preview.png").write_bytes(b"minimal preview placeholder")
    write_json(directory / "spec.json", {
        "entry": "code/render.py", "panel": "code/panel.py", "language": "python",
        "tables": {"values": {"interface": "feature-importance",
                               "description": "feature ranks"}}, "style": {},
    })
    write_page(root / "templates/rank-plot.md", {
        "type": "template", "id": "rank-plot", "title": "rank plot", "status": "ready",
        "language": "python", "layouts": ["src__rank"], "panels": ["A"], "chart_types": ["rank"],
        "tags": ["单细胞"], "favorite": False,
    }, page_body("rank plot", "rank visualization"))
    # Templates only come from a replicated, signed source (D044).
    write_json(config.gallery_root / "src/figures/rank/meta.json", {
        "id": "src__rank", "version": 1, "status": "approved", "approved_version": 1,
        "language": "python", "data_provenance": "synthetic", "code_provenance": "synthetic",
        "post": {"title": None, "account": None, "publish_date": None, "url": None}})
    write_page(root / "chart-types/rank.md", {"type": "chart-type", "slug": "rank", "title": "rank"}, "# rank\n")
    write_page(root / "layouts/src__rank.md", {
        "type": "layout", "id": "src__rank", "title": "rank source", "status": "pending_template",
        "gallery_entry": "src/figures/rank", "gallery_version": 1, "signedoff_version": 1,
        "language": "python", "tags": [], "chart_types": ["rank"], "favorite": False,
        "panels": {"A": "rank"}, "templates": ["rank-plot"], "template_panels": {"rank-plot": ["A"]},
    }, "# rank source\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n\n## 不适用\n\n"
       "## 知识关联检查\n\n## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n")
    for page in (*(root / 'methods').glob('*.md'), root / 'templates/rank-plot.md', root / 'layouts/src__rank.md'):
        complete_sections(page)
    seal_replay(directory)
    for page in (*(root / 'methods').glob('*.md'), root / 'templates/rank-plot.md'):
        record_ready_receipt(config, page)
    return config, config_path


def update_meta(root, relative, **changes):
    path = root / relative
    meta, body = read_page(path)
    meta.update(changes)
    write_page(path, meta, body)


def test_save_rebuilds_template_facts_with_both_compatible_methods(tiny_wiki):
    config, _ = tiny_wiki
    save(config, "rebuild relationships")
    facts = get_block(read_page(config.wiki_root / "templates/rank-plot.md")[1], "facts")
    assert "[[interfaces/feature-importance|" in facts
    assert "[[methods/rank-a|rank-a]]（ready）" in facts
    assert "[[methods/rank-b|rank-b]]（ready）" in facts
    assert "BROKEN FACTS" not in facts


def test_facts_connect_interfaces_and_next_method_and_exclude_archived(tiny_wiki):
    config, _ = tiny_wiki
    root = config.wiki_root
    save(config, "derive relationships")
    facts = get_block(read_page(root / "methods/rank-a.md")[1], "facts")
    assert "[[methods/score-c|" in facts
    assert "[[templates/rank-plot|rank plot]]（ready）" in facts
    interface_facts = get_block(read_page(root / "interfaces/feature-importance.md")[1], "facts")
    for target in ("methods/rank-a", "methods/rank-b", "methods/score-c", "templates/rank-plot"):
        assert f"[[{target}|" in interface_facts
    update_meta(root, "methods/rank-b.md", status="archived", archived_from="ready")
    update_meta(root, "methods/score-c.md", status="archived", archived_from="ready")
    save(config, "archive methods")
    assert "[[methods/rank-b|" not in get_block(read_page(root / "templates/rank-plot.md")[1], "facts")
    assert "[[methods/score-c|" not in get_block(read_page(root / "methods/rank-a.md")[1], "facts")
    index = (root / "index.md").read_text(encoding="utf-8")
    assert "[[methods/rank-a|" in index and "[[interfaces/feature-importance|" in index


def test_relationships_require_all_interfaces(tiny_wiki):
    config, _ = tiny_wiki
    root = config.wiki_root
    spec_path = root / "templates/rank-plot/spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["tables"]["scores"] = {"interface": "sample-scores", "description": "scores"}
    write_json(spec_path, spec)
    update_meta(root, "methods/score-c.md", inputs=["feature-importance", "sample-scores"])
    save(config, "require complete inputs")
    facts = get_block(read_page(root / "methods/rank-a.md")[1], "facts")
    assert "[[templates/rank-plot|" not in facts
    assert "[[methods/score-c|" not in facts
    update_meta(root, "methods/rank-a.md", outputs=["feature-importance", "sample-scores"])
    save(config, "supply complete outputs")
    facts = get_block(read_page(root / "methods/rank-a.md")[1], "facts")
    assert "[[templates/rank-plot|" in facts and "[[methods/score-c|" in facts


def test_save_restores_derived_facts_preserves_sections_and_lists_code(tiny_wiki):
    from fastapi.testclient import TestClient
    from rwiki.server import create_app

    config, config_path = tiny_wiki
    root = config.wiki_root
    relative = "methods/rank-a/code/辅助 文件/prepare 数据.py"
    code = root / relative
    code.parent.mkdir()
    code.write_text("# reusable preparation\n", encoding="utf-8")
    save(config, "canonical facts")
    paths = [root / "templates/rank-plot.md", root / "methods/rank-a.md",
             root / "interfaces/feature-importance.md"]
    originals = {}
    for path in paths:
        meta, body = read_page(path)
        originals[path] = body
        write_page(path, meta, set_block(body, "facts", "\nHAND EDITED WRONG\n"))
    result = run_cli(config_path, "save", "restore canonical facts")
    assert result.returncode == 0, result.stderr
    for path, original in originals.items():
        assert read_page(path)[1] == original
        assert "author note" in get_block(original, "user")
    facts = get_block(originals[root / "methods/rank-a.md"], "facts")
    href = re.search(r"\[" + re.escape(relative) + r"\]\(([^)]+)\)", facts)[1]
    with TestClient(create_app(config)) as client:
        response = client.get(href)
    assert response.status_code == 200
    assert response.content == code.read_bytes()
    assert "text/html" not in response.headers["content-type"]
    assert href.startswith("/files/wiki/")
    assert "%20" in href and "%E8%BE%85" in href
    assert "methods/rank-a/code/run.py" in facts
    assert "参数" not in facts and "依赖" not in facts


def test_suggest_pipeline_lists_ready_method_note_context(tiny_wiki):
    from rwiki.suggest import suggest_pipeline

    config, config_path = tiny_wiki
    save(config, "prepare suggestion")
    groups = suggest_pipeline(config, "rank-plot", "marker")
    assert len(groups) == 1 and groups[0]["id"] == "rank-plot"
    methods = {method["id"]: method for method in groups[0]["methods"]}
    assert set(methods) == {"rank-a", "rank-b"}
    for method_id, applicable in (("rank-a", "marker ranking"), ("rank-b", "stable ranking")):
        method = methods[method_id]
        assert method["applicable"] == applicable
        assert method["not_applicable"] == f"avoid {method_id}"
        assert method["tags"]
        assert method["code_files"] == [f"methods/{method_id}/code/run.py"]
        assert "params" not in method and "dependencies" not in method
    assert suggest_pipeline(config, "missing-figure", "") == []
    result = run_cli(config_path, "suggest-pipeline", "--figure", "rank-plot", "--q", "marker")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == groups


def test_suggest_pipeline_excludes_unready_methods(tiny_wiki):
    from rwiki.suggest import suggest_pipeline

    config, _ = tiny_wiki
    update_meta(config.wiki_root, "methods/rank-a.md", status="draft")
    update_meta(config.wiki_root, "methods/rank-b.md", status="archived", archived_from="ready")
    groups = suggest_pipeline(config, None, "")
    assert [group["id"] for group in groups] == ["rank-plot"]
    assert groups[0]["methods"] == []


def test_graph_feeds_follow_frontmatter_interfaces(tiny_wiki):
    from fastapi.testclient import TestClient
    from rwiki.server import create_app

    config, _ = tiny_wiki
    root = config.wiki_root
    save(config, "derive graph")
    for slug, target in (("a", "b"), ("b", "a")):
        write_page(root / f"projects/{slug}.md", {
            "type": "project", "slug": slug, "title": slug, "templates": [],
        }, f"[[projects/{target}]] [[projects/{target}|again]] [[projects/{slug}]]\n")
    with TestClient(create_app(config)) as client:
        links = client.get("/api/graph").json()["links"]
    for source, target in (
        ("methods/rank-a.md", "interfaces/feature-importance.md"),
        ("methods/rank-b.md", "interfaces/feature-importance.md"),
        ("interfaces/feature-importance.md", "methods/score-c.md"),
        ("methods/score-c.md", "interfaces/sample-scores.md"),
        ("interfaces/feature-importance.md", "templates/rank-plot.md"),
    ):
        assert {"source": source, "target": target, "kind": "feeds"} in links
        assert sum({edge["source"], edge["target"]} == {source, target} for edge in links) == 1
    ordinary = [edge for edge in links if {edge["source"], edge["target"]} == {"projects/a.md", "projects/b.md"}]
    assert len(ordinary) == 1 and ordinary[0]["kind"] == "link"
    assert all(edge["source"] != edge["target"] for edge in links)


def test_server_method_draft_ready_return_tags_and_common_actions(tiny_wiki):
    from fastapi.testclient import TestClient
    from rwiki.server import create_app

    config, _ = tiny_wiki
    root = config.wiki_root
    update_meta(root, "methods/rank-a.md", status="draft")
    save(config, "await author")
    with TestClient(create_app(config)) as client:
        for path in ("methods/rank-a.md", "interfaces/feature-importance.md"):
            response = client.get("/api/page", params={"path": path})
            assert response.status_code == 200 and response.json()["gallery"] is None
        response = client.post("/api/methods/rank-a/confirm")
        assert response.status_code == 200, response.text
        assert response.json()["meta"]["status"] == "ready"
        assert client.post("/api/methods/rank-a/confirm").status_code == 409
        response = client.post("/api/methods/rank-a/return", json={"reason": "expand explanation"})
        assert response.status_code == 200, response.text
        assert response.json()["meta"]["status"] == "draft"
        assert client.post("/api/methods/rank-a/return", json={"reason": "again"}).status_code == 409
        for action, payload in (
            ("favorite", {"value": True}), ("note", {"text": "updated author note"}),
            ("tags", {"tags": [" custom ", "custom", "新标签"]}),
            ("archive", None), ("restore", None),
        ):
            response = client.post(f"/api/methods/rank-a/{action}", json=payload)
            assert response.status_code == 200, response.text
        meta, body = read_page(root / "methods/rank-a.md")
        assert meta["status"] == "draft" and meta["favorite"]
        assert meta["tags"] == ["custom", "新标签"]
        assert "updated author note" in get_block(body, "user")
        assert "- 标签：custom、新标签" in get_block(body, "facts")
    assert "return rank-a: expand explanation" in (root / "log.md").read_text(encoding="utf-8")


def test_cli_record_use_method_without_params_updates_backlink(tiny_wiki):
    config, config_path = tiny_wiki
    result = run_cli(config_path, "record-use", "rank-plot", "--project", "study",
                     "--title", "Study", "--output", "figure.png", "--method", "rank-a")
    assert result.returncode == 0, result.stderr
    meta, body = read_page(config.wiki_root / "projects/study.md")
    assert meta["methods"] == ["rank-a"] and "[[methods/rank-a|rank-a]]" in body
    assert "[[projects/study|Study]]" in read_page(config.wiki_root / "methods/rank-a.md")[1]


def test_record_use_rejects_nonready_method(tiny_wiki):
    from rwiki.errors import WikiError
    from rwiki.usage import record_use

    config, _ = tiny_wiki
    update_meta(config.wiki_root, "methods/rank-a.md", status="draft")
    with pytest.raises(WikiError, match="ready"):
        record_use(config, "rank-plot", "study", "Study", "figure.png", None, method_id="rank-a")
    assert not (config.wiki_root / "projects/study.md").exists()


@pytest.mark.parametrize("case,page,needle", [
    ("method-required", "methods/rank-a.md", "license"),
    ("method-status", "methods/rank-a.md", "status"),
    ("method-source", "methods/rank-a.md", "source.kind"),
    ("method-written-cite", "methods/rank-a.md", "cite"),
    ("method-input", "methods/rank-a.md", "missing-interface"),
    ("method-output", "methods/rank-a.md", "missing-interface"),
    ("interface-required", "interfaces/feature-importance.md", "slug"),
    ("interface-columns", "interfaces/feature-importance.md", "columns"),
    ("template-interface", "templates/rank-plot.md", "missing-interface"),
])
def test_lint_reports_asset_and_frontmatter_errors_without_aborting(tiny_wiki, case, page, needle):
    from rwiki.lint import lint

    config, _ = tiny_wiki
    root = config.wiki_root
    save(config, "valid fixture")
    if case in ("method-required", "interface-required"):
        meta, body = read_page(root / page)
        del meta["license" if case == "method-required" else "slug"]
        write_page(root / page, meta, body)
    elif case == "method-status":
        update_meta(root, page, status="pending_confirm")
    elif case == "method-source":
        update_meta(root, page, source={"kind": ["post"]})
    elif case == "method-written-cite":
        update_meta(root, page, source={"kind": "written"}, cite=[])
    elif case in ("method-input", "method-output"):
        update_meta(root, page, **{"inputs" if case == "method-input" else "outputs": ["missing-interface"]})
    elif case == "interface-columns":
        update_meta(root, page, columns={"feature": {"type": "bool", "description": ""}})
    elif case == "template-interface":
        path = root / "templates/rank-plot/spec.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        spec["tables"]["values"]["interface"] = "missing-interface"
        write_json(path, spec)
    write_page(root / "projects/also-invalid.md", {
        "type": "project", "slug": "also-invalid", "title": "also invalid",
    }, "# also invalid\n")
    diagnostics = lint(config)
    assert any(line.startswith(f"ERROR {page}:") and needle in line for line in diagnostics), diagnostics
    assert any(line.startswith("ERROR projects/also-invalid.md:") and "templates" in line
               for line in diagnostics), diagnostics


def test_lint_accepts_written_note_with_cite_and_no_assets(tiny_wiki):
    from rwiki.lint import lint

    config, _ = tiny_wiki
    root = config.wiki_root
    update_meta(root, "methods/rank-a.md", source={"kind": "written"}, cite=["Official documentation"])
    record_ready_receipt(config, root / "methods/rank-a.md")  # changed provenance is re-checked
    save(config, "written with provenance")
    assert lint(config) == []


def test_lint_warns_for_stale_facts_and_save_clears_warning(tiny_wiki):
    from rwiki.lint import lint

    config, _ = tiny_wiki
    root = config.wiki_root
    save(config, "valid facts")
    for relative in ("templates/rank-plot.md", "methods/rank-a.md", "interfaces/feature-importance.md"):
        meta, body = read_page(root / relative)
        write_page(root / relative, meta, set_block(body, "facts", "\nstale\n"))
    diagnostics = lint(config)
    assert sum(line.startswith("WARN ") and "save" in line for line in diagnostics) == 3
    save(config, "restore facts")
    assert not any(line.startswith("WARN ") and "save" in line for line in lint(config))


def test_lint_damaged_method_frontmatter_keeps_other_diagnostics(tiny_wiki):
    from rwiki.lint import lint

    config, _ = tiny_wiki
    (config.wiki_root / "methods/rank-a.md").write_text("---\ntype: [\n---\n# broken\n", encoding="utf-8")
    (config.wiki_root / "index.md").write_text("[[missing]]\n", encoding="utf-8")
    diagnostics = lint(config)
    assert any(line.startswith("ERROR methods/rank-a.md:") and "frontmatter" in line for line in diagnostics)
    assert any(line.startswith("ERROR index.md:") and "missing" in line for line in diagnostics)


def test_method_facts_source_fallback_and_self_consuming_next_step(tiny_wiki):
    config, _ = tiny_wiki
    root = config.wiki_root
    update_meta(root, "methods/rank-a.md", source={"kind": "post", "gallery_entry": "post/figures/fig"},
                inputs=["feature-importance"])
    save(config, "derive reusable step")
    facts = get_block(read_page(root / "methods/rank-a.md")[1], "facts")
    assert "- 来源：post__fig\n" in facts
    assert "[[methods/rank-a|rank-a]]（ready）" in facts


def test_cli_mark_ready_accepts_draft_note(tiny_wiki):
    config, config_path = tiny_wiki
    root = config.wiki_root
    update_meta(root, "methods/rank-a.md", status="draft")
    ready = run_cli(config_path, "mark-ready", "rank-a")
    assert ready.returncode == 0, ready.stderr
    assert read_page(root / "methods/rank-a.md")[0]["status"] == "ready"
    repeated = run_cli(config_path, "mark-ready", "rank-a")
    assert repeated.returncode == 1 and "draft" in repeated.stderr

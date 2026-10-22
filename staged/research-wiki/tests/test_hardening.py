"""Regression tests for the 2026-10-22 review: local-only API, atomic writes, gates and evidence."""
import json

import pytest
from fastapi.testclient import TestClient

from conftest import ENTRY_ID
from test_semantic_relations import relation, semantic_wiki, update  # noqa: F401  (fixture reuse)
from test_templates import approved, fake_template  # noqa: F401  (fixture reuse)
from rwiki.acceptance import acceptance_stale
from rwiki.errors import WikiError
from rwiki.layouts import load_layout
from rwiki.lint import lint
from rwiki.pages import read_page, write_page
from rwiki.relations import relation_errors
from rwiki.server import create_app
from rwiki.spec import load_spec
from rwiki.templates import mark_ready, verify_template


def client(config):
    return TestClient(create_app(config))


def gallery_meta(config):
    return config.gallery_root / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/meta.json"


def test_foreign_host_and_cross_site_writes_are_rejected(ingested):
    config, _ = ingested
    page = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    with client(config) as c:
        # DNS rebinding: a foreign name pointing at 127.0.0.1 cannot read or write.
        assert c.get("/api/pages", headers={"Host": "evil.example:8765"}).status_code == 403
        for headers in ({"Origin": "https://evil.example"}, {"Origin": "null"},
                        {"Sec-Fetch-Site": "cross-site"}):
            assert c.post(f"/api/layouts/{ENTRY_ID}/signoff", headers=headers).status_code == 403
        assert read_page(page)[0]["status"] == "pending_signoff"
        local = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}
        assert c.post(f"/api/layouts/{ENTRY_ID}/favorite", json={"value": True}, headers=local).status_code == 200


def test_repository_internals_are_not_served(ingested):
    config, _ = ingested
    with client(config) as c:
        assert c.get("/files/wiki/.git/config").status_code == 404
        assert c.get("/files/wiki/.git/HEAD").status_code == 404
        assert c.get("/files/wiki/AGENTS.md").status_code == 200


def test_failed_save_restores_page_and_gallery(ingested):
    config, _ = ingested
    page = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    before_page, before_gallery = page.read_bytes(), gallery_meta(config).read_bytes()
    (config.wiki_root / ".git").rename(config.wiki_root / "removed-git")  # commit will fail
    with client(config) as c:
        assert c.post(f"/api/layouts/{ENTRY_ID}/signoff").status_code == 500
    assert page.read_bytes() == before_page
    assert gallery_meta(config).read_bytes() == before_gallery


def test_one_unreadable_page_does_not_take_down_list_or_saves(ingested):
    config, _ = ingested
    (config.wiki_root / "projects").mkdir(exist_ok=True)
    (config.wiki_root / "projects/broken.md").write_text("no frontmatter", encoding="utf-8")
    with client(config) as c:
        assert c.get("/api/pages").status_code == 200
        assert c.post(f"/api/layouts/{ENTRY_ID}/favorite", json={"value": True}).status_code == 200
    assert any("projects/broken.md" in line and "frontmatter" in line for line in lint(config))


def test_sole_source_of_a_live_template_cannot_be_deleted(layout_workspace):
    config, _, target, _ = layout_workspace
    page = target.with_suffix(".md")
    meta, body = read_page(page)
    meta["archived_from"], meta["status"] = meta["status"], "archived"
    write_page(page, meta, body)
    with client(config) as c:
        response = c.get(f"/api/layouts/{ENTRY_ID}/delete-plan")
    assert response.status_code == 409 and "唯一出处" in response.json()["detail"]
    assert page.is_file()


def test_spec_files_must_stay_inside_the_template(fake_template):
    config, _, target = fake_template
    (target.parent / "outside.py").write_text("", encoding="utf-8")
    spec = json.loads((target / "spec.json").read_text(encoding="utf-8"))
    for key, value in (("entry", "../outside.py"), ("panel", "../outside.py")):
        bad = dict(spec, **{key: value})
        (target / "spec.json").write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(WikiError, match="越出模板目录"):
            load_spec(target)


def test_layout_with_missing_template_mapping_is_a_diagnostic_not_a_crash(layout_workspace):
    config, _, target, layout = layout_workspace
    page = target.with_suffix(".md")
    meta, body = read_page(page)
    meta["template_panels"] = {}
    write_page(page, meta, body)
    with pytest.raises(WikiError, match="归属不一致"):
        load_layout(target)
    layout["panels"][0]["tables"] = {"values": "../values.csv"}
    meta["template_panels"] = {layout["panels"][0]["template"]: ["A"], layout["panels"][1]["template"]: ["B"]}
    write_page(page, meta, body)
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    with pytest.raises(WikiError, match="普通文件名"):
        load_layout(target)


def test_mark_ready_never_duplicates_the_preview_embed(fake_template):
    config, _, target = fake_template
    verify_template(config, target.name)
    page = target.with_suffix(".md")
    meta, body = read_page(page)
    embed = f"![[templates/{target.name}/preview.png]]"
    write_page(page, meta, body.replace("\n", f"\n\n{embed}\n", 1))
    mark_ready(config, target.name)
    meta, body = read_page(page)
    assert meta["status"] == "ready" and body.count(embed) == 1
    assert not acceptance_stale(page)


def test_mark_ready_rolls_back_when_the_commit_fails(fake_template):
    config, _, target = fake_template
    verify_template(config, target.name)
    page = target.with_suffix(".md")
    before = page.read_bytes()
    (config.wiki_root / ".git").rename(config.wiki_root / "removed-git")
    with pytest.raises(Exception):
        mark_ready(config, target.name)
    assert page.read_bytes() == before
    assert read_page(page)[0]["status"] == "draft" and not (target / "acceptance.json").exists()


def test_ready_entry_without_receipt_is_stale(fake_template):
    config, _, target = fake_template
    verify_template(config, target.name)
    mark_ready(config, target.name)
    page = target.with_suffix(".md")
    (target / "acceptance.json").unlink()
    assert acceptance_stale(page)
    assert any("入库验收记录已过期" in line for line in lint(config))


def test_direct_requires_a_confirmed_template_reading_declared_outputs(semantic_wiki):  # noqa: F811
    config, _ = semantic_wiki
    update(config, "templates/f-a.md", status="draft")
    meta, _ = read_page(config.wiki_root / "methods/m-a.md")
    assert any("draft" in error for error in relation_errors(config, meta))
    update(config, "templates/f-a.md", status="ready")
    # m-a outputs source-values; f-b reads plot-values, so direct is not structurally possible.
    update(config, "methods/m-a.md", figure_relations=[relation("templates/f-b")])
    meta, _ = read_page(config.wiki_root / "methods/m-a.md")
    assert any("plot-values" in error and "adaptable" in error for error in relation_errors(config, meta))


def test_method_without_any_template_must_explain_why(semantic_wiki):  # noqa: F811
    config, _ = semantic_wiki
    page = config.wiki_root / "methods/m-c.md"
    update(config, "methods/m-c.md", outputs=["plot-values"])
    update(config, "templates/f-b.md", status="archived", archived_from="ready")
    meta, body = read_page(page)
    write_page(page, meta, body.replace("无图原因", "暂未说明"))
    assert any(line.startswith("WARN methods/m-c.md:") and "无图原因" in line for line in lint(config))
    write_page(page, meta, body)
    assert not any(line.startswith("WARN methods/m-c.md:") and "无图原因" in line for line in lint(config))

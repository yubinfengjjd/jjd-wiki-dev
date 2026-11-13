import pytest

from conftest import ENTRY_ID, run_cli, update_gallery
from rwiki.pages import read_page, write_page


def test_clean_wiki_prints_ok(ingested):
    _, config_path = ingested
    result = run_cli(config_path, "lint")
    assert result.returncode == 0
    assert result.stdout.strip() == "OK"


@pytest.mark.parametrize("target", ["[[missing]]", "![[missing.png]]"])
def test_broken_links_are_errors(ingested, target):
    config, config_path = ingested
    path = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(path)
    write_page(path, meta, body + target)
    result = run_cli(config_path, "lint")
    assert result.returncode == 1
    assert f"ERROR layouts/{ENTRY_ID}.md:" in result.stdout
    assert "断链" in result.stdout


@pytest.mark.parametrize("change, message", [
    ({"tags": "bad"}, "tags"),
    ({"status": "pending_template"}, "approved"),
    ({"status": "ready"}, "preview.png"),
    ({"status": "invalid"}, "status"),
    ({"status": "archived"}, "archived_from"),
    ({"type": "unknown"}, "type"),
    ({"tags": [1]}, "tags"),
])
def test_metadata_and_state_errors(ingested, change, message):
    config, config_path = ingested
    path = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(path)
    meta.update(change)
    write_page(path, meta, body)
    result = run_cli(config_path, "lint")
    assert result.returncode == 1
    assert message in result.stdout


@pytest.mark.parametrize("text, expected", [
    ("# 无 frontmatter\n", "frontmatter"),
    ("---\ntitle: [\n---\n正文", "frontmatter"),
    ("---\ntitle: 标题\n---\n正文", "type"),
    ("---\ntype: chart-type\ntitle: 标题\n---\n正文", "slug"),
    ("---\ntype: project\nslug: test\ntitle: 标题\n---\n正文", "templates"),
])
def test_bad_pages_are_reported_without_stopping_other_diagnostics(ingested, text, expected):
    config, config_path = ingested
    (config.wiki_root / "chart-types/bad.md").write_text(text, encoding="utf-8")
    (config.wiki_root / "index.md").write_text("[[missing]]\n", encoding="utf-8")
    result = run_cli(config_path, "lint")
    assert result.returncode == 1
    assert "ERROR chart-types/bad.md:" in result.stdout
    assert expected in result.stdout
    assert "ERROR index.md:" in result.stdout


@pytest.mark.parametrize("name", ["user", "facts"])
def test_damaged_block_is_error(ingested, name):
    config, config_path = ingested
    path = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    text = path.read_text(encoding="utf-8").replace(f"<!-- {name}:end -->", "")
    path.write_text(text, encoding="utf-8")
    result = run_cli(config_path, "lint")
    assert result.returncode == 1
    assert f"{name} 区块" in result.stdout


def test_gallery_missing_and_approved_pending_signoff_are_errors(ingested):
    config, config_path = ingested
    update_gallery(config, status="approved")
    result = run_cli(config_path, "lint")
    assert result.returncode == 1
    assert "approved" in result.stdout and "pending_signoff" in result.stdout
    entry = config.gallery_root / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/meta.json"
    entry.unlink()
    result = run_cli(config_path, "lint")
    assert result.returncode == 1
    assert "meta.json 不存在" in result.stdout


def test_old_version_warns_but_exits_zero(ingested):
    config, config_path = ingested
    update_gallery(config, version=2)
    result = run_cli(config_path, "lint")
    assert result.returncode == 0
    assert f"WARN layouts/{ENTRY_ID}.md:" in result.stdout
    assert "version" in result.stdout
    assert result.stdout.rstrip().endswith("OK")


def test_empty_applicability_and_stale_index_warn(ingested):
    config, config_path = ingested
    update_gallery(config, status="approved")
    path = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(path)
    meta["status"] = "pending_template"
    meta['signedoff_version'] = meta['gallery_version']
    write_page(path, meta, body)
    result = run_cli(config_path, "lint")
    assert result.returncode == 0
    assert "适用" in result.stdout
    assert "WARN index.md:" in result.stdout and "save" in result.stdout


@pytest.mark.parametrize("kind,field", [("layout", "panels"), ("layout", "templates"),
                                        ("template", "layouts"), ("template", "panels")])
def test_new_page_required_keys(layout_workspace, kind, field):
    config, config_path, _, _ = layout_workspace
    page = (config.wiki_root / f"layouts/{ENTRY_ID}.md" if kind == "layout" else
            config.wiki_root / f"templates/{ENTRY_ID}--bar.md")
    meta, body = read_page(page)
    del meta[field]
    write_page(page, meta, body)
    result = run_cli(config_path, "lint")
    assert result.returncode == 1
    assert field in result.stdout


@pytest.mark.parametrize("fault,message", [
    ("missing-template", "模板"), ("missing-layout", "版式"),
    ("template-backlink", "layouts"), ("layout-backlink", "templates"),
    ("ready-spec", "spec.json"), ("ready-preview", "preview.png"),
    ("template-status", "status"), ("layout-status", "status"),
    ("ready-layout-preview", "preview.png"), ("ready-layout-draft", "ready"),
    ("ready-layout-uncovered", "覆盖"), ("invalid-layout-json", "letter"),
])
def test_lint_relationships_ready_rules_and_layout_json(layout_workspace, fault, message):
    config, config_path, target, layout = layout_workspace
    lp = target.with_suffix(".md")
    tp = config.wiki_root / f"templates/{ENTRY_ID}--bar.md"
    lm, lb = read_page(lp)
    tm, tb = read_page(tp)
    if fault == "missing-template":
        lm["templates"].append("missing")
    elif fault == "missing-layout":
        tm["layouts"].append("missing")
    elif fault == "template-backlink":
        tm["layouts"] = []
    elif fault == "layout-backlink":
        lm["templates"].remove(tm["id"])
    elif fault == "ready-spec":
        (tp.with_suffix("") / "spec.json").unlink()
        (target / "layout.json").unlink()
    elif fault == "ready-preview":
        (tp.with_suffix("") / "preview.png").unlink()
    elif fault == "template-status":
        tm["status"] = "pending_template"
    elif fault == "layout-status":
        lm["status"] = "draft"
    elif fault.startswith("ready-layout"):
        from PIL import Image
        lm["status"] = "ready"
        if fault != "ready-layout-preview":
            Image.new("RGB", (2, 2)).save(target / "preview.png")
        if fault == "ready-layout-draft":
            tm["status"] = "draft"
        if fault == "ready-layout-uncovered":
            lm["panels"]["C"] = "bar"
    else:
        import json
        layout["panels"][0]["letter"] = "Z"
        (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    write_page(lp, lm, lb)
    write_page(tp, tm, tb)
    result = run_cli(config_path, "lint")
    assert result.returncode == 1
    assert message in result.stdout + result.stderr


def test_lint_reports_bad_layout_json_alongside_other_findings(layout_workspace):
    import json
    config, config_path, target, layout = layout_workspace
    layout["panels"][0]["letter"] = "Z"
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    tp = config.wiki_root / f"templates/{ENTRY_ID}--bar.md"
    tm, tb = read_page(tp)
    tm["layouts"] = []
    write_page(tp, tm, tb)
    result = run_cli(config_path, "lint")
    assert result.returncode == 1
    assert "layout.json: layout.panels[0].letter" in result.stdout
    # An emptied source list is a template of unknown origin (D044), not just a back-link gap.
    assert f"{ENTRY_ID}--bar.md: 模板必须记录来源" in result.stdout

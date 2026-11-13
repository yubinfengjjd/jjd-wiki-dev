import json

import pytest

from conftest import ENTRY_ID, run_cli
from rwiki.errors import WikiError
from rwiki.ingest import ingest_figure
from rwiki.pages import get_block, read_page, set_block, write_page
from rwiki.spec import load_spec
from rwiki.templates import mark_ready, scaffold_template


def test_ingest_creates_layout_with_panel_map_and_no_template(workspace):
    config, config_path = workspace
    result = run_cli(config_path, "ingest-figure", ENTRY_ID)
    assert result.returncode == 0, result.stderr
    meta, body = read_page(config.wiki_root / f"layouts/{ENTRY_ID}.md")
    assert meta["type"] == "layout"
    assert meta["panels"] == {"A": "bar", "B": "beeswarm", "C": "radial-bar",
                              "D": "bar", "E": "beeswarm", "F": "radial-bar"}
    assert meta["chart_types"] == ["bar", "beeswarm", "radial-bar"]
    assert meta["templates"] == []
    assert "面板：尚未拆分（A–F）" in get_block(body, "facts")
    assert f"![[layouts/{ENTRY_ID}/thumb.png]]" in body
    assert not list((config.wiki_root / "templates").iterdir())
    assert "## 版式" in (config.wiki_root / "index.md").read_text(encoding="utf-8")


def test_missing_panel_map_fails_without_writing(workspace):
    config, _ = workspace
    path = next(config.gallery_root.glob("*/figures/*/meta.json"))
    gallery = json.loads(path.read_text(encoding="utf-8"))
    del gallery["figure"]["panel_map"]
    path.write_text(json.dumps(gallery), encoding="utf-8")
    with pytest.raises(WikiError, match="sci-figure-replica"):
        ingest_figure(config, ENTRY_ID)
    assert not list((config.wiki_root / "layouts").iterdir())


@pytest.mark.parametrize("language,panel", [("python", None), ("python", "code/missing.py"),
                                            ("r", "code/panel.py")])
def test_spec_enforces_language_panel_contract(tmp_path, language, panel):
    code = tmp_path / "code"
    code.mkdir()
    extension = "py" if language == "python" else "R"
    (code / f"render.{extension}").write_text("", encoding="utf-8")
    spec = {"language": language, "entry": f"code/render.{extension}",
            "tables": {"t": {"interface": "values", "description": "数值"}},
            "style": {}}
    if panel is not None:
        spec["panel"] = panel
    (tmp_path / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(WikiError, match="panel"):
        load_spec(tmp_path)


@pytest.mark.parametrize("chart,letters,message", [
    ("bar", ["Z"], "字母"), ("bar", ["B"], "图型"),
    ("bar", ["A", "A"], "重复"), ("bar", [], "非空")])
def test_scaffold_rejects_invalid_selection_before_writing(ingested, chart, letters, message):
    from conftest import update_gallery
    config, _ = ingested
    update_gallery(config, status="approved")
    ingest_figure(config, ENTRY_ID)
    with pytest.raises(WikiError, match=message):
        scaffold_template(config, ENTRY_ID, chart, letters)
    assert not list((config.wiki_root / "templates").iterdir())


def test_scaffold_generates_linked_facts_and_blocks_covered_panels(ingested):
    from conftest import update_gallery
    config, _ = ingested
    update_gallery(config, status="approved")
    ingest_figure(config, ENTRY_ID)
    scaffold_template(config, ENTRY_ID, "bar", ["A", "D"])
    tid = ENTRY_ID + "--bar"
    meta, body = read_page(config.wiki_root / f"layouts/{ENTRY_ID}.md")
    assert meta["template_panels"] == {tid: ["A", "D"]}
    assert f"[[templates/{tid}|bar]]" in get_block(body, "facts")
    assert "（A、D）" in get_block(body, "facts")
    tm, tb = read_page(config.wiki_root / f"templates/{tid}.md")
    assert tm["status"] == "draft" and tm["panels"] == ["A", "D"]
    assert f"[[layouts/{ENTRY_ID}|" in get_block(tb, "facts")
    assert "preview.png" not in tb
    # A different template id must not bypass panel ownership checks.
    other = dict(tm, id="other")
    write_page(config.wiki_root / "templates/other.md", other, tb)
    (config.wiki_root / f"templates/{tid}.md").unlink()
    (config.wiki_root / "templates" / tid).rename(config.wiki_root / "templates/other")
    meta["templates"] = ["other"]
    meta["template_panels"] = {"other": ["A"]}
    write_page(config.wiki_root / f"layouts/{ENTRY_ID}.md", meta, body)
    with pytest.raises(WikiError, match="覆盖"):
        scaffold_template(config, ENTRY_ID, "bar", ["A"])


def test_attach_preserves_source_panels_and_uses_target_letters(layout_workspace):
    from conftest import commit_count, run_cli
    config, path, target, _ = layout_workspace
    source = ENTRY_ID + "--bar"
    layout, body = read_page(target.with_suffix(".md"))
    layout.update(id="second", panels={"C": "bar", "F": "bar"}, templates=[], template_panels={})
    write_page(config.wiki_root / "layouts/second.md", layout, body)
    before = commit_count(config.wiki_root)
    result = run_cli(path, "attach-template", "second", source, "--panels", "C,F")
    assert result.returncode == 0, result.stderr
    assert commit_count(config.wiki_root) == before + 1
    tm, tb = read_page(config.wiki_root / f"templates/{source}.md")
    assert tm["layouts"] == [ENTRY_ID, "second"] and tm["panels"] == ["A"]
    lm, lb = read_page(config.wiki_root / "layouts/second.md")
    assert lm["templates"] == [source] and lm["template_panels"] == {source: ["C", "F"]}
    assert "（C、F）" in get_block(lb, "facts") and "[[layouts/second|" in get_block(tb, "facts")
    result = run_cli(path, "attach-template", "second", source, "--panels", "C")
    assert result.returncode == 1 and "覆盖" in result.stderr


@pytest.mark.parametrize("fault,message", [("draft", "ready"), ("letter", "字母"),
                                          ("chart", "图型"), ("layout-state", "pending_template")])
def test_attach_rejects_invalid_selection_without_writes(layout_workspace, fault, message):
    from rwiki.templates import attach_template
    config, _, target, _ = layout_workspace
    tid = ENTRY_ID + "--bar"
    page = config.wiki_root / f"templates/{tid}.md"
    tm, tb = read_page(page)
    if fault == "draft":
        tm["status"] = "draft"
        write_page(page, tm, tb)
    lm, lb = read_page(target.with_suffix(".md"))
    lm.update(id="second", panels={"C": "dot" if fault == "chart" else "bar"},
              templates=[], template_panels={})
    if fault == "layout-state":
        lm["status"] = "ready"
    second = config.wiki_root / "layouts/second.md"
    write_page(second, lm, lb)
    original = second.read_bytes(), page.read_bytes()
    with pytest.raises(WikiError, match=message):
        attach_template(config, "second", tid, ["Z" if fault == "letter" else "C"])
    assert (second.read_bytes(), page.read_bytes()) == original


def test_mark_layout_ready_checks_templates_and_full_coverage(layout_workspace):
    from PIL import Image
    config, _, target, _ = layout_workspace
    Image.new("RGB", (2, 2)).save(target / "preview.png")
    tp = config.wiki_root / f"templates/{ENTRY_ID}--bar.md"
    tm, tb = read_page(tp)
    tm["status"] = "draft"
    write_page(tp, tm, tb)
    with pytest.raises(WikiError, match="ready"):
        mark_ready(config, ENTRY_ID)
    tm["status"] = "ready"
    write_page(tp, tm, tb)
    page = target.with_suffix(".md")
    lm, lb = read_page(page)
    lm["panels"]["C"] = "bar"
    write_page(page, lm, lb)
    with pytest.raises(WikiError, match="覆盖"):
        mark_ready(config, ENTRY_ID)
    del lm["panels"]["C"]
    write_page(page, lm, lb)
    from conftest import seal_replay
    seal_replay(target)
    mark_ready(config, ENTRY_ID)
    assert read_page(page)[0]["status"] == "ready"


@pytest.mark.parametrize("args", [
    ("scaffold-template", "missing", "--chart-type", "bar", "--panels", "A"),
    ("attach-template", ENTRY_ID, "missing", "--panels", "A"),
    ("render-layout", "missing", "--data", ".", "--out", "."),
])
def test_missing_page_cli_error_has_no_traceback(ingested, args):
    from conftest import update_gallery
    config, path = ingested
    update_gallery(config, status="approved")
    ingest_figure(config, ENTRY_ID)
    result = run_cli(path, *args)
    assert result.returncode == 1 and "不存在" in result.stderr
    assert "Traceback" not in result.stderr

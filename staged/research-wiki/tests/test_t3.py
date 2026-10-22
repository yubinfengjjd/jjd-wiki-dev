import json
from datetime import date

import pytest
from PIL import Image

from conftest import (ENTRY_ID, commit_count, run_cli, update_gallery, write_interface, complete_sections,
                      record_ready_receipt, seal_replay)
from rwiki.ingest import ingest_figure
from rwiki.pages import get_block, read_page, set_block, write_page
from rwiki.store import git, save


@pytest.fixture
def candidates(workspace):
    config, config_path = workspace
    update_gallery(config, status="approved")
    ingest_figure(config, ENTRY_ID)
    original = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    source, original_body = read_page(original)
    write_page(original, source, original_body.replace("## 适用\n", "## 适用\n\n测试适用说明。\n"))
    for entry_id, title, size, color in (
        ("alpha", "A 特征重要性", (20, 10), "red"),
        ("beta", "B 生存", (10, 10), "green"),
        ("gamma", "C SHAP", (10, 20), "blue"),
    ):
        meta = {key: source[key] for key in ("language", "tags", "chart_types", "favorite")}
        meta.update(type="template", id=entry_id, title=title, status="ready", layouts=[ENTRY_ID], panels=["A", "D"])
        meta["tags"] = ["自由标签"]
        meta["chart_types"] = ["bar", "beeswarm"]
        body = (f"# {title}\n\n<!-- facts:start -->\n原始事实词\n<!-- facts:end -->\n\n"
                "## 适用\n\n用于比较 模型贡献。\n\n## 不适用\n\n不适用独有词。\n\n"
                "## 数据要求\n\n占位\n\n## 使用记录\n\n"
                "<!-- user:start -->\n作者备注词\n<!-- user:end -->\n")
        write_page(config.wiki_root / f"templates/{entry_id}.md", meta, body)
        target = config.wiki_root / "templates" / entry_id
        (target / "code").mkdir(parents=True)
        (target / "code/render.py").write_text("", encoding="utf-8")
        (target / "code/panel.py").write_text("", encoding="utf-8")
        (target / "code/__init__.py").write_text("", encoding="utf-8")
        write_interface(config.wiki_root, "summary", {
            "feature": {"type": "str", "description": "??"},
            "shap": {"type": "float", "description": "??"}})
        write_interface(config.wiki_root, "detail", {
            "feature": {"type": "str", "description": "??"},
            "percent": {"type": "float", "description": "??"},
            "value": {"type": "float", "description": "??"}})
        spec = {"entry": "code/render.py", "panel": "code/panel.py", "language": "python", "tables": {
            "summary": {"description": "??", "interface": "summary"},
            "detail": {"description": "??", "interface": "detail"}},
            "style": {"color": "red", "dpi": 100}}
        (target / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        Image.new("RGB", size, color).save(target / "preview.png")
        complete_sections(target.with_suffix('.md'))
        seal_replay(target)
        record_ready_receipt(config, target.with_suffix('.md'))
    for entry_id, status in (("waiting", "draft"), ("retired", "archived")):
        meta = dict(meta, id=entry_id, title="0 不可推荐", status=status)
        if status == "archived":
            meta["archived_from"] = "ready"
        write_page(config.wiki_root / f"templates/{entry_id}.md", meta, body)
    source["templates"] = ["alpha", "beta", "gamma", "waiting", "retired"]
    source["template_panels"] = {tid: ["A", "D"] for tid in source["templates"]}
    write_page(original, source, original_body.replace("## 适用\n", "## 适用\n\n测试适用说明。\n"))
    save(config, "test candidates")
    return config, config_path


def suggestions(config_path, *args):
    result = run_cli(config_path, "suggest", *args)
    assert result.returncode == 0, result.stderr
    assert "特征重要性" in result.stdout  # JSON retains Chinese text.
    return json.loads(result.stdout)


def test_suggest_ready_only_title_order_default_and_limit(candidates):
    config, path = candidates
    before = commit_count(config.wiki_root)
    result = suggestions(path)
    assert [item["id"] for item in result] == ["alpha", "beta", "gamma"]
    assert all(item["score"] == 0 and item["reasons"] == [] for item in result)
    assert [item["id"] for item in suggestions(path, "--limit", "2")] == ["alpha", "beta"]
    assert git(config.wiki_root, "status", "--porcelain") == ""
    assert commit_count(config.wiki_root) == before


@pytest.mark.parametrize("args, score, fragments", [
    (("--chart-type", "bar", "beeswarm", "unknown"), 4, ["bar", "beeswarm"]),
    (("--columns", " FEATURE,shap "), 2.7, ["summary", "detail", "feature", "shap", "percent", "value", "覆盖", "缺"]),
    (("--q", "特征重要性 自由标签 模型贡献 作者备注词 特征重要性 原始事实词 不适用独有词"),
     3, ["特征重要性", "自由标签", "模型贡献"]),
])
def test_suggest_each_signal_scores_with_chinese_reasons(candidates, args, score, fragments):
    _, path = candidates
    first = suggestions(path, *args)[0]
    assert first["id"] == "alpha"
    assert first["score"] == score
    for fragment in fragments:
        assert fragment in "\n".join(first["reasons"])


def test_suggest_sorts_by_score_then_title_and_adds_signals(candidates):
    _, path = candidates
    result = suggestions(path, "--chart-type", "bar",
                         "--columns", "feature,shap", "--q", "SHAP")
    assert [item["id"] for item in result] == ["gamma", "alpha", "beta"]
    assert [item["score"] for item in result] == [5.7, 4.7, 4.7]


def test_suggest_metadata_and_author_note_are_returned(candidates):
    config, path = candidates
    first = suggestions(path)[0]
    assert set(first) == {"id", "title", "score", "reasons", "page", "preview", "applicable",
                          "not_applicable", "note", "tables", "style_keys", "kind", "relations",
                          "prerequisites", "code_status", "discovery_note"}
    assert first["page"] == "templates/alpha.md"
    assert first["preview"] == str((config.wiki_root / "templates/alpha/preview.png").resolve())
    assert first["applicable"] == "用于比较 模型贡献。"
    assert first["not_applicable"] == "不适用独有词。"
    assert first["note"] == "作者备注词"
    assert first["tables"]["summary"]["interface"] == "summary"
    assert first["tables"]["summary"]["columns"] == {
        "feature": {"type": "str", "description": "??"},
        "shap": {"type": "float", "description": "??"}}
    assert set(first["tables"]["detail"]["columns"]) == {"feature", "percent", "value"}
    assert first["style_keys"] == ["color", "dpi"]


def test_suggest_column_rounding_is_half_up(candidates):
    config, path = candidates
    spec_path = config.wiki_root / "templates/alpha/spec.json"
    spec = json.loads(spec_path.read_text())
    write_interface(config.wiki_root, "rounding", {
        f"c{i}": {"type": "int", "description": "??"} for i in range(16)})
    spec["tables"] = {"data": {"interface": "rounding", "description": "???"}}
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    seal_replay(spec_path.parent)
    first = suggestions(path, "--columns", "c0")[0]
    assert first["id"] == "alpha"
    assert first["score"] == 0.3  # 1/16 × 4 = 0.25, 四舍五入。


def test_suggest_excludes_user_headings_from_applicability(candidates):
    config, path = candidates
    page = config.wiki_root / "templates/alpha.md"
    meta, body = read_page(page)
    write_page(page, meta, set_block(body, "user", "\n## 适用\n作者的私人标题\n"))
    first = suggestions(path)[0]
    assert first["applicable"] == "用于比较 模型贡献。"
    assert first["note"] == "## 适用\n作者的私人标题"


def test_suggest_no_ready_returns_empty_array(workspace):
    config, path = workspace
    result = run_cli(path, "suggest")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == []


def test_suggest_and_use_layout_alongside_templates(candidates, tmp_path):
    config, path = candidates
    page = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(page)
    meta.update(status="ready", templates=["alpha", "beta"],
                template_panels={"alpha": ["A"], "beta": ["D"]},
                panels={"A": "bar", "D": "bar"}, title="0 组合版式")
    write_page(page, meta, body)
    Image.new("RGB", (20, 10), "yellow").save(config.wiki_root / f"layouts/{ENTRY_ID}/preview.png")
    target = page.with_suffix('')
    layout = {'canvas': {'width_in': 4, 'height_in': 3, 'dpi': 50}, 'labels': [], 'panels': [
        {'letter': letter, 'template': tid, 'rect': [0.1, y, 0.8, 0.35],
         'tables': {'summary': 'summary.csv', 'detail': 'detail.csv'}, 'style': {}}
        for letter, tid, y in [('A', 'alpha', 0.1), ('D', 'beta', 0.55)]]}
    (target / 'layout.json').write_text(json.dumps(layout), encoding='utf-8')
    complete_sections(page)
    seal_replay(target)
    record_ready_receipt(config, page)
    result = suggestions(path, "--columns", "feature,shap", "--limit", "4")
    layout = next(item for item in result if item["id"] == ENTRY_ID)
    assert layout["kind"] == "layout" and layout["templates"] == ["alpha", "beta"]
    assert layout["score"] == 2.7
    assert len(layout["tables"]) == 4  # same table names in different templates both count
    assert all(item["kind"] == "template" for item in result if item["id"] != ENTRY_ID)
    out = tmp_path / "layout-sheet.png"
    rendered = run_cli(path, "contact-sheet", ENTRY_ID, "alpha", "--out", str(out))
    assert rendered.returncode == 0, rendered.stderr
    with Image.open(out) as image:
        assert image.getpixel((450, 200)) == (255, 255, 0)
    args = ("record-use", ENTRY_ID, "--project", "layout-use", "--title", "版式课题", "--output", "figure.png")
    first = run_cli(path, *args)
    assert first.returncode == 0, first.stderr
    project, project_body = read_page(config.wiki_root / "projects/layout-use.md")
    assert project["templates"] == [ENTRY_ID]
    assert f"[[layouts/{ENTRY_ID}|0 组合版式]]" in project_body
    count = commit_count(config.wiki_root)
    assert run_cli(path, *args).returncode == 0
    assert commit_count(config.wiki_root) == count


def test_contact_sheet_three_previews_width_color_and_no_save(candidates, tmp_path):
    config, path = candidates
    before = commit_count(config.wiki_root)
    out = tmp_path / "sheet.png"
    result = run_cli(path, "contact-sheet", "alpha", "beta", "gamma", "--out", str(out))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(out.resolve())
    with Image.open(out) as sheet:
        assert sheet.width == 2780
        assert sheet.getpixel((900, sheet.height - 1)) == (255, 255, 255)
        for x, color in ((450, (255, 0, 0)), (1390, (0, 128, 0)), (2330, (0, 0, 255))):
            assert sheet.getpixel((x, 200)) == color
        assert sheet.crop((0, 0, 900, 80)).getbbox()
    assert git(config.wiki_root, "status", "--porcelain") == ""
    assert commit_count(config.wiki_root) == before


def test_contact_sheet_truncates_long_chinese_title(candidates, tmp_path):
    config, path = candidates
    page = config.wiki_root / "templates/alpha.md"
    meta, body = read_page(page)
    meta["title"] = "非常长的中文标题" * 50
    write_page(page, meta, body)
    out = tmp_path / "long.png"
    result = run_cli(path, "contact-sheet", "alpha", "--out", str(out))
    assert result.returncode == 0, result.stderr
    with Image.open(out) as sheet:
        assert sheet.width == 900
        # Right margin remains white even when the full title cannot fit.
        assert all(pixel == (255, 255, 255) for pixel in sheet.crop((895, 0, 900, 100)).getdata())


@pytest.mark.parametrize("ids", [("waiting",), ("retired",), ("absent",),
                                  ("alpha", "beta", "gamma", "alpha")])
def test_contact_sheet_rejects_invalid_candidates_before_output(candidates, tmp_path, ids):
    _, path = candidates
    out = tmp_path / "bad.png"
    result = run_cli(path, "contact-sheet", *ids, "--out", str(out))
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "invalid choice" not in result.stderr
    assert not out.exists()


def test_record_use_creates_project_links_and_commit(candidates):
    config, path = candidates
    template = config.wiki_root / "templates/alpha.md"
    _, before_body = read_page(template)
    before = commit_count(config.wiki_root)
    result = run_cli(path, "record-use", "alpha", "--project", "demo-qsar", "--title", "课题一",
                     "--output", "D:\\demo\\fig3.png", "--note", "作者选定")
    assert result.returncode == 0, result.stderr
    project, body = read_page(config.wiki_root / "projects/demo-qsar.md")
    assert project == {"type": "project", "slug": "demo-qsar", "title": "课题一", "templates": ["alpha"]}
    assert f"- {date.today().isoformat()} [[templates/alpha|A 特征重要性]]，输出 `D:\\demo\\fig3.png`；作者选定" in body
    assert body.index("[[templates/alpha|") < body.index("<!-- user:start -->")
    _, template_body = read_page(template)
    assert f"- {date.today().isoformat()} [[projects/demo-qsar|课题一]]" in template_body
    assert get_block(template_body, "user") == get_block(before_body, "user")
    assert get_block(template_body, "facts") == get_block(before_body, "facts")
    assert commit_count(config.wiki_root) == before + 1
    assert git(config.wiki_root, "log", "-1", "--format=%s").strip() == "use alpha in demo-qsar"
    check = run_cli(path, "lint")
    # The fixture deliberately keeps a draft non-candidate and a pending-template
    # source incomplete; these are WARN findings, not lint errors.
    assert check.returncode == 0 and check.stdout.rstrip().endswith("OK"), check.stdout
    assert "ERROR " not in check.stdout, check.stdout


def test_record_use_does_not_invalidate_acceptance(candidates):
    from rwiki.acceptance import acceptance_stale, ready_for_use, record_acceptance
    from rwiki.workflow import workflow_snapshot

    config, path = candidates
    template = config.wiki_root / "templates/alpha.md"
    record_acceptance(config, template)
    assert ready_for_use(config, template)
    result = run_cli(path, "record-use", "alpha", "--project", "usage-acceptance",
                     "--title", "Usage acceptance", "--output", "D:/demo/fig.png")
    assert result.returncode == 0, result.stderr
    # A usage link is an append-only log entry, not a change to the note content.
    assert not acceptance_stale(template)
    assert ready_for_use(config, template)
    assert workflow_snapshot(config)["templates/alpha.md"]["stage"] == "complete"


def test_record_use_appends_templates_outputs_preserves_notes_and_deduplicates(candidates):
    config, path = candidates
    args = ("--project", "demo", "--title", "演示课题", "--output", "D:/one.png")
    first = run_cli(path, "record-use", "alpha", *args)
    assert first.returncode == 0, first.stderr
    project = config.wiki_root / "projects/demo.md"
    meta, body = read_page(project)
    # User text may contain headings and record-like links; it remains untouched.
    note = "\n## 私人笔记\n[[templates/beta|B 生存]]，输出 `D:/two.png`\n"
    write_page(project, meta, set_block(body, "user", note))
    save(config, "author note")
    result = run_cli(path, "record-use", "beta", "--project", "demo", "--title", "演示课题",
                     "--output", "D:/two.png")
    assert result.returncode == 0, result.stderr
    # A second output for the first template adds only a project row.
    result = run_cli(path, "record-use", "alpha", "--project", "demo", "--title", "演示课题",
                     "--output", "D:/one.png.backup")
    assert result.returncode == 0, result.stderr
    meta, body = read_page(project)
    assert meta["templates"] == ["alpha", "beta"]
    assert body.count("- " + date.today().isoformat()) == 3
    assert get_block(body, "user") == note
    before = commit_count(config.wiki_root)
    original = project.read_bytes()
    result = run_cli(path, "record-use", "alpha", *args, "--note", "重复时不应改变原记录")
    assert result.returncode == 0, result.stderr
    assert project.read_bytes() == original
    assert commit_count(config.wiki_root) == before
    assert git(config.wiki_root, "status", "--porcelain") == ""
    _, body = read_page(config.wiki_root / "templates/alpha.md")
    assert body.count("[[projects/demo|") == 1


@pytest.mark.parametrize("entry_id, slug", [("waiting", "demo"), ("retired", "demo"),
                                          ("absent", "demo"), ("alpha", "../escape"),
                                          ("alpha", "Upper"), ("alpha", "bad_slug"), ("alpha", "")])
def test_record_use_rejects_invalid_state_or_slug_without_mutation(candidates, entry_id, slug):
    config, path = candidates
    before = commit_count(config.wiki_root)
    result = run_cli(path, "record-use", entry_id, "--project", slug, "--title", "课题", "--output", "x.png")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "invalid choice" not in result.stderr
    assert not list((config.wiki_root / "projects").iterdir())
    assert git(config.wiki_root, "status", "--porcelain") == ""
    assert commit_count(config.wiki_root) == before


@pytest.mark.parametrize("template_title, project_title, output", [
    ("A 特征重要性", "课题", "D:/demo/fig`3.png"),
    ("A 特征重要性 [模型]", "课题", "D:/demo/fig3.png"),
    ("A 特征重要性", "课题 [模型]", "D:/demo/fig3.png"),
])
def test_record_use_deduplicates_legal_path_and_title_characters(
        candidates, template_title, project_title, output):
    config, path = candidates
    template = config.wiki_root / "templates/alpha.md"
    meta, body = read_page(template)
    meta["title"] = template_title
    write_page(template, meta, body)
    args = ("record-use", "alpha", "--project", "demo", "--title", project_title, "--output", output)
    first = run_cli(path, *args)
    assert first.returncode == 0, first.stderr
    before = commit_count(config.wiki_root)
    project = config.wiki_root / "projects/demo.md"
    original_project, original_template = project.read_bytes(), template.read_bytes()
    repeated = run_cli(path, *args)
    assert repeated.returncode == 0, repeated.stderr
    assert commit_count(config.wiki_root) == before
    assert project.read_bytes() == original_project
    assert template.read_bytes() == original_template
    assert git(config.wiki_root, "status", "--porcelain") == ""


def test_lint_reports_project_template_missing_even_without_body_link(workspace):
    config, path = workspace
    write_page(config.wiki_root / "projects/demo.md", {
        "type": "project", "slug": "demo", "title": "课题", "templates": ["missing"]},
        "# 课题\n\n## 使用的模板\n\n<!-- user:start -->\n<!-- user:end -->\n")
    save(config, "project with missing template")
    result = run_cli(path, "lint")
    assert result.returncode == 1
    assert "ERROR projects/demo.md:" in result.stdout
    assert "missing" in result.stdout and "模板" in result.stdout

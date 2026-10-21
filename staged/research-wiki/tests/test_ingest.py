import json
import shutil

import pytest

from conftest import ENTRY_ID, commit_count, run_cli, update_gallery
from rwiki.errors import WikiError
from rwiki.ingest import ingest_figure
from rwiki.pages import get_block, read_page, set_block, write_page


def test_null_source_and_empty_free_tags_omit_lines(workspace):
    config, _ = workspace
    entry = config.gallery_root / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/meta.json"
    gallery = json.loads(entry.read_text(encoding="utf-8"))
    gallery["post"].update(title=None, account=None, publish_date=None, url=None)
    gallery["scenarios"]["free"] = []
    update_gallery(config, post=gallery["post"], scenarios=gallery["scenarios"])
    ingest_figure(config, ENTRY_ID)
    facts = get_block(read_page(config.wiki_root / f"layouts/{ENTRY_ID}.md")[1], "facts")
    for label in ("来源", "公众号", "日期", "URL", "自由标签"):
        assert f"- {label}：" not in facts
    assert "None" not in facts
    assert "- 画廊条目：" in facts


def test_null_post_title_uses_only_figure_label(workspace):
    config, _ = workspace
    entry = config.gallery_root / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/meta.json"
    gallery = json.loads(entry.read_text(encoding="utf-8"))
    gallery["post"]["title"] = None
    update_gallery(config, post=gallery["post"])
    ingest_figure(config, ENTRY_ID)
    meta, body = read_page(config.wiki_root / f"layouts/{ENTRY_ID}.md")
    assert meta["title"] == gallery["figure"]["label"]
    assert body.startswith(f"# {meta['title']}\n")


def test_first_ingest_builds_pages_thumbnail_facts_index_and_one_commit(workspace):
    config, config_path = workspace
    result = run_cli(config_path, "ingest-figure", ENTRY_ID)
    assert result.returncode == 0, result.stderr
    root = config.wiki_root
    meta, body = read_page(root / f"layouts/{ENTRY_ID}.md")
    assert meta["status"] == "pending_signoff"
    assert meta["chart_types"] == ["bar", "beeswarm", "radial-bar"]
    assert meta["tags"] == ["模型解释与特征重要性", "化学信息与QSAR", "SHAP", "LightGBM", "CatBoost", "pLC50", "AR-DBP"]
    assert meta["gallery_entry"] == "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f"
    entry = config.gallery_root / meta["gallery_entry"]
    assert (root / f"layouts/{ENTRY_ID}/thumb.png").read_bytes() == (entry / "thumb.png").read_bytes()
    assert not (root / "scenarios").exists()
    for slug in ("bar", "beeswarm", "radial-bar"):
        assert (root / f"chart-types/{slug}.md").is_file()
    facts = get_block(body, "facts")
    for expected in ("Python机器学习AI", "2026-08-17", "https://mp.weixin.qq.com/",
                     "mixed", "reconstructed", "python", "LightGBM",
                     "模型解释与特征重要性",
                     "[[chart-types/radial-bar]]"):
        assert expected in facts
    assert f"[[layouts/{ENTRY_ID}|" in (root / "index.md").read_text(encoding="utf-8")
    assert f"ingest {ENTRY_ID}" in (root / "log.md").read_text(encoding="utf-8")
    assert commit_count(root) == 2


def test_reingest_protects_wiki_content_and_transitions_status(ingested):
    config, _ = ingested
    page = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(page)
    meta["tags"] = ["单细胞分析", "作者自定"]
    meta["favorite"] = True
    body = set_block(body, "user", "\n作者备注（一个字不改）\n")
    body = body.replace("## 适用\n", "## 适用\n\n经作者确认的适用说明。\n")
    write_page(page, meta, body)
    outside_facts = set_block(body, "facts", "")
    update_gallery(config, status="approved")
    ingest_figure(config, ENTRY_ID)
    new_meta, new_body = read_page(page)
    assert new_meta["status"] == "pending_template"
    assert new_meta["tags"] == meta["tags"]
    assert new_meta["favorite"] is True
    assert set_block(new_body, "facts", "") == outside_facts
    assert "单细胞分析" in get_block(new_body, "facts")
    assert not (config.wiki_root / "scenarios").exists()
    update_gallery(config, version=2)
    ingest_figure(config, ENTRY_ID)
    assert read_page(page)[0]["status"] == "pending_signoff"
    assert read_page(page)[0]["gallery_version"] == 2


def test_archived_and_existing_hubs_are_preserved(ingested):
    config, _ = ingested
    page = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(page)
    meta.update(status="archived", archived_from="pending_signoff")
    write_page(page, meta, body)
    hub = config.wiki_root / "chart-types/bar.md"
    hub.write_text(hub.read_text(encoding="utf-8") + "作者补充。\n", encoding="utf-8")
    original = hub.read_bytes()
    update_gallery(config, status="approved", version=2)
    ingest_figure(config, ENTRY_ID)
    assert read_page(page)[0]["status"] == "archived"
    assert read_page(page)[0]["archived_from"] == "pending_signoff"
    assert hub.read_bytes() == original


def test_missing_entry_exits_one_without_traceback(workspace):
    _, config_path = workspace
    result = run_cli(config_path, "ingest-figure", "missing__figure")
    assert result.returncode == 1
    assert "不存在" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("change, message", [
    ({"id": "wrong"}, "id"),
])
def test_invalid_gallery_entry_rejected_before_writing(workspace, change, message):
    config, _ = workspace
    update_gallery(config, **change)
    with pytest.raises(WikiError, match=message):
        ingest_figure(config, ENTRY_ID)
    assert not list((config.wiki_root / "layouts").iterdir())


@pytest.mark.parametrize("available", ["thumb.png", "output/replica.png", "source/fig01.png", None])
def test_thumbnail_priority_and_missing_source(workspace, available):
    config, _ = workspace
    entry = config.gallery_root / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f"
    candidates = [entry / "thumb.png", entry / "output/replica.png", entry / "source/fig01.png"]
    for index, path in enumerate(candidates):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes([index]))
    for path in candidates:
        if available is not None and path == entry / available:
            break
        path.unlink()
    if available is None:
        with pytest.raises(WikiError, match="缩略图"):
            ingest_figure(config, ENTRY_ID)
    else:
        ingest_figure(config, ENTRY_ID)
        assert (config.wiki_root / f"layouts/{ENTRY_ID}/thumb.png").read_bytes() == (entry / available).read_bytes()


def test_all_ingests_multiple_entries_with_one_commit_and_ignores_history(workspace):
    config, config_path = workspace
    post = config.gallery_root / "2026-08-17-shap-feature-mechanism"
    second = post / "figures/fig02"
    shutil.copytree(post / "figures/fig01-shap-a-f", second)
    path = second / "meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["id"] = "2026-08-17-shap-feature-mechanism__fig02"
    path.write_text(json.dumps(meta), encoding="utf-8")
    history = post / "figures/fig01-shap-a-f/history/v1"
    history.mkdir(parents=True)
    (history / "meta.json").write_text("invalid JSON", encoding="utf-8")
    result = run_cli(config_path, "ingest-figure", "--all")
    assert result.returncode == 0, result.stderr
    assert len(list((config.wiki_root / "layouts").glob("*.md"))) == 2
    assert commit_count(config.wiki_root) == 2


def test_reingest_updates_panel_map_and_keeps_wiki_title(ingested):
    config, _ = ingested
    path = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(path)
    meta["title"] = "作者标题"
    meta["chart_types"] = ["beeswarm"]
    write_page(path, meta, body)
    entry = config.gallery_root / meta["gallery_entry"] / "meta.json"
    gallery = json.loads(entry.read_text(encoding="utf-8"))
    gallery["language"] = "r"
    gallery["figure"]["panel_map"] = {"A": "scatter"}
    gallery["post"]["title"] = "新的原帖标题"
    entry.write_text(json.dumps(gallery), encoding="utf-8")
    ingest_figure(config, ENTRY_ID)
    updated, updated_body = read_page(path)
    assert updated["language"] == "r"
    assert updated["title"] == "作者标题"
    assert updated["chart_types"] == ["scatter"]
    assert updated["panels"] == {"A": "scatter"}
    assert "新的原帖标题" in get_block(updated_body, "facts")
    assert "[[chart-types/scatter]]" in updated_body


@pytest.mark.parametrize("status", ["pending_template", "ready"])
def test_same_version_approved_preserves_template_state(workspace, status):
    config, _ = workspace
    update_gallery(config, status="approved")
    ingest_figure(config, ENTRY_ID)
    path = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(path)
    assert meta["status"] == "pending_template"
    meta["status"] = status
    write_page(path, meta, body)
    ingest_figure(config, ENTRY_ID)
    assert read_page(path)[0]["status"] == status


def test_unchanged_reingest_does_not_add_commit(ingested):
    config, _ = ingested
    log = (config.wiki_root / "log.md").read_bytes()
    ingest_figure(config, ENTRY_ID)
    assert commit_count(config.wiki_root) == 2
    assert (config.wiki_root / "log.md").read_bytes() == log

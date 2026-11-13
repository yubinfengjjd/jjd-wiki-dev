import pytest

from rwiki.errors import WikiError
from rwiki.pages import get_block, read_page, set_block, write_page


def test_page_roundtrip_preserves_unicode_order_and_body(tmp_path):
    path = tmp_path / "中文.md"
    meta = {"title": "特征重要性", "type": "chart-type", "slug": "shap"}
    body = "# 中文\n\n正文\n"
    write_page(path, meta, body)
    assert read_page(path) == (meta, body)
    raw = path.read_bytes()
    assert b"\r" not in raw
    assert raw.decode("utf-8").startswith("---\ntitle: 特征重要性\ntype: chart-type\nslug: shap\n---\n")


@pytest.mark.parametrize("text", ["# 没有 frontmatter\n", "---\ntitle: [\n---\n", "---\n- 列表\n---\n"])
def test_invalid_frontmatter_is_wiki_error(tmp_path, text):
    path = tmp_path / "bad.md"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(WikiError, match="frontmatter"):
        read_page(path)


def test_blocks_replace_only_between_markers():
    body = "前\n<!-- user:start -->\n原备注\n<!-- user:end -->\n后\n"
    assert get_block(body, "user") == "\n原备注\n"
    assert set_block(body, "user", "\n新备注\n") == (
        "前\n<!-- user:start -->\n新备注\n<!-- user:end -->\n后\n"
    )
    facts = "<!-- facts:start --><!-- facts:end -->"
    assert get_block(set_block(facts, "facts", "事实"), "facts") == "事实"


@pytest.mark.parametrize("body", [
    "<!-- user:start -->",
    "<!-- user:start --><!-- user:start --><!-- user:end -->",
    "<!-- user:end --><!-- user:start -->",
])
def test_invalid_markers_rejected_on_read_and_write(body):
    with pytest.raises(WikiError, match="user"):
        get_block(body, "user")
    with pytest.raises(WikiError, match="user"):
        set_block(body, "user", "新内容")

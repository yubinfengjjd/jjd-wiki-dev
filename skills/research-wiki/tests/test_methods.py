import sys
from types import SimpleNamespace

import pytest

from rwiki.errors import WikiError
from rwiki.pages import get_block, read_page, write_page
from rwiki.store import init


@pytest.fixture
def method_config(tmp_path):
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text('{"scenarios": {}}', encoding="utf-8")
    config = SimpleNamespace(wiki_root=tmp_path / "wiki", gallery_root=tmp_path / "gallery",
                             taxonomy=taxonomy, python_exe=sys.executable,
                             rscript_exe="unused", port=8765)
    init(config)
    return config


@pytest.mark.parametrize("kind", ["project", "repo", "post", "written"])
def test_scaffold_creates_note_with_only_optional_source(method_config, tmp_path, kind):
    from rwiki.methods import scaffold_method

    source = tmp_path / "analysis"
    source.mkdir()
    (source / "helper.py").write_text("ORIGINAL = 1\n", encoding="utf-8")
    kwargs = {"from_path": source}
    if kind == "repo":
        kwargs.update(url="https://example.invalid/repo", commit="abc123")
    elif kind == "post":
        gallery = method_config.gallery_root / "post/figures/fig/original_code"
        gallery.mkdir(parents=True)
        (gallery / "helper.py").write_text("ORIGINAL = 1\n", encoding="utf-8")
        kwargs = {"from_entry": "post__fig"}
    elif kind == "written":
        kwargs = {"written": True}
    scaffold_method(method_config, "rank-a", "排名", "none", **kwargs)
    target = method_config.wiki_root / "methods/rank-a"
    meta, body = read_page(target.with_suffix(".md"))
    assert meta["status"] == "draft" and meta["source"]["kind"] == kind
    assert meta["inputs"] == meta["outputs"] == meta["tags"] == []
    assert "language" not in meta and "scenarios" not in meta
    assert not any((target / name).exists() for name in ("method.json", "params.yaml", "example", "code"))
    if kind == "written":
        assert not target.exists()
    else:
        assert (target / "source/helper.py").read_text(encoding="utf-8") == "ORIGINAL = 1\n"
    for heading in ("用途", "适用", "不适用", "输入", "怎么做", "代码", "输出", "使用记录"):
        assert f"## {heading}\n\n" in body
    assert get_block(body, "user").strip() == ""
    with pytest.raises(WikiError, match="已存在"):
        scaffold_method(method_config, "rank-a", "重复", "MIT", **kwargs)


def test_scaffold_copies_single_source_file(method_config, tmp_path):
    from rwiki.methods import scaffold_method

    source = tmp_path / "analysis.py"
    source.write_bytes(b"# reference\n")
    scaffold_method(method_config, "single", "单文件", "MIT", from_path=source)
    assert (method_config.wiki_root / "methods/single/source/analysis.py").read_bytes() == source.read_bytes()


def test_confirm_accepts_draft_note_without_code_or_execution_assets(method_config):
    from rwiki.methods import confirm_method, scaffold_method

    scaffold_method(method_config, "written", "笔记", "none", written=True)
    page = method_config.wiki_root / "methods/written.md"
    meta, body = read_page(page)
    meta["cite"] = ["Official documentation"]
    write_page(page, meta, body)
    from conftest import complete_sections
    complete_sections(page)
    confirm_method(method_config, "written")
    assert read_page(page)[0]["status"] == "ready"
    with pytest.raises(WikiError, match="draft"):
        confirm_method(method_config, "written")


def test_method_module_no_longer_exposes_execution_helpers():
    from rwiki import methods

    for name in ("run_method", "verify_method", "load_method", "load_params",
                 "check_dependencies", "check_outputs"):
        assert not hasattr(methods, name)

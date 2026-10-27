"""worktree 中限制性目录经联接指向主检出：快照与 spec 入口不误报越出，安全边界不变。"""
import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import write_interface
from rwiki.acceptance import snapshot
from rwiki.confine import confined
from rwiki.errors import WikiError
from rwiki.pages import read_page, write_page
from rwiki.spec import load_spec

pytestmark = pytest.mark.skipif(os.name != "nt", reason="目录联接只在 Windows 上")

BODY = "# 页\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n\n说明\n\n<!-- user:start -->\n<!-- user:end -->\n"


def junction(dst: Path, src: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], check=True, capture_output=True)


def method(wiki: Path, slug: str, license: str, files: dict | None) -> Path:
    page = wiki / "methods" / f"{slug}.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    write_page(page, {"type": "method", "id": slug, "title": slug, "status": "ready", "license": license}, BODY)
    for name, text in (files or {}).items():
        target = wiki / "methods" / slug / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return page


@pytest.fixture
def checkouts(tmp_path):
    """主检出与 worktree 两份 知识库；worktree 中的限制性 source/ 是指向主检出的联接。"""
    main, work = tmp_path / "main" / "知识库", tmp_path / "work" / "知识库"
    files = {"a.R": "x <- 1\n", "sub/b.R": "y <- 2\n"}
    for wiki in (main, work):
        method(wiki, "gpl", "GPL-3", files if wiki == main else None)
    junction(work / "methods/gpl/source", main / "methods/gpl/source")
    return main, work


def test_snapshot_same_through_restricted_junction(checkouts):
    main, work = checkouts
    assert snapshot(work / "methods/gpl.md") == snapshot(main / "methods/gpl.md")
    # 联接内文件确实计入：没有源码时快照不同。
    empty = method(main.parent.parent / "empty" / "知识库", "gpl", "GPL-3", None)
    assert snapshot(empty) != snapshot(main / "methods/gpl.md")


def test_non_restricted_junction_excluded(checkouts, tmp_path):
    main, work = checkouts
    # MIT 许可：source/ 不在 restricted_dirs，联接内容不计入。
    method(main, "mit", "MIT", {"a.R": "x <- 1\n"})
    method(work, "mit", "MIT", None)
    junction(work / "methods/mit/source", main / "methods/mit/source")
    bare = method(tmp_path / "bare" / "知识库", "mit", "MIT", None)
    assert snapshot(work / "methods/mit.md") == snapshot(bare)
    assert not confined(work / "methods/mit/source/a.R", work / "methods/mit", work)


def test_restricted_junction_to_other_path_excluded(checkouts, tmp_path):
    main, work = checkouts
    # 位置在 restricted_dirs 中，但指向另一页面的目录：不是“另一检出同一相对路径”。
    method(main, "other", "GPL-3", {"a.R": "z <- 3\n"})
    method(work, "gpl2", "GPL-3", None)
    junction(work / "methods/gpl2/source", main / "methods/other/source")
    assert not confined(work / "methods/gpl2/source/a.R", work / "methods/gpl2", work)
    # 指向任意外部目录同样排除。
    outside = tmp_path / "outside" / "source"
    outside.mkdir(parents=True)
    (outside / "a.R").write_text("w <- 4\n", encoding="utf-8")
    method(work, "gpl3", "GPL-3", None)
    junction(work / "methods/gpl3/source", outside)
    assert not confined(work / "methods/gpl3/source/a.R", work / "methods/gpl3", work)
    assert snapshot(work / "methods/gpl3.md") == snapshot(method(tmp_path / "e" / "知识库", "gpl3", "GPL-3", None))


def test_nested_link_inside_junction_excluded(checkouts, tmp_path):
    main, work = checkouts
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.R").write_text("s <- 1\n", encoding="utf-8")
    junction(main / "methods/gpl/source/ext", outside)
    assert confined(work / "methods/gpl/source/a.R", work / "methods/gpl", work)
    assert not confined(work / "methods/gpl/source/ext/secret.R", work / "methods/gpl", work)
    assert not confined(main / "methods/gpl/source/ext/secret.R", main / "methods/gpl", main)
    assert snapshot(work / "methods/gpl.md") == snapshot(main / "methods/gpl.md")


def test_file_symlink_to_outside_excluded(tmp_path):
    wiki = tmp_path / "知识库"
    page = method(wiki, "gpl", "GPL-3", {"a.R": "x <- 1\n"})
    before = snapshot(page)
    outside = tmp_path / "secret.R"
    outside.write_text("s <- 1\n", encoding="utf-8")
    try:
        os.symlink(outside, wiki / "methods/gpl/source/link.R")
    except OSError:
        pytest.skip("本机无权创建符号链接")
    assert not confined(wiki / "methods/gpl/source/link.R", wiki / "methods/gpl", wiki)
    assert snapshot(page) == before


def template(wiki: Path, license: str, with_code: bool) -> Path:
    target = wiki / "templates" / "t"
    target.mkdir(parents=True, exist_ok=True)
    write_interface(wiki, "values", {"value": {"type": "float", "description": "数值"}})
    (target / "spec.json").write_text(json.dumps({
        "entry": "code/render.R", "language": "r", "style": {},
        "tables": {"values": {"interface": "values", "description": "数值"}}}), encoding="utf-8")
    write_page(wiki / "templates/t.md", {"type": "template", "id": "t", "title": "t", "status": "ready",
                                         "license": license}, BODY)
    if with_code:
        (target / "code").mkdir()
        (target / "code/render.R").write_text("plot(1)\n", encoding="utf-8")
    return target


def test_spec_entry_through_restricted_junction(tmp_path):
    main, work = tmp_path / "main" / "知识库", tmp_path / "work" / "知识库"
    template(main, "CC-BY-NC-SA-4.0", True)
    target = template(work, "CC-BY-NC-SA-4.0", False)
    junction(target / "code", main / "templates/t/code")
    assert load_spec(target)["entry"] == "code/render.R"


def test_spec_entry_through_outside_junction_rejected(tmp_path):
    outside = tmp_path / "outside" / "code"
    outside.mkdir(parents=True)
    (outside / "render.R").write_text("plot(1)\n", encoding="utf-8")
    for license in ("CC-BY-NC-SA-4.0", "MIT"):
        wiki = tmp_path / license / "知识库"
        target = template(wiki, license, False)
        junction(target / "code", outside)
        with pytest.raises(WikiError, match="越出模板目录"):
            load_spec(target)


@pytest.mark.local
@pytest.mark.parametrize("page", ["methods/scp-local-source.md", "templates/figureya-6rhrsv2--forest.md"])
def test_main_checkout_snapshot_unchanged(vault_root, page):
    path = vault_root / "知识库" / page
    meta, _ = read_page(path)
    assert meta["status"] == "ready"
    receipt = json.loads((path.with_suffix("") / "acceptance.json").read_text(encoding="utf-8"))
    assert snapshot(path) == receipt["snapshot"]

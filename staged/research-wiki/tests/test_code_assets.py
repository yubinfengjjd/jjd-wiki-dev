import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from rwiki import code_assets
from rwiki.errors import WikiError
from rwiki.pages import write_page


@pytest.fixture
def code_config(tmp_path):
    config = SimpleNamespace(wiki_root=tmp_path / "wiki", gallery_root=tmp_path / "gallery")
    config.wiki_root.mkdir()
    config.gallery_root.mkdir()
    return config


def page(config, kind="methods", entry_id="demo", **meta):
    target = config.wiki_root / kind / f"{entry_id}.md"
    write_page(target, {"type": kind[:-1], "id": entry_id, "title": "Fixture",
                        "status": "draft", **meta}, "# Fixture\n")
    return target.with_suffix("")


def asset(root, name, content):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def manifest(root, entries):
    return asset(root, "code-manifest.json", json.dumps({"files": entries}).encode("utf-8"))


def gallery(config, entry_id="source", **meta):
    root = config.gallery_root / "post" / "figures" / entry_id
    asset(root, "meta.json", json.dumps({"id": entry_id, "language": "python",
          "code_provenance": "reconstructed", "original_code_provenance": "archived_only",
          **meta}).encode("utf-8"))
    page(config, "layouts", entry_id, gallery_entry=f"post/figures/{entry_id}",
         panels={"A": "scatter"})
    return root


def test_multifile_native_assets_keep_variants_languages_hashes_and_bytes(code_config):
    root = page(code_config)
    blobs = {"source/main.py": b"\xef\xbb\xbfprint('original')\r\n",
             "source/lib/model.R": b"fit <- function(x) mean(x)\n",
             "code/main.py": b"def fit(x):\n    return x\n",
             "code/settings.yaml": b"seed: 7\n"}
    for name, content in blobs.items():
        asset(root, name, content)
    for name in ("source/article.html", "source/source.md", "source/README.md",
                 "code/__pycache__/main.pyc", "code/.git/config", "code/.venv/bad.py"):
        asset(root, name, b"not an asset")
    listing = code_assets.code_files(code_config, "methods/demo.md")
    found = {row["path"]: row for row in listing["files"]}
    assert set(found) == set(blobs)
    assert found["source/lib/model.R"]["language"] == "r"
    assert found["code/settings.yaml"]["language"] == "yaml"
    for name, content in blobs.items():
        row = found[name]
        variant = "original" if name.startswith("source/") else "reusable"
        assert row["variant"] == variant
        assert row["sha256"] == hashlib.sha256(content).hexdigest()
        assert row["size"] == len(content) and row["text"] is True
        assert row["verification"]["state"] == "unknown"
        assert code_assets.code_file(code_config, "methods/demo.md", variant, name).read_bytes() == content
    read = code_assets.read_code(code_config, "methods/demo.md", "original", "source/main.py")
    assert read["text"] == "print('original')\r\n" and read["encoding"] == "utf-8-sig"
    assert read["sha256"] == hashlib.sha256(blobs["source/main.py"]).hexdigest()


@pytest.mark.parametrize("bad", ["../source/main.py", "source/../main.py", "/source/main.py",
                                  "C:/secret.py", "C:secret.py", "source\\main.py",
                                  "//host/share.py", "source/main.py:stream", "source/./main.py"])
def test_file_lookup_rejects_paths_outside_enumerated_asset_names(code_config, bad):
    root = page(code_config)
    asset(root, "source/main.py", b"safe\n")
    with pytest.raises(WikiError):
        code_assets.code_file(code_config, "methods/demo.md", "original", bad)


@pytest.mark.parametrize("bad", ["methods/missing.md", "interfaces/demo.md", "methods/demo.py",
                                  "../methods/demo.md", "methods/x/../demo.md", "C:/demo.md",
                                  "methods\\demo.md", "/methods/demo.md"])
def test_only_actual_visual_pages_are_accepted(code_config, bad):
    page(code_config)
    with pytest.raises(WikiError):
        code_assets.code_files(code_config, bad)


def test_variant_cannot_read_another_version_or_unlisted_wiki_asset(code_config):
    root = page(code_config)
    asset(root, "source/main.py", b"source\n")
    asset(root, "example/private.py", b"not code-root\n")
    for variant, name in (("reusable", "source/main.py"), ("other", "source/main.py"),
                          ("original", "example/private.py")):
        with pytest.raises(WikiError):
            code_assets.read_code(code_config, "methods/demo.md", variant, name)


def test_no_assets_is_clear_and_does_not_fabricate_code(code_config):
    root = page(code_config, source={"kind": "written"})
    asset(root, "source/README.md", b"Only prose")
    result = code_assets.code_files(code_config, "methods/demo.md")
    assert result["files"] == [] and "暂无" in result["note"]
    assert not (root / "code").exists()


def test_unknown_encoding_and_binary_are_download_only(code_config):
    root = page(code_config)
    asset(root, "source/unknown.R", b"# \x80\xff\n")
    asset(root, "source/object.bin", b"\x00\x01BIN\x00")
    rows = code_assets.code_files(code_config, "methods/demo.md")["files"]
    assert len(rows) == 2 and all(row["text"] is False for row in rows)
    for name in ("source/unknown.R", "source/object.bin"):
        result = code_assets.read_code(code_config, "methods/demo.md", "original", name)
        assert result["text"] is None and result["encoding"] is None
        assert "下载" in result["note"]
        assert code_assets.code_file(code_config, "methods/demo.md", "original", name).read_bytes() == (root / name).read_bytes()


def test_gb18030_requires_explicit_existing_file_metadata(code_config):
    root = page(code_config)
    raw = "# 中文原始代码\nprint(1)\n".encode("gb18030")
    asset(root, "source/main.py", raw)
    assert code_assets.read_code(code_config, "methods/demo.md", "original", "source/main.py")["text"] is None
    manifest(root, [{"variant": "original", "path": "source/main.py", "encoding": "gb18030"}])
    read = code_assets.read_code(code_config, "methods/demo.md", "original", "source/main.py")
    assert read["encoding"] == "gb18030" and read["text"].startswith("# 中文原始代码")
    assert (root / "source/main.py").read_bytes() == raw


def test_python_declared_gb18030_can_be_read_without_guessing(code_config):
    root = page(code_config)
    raw = "# coding: gb18030\n# 中文\n".encode("gb18030")
    asset(root, "source/main.py", raw)
    read = code_assets.read_code(code_config, "methods/demo.md", "original", "source/main.py")
    assert read["encoding"] == "gb18030" and "中文" in read["text"]


def test_python_encoding_must_be_a_comment_declaration(code_config):
    root = page(code_config)
    asset(root, "source/main.py", 'description = "coding: gb18030"\n# 中文\n'.encode("gb18030"))
    read = code_assets.read_code(code_config, "methods/demo.md", "original", "source/main.py")
    assert read["text"] is None and read["encoding"] is None


def test_notebook_and_html_are_returned_as_raw_text_without_execution(code_config, tmp_path):
    root = page(code_config)
    marker = tmp_path / "executed"
    notebook = json.dumps({"cells": [{"cell_type": "code", "source": [f"open({str(marker)!r}, 'w')"],
                                     "outputs": [{"data": {"text/html": "<script>bad()</script>"}}]}]})
    asset(root, "code/example.ipynb", notebook.encode("utf-8"))
    asset(root, "code/snippet.html", b"<script>window.bad()</script>")
    assert code_assets.read_code(code_config, "methods/demo.md", "reusable", "code/example.ipynb")["text"] == notebook
    assert code_assets.read_code(code_config, "methods/demo.md", "reusable", "code/snippet.html")["text"] == "<script>window.bad()</script>"
    assert not marker.exists()


def test_large_text_keeps_download_available_without_unbounded_preview(code_config):
    root = page(code_config)
    raw = b"# large\n" * (300 * 1024)
    asset(root, "source/large.py", raw)
    read = code_assets.read_code(code_config, "methods/demo.md", "original", "source/large.py")
    assert read["text"] is None and "下载" in read["note"]
    assert read["size"] == len(raw)
    assert code_assets.code_file(code_config, "methods/demo.md", "original", "source/large.py").read_bytes() == raw


def test_manifest_enriches_only_existing_files_without_trusting_hash_or_redirect(code_config, tmp_path):
    root = page(code_config)
    raw = b"fit <- function(x) x\n"
    asset(root, "source/model.R", raw)
    secret = asset(tmp_path, "secret.py", b"private\n")
    manifest(root, [
        {"variant": "original", "path": "source/model.R", "sha256": "false",
         "source": "Collected snippet", "verification": {"state": "not_run", "scope": "archive"}},
        {"variant": "original", "path": str(secret)},
        {"variant": "original", "path": "source/missing.py", "file": str(secret)},
        {"variant": "original", "path": "../secret.py"},
    ])
    listing = code_assets.code_files(code_config, "methods/demo.md")["files"]
    assert len(listing) == 1 and listing[0]["path"] == "source/model.R"
    assert listing[0]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert listing[0]["verification"]["state"] == "not_run"
    assert "Collected snippet" in listing[0]["source"]


def test_layout_gallery_replica_and_historical_reconstruction_are_labelled_generated(code_config):
    root = gallery(code_config, original_code_provenance="example_not_target")
    asset(root, "original_code/original.R", b"x <- 1\n")
    asset(root, "original_code/previous_reconstruction.py", b"x = 2\n")
    asset(root, "code/replica.py", b"x = 3\n")
    manifest(root, [{"variant": "reusable", "path": "code/replica.py", "source": "author original"}])
    rows = {row["path"]: row for row in code_assets.code_files(code_config, "layouts/source.md")["files"]}
    assert rows["code/replica.py"]["variant"] == "reusable"
    assert "生成" in rows["code/replica.py"]["source"] and "非作者原版" in rows["code/replica.py"]["source"]
    assert "未验证" in rows["code/replica.py"]["source"]
    assert "非目标图" in rows["original_code/original.R"]["source"]
    assert "非作者原版" in rows["original_code/previous_reconstruction.py"]["source"]


def test_template_uses_own_versions_and_existing_origin_originals_without_copying(code_config):
    origin = gallery(code_config)
    asset(origin, "original_code/native.R", b"x <- 1\n")
    asset(origin, "code/replica.py", b"origin replica\n")
    root = page(code_config, "templates", "panel", layouts=["source"])
    asset(root, "source/saved.py", b"saved\n")
    asset(root, "code/panel.py", b"adapted\n")
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    rows = code_assets.code_files(code_config, "templates/panel.md")["files"]
    assert {(row["variant"], row["path"]) for row in rows} == {
        ("original", "source/saved.py"), ("reusable", "code/panel.py"),
        ("original", "gallery/source/original_code/native.R")}
    assert code_assets.code_file(code_config, "templates/panel.md", "original",
                                 "gallery/source/original_code/native.R").read_bytes() == b"x <- 1\n"
    assert sorted(path.relative_to(root).as_posix() for path in root.rglob("*")) == before


def test_legacy_manifest_preserves_original_fence_metadata_but_does_not_add_files(code_config):
    root = page(code_config)
    asset(root, "source/block.txt", b"print(1)\n")
    asset(root, "source/manifest.json", json.dumps({"blocks": [
        {"file": "block.txt", "original_fence_language": "javascript", "executed": False},
        {"file": "../not-an-asset.py", "original_language": "python"}]}).encode("utf-8"))
    row, = code_assets.code_files(code_config, "methods/demo.md")["files"]
    assert row["language"] == "javascript"
    assert row["verification"]["state"] == "not_run"
    assert "fence" in row["source"]


def make_symlink(link, target, is_directory=False):
    try:
        link.symlink_to(target, target_is_directory=is_directory)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"host cannot create symlinks: {error}")


def make_directory_link(link, target):
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        if os.name != "nt":
            pytest.skip(f"host cannot create directory links: {error}")
        result = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
                                capture_output=True, text=True, errors="replace")
        if result.returncode:
            pytest.skip(f"host cannot create directory junctions: {result.returncode}")


def test_directory_redirects_cannot_expose_siblings_or_host_files(code_config, tmp_path):
    root = page(code_config)
    outside = asset(tmp_path, "outside/secret.py", b"private\n")
    (root / "source").mkdir(parents=True)
    make_directory_link(root / "source/linked", outside.parent)
    make_directory_link(root / "code", outside.parent)
    assert code_assets.code_files(code_config, "methods/demo.md")["files"] == []
    for variant, name in (("original", "source/linked/secret.py"), ("reusable", "code/secret.py")):
        with pytest.raises(WikiError):
            code_assets.code_file(code_config, "methods/demo.md", variant, name)


def test_gallery_directory_redirect_cannot_scan_another_root(code_config, tmp_path):
    root = gallery(code_config)
    outside = asset(tmp_path, "outside/native.py", b"private\n")
    make_directory_link(root / "original_code", outside.parent)
    assert code_assets.code_files(code_config, "layouts/source.md")["files"] == []


def test_symlinked_assets_and_asset_roots_cannot_escape_entry(code_config, tmp_path):
    root = page(code_config)
    (root / "source").mkdir(parents=True)
    outside = asset(tmp_path, "outside/secret.py", b"private\n")
    make_symlink(root / "source/link.py", outside)
    make_symlink(root / "code", outside.parent, is_directory=True)
    assert code_assets.code_files(code_config, "methods/demo.md")["files"] == []
    for variant, name in (("original", "source/link.py"), ("reusable", "code/secret.py")):
        with pytest.raises(WikiError):
            code_assets.code_file(code_config, "methods/demo.md", variant, name)


def test_symlinked_page_and_manifest_cannot_redirect_to_host(code_config, tmp_path):
    root = page(code_config)
    asset(root, "source/safe.py", b"safe\n")
    outside_page = asset(tmp_path, "outside.md", b"---\ntype: method\nid: outside\n---\n# Outside\n")
    make_symlink(code_config.wiki_root / "methods/outside.md", outside_page)
    outside_manifest = asset(tmp_path, "outside.json", b'{"files": []}')
    make_symlink(root / "code-manifest.json", outside_manifest)
    with pytest.raises(WikiError):
        code_assets.code_files(code_config, "methods/outside.md")
    assert len(code_assets.code_files(code_config, "methods/demo.md")["files"]) == 1


@pytest.mark.parametrize("entry", ["../outside", "C:/outside", "post\\figures\\outside"])
def test_gallery_metadata_cannot_redirect_outside_gallery(code_config, entry):
    page(code_config, "layouts", "bad", gallery_entry=entry, panels={"A": "scatter"})
    assert code_assets.code_files(code_config, "layouts/bad.md")["files"] == []

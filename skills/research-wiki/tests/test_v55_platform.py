"""Tests for Research Wiki v5.5 Three-in-One Platform Upgrade: caching, thumbnails/ETag, and 1-click active template deletion."""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from PIL import Image

from conftest import write_config
from rwiki import curation
from rwiki.config import Config
from rwiki.deletion import delete_archived, prepare
from rwiki.pages import read_page, set_block, write_page
from rwiki.project_tracker import add_project_step
from rwiki.read_cache import invalidate_cache
from rwiki.server import create_app
from rwiki.store import init, save
from rwiki.verification import clear_digest_cache, digest


def _png_bytes(width: int = 1200, height: int = 800, color=(30, 120, 180)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color)
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_v55_wiki(tmp_path: Path, name: str = "wiki_a", *, title_prefix: str = "A") -> Config:
    base = tmp_path / name
    wiki = base / "wiki"
    gallery = base / "gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    taxonomy = base / "taxonomy.json"
    taxonomy.write_text(json.dumps({"scenarios": {"single-cell": {"label": "单细胞分析"}}}), encoding="utf-8")
    cfg = Config(
        wiki,
        gallery,
        taxonomy,
        Path(sys.executable),
        Path("Rscript"),
        8765,
        work_root=base / "work",
    )
    init(cfg)
    write_config(base / "config.json", wiki)

    write_page(
        wiki / "methods/cell-type-annotation.md",
        {
            "type": "method",
            "id": "cell-type-annotation",
            "title": f"{title_prefix}-细胞类型注释",
            "status": "ready",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test 2026"],
            "favorite": False,
            "method_kind": "analysis",
            "purposes": ["注释与参考映射"],
            "summary": "注释方法。",
            "data_contract": {"input": "counts", "output": "cells"},
            "figure_relations": [
                {
                    "figure": "templates/tpl-default",
                    "compatibility": "adaptable",
                    "reason": "default UMAP style",
                    "prerequisites": [],
                    "adaptation": "export csv",
                    "evidence": ["methods/cell-type-annotation.md#输出"],
                    "verification": {"state": "not_run", "scope": "test", "evidence": []},
                },
                {
                    "figure": "templates/tpl-variant",
                    "compatibility": "adaptable",
                    "reason": "variant UMAP style",
                    "prerequisites": [],
                    "adaptation": "export csv",
                    "evidence": ["methods/cell-type-annotation.md#输出"],
                    "verification": {"state": "not_run", "scope": "test", "evidence": []},
                },
            ],
            "next_steps": [
                {
                    "branch_id": "b1",
                    "direction": "细胞类型 UMAP 展示",
                    "when": "注释完成后",
                    "analysis_templates": [],
                    "intermediate_interface": "",
                    "viz_templates": ["tpl-default", "tpl-variant"],
                }
            ],
        },
        "# 细胞类型注释\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    for tid, tier, jstyle in (
        ("tpl-default", "default", "Standard"),
        ("tpl-variant", "variant", "Cancer Discovery"),
    ):
        write_page(
            wiki / f"templates/{tid}.md",
            {
                "type": "template",
                "id": tid,
                "title": f"{title_prefix}-{tid}",
                "status": "ready",
                "layouts": [],
                "sources": ["methods/cell-type-annotation"],
                "panels": [],
                "language": "python",
                "primary_method": "cell-type-annotation",
                "style_tier": tier,
                "journal_style": jstyle,
                "tags": ["single-cell"],
                "chart_types": ["umap"],
                "favorite": False,
            },
            f"# {title_prefix}-{tid}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n测试。\n\n<!-- user:start -->\n<!-- user:end -->\n",
        )
        tdir = wiki / f"templates/{tid}"
        (tdir / "code").mkdir(parents=True, exist_ok=True)
        (tdir / "code/render.py").write_text("print('ok')\n", encoding="utf-8")
        (tdir / "preview.png").write_bytes(_png_bytes(1200, 800))
        (tdir / "spec.json").write_text(
            json.dumps({
                "entry": "code/render.py",
                "language": "python",
                "tables": {"cells": {"interface": None, "description": "cells", "columns": {"cell_id": {"type": "str"}}}},
                "style": {},
            }),
            encoding="utf-8",
        )

    write_page(
        wiki / "scenarios/pb.md",
        {
            "type": "scenario",
            "id": "pb",
            "title": f"{title_prefix}-Playbook",
            "picks": [{"id": "templates/tpl-default"}, {"id": "templates/tpl-variant"}],
            "steps": [
                {
                    "id": "s1",
                    "title": "UMAP",
                    "method_id": "cell-type-annotation",
                    "templates": ["templates/tpl-default", "templates/tpl-variant"],
                    "viz_templates": ["tpl-default", "tpl-variant"],
                    "next_steps": [],
                }
            ],
        },
        "# Playbook\n\n参考 [[templates/tpl-default]]。\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    wf_dir = wiki / "methods/wf-paper"
    wf_dir.mkdir(parents=True, exist_ok=True)
    write_page(
        wiki / "methods/wf-paper.md",
        {
            "type": "method",
            "id": "wf-paper",
            "title": f"{title_prefix}-论文流程",
            "status": "draft",
            "method_kind": "workflow",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test 2026"],
            "favorite": False,
        },
        "# 论文流程\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    (wf_dir / "panel-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "paper_id": "2026-test",
                "gallery_entry": "gal-1",
                "panels": [
                    {
                        "panel_key": "fig01/A",
                        "figure": "Fig. 1",
                        "panel": "1A",
                        "evidence_tier": "local_recompute",
                        "template_id": "tpl-default",
                        "extra_templates": ["tpl-variant"],
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    gdir = gallery / "gal-1/figures"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "fig01_replica.png").write_bytes(_png_bytes(1400, 900, (180, 60, 40)))
    (gallery / "gal-1/meta.json").write_text(
        json.dumps({"slug": "gal-1", "workflow_id": "wf-paper", "figures": [{"slug": "fig01", "replica": "figures/fig01_replica.png"}]}),
        encoding="utf-8",
    )
    save(cfg, f"init {name}")
    return cfg


def test_digest_cache_hits_and_invalidates_on_file_change(tmp_path: Path, monkeypatch):
    clear_digest_cache()
    target = tmp_path / "sample.bin"
    target.write_bytes(b"hello-v55")
    first = digest(target)

    # Patch Path.open to prove second digest() hits cache without disk read.
    real_open = Path.open

    def fail_open(self, *args, **kwargs):
        if self.resolve() == target.resolve():
            raise AssertionError("digest() should have hit cache without opening file")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_open)
    assert digest(target) == first

    # Restore open, mutate size/mtime, and confirm recomputation.
    monkeypatch.setattr(Path, "open", real_open)
    target.write_bytes(b"hello-v55-updated-content")
    second = digest(target)
    assert second != first


def test_vault_cache_multi_root_isolation_and_write_invalidation(tmp_path: Path):
    invalidate_cache()
    cfg_a = _make_v55_wiki(tmp_path, "root_a", title_prefix="Alpha")
    cfg_b = _make_v55_wiki(tmp_path, "root_b", title_prefix="Beta")

    with TestClient(create_app(cfg_a)) as client_a, TestClient(create_app(cfg_b)) as client_b:
        pages_a = client_a.get("/api/pages").json()
        pages_b = client_b.get("/api/pages").json()
        assert any(p["meta"]["title"] == "Alpha-tpl-default" for p in pages_a)
        assert not any("Beta-" in p["meta"]["title"] for p in pages_a)
        assert any(p["meta"]["title"] == "Beta-tpl-default" for p in pages_b)
        assert not any("Alpha-" in p["meta"]["title"] for p in pages_b)

        # Write endpoint (favorite) must immediately invalidate cache on root_a only
        r_fav = client_a.post("/api/templates/tpl-default/favorite", json={"value": True})
        assert r_fav.status_code == 200
        pages_a_after = client_a.get("/api/pages").json()
        tpl_a = next(p for p in pages_a_after if p["path"] == "templates/tpl-default.md")
        assert tpl_a["meta"]["favorite"] is True

        # add_project_step must also invalidate cache
        add_project_step(cfg_a, "demo-proj", title="Step 1", templates="tpl-default", commit=True)
        pages_a_proj = client_a.get("/api/pages").json()
        assert any(p["path"] == "projects/demo-proj.md" for p in pages_a_proj)

        # Graph, method-hubs, taxonomy, playbooks, papers all return valid isolated payloads
        assert any(n["title"] == "Alpha-tpl-default" for n in client_a.get("/api/graph").json()["nodes"])
        assert client_a.get("/api/method-taxonomy").json()["total"] == 1
        assert client_a.get("/api/method-hubs").json()["methods"][0]["title"] == "Alpha-细胞类型注释"
        assert client_a.get("/api/playbooks").json()["playbooks"][0]["title"] == "Alpha-Playbook"
        assert client_a.get("/api/papers").json()["papers"][0]["title"] == "Alpha-论文流程"


def test_thumbnail_webp_resize_etag_and_304(tmp_path: Path, monkeypatch):
    cfg = _make_v55_wiki(tmp_path, "thumb_root", title_prefix="Thumb")
    thumb_dir = tmp_path / "thumbs_cache"
    monkeypatch.setenv("RWIKI_THUMB_DIR", str(thumb_dir))

    with TestClient(create_app(cfg)) as client:
        # Original PNG
        full_resp = client.get("/files/wiki/templates/tpl-default/preview.png")
        assert full_resp.status_code == 200
        assert "ETag" in full_resp.headers
        assert full_resp.headers.get("Cache-Control") == "public, max-age=60, must-revalidate"
        with Image.open(io.BytesIO(full_resp.content)) as orig_im:
            assert orig_im.size == (1200, 800)

        # Conditional 304 on original
        cond_full = client.get(
            "/files/wiki/templates/tpl-default/preview.png",
            headers={"If-None-Match": full_resp.headers["ETag"]},
        )
        assert cond_full.status_code == 304

        # On-demand ?w=600 WebP thumbnail on both /files/wiki and /files/gallery
        thumb_resp = client.get("/files/wiki/templates/tpl-default/preview.png?w=600")
        assert thumb_resp.status_code == 200
        assert thumb_resp.headers["content-type"].startswith("image/webp")
        assert thumb_resp.headers["ETag"] != full_resp.headers["ETag"]
        with Image.open(io.BytesIO(thumb_resp.content)) as thumb_im:
            assert thumb_im.width == 600
            assert thumb_im.height == 400
        assert any(thumb_dir.glob("*.webp"))

        # Conditional 304 on thumbnail
        cond_thumb = client.get(
            "/files/wiki/templates/tpl-default/preview.png?w=600",
            headers={"If-None-Match": thumb_resp.headers["ETag"]},
        )
        assert cond_thumb.status_code == 304

        # Gallery thumbnail also works
        gal_thumb = client.get("/files/gallery/gal-1/figures/fig01_replica.png?w=600")
        assert gal_thumb.status_code == 200
        with Image.open(io.BytesIO(gal_thumb.content)) as gim:
            assert gim.width == 600

        # Out-of-bounds width rejected with 422
        assert client.get("/files/wiki/templates/tpl-default/preview.png?w=50").status_code == 422
        assert client.get("/files/wiki/templates/tpl-default/preview.png?w=5000").status_code == 422


def test_allow_active_one_click_template_deletion_and_slot_warning(tmp_path: Path):
    cfg = _make_v55_wiki(tmp_path, "del_root", title_prefix="Del")
    with TestClient(create_app(cfg)) as client:
        # Without allow_active, active template deletion is blocked (409)
        assert client.get("/api/templates/tpl-default/delete-plan").status_code == 409
        # Non-template active item cannot bypass archive even with allow_active=true
        assert client.get("/api/methods/cell-type-annotation/delete-plan?allow_active=true").status_code == 409

        # With allow_active=true, active default template produces slot_default_warning
        plan = client.get("/api/templates/tpl-default/delete-plan?allow_active=true").json()
        assert plan["asset_files"] >= 2
        assert plan["slot_default_warning"] is not None
        assert plan["slot_default_warning"]["recommended_successor"] == "tpl-variant"
        assert "tpl-variant" in plan["slot_default_warning"]["remaining_variants"]

        # Prime read cache first
        assert any(p["path"] == "templates/tpl-default.md" for p in client.get("/api/pages").json())

        # Execute 1-click deletion
        resp = client.post(
            "/api/templates/tpl-default/delete",
            json={"confirmed": True, "revision": plan["revision"], "allow_active": True},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["deleted"] is True
        assert not (cfg.wiki_root / "templates/tpl-default.md").exists()
        assert not (cfg.wiki_root / "templates/tpl-default").exists()

        # Cache must be invalidated immediately
        pages_after = client.get("/api/pages").json()
        assert not any(p["path"] == "templates/tpl-default.md" for p in pages_after)
        assert client.get("/api/page", params={"path": "templates/tpl-default.md"}).status_code == 404

        # References cleaned across method, scenario, and panel-manifest.yaml
        m_meta, _ = read_page(cfg.wiki_root / "methods/cell-type-annotation.md")
        assert [r["figure"] for r in m_meta["figure_relations"]] == ["templates/tpl-variant"]
        assert m_meta["next_steps"][0]["viz_templates"] == ["tpl-variant"]

        pb_meta, pb_body = read_page(cfg.wiki_root / "scenarios/pb.md")
        assert [p["id"] for p in pb_meta["picks"]] == ["templates/tpl-variant"]
        assert pb_meta["steps"][0]["templates"] == ["templates/tpl-variant"]
        assert pb_meta["steps"][0]["viz_templates"] == ["tpl-variant"]
        assert "条目已删除" in pb_body

        manifest = yaml.safe_load((cfg.wiki_root / "methods/wf-paper/panel-manifest.yaml").read_text(encoding="utf-8"))
        assert manifest["panels"][0]["template_id"] is None
        assert manifest["panels"][0]["extra_templates"] == ["tpl-variant"]

        # Author <!-- user --> protection still blocks active template deletion
        p_meth = cfg.wiki_root / "methods/cell-type-annotation.md"
        mm, mb = read_page(p_meth)
        write_page(p_meth, mm, set_block(mb, "user", "\n保留 [[templates/tpl-variant]]\n"))
        blocked = client.get("/api/templates/tpl-variant/delete-plan?allow_active=true")
        assert blocked.status_code == 409 and "作者备注" in blocked.text


def test_vault_cache_bucket_isolation_and_extended_fingerprint(tmp_path: Path):
    import rwiki.read_cache as rc

    invalidate_cache()
    cfg = _make_v55_wiki(tmp_path, "bucket_iso", title_prefix="Iso")

    # Add a recipe to cover recipes/*/preview.png and recipes/*/verify/*
    write_page(
        cfg.wiki_root / "recipes/rec-1.md",
        {
            "type": "recipe",
            "id": "rec-1",
            "title": "配方一",
            "status": "ready",
            "tags": ["single-cell"],
            "language": "python",
            "source": {"id": "figya", "item": "1"},
            "favorite": False,
        },
        "# 配方\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    rec_dir = cfg.wiki_root / "recipes/rec-1"
    (rec_dir / "verify").mkdir(parents=True, exist_ok=True)
    (rec_dir / "preview.png").write_bytes(_png_bytes(200, 200))
    (rec_dir / "verify/verify.json").write_text('{"ok": true}', encoding="utf-8")

    with TestClient(create_app(cfg)) as client:
        assert client.get("/api/pages").status_code == 200
        assert client.get("/api/method-taxonomy").status_code == 200
        assert client.get("/api/playbooks").status_code == 200
        assert client.get("/api/graph").status_code == 200

        # Alternating gallery-aware and wiki-only reads must NOT evict each other
        calls = {"gal": 0, "wiki": 0}

        def build_gal():
            calls["gal"] += 1
            return {"kind": "gal"}

        def build_wiki():
            calls["wiki"] += 1
            return {"kind": "wiki"}

        assert rc.cached_vault_value(cfg.wiki_root, "probe_gal", build_gal, gallery_root=cfg.gallery_root) == {"kind": "gal"}
        assert rc.cached_vault_value(cfg.wiki_root, "probe_wiki", build_wiki, gallery_root=None) == {"kind": "wiki"}
        assert rc.cached_vault_value(cfg.wiki_root, "probe_gal", build_gal, gallery_root=cfg.gallery_root) == {"kind": "gal"}
        assert rc.cached_vault_value(cfg.wiki_root, "probe_wiki", build_wiki, gallery_root=None) == {"kind": "wiki"}
        assert calls == {"gal": 1, "wiki": 1}

        # invalidate_cache(root) clears ALL (root_key, *) buckets
        invalidate_cache(cfg.wiki_root)
        rc.cached_vault_value(cfg.wiki_root, "probe_gal", build_gal, gallery_root=cfg.gallery_root)
        rc.cached_vault_value(cfg.wiki_root, "probe_wiki", build_wiki, gallery_root=None)
        assert calls == {"gal": 2, "wiki": 2}

    # Extended fingerprint tracks methods/*/code/*, methods/*/verify/*, templates/*/runtime.json, recipes/*/preview.png & verify/*
    fp0 = rc.vault_fingerprint(cfg.wiki_root, cfg.gallery_root)
    m_code = cfg.wiki_root / "methods/cell-type-annotation/code/run.py"
    m_code.parent.mkdir(parents=True, exist_ok=True)
    m_code.write_text("print('v1')\n", encoding="utf-8")
    fp1 = rc.vault_fingerprint(cfg.wiki_root, cfg.gallery_root)
    assert fp1 != fp0

    m_verify = cfg.wiki_root / "methods/cell-type-annotation/verify/receipt.json"
    m_verify.parent.mkdir(parents=True, exist_ok=True)
    m_verify.write_text('{"state":"ok"}\n', encoding="utf-8")
    fp2 = rc.vault_fingerprint(cfg.wiki_root, cfg.gallery_root)
    assert fp2 != fp1

    tpl_rt = cfg.wiki_root / "templates/tpl-default/runtime.json"
    tpl_rt.write_text('{"schema_version":1}\n', encoding="utf-8")
    fp3 = rc.vault_fingerprint(cfg.wiki_root, cfg.gallery_root)
    assert fp3 != fp2

    (rec_dir / "verify/verify.json").write_text('{"ok": true, "v": 2}', encoding="utf-8")
    fp4 = rc.vault_fingerprint(cfg.wiki_root, cfg.gallery_root)
    assert fp4 != fp3

    (rec_dir / "preview.png").write_bytes(_png_bytes(300, 300))
    fp5 = rc.vault_fingerprint(cfg.wiki_root, cfg.gallery_root)
    assert fp5 != fp4


def test_asset_checkout_invalidates_cache_and_tracks_linked_worktree_config(tmp_path: Path, monkeypatch):
    import subprocess
    import rwiki.asset_checkout as ac
    import rwiki.read_cache as rc

    def git(cwd: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout

    main_repo = tmp_path / "main"
    main_repo.mkdir()
    git(main_repo, "init", "-q")
    git(main_repo, "config", "user.name", "tester")
    git(main_repo, "config", "user.email", "tester@example.invalid")
    wiki_rel = Path("wiki")
    (main_repo / wiki_rel / "methods").mkdir(parents=True)
    (main_repo / wiki_rel / "methods/m1.md").write_text(
        "---\ntype: method\nid: m1\ntitle: M1\nstatus: ready\ninputs: []\noutputs: []\n---\n# M1\n",
        encoding="utf-8",
    )
    (main_repo / wiki_rel / "methods/m1/code").mkdir(parents=True)
    (main_repo / wiki_rel / "methods/m1/code/run.py").write_text("print(1)\n", encoding="utf-8")
    (main_repo / wiki_rel / "AGENTS.md").write_text("rules\n", encoding="utf-8")
    git(main_repo, "add", ".")
    git(main_repo, "commit", "-qm", "init")

    wt_dir = tmp_path / "wt"
    git(main_repo, "worktree", "add", "-q", str(wt_dir))
    wt_wiki = wt_dir / "wiki"
    cfg = Config(
        wt_wiki,
        tmp_path / "gal",
        tmp_path / "tax.json",
        Path(sys.executable),
        Path("Rscript"),
        8765,
        work_root=tmp_path / "work",
    )
    (tmp_path / "tax.json").write_text(json.dumps({"scenarios": {}}), encoding="utf-8")

    assert ac.profile(cfg) == "full"
    # External process enables sparse-checkout on the linked worktree without touching .git file
    git(wt_dir, "sparse-checkout", "set", "--no-cone", "/wiki/methods/*.md")
    assert ac.profile(cfg) == "light"

    with TestClient(create_app(cfg)) as client:
        resp = client.post("/api/methods/m1/favorite", json={"value": True})
        assert resp.status_code == 409

    # fetch_assets and set_profile invalidate cache even on error
    seen_invalidations: list[Path | None] = []
    orig_invalidate = ac.invalidate_cache

    def spy_invalidate(root=None):
        seen_invalidations.append(root)
        return orig_invalidate(root)

    monkeypatch.setattr(ac, "invalidate_cache", spy_invalidate)
    res = ac.fetch_assets(cfg, "m1")
    assert res["changed"] is True
    assert any(p == cfg.wiki_root for p in seen_invalidations)

    seen_invalidations.clear()
    with pytest.raises(Exception):
        ac.set_profile(cfg, "invalid-profile")
    assert any(p == cfg.wiki_root for p in seen_invalidations)


def test_deletion_toctou_git_rollback_sole_layout_and_ref_cleanup(tmp_path: Path, monkeypatch):
    import subprocess
    import rwiki.deletion as del_mod

    cfg = _make_v55_wiki(tmp_path, "del_hard", title_prefix="Hard")

    # 1. Sole-layout guard: typed spelling layouts/<id>.md and multi-source check
    write_page(
        cfg.wiki_root / "layouts/lay-sole.md",
        {
            "type": "layout",
            "id": "lay-sole",
            "title": "唯一版式",
            "status": "archived",
            "archived_from": "ready",
            "gallery_entry": "g-sole",
            "gallery_version": "1.0.0",
            "panels": {"A": "umap"},
        },
        "# 唯一版式\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    write_page(
        cfg.wiki_root / "templates/tpl-uses-sole.md",
        {
            "type": "template",
            "id": "tpl-uses-sole",
            "title": "依赖唯一版式的模板",
            "status": "ready",
            "layouts": ["layouts/lay-sole.md", "lay-sole"],
            "sources": [],
            "panels": ["A"],
            "language": "python",
            "tags": ["single-cell"],
            "chart_types": ["umap"],
            "favorite": False,
        },
        "# 依赖唯一版式\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    save(cfg, "add sole layout test")
    with pytest.raises(Exception, match="唯一出处"):
        prepare(cfg, cfg.wiki_root / "layouts/lay-sole.md")

    # 2. Cleanup legacy next_steps.methods + relative Markdown links with #fragment + user block check
    write_page(
        cfg.wiki_root / "methods/m-old.md",
        {
            "type": "method",
            "id": "m-old",
            "title": "旧方法",
            "status": "archived",
            "archived_from": "ready",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test"],
            "favorite": False,
        },
        "# 旧方法\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    write_page(
        cfg.wiki_root / "methods/m-ref.md",
        {
            "type": "method",
            "id": "m-ref",
            "title": "引用方法",
            "status": "ready",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test"],
            "favorite": False,
            "next_steps": [
                {"branch_id": "b1", "direction": "d", "when": "w", "methods": ["m-old", "cell-type-annotation"]}
            ],
        },
        "# 引用方法\n\n详见 [旧方法链接](./m-old.md#section-1) 和 [另一处](../methods/m-old#top)。\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    save(cfg, "add ref cleanup test")

    plan, _, _, _ = prepare(cfg, cfg.wiki_root / "methods/m-old.md")
    # Simulate concurrent edit between prepare() and delete_archived()
    p_ref = cfg.wiki_root / "methods/m-ref.md"
    rm, rb = read_page(p_ref)
    write_page(p_ref, rm, set_block(rb, "user", "\n保留备注\n"))
    with pytest.raises(Exception, match="内容或关联已变化"):
        delete_archived(cfg, cfg.wiki_root / "methods/m-old.md", plan["revision"])

    # Reset user block empty and test Git commit failure rollback (must leave index clean!)
    write_page(p_ref, rm, set_block(rb, "user", "\n"))
    save(cfg, "clear user note")
    plan2, _, _, _ = prepare(cfg, cfg.wiki_root / "methods/m-old.md")

    real_save = del_mod.save

    def fail_after_git_add(config, message):
        del_mod.save  # simulate git add then commit failure
        subprocess.run(["git", "-C", str(config.wiki_root), "add", "-A", "--", "."], check=True)
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(del_mod, "save", fail_after_git_add)
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        delete_archived(cfg, cfg.wiki_root / "methods/m-old.md", plan2["revision"])
    monkeypatch.setattr(del_mod, "save", real_save)

    # Index must NOT have staged changes left behind, and m-old.md must be restored
    staged = subprocess.run(
        ["git", "-C", str(cfg.wiki_root), "diff", "--cached", "--name-only"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert staged == ""
    assert (cfg.wiki_root / "methods/m-old.md").is_file()

    # Now succeed with deletion and verify legacy next_steps.methods + relative #fragment links cleaned
    res = delete_archived(cfg, cfg.wiki_root / "methods/m-old.md", plan2["revision"])
    assert res["deleted"] is True
    mref_after, bref_after = read_page(p_ref)
    assert mref_after["next_steps"][0]["methods"] == ["cell-type-annotation"]
    assert "m-old" not in bref_after
    assert "条目已删除" in bref_after

    # 3. Relative link inside <!-- user --> block must block deletion
    write_page(
        p_ref,
        mref_after,
        set_block(bref_after, "user", "\n保留 [模板](../templates/tpl-variant.md#anchor)\n"),
    )
    with pytest.raises(Exception, match="作者备注"):
        prepare(cfg, cfg.wiki_root / "templates/tpl-variant.md", allow_active=True)

    # 4. Empty chart_types must NOT form an output slot warning
    tpl_def_path = cfg.wiki_root / "templates/tpl-default.md"
    dm, db = read_page(tpl_def_path)
    dm["chart_types"] = []
    write_page(tpl_def_path, dm, db)
    plan_no_slot, _, _, _ = prepare(cfg, tpl_def_path, allow_active=True)
    assert plan_no_slot["slot_default_warning"] is None


def test_thumbnail_security_limits_symlink_and_quota(tmp_path: Path, monkeypatch):
    import rwiki.server as srv

    cfg = _make_v55_wiki(tmp_path, "thumb_sec", title_prefix="Sec")
    thumb_dir = tmp_path / "thumbs_sec"
    monkeypatch.setenv("RWIKI_THUMB_DIR", str(thumb_dir))
    monkeypatch.setattr(srv, "_THUMB_MAX_FILES", 2)
    monkeypatch.setattr(srv, "_THUMB_MAX_DECODE_PIXELS", 1_000_000)

    # Tall image capped to height <= 2400
    tall_path = cfg.wiki_root / "templates/tpl-default/tall.png"
    tall_path.write_bytes(_png_bytes(160, 4000))
    # Huge image exceeding decode limit
    huge_path = cfg.wiki_root / "templates/tpl-default/huge.png"
    huge_path.write_bytes(_png_bytes(1200, 1000))

    with TestClient(create_app(cfg)) as client:
        assert client.get("/files/wiki/templates/tpl-default/huge.png?w=600").status_code == 413
        tall_resp = client.get("/files/wiki/templates/tpl-default/tall.png?w=160")
        assert tall_resp.status_code == 200
        with Image.open(io.BytesIO(tall_resp.content)) as tim:
            assert tim.height <= 2400

        # Create 3 thumbnails at distinct widths -> quota of 2 prunes oldest
        for w in (200, 300, 400):
            r = client.get(f"/files/wiki/templates/tpl-default/preview.png?w={w}")
            assert r.status_code == 200
            time.sleep(0.02)
        cached_files = list(thumb_dir.glob("*.webp"))
        assert len(cached_files) <= 2
        assert all("_v2.webp" in p.name for p in cached_files)

        # Plant a symlink at cached thumb path (if OS permits) and ensure it is never returned
        target_secret = tmp_path / "secret.txt"
        target_secret.write_text("SECRET_SHOULD_NOT_LEAK", encoding="utf-8")
        sample_thumb = cached_files[0]
        w_val = int(sample_thumb.stem.split("_w")[1].split("_")[0])
        sample_thumb.unlink()
        try:
            sample_thumb.symlink_to(target_secret)
        except OSError:
            pass
        else:
            repaired = client.get(f"/files/wiki/templates/tpl-default/preview.png?w={w_val}")
            assert repaired.status_code == 200
            assert b"SECRET_SHOULD_NOT_LEAK" not in repaired.content
            assert repaired.headers["content-type"].startswith("image/webp")


def test_papers_security_honest_receipts_and_manifest_only_figures(tmp_path: Path):
    import hashlib

    cfg = _make_v55_wiki(tmp_path, "papers_sec", title_prefix="PaperSec")
    wf_dir = cfg.wiki_root / "methods/wf-paper"
    (wf_dir / "code/panels").mkdir(parents=True, exist_ok=True)
    script_a = wf_dir / "code/panels/fig01_a.py"
    script_a.write_text("print('fig01a')\n", encoding="utf-8")
    sha_a = hashlib.sha256(script_a.read_bytes()).hexdigest()

    (wf_dir / "panel-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "paper_id": "2026-test",
                "gallery_entry": "gal-1",
                "panels": [
                    {
                        "panel_key": "fig01/A",
                        "figure": "Fig. 1",
                        "panel": "1A",
                        "evidence_tier": "local_recompute",
                        "template_id": "tpl-default",
                        "script_path": "code/panels/fig01_a.py",
                    },
                    {
                        "panel_key": "sfig04/A",
                        "figure": "Supp. Fig. 4",
                        "panel": "S4A",
                        "evidence_tier": "excluded_imaging",
                    },
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (wf_dir / "panel-receipts.json").write_text(
        json.dumps({
            "schema_version": 1,
            "generated_at": "2026-11-20T12:00:00Z",
            "panels": [
                {
                    "panel_key": "fig01/A",
                    "script_path": "code/panels/fig01_a.py",
                    "script_sha256": sha_a,
                    "status": "generated",
                }
            ],
        }),
        encoding="utf-8",
    )

    # Unregistered method workflow (has code/ but no panel-manifest.yaml) must be rejected by panel-code
    unreg_code = cfg.wiki_root / "methods/cell-type-annotation/code/secret.py"
    unreg_code.parent.mkdir(parents=True, exist_ok=True)
    unreg_code.write_text("print('unreg')\n", encoding="utf-8")

    # Outside symlink inside code/ must fail both detail.script_available and panel-code
    outside = tmp_path / "outside_panel.py"
    outside.write_text("print('escaped')\n", encoding="utf-8")
    symlink_supported = True
    try:
        (wf_dir / "code/panels/escape.py").symlink_to(outside)
    except OSError:
        symlink_supported = False

    with TestClient(create_app(cfg)) as client:
        assert client.get("/api/papers/cell-type-annotation/panel-code", params={"path": "code/secret.py"}).status_code == 404
        assert client.get("/api/papers/wf-paper/panel-code", params={"path": "code/panels/fig01_a.py"}).status_code == 200
        if symlink_supported:
            assert client.get("/api/papers/wf-paper/panel-code", params={"path": "code/panels/escape.py"}).status_code == 404

        papers = client.get("/api/papers").json()["papers"]
        p0 = papers[0]
        assert p0["reproduced_figure_count"] == 1
        assert p0["manifest_only_figure_count"] == 1
        assert p0["manifest_only_figures"][0]["slug"] == "sfig04"
        assert p0["receipt_counts"]["generated"] == 1
        assert p0["receipt_counts"]["smoke_tested"] == 0
        assert p0["receipt_counts"]["hash_matched"] == 1

        detail = client.get("/api/papers/wf-paper").json()
        assert detail["reproduced_figure_count"] == 1
        assert detail["manifest_only_figure_count"] == 1
        assert detail["receipts_summary"]["generated"] == 1
        assert detail["receipts_summary"]["smoke_tested"] == 0
        assert detail["receipts_summary"]["hash_matched"] == 1
        figs_by_slug = {f["slug"]: f for f in detail["figures"]}
        assert figs_by_slug["fig01"]["manifest_only"] is False
        assert figs_by_slug["sfig04"]["manifest_only"] is True


def test_project_tracker_parses_local_data_boundary_label():
    from rwiki.project_tracker import parse_steps

    md = (
        "## 5 阶段科学步进走线实录\n\n"
        "### Stage 1（Main Fig. 1D–E）：CyCIF 演进图谱构建\n\n"
        "- **【科学问题与假设】**：测试问题。\n"
        "- **【方法与模板】**：[[methods/cell-type-annotation]] + [[templates/tri-panel-stage-umap]]\n"
        "- **【原文结论与本地数据边界】**：基于 Panel 2 实测 15 个公共蛋白重算。\n"
        "- **【触发下一步分叉】**：进入 Stage 2。\n"
    )
    steps = parse_steps(md)
    assert len(steps) == 1
    assert steps[0]["step"] == 1
    assert "tri-panel-stage-umap" in steps[0]["templates"]
    assert steps[0]["observation"] == "基于 Panel 2 实测 15 个公共蛋白重算。"
    assert steps[0]["next_branch"] == "进入 Stage 2。"

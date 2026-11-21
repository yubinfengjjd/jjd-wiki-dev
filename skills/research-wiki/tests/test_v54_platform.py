"""Tests for Research Wiki v5.4 Platform Upgrade: Jinja2 decoupling, atomic panel manifests, facts summary, deletion, and /api/papers."""
from __future__ import annotations

import builtins
import json
import sys
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from conftest import write_config
from rwiki.config import Config
from rwiki.deletion import delete_archived, prepare
from rwiki.facts import method_facts
from rwiki.lint import lint
from rwiki.pages import read_page, write_page
from rwiki.panel_manifest import (
    EXCLUDED_EVIDENCE_TIERS,
    VALID_EVIDENCE_TIERS,
    manifest_facts_lines,
    panel_manifest_errors,
    summarize_panel_manifest,
)
from rwiki.server import create_app
from rwiki.store import init, save


def _make_wiki(tmp_path: Path) -> Config:
    wiki = tmp_path / "wiki"
    gallery = tmp_path / "gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text(json.dumps({"scenarios": {"single-cell": {"label": "单细胞分析"}}}), encoding="utf-8")
    cfg = Config(
        wiki,
        gallery,
        taxonomy,
        Path(sys.executable),
        Path("Rscript"),
        8765,
        work_root=tmp_path / "work",
    )
    init(cfg)
    write_config(tmp_path / "config.json", wiki)

    write_page(
        wiki / "methods/cell-type-annotation.md",
        {
            "type": "method",
            "id": "cell-type-annotation",
            "title": "细胞类型注释",
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
        },
        "# 细胞类型注释\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    write_page(
        wiki / "templates/tpl-umap.md",
        {
            "type": "template",
            "id": "tpl-umap",
            "title": "基质亚群包络图",
            "status": "ready",
            "layouts": [],
            "sources": ["methods/cell-type-annotation"],
            "panels": [],
            "language": "r",
            "primary_method": "cell-type-annotation",
            "style_tier": "variant",
            "journal_style": "Cai2026-npjPO",
            "tags": ["single-cell"],
            "chart_types": ["umap"],
            "favorite": False,
        },
        "# 基质亚群包络图\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n测试。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    tdir = wiki / "templates/tpl-umap"
    (tdir / "code").mkdir(parents=True, exist_ok=True)
    (tdir / "code/render.R").write_text("cat('ok')\n", encoding="utf-8")
    (tdir / "spec.json").write_text(
        json.dumps({
            "entry": "code/render.R",
            "language": "r",
            "tables": {"cells": {"interface": None, "description": "cells", "columns": {"cell_id": {"type": "str"}}}},
            "style": {},
        }),
        encoding="utf-8",
    )
    save(cfg, "init v54 test wiki")
    return cfg


def test_panel_manifest_supports_excluded_schematic_imaging_and_atomic_fields(tmp_path: Path):
    cfg = _make_wiki(tmp_path)
    assert {"excluded_schematic", "excluded_imaging", "excluded_wet_lab"} <= VALID_EVIDENCE_TIERS
    assert EXCLUDED_EVIDENCE_TIERS == frozenset({"excluded_wet_lab", "excluded_schematic", "excluded_imaging"})

    wf_path = cfg.wiki_root / "methods/demo-wf.md"
    write_page(
        wf_path,
        {
            "type": "method",
            "id": "demo-wf",
            "title": "演示复刻流程",
            "status": "draft",
            "method_kind": "workflow",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Demo 2026"],
            "favorite": False,
            "summary": "演示。",
            "data_contract": {"input": "raw", "output": "figs"},
        },
        "# 演示\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    wf_dir = cfg.wiki_root / "methods/demo-wf"
    (wf_dir / "code/panels").mkdir(parents=True, exist_ok=True)
    (wf_dir / "code/panels/fig01_b.R").write_text("# Fig 1B script\nprint('fig01b')\n", encoding="utf-8")
    manifest = {
        "schema_version": 2,
        "paper_id": "2026-demo",
        "doi": "10.1000/demo",
        "journal": "Nature",
        "year": 2026,
        "gallery_entry": "2026-demo-gallery",
        "panels": [
            {
                "panel_key": "fig01/A",
                "figure_slug": "fig01",
                "panel_letter": "A",
                "figure": "Fig. 1",
                "panel": "1A",
                "evidence_tier": "excluded_schematic",
                "template_id": None,
                "script_path": None,
                "description": "研究设计流程图",
            },
            {
                "panel_key": "fig01/B",
                "figure_slug": "fig01",
                "panel_letter": "B",
                "figure": "Fig. 1",
                "panel": "1B",
                "evidence_tier": "local_recompute",
                "template_disposition": "paper_variant",
                "template_id": "tpl-umap",
                "script_path": "code/panels/fig01_b.R",
                "input_tables": ["cells.csv"],
                "description": "UMAP 降维",
            },
            {
                "panel_key": "fig03/F",
                "figure_slug": "fig03",
                "panel_letter": "F",
                "figure": "Fig. 3",
                "panel": "3F",
                "evidence_tier": "excluded_wet_lab",
                "description": "小鼠实验",
            },
            {
                "panel_key": "fig03/H",
                "figure_slug": "fig03",
                "panel_letter": "H",
                "figure": "Fig. 3",
                "panel": "3H",
                "evidence_tier": "excluded_imaging",
                "description": "mIF 原位显微影像",
            },
        ],
    }
    (wf_dir / "panel-manifest.yaml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    (wf_dir / "method-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "paper_id": "2026-demo",
                "workflow_id": "demo-wf",
                "steps": [
                    {
                        "step_id": "step01-demo",
                        "title": "演示计算步骤",
                        "script_path": "code/panels/fig01_b.R",
                        "method_disposition": "paper_specific_only",
                        "method_id": None,
                        "implementation_id": None,
                        "disposition_note": "合成测试夹具专用步骤，无需入库通用分析方法。",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    assert panel_manifest_errors(cfg, wf_path) == []
    stats = summarize_panel_manifest(manifest)
    assert stats["excluded_schematic"] == 1
    assert stats["excluded_imaging"] == 1
    assert stats["excluded_wet_lab"] == 1
    assert stats["excluded_total"] == 3
    assert stats["computed"] == 1
    assert stats["templates"] == 1

    lines = manifest_facts_lines(cfg, wf_path)
    assert "剔除示意图 1" in lines[0]
    assert "剔除显微影像 1" in lines[0]

    # Traversal script_path must fail validation
    bad_manifest = dict(manifest)
    bad_manifest["panels"] = [
        {
            "panel_key": "fig01/C",
            "figure": "Fig. 1",
            "panel": "1C",
            "evidence_tier": "local_recompute",
            "script_path": "../secret.py",
        }
    ]
    (wf_dir / "panel-manifest.yaml").write_text(yaml.safe_dump(bad_manifest, allow_unicode=True), encoding="utf-8")
    errs = panel_manifest_errors(cfg, wf_path)
    assert any("script_path" in e for e in errs)


def test_facts_summarizes_code_panels_directory(tmp_path: Path):
    cfg = _make_wiki(tmp_path)
    wf_path = cfg.wiki_root / "methods/demo-wf.md"
    write_page(
        wf_path,
        {
            "type": "method",
            "id": "demo-wf",
            "title": "演示流程",
            "status": "draft",
            "method_kind": "workflow",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Demo 2026"],
            "favorite": False,
        },
        "# 演示\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    code_dir = cfg.wiki_root / "methods/demo-wf/code"
    (code_dir / "panels").mkdir(parents=True, exist_ok=True)
    (code_dir / "01_step.R").write_text("# step 1\n", encoding="utf-8")
    for idx in range(15):
        (code_dir / f"panels/fig01_{chr(97 + idx)}.R").write_text(f"# panel {idx}\n", encoding="utf-8")

    meta, _ = read_page(wf_path)
    facts_text = method_facts(cfg, meta)
    assert "methods/demo-wf/code/01_step.R" in facts_text
    assert "独立 Panel 脚本：共 15 个（见前端「论文复刻」面板）" in facts_text
    assert "code/panels/fig01_a.R" not in facts_text


def test_playbooks_and_plain_template_render_without_jinja2(tmp_path: Path, monkeypatch):
    cfg = _make_wiki(tmp_path)
    write_page(
        cfg.wiki_root / "scenarios/pb.md",
        {
            "type": "scenario",
            "id": "pb",
            "title": "Playbook",
            "picks": [],
            "steps": [{"id": "s1", "title": "Step 1", "method_id": "cell-type-annotation", "next_steps": []}],
        },
        "# PB\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    real_import = builtins.__import__

    def _block_jinja(name, *args, **kwargs):
        if name == "jinja2" or name.startswith("jinja2."):
            raise ModuleNotFoundError("No module named 'jinja2'")
        return real_import(name, *args, **kwargs)

    # Clear cached studio / template_renderer / template_spec and block jinja2 import
    for mod in list(sys.modules):
        if mod in ("rwiki.studio", "rwiki.template_renderer", "rwiki.template_spec") or mod == "jinja2" or mod.startswith("jinja2."):
            sys.modules.pop(mod, None)
    monkeypatch.setattr(builtins, "__import__", _block_jinja)

    from rwiki.studio import get_playbooks, render_studio_code
    from rwiki.template_renderer import render_template_code

    pb = get_playbooks(cfg)
    assert pb["playbooks"][0]["id"] == "pb"

    with TestClient(create_app(cfg)) as client:
        resp = client.get("/api/playbooks")
        assert resp.status_code == 200
        assert resp.json()["playbooks"][0]["id"] == "pb"

    plain = render_template_code(
        "print('plain R script')\n",
        language="R",
        spec={"parameters": {"palette": {"type": "select", "default": "NPG", "choices": ["NPG"]}}},
        parameters={"palette": "NPG"},
    )
    assert "print('plain R script')" in plain["code"]
    assert "RWIKI_PARAMS_JSON" in plain["code"]

    studio_out = render_studio_code(cfg, entry_id="tpl-umap")
    assert "cat('ok')" in studio_out["code"]

    with pytest.raises(RuntimeError, match="Jinja2"):
        render_template_code("{{ palette_name }}", language="R")


def test_deletion_cleans_nested_steps_panel_manifest_and_bare_paths(tmp_path: Path):
    cfg = _make_wiki(tmp_path)
    write_page(
        cfg.wiki_root / "templates/tpl-old.md",
        {
            "type": "template",
            "id": "tpl-old",
            "title": "旧示意图模板",
            "status": "archived",
            "archived_from": "ready",
            "layouts": [],
            "sources": ["methods/cell-type-annotation"],
            "panels": [],
            "language": "r",
            "tags": ["single-cell"],
            "chart_types": ["network"],
            "favorite": False,
        },
        "# 旧示意图\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    write_page(
        cfg.wiki_root / "scenarios/test-pb.md",
        {
            "type": "scenario",
            "id": "test-pb",
            "title": "测试分支树",
            "picks": [{"id": "templates/tpl-old", "note": "old"}, {"id": "templates/tpl-umap", "note": "keep"}],
            "steps": [
                {
                    "id": "s1",
                    "title": "Step 1",
                    "method_id": "cell-type-annotation",
                    "templates": ["templates/tpl-old", "templates/tpl-umap"],
                    "viz_templates": ["tpl-old"],
                    "next_steps": [],
                }
            ],
        },
        "# 分支\n\n参考 `templates/tpl-old` 与 templates/tpl-old/spec.json。\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    wf_dir = cfg.wiki_root / "methods/wf-clean"
    wf_dir.mkdir(parents=True, exist_ok=True)
    write_page(
        cfg.wiki_root / "methods/wf-clean.md",
        {
            "type": "method",
            "id": "wf-clean",
            "title": "清理测试流程",
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
        "# 清理测试\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    (wf_dir / "code").mkdir(parents=True, exist_ok=True)
    (wf_dir / "code/step01.R").write_text("# clean fixture step\n", encoding="utf-8")
    (wf_dir / "method-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "paper_id": "2026-clean-test",
                "workflow_id": "wf-clean",
                "steps": [
                    {
                        "step_id": "step01-clean",
                        "title": "清理夹具步骤",
                        "script_path": "code/step01.R",
                        "method_disposition": "paper_specific_only",
                        "method_id": None,
                        "implementation_id": None,
                        "disposition_note": "删除回归夹具专用步骤。",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (wf_dir / "panel-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "panels": [
                    {"panel_key": "fig01/A", "figure": "Fig. 1", "panel": "1A", "evidence_tier": "original_table", "template_id": "tpl-old"},
                    {"panel_key": "fig01/B", "figure": "Fig. 1", "panel": "1B", "evidence_tier": "local_recompute", "template_id": "tpl-umap"},
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    save(cfg, "seed deletion test")

    plan, _, _, _ = prepare(cfg, cfg.wiki_root / "templates/tpl-old.md")
    res = delete_archived(cfg, cfg.wiki_root / "templates/tpl-old.md", plan["revision"])
    assert res["deleted"] is True

    pb_meta, pb_body = read_page(cfg.wiki_root / "scenarios/test-pb.md")
    assert pb_meta["steps"][0]["templates"] == ["templates/tpl-umap"]
    assert pb_meta["steps"][0]["viz_templates"] == []
    assert [p["id"] for p in pb_meta["picks"]] == ["templates/tpl-umap"]
    assert "tpl-old" not in pb_body
    assert "条目已删除" in pb_body

    manifest_after = yaml.safe_load((wf_dir / "panel-manifest.yaml").read_text(encoding="utf-8"))
    assert manifest_after["panels"][0]["template_id"] is None
    assert manifest_after["panels"][1]["template_id"] == "tpl-umap"
    assert "tpl-old" not in (cfg.wiki_root / "index.md").read_text(encoding="utf-8")


def test_papers_endpoints_detail_code_security_and_template_origins(tmp_path: Path):
    cfg = _make_wiki(tmp_path)
    wf_id = "cai-test-workflow"
    wf_path = cfg.wiki_root / f"methods/{wf_id}.md"
    write_page(
        wf_path,
        {
            "type": "method",
            "id": wf_id,
            "title": "测试乳腺癌基质复刻流程",
            "status": "draft",
            "method_kind": "workflow",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "CC-BY-NC-ND-4.0",
            "cite": ["Cai et al. (npj Precision Oncology, 2026)"],
            "favorite": False,
            "summary": "论文复刻工作流摘要。",
        },
        "# 复刻流程\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    wf_dir = cfg.wiki_root / "methods" / wf_id
    (wf_dir / "code/panels").mkdir(parents=True, exist_ok=True)
    (wf_dir / "code/panels/fig01_b.R").write_text("# Fig 1B script\nprint('fig01b')\n", encoding="utf-8")
    (wf_dir / "secret.txt").write_text("do-not-leak", encoding="utf-8")
    (wf_dir / "panel-receipts.json").write_text(
        json.dumps({
            "schema_version": 1,
            "generated_at": "2026-11-20T10:00:00Z",
            "panels": [
                {"panel_key": "fig01/B", "script_path": "code/panels/fig01_b.R", "status": "pass"}
            ],
        }),
        encoding="utf-8",
    )
    (wf_dir / "method-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "paper_id": "2026-cai-test",
                "workflow_id": wf_id,
                "steps": [
                    {
                        "step_id": "step01-panel-b",
                        "title": "演示计算步骤",
                        "script_path": "code/panels/fig01_b.R",
                        "method_disposition": "paper_specific_only",
                        "method_id": None,
                        "implementation_id": None,
                        "disposition_note": "论文 API 夹具专用步骤。",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (wf_dir / "panel-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "paper_id": "2026-cai-test",
                "doi": "10.1038/s41698-026-01718-1",
                "journal": "npj Precision Oncology",
                "year": 2026,
                "gallery_entry": "2026-cai-gallery",
                "panels": [
                    {
                        "panel_key": "fig01/A",
                        "figure_slug": "fig01",
                        "panel_letter": "A",
                        "figure": "Fig. 1",
                        "panel": "1A",
                        "evidence_tier": "excluded_schematic",
                        "description": "研究路线示意图",
                    },
                    {
                        "panel_key": "fig01/B",
                        "figure_slug": "fig01",
                        "panel_letter": "B",
                        "figure": "Fig. 1",
                        "panel": "1B",
                        "evidence_tier": "local_recompute",
                        "template_id": "tpl-umap",
                        "script_path": "code/panels/fig01_b.R",
                        "input_tables": ["cells.csv"],
                        "description": "三大区室 UMAP",
                    },
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    gdir = cfg.gallery_root / "2026-cai-gallery"
    (gdir / "figures").mkdir(parents=True, exist_ok=True)
    tiny_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
    (gdir / "figures/fig01_replica.png").write_bytes(tiny_png)
    (gdir / "figures/fig01_side_by_side.png").write_bytes(tiny_png)
    (gdir / "meta.json").write_text(
        json.dumps({
            "slug": "2026-cai-gallery",
            "paper_id": "2026-cai-test",
            "doi": "10.1038/s41698-026-01718-1",
            "workflow_id": wf_id,
            "figures": [
                {
                    "slug": "fig01",
                    "label": "Fig. 1",
                    "caption": "Stromal atlas",
                    "panels": ["A", "B"],
                    "replica": "figures/fig01_replica.png",
                    "side_by_side": "figures/fig01_side_by_side.png",
                    "replica_px": [2880, 3660],
                    "side_by_side_px": [2061, 1338],
                    "visual_review": "PASS",
                }
            ],
        }),
        encoding="utf-8",
    )

    with TestClient(create_app(cfg)) as client:
        r_list = client.get("/api/papers")
        assert r_list.status_code == 200
        papers = r_list.json()["papers"]
        assert len(papers) == 1
        assert papers[0]["workflow_id"] == wf_id
        assert papers[0]["journal"] == "npj Precision Oncology"
        assert papers[0]["year"] == 2026
        assert papers[0]["cover_url"] == "/files/gallery/2026-cai-gallery/figures/fig01_replica.png"
        assert papers[0]["stats"]["computed"] == 1
        assert papers[0]["stats"]["excluded_total"] == 1

        r_detail = client.get(f"/api/papers/{wf_id}")
        assert r_detail.status_code == 200
        detail = r_detail.json()
        assert len(detail["figures"]) == 1
        fig1 = detail["figures"][0]
        assert fig1["replica_url"] == "/files/gallery/2026-cai-gallery/figures/fig01_replica.png"
        assert fig1["side_by_side_url"] == "/files/gallery/2026-cai-gallery/figures/fig01_side_by_side.png"
        assert len(fig1["panels"]) == 2
        p_a, p_b = fig1["panels"]
        assert p_a["is_excluded"] is True and p_a["evidence_tier"] == "excluded_schematic"
        assert p_b["script_path"] == "code/panels/fig01_b.R"
        assert p_b["receipt"]["status"] == "pass"
        assert p_b["template"]["id"] == "tpl-umap"

        r_code = client.get(f"/api/papers/{wf_id}/panel-code", params={"path": "code/panels/fig01_b.R"})
        assert r_code.status_code == 200
        assert "print('fig01b')" in r_code.json()["text"]

        # Security: traversal and non-code directories must be rejected with 404
        for bad in ("../cell-type-annotation.md", "../../config.json", "secret.txt", "panel-manifest.yaml", "/etc/passwd"):
            assert client.get(f"/api/papers/{wf_id}/panel-code", params={"path": bad}).status_code == 404

        assert client.get("/api/papers/nonexistent-wf").status_code == 404

        # Cross-paper template origin metadata on /api/pages and /api/page
        pages = client.get("/api/pages").json()
        tpl_item = next(p for p in pages if p["path"] == "templates/tpl-umap.md")
        assert tpl_item["paper_origins"][0]["workflow_id"] == wf_id
        tpl_detail = client.get("/api/page", params={"path": "templates/tpl-umap.md"}).json()
        assert tpl_detail["paper_origins"][0]["workflow_id"] == wf_id

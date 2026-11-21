"""Tests for Research Wiki v5.6 Hard Intake Gate (Schema v2 panel-manifest + Output Slot lint rules)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from conftest import write_config
from rwiki.config import Config
from rwiki.lint import lint
from rwiki.pages import write_page
from rwiki.panel_manifest import VALID_TEMPLATE_DISPOSITIONS, panel_manifest_errors
from rwiki.store import init


def _make_v56_wiki(tmp_path: Path) -> Config:
    wiki = tmp_path / "wiki"
    gallery = tmp_path / "gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text(
        json.dumps(
            {
                "scenarios": {
                    "single-cell": {"label": "单细胞分析"},
                    "transcriptomics": {"label": "转录组分析"},
                }
            }
        ),
        encoding="utf-8",
    )
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
            "status": "draft",
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
        "# 细胞类型注释\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n测试。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    write_page(
        wiki / "methods/wf-paper.md",
        {
            "type": "method",
            "id": "wf-paper",
            "title": "论文复刻工作流",
            "status": "draft",
            "method_kind": "workflow",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Demo 2026"],
            "favorite": False,
            "summary": "复刻流程。",
            "data_contract": {"input": "raw", "output": "figs"},
        },
        "# 论文复刻工作流\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n测试。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    return cfg


def _write_tpl(
    cfg: Config,
    tid: str,
    *,
    status: str = "ready",
    primary_method: str | None = "cell-type-annotation",
    style_tier: str | None = "default",
    journal_style: str | None = "Standard",
    tags: list[str] | None = None,
    chart_types: list[str] | None = None,
) -> Path:
    meta: dict = {
        "type": "template",
        "id": tid,
        "title": f"模板 {tid}",
        "status": status,
        "layouts": [],
        "sources": ["methods/cell-type-annotation"],
        "panels": [],
        "language": "r",
        "tags": ["single-cell"] if tags is None else tags,
        "chart_types": ["umap"] if chart_types is None else chart_types,
        "favorite": False,
    }
    if primary_method is not None:
        meta["primary_method"] = primary_method
    if style_tier is not None:
        meta["style_tier"] = style_tier
    if journal_style is not None:
        meta["journal_style"] = journal_style

    page_path = cfg.wiki_root / f"templates/{tid}.md"
    write_page(
        page_path,
        meta,
        f"# 模板 {tid}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n测试。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    tdir = cfg.wiki_root / f"templates/{tid}"
    (tdir / "code").mkdir(parents=True, exist_ok=True)
    (tdir / "code/render.R").write_text("cat('ok')\n", encoding="utf-8")
    (tdir / "spec.json").write_text(
        json.dumps(
            {
                "entry": "code/render.R",
                "language": "r",
                "tables": {"cells": {"interface": None, "description": "cells", "columns": {"id": {"type": "str"}}}},
                "style": {},
            }
        ),
        encoding="utf-8",
    )
    if status == "ready":
        (tdir / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (tdir / "verify").mkdir(parents=True, exist_ok=True)
        (tdir / "verify/receipt.json").write_text('{"schema_version":2,"exit_code":0}', encoding="utf-8")
    return page_path


def _write_manifest(cfg: Config, payload: dict) -> Path:
    wf_dir = cfg.wiki_root / "methods/wf-paper"
    wf_dir.mkdir(parents=True, exist_ok=True)
    mpath = wf_dir / "panel-manifest.yaml"
    mpath.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    if payload.get("schema_version") == 2 and not (wf_dir / "method-manifest.yaml").is_file():
        step_script = wf_dir / "code/step01_fixture.R"
        step_script.parent.mkdir(parents=True, exist_ok=True)
        step_script.write_text("cat('fixture step ok')\n", encoding="utf-8")
        (wf_dir / "method-manifest.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "paper_id": str(payload.get("paper_id") or "2026-v56-fixture"),
                    "workflow_id": "wf-paper",
                    "steps": [
                        {
                            "step_id": "step01-fixture",
                            "title": "合成夹具步骤",
                            "script_path": "code/step01_fixture.R",
                            "method_disposition": "paper_specific_only",
                            "method_id": None,
                            "implementation_id": None,
                            "disposition_note": "v5.6 面板门禁测试夹具专用占位步骤。",
                        }
                    ],
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
    return mpath


def _touch_panel_script(cfg: Config, rel_path: str = "code/panels/fig01_a.R") -> None:
    script = cfg.wiki_root / "methods/wf-paper" / rel_path
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("cat('panel ok')\n", encoding="utf-8")


def test_valid_template_dispositions_constant():
    assert VALID_TEMPLATE_DISPOSITIONS == frozenset(
        {"paper_variant", "reuse_identical", "paper_specific_only"}
    )


def test_schema_v1_and_unversioned_manifests_remain_backward_compatible(tmp_path: Path):
    cfg = _make_v56_wiki(tmp_path)
    _write_tpl(cfg, "tpl-old", status="draft", primary_method=None, style_tier=None, journal_style=None)

    for version in (1, None):
        payload = {
            "paper_id": "2026-legacy",
            "panels": [
                {
                    "panel_key": "fig01/A",
                    "figure": "Fig. 1",
                    "panel": "1A",
                    "evidence_tier": "local_recompute",
                    "template_id": "tpl-old",
                    "script_path": "code/panels/missing_in_v1.R",
                }
            ],
        }
        if version is not None:
            payload["schema_version"] = version
        _write_manifest(cfg, payload)
        assert panel_manifest_errors(cfg, "wf-paper") == []


def test_schema_v2_rejects_missing_or_invalid_template_disposition_and_allows_excluded(tmp_path: Path):
    cfg = _make_v56_wiki(tmp_path)
    _write_tpl(cfg, "tpl-ready-default")
    _touch_panel_script(cfg, "code/panels/fig01_b.R")

    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig01/A",
                    "figure": "Fig. 1",
                    "panel": "1A",
                    "evidence_tier": "excluded_schematic",
                    "template_id": None,
                    "script_path": None,
                },
                {
                    "panel_key": "fig01/B",
                    "figure": "Fig. 1",
                    "panel": "1B",
                    "evidence_tier": "local_recompute",
                    "template_id": "tpl-ready-default",
                    "script_path": "code/panels/fig01_b.R",
                },
            ],
        },
    )
    errs = panel_manifest_errors(cfg, "wf-paper")
    assert len(errs) == 1 and "panels[1].template_disposition" in errs[0]

    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig01/B",
                    "figure": "Fig. 1",
                    "panel": "1B",
                    "evidence_tier": "local_recompute",
                    "template_disposition": "bogus_mode",
                    "template_id": "tpl-ready-default",
                    "script_path": "code/panels/fig01_b.R",
                }
            ],
        },
    )
    errs = panel_manifest_errors(cfg, "wf-paper")
    assert any("template_disposition" in e and "bogus_mode" in e for e in errs)


def test_schema_v2_paper_variant_requires_ready_slotted_template(tmp_path: Path):
    cfg = _make_v56_wiki(tmp_path)
    _touch_panel_script(cfg, "code/panels/fig01_a.R")

    # Rejects missing template_id
    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig01/A",
                    "figure": "Fig. 1",
                    "panel": "1A",
                    "evidence_tier": "local_recompute",
                    "template_disposition": "paper_variant",
                    "template_id": None,
                    "script_path": "code/panels/fig01_a.R",
                }
            ],
        },
    )
    assert any("template_id" in e for e in panel_manifest_errors(cfg, "wf-paper"))

    # Rejects draft template missing primary_method / style_tier / journal_style
    _write_tpl(cfg, "tpl-incomplete", status="draft", primary_method=None, style_tier=None, journal_style=None)
    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig01/A",
                    "figure": "Fig. 1",
                    "panel": "1A",
                    "evidence_tier": "local_recompute",
                    "template_disposition": "paper_variant",
                    "template_id": "tpl-incomplete",
                    "script_path": "code/panels/fig01_a.R",
                }
            ],
        },
    )
    errs = panel_manifest_errors(cfg, "wf-paper")
    assert any("status 必须为 ready" in e for e in errs)
    assert any("primary_method" in e for e in errs)
    assert any("style_tier" in e for e in errs)
    assert any("journal_style" in e for e in errs)

    # Passes when template is ready and has primary_method, style_tier, journal_style
    _write_tpl(cfg, "tpl-complete", status="ready", primary_method="cell-type-annotation", style_tier="variant", journal_style="Nature 2026")
    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig01/A",
                    "figure": "Fig. 1",
                    "panel": "1A",
                    "evidence_tier": "local_recompute",
                    "template_disposition": "paper_variant",
                    "template_id": "tpl-complete",
                    "script_path": "code/panels/fig01_a.R",
                }
            ],
        },
    )
    assert panel_manifest_errors(cfg, "wf-paper") == []


def test_schema_v2_reuse_identical_requires_existing_template_and_disposition_note(tmp_path: Path):
    cfg = _make_v56_wiki(tmp_path)
    _write_tpl(cfg, "tpl-base", status="ready")
    _touch_panel_script(cfg, "code/panels/fig02_a.R")

    # Missing template_id and disposition_note
    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig02/A",
                    "figure": "Fig. 2",
                    "panel": "2A",
                    "evidence_tier": "original_table",
                    "template_disposition": "reuse_identical",
                    "template_id": None,
                    "disposition_note": "  ",
                    "script_path": "code/panels/fig02_a.R",
                }
            ],
        },
    )
    errs = panel_manifest_errors(cfg, "wf-paper")
    assert any("template_id" in e for e in errs)
    assert any("disposition_note" in e for e in errs)

    # Valid reuse_identical passes
    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig02/A",
                    "figure": "Fig. 2",
                    "panel": "2A",
                    "evidence_tier": "original_table",
                    "template_disposition": "reuse_identical",
                    "template_id": "tpl-base",
                    "disposition_note": "与既有标准 UMAP 模板配色及图元完全一致，仅基因标签不同。",
                    "script_path": "code/panels/fig02_a.R",
                }
            ],
        },
    )
    assert panel_manifest_errors(cfg, "wf-paper") == []


def test_schema_v2_paper_specific_only_requires_null_template_id_and_disposition_note(tmp_path: Path):
    cfg = _make_v56_wiki(tmp_path)
    _write_tpl(cfg, "tpl-base", status="ready")
    _touch_panel_script(cfg, "code/panels/fig03_c.R")

    # Non-None template_id and missing disposition_note must fail
    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig03/C",
                    "figure": "Fig. 3",
                    "panel": "3C",
                    "evidence_tier": "proxy",
                    "template_disposition": "paper_specific_only",
                    "template_id": "tpl-base",
                    "script_path": "code/panels/fig03_c.R",
                }
            ],
        },
    )
    errs = panel_manifest_errors(cfg, "wf-paper")
    assert any("template_id 必须为 None" in e for e in errs)
    assert any("disposition_note" in e for e in errs)

    # Valid paper_specific_only passes
    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig03/C",
                    "figure": "Fig. 3",
                    "panel": "3C",
                    "evidence_tier": "proxy",
                    "template_disposition": "paper_specific_only",
                    "template_id": None,
                    "disposition_note": "该面板为特定队列基因重排时间线示意图级统计拼图，高度论文特异。",
                    "script_path": "code/panels/fig03_c.R",
                }
            ],
        },
    )
    assert panel_manifest_errors(cfg, "wf-paper") == []


def test_schema_v2_requires_existing_on_disk_script_path_for_computed_panels(tmp_path: Path):
    cfg = _make_v56_wiki(tmp_path)
    _write_tpl(cfg, "tpl-base", status="ready")

    # Missing script_path and hollow non-existent script_path both fail
    _write_manifest(
        cfg,
        {
            "schema_version": 2,
            "panels": [
                {
                    "panel_key": "fig01/A",
                    "figure": "Fig. 1",
                    "panel": "1A",
                    "evidence_tier": "local_recompute",
                    "template_disposition": "reuse_identical",
                    "template_id": "tpl-base",
                    "disposition_note": "复用基础模板",
                },
                {
                    "panel_key": "fig01/B",
                    "figure": "Fig. 1",
                    "panel": "1B",
                    "evidence_tier": "local_recompute",
                    "template_disposition": "reuse_identical",
                    "template_id": "tpl-base",
                    "disposition_note": "复用基础模板",
                    "script_path": "code/panels/does_not_exist.R",
                },
            ],
        },
    )
    errs = panel_manifest_errors(cfg, "wf-paper")
    assert any("panels[0].script_path 缺失" in e for e in errs)
    assert any("panels[1].script_path 指向的脚本文件不存在" in e for e in errs)


def test_output_slot_gate_forbids_lone_variant_requires_completeness_and_tag_alignment(tmp_path: Path):
    # 1. Lone variant in a slot is forbidden
    cfg_lone = _make_v56_wiki(tmp_path / "lone")
    _write_tpl(cfg_lone, "tpl-lone-var", status="draft", style_tier="variant", journal_style="Nature 2026")
    errors = [line for line in lint(cfg_lone) if line.startswith("ERROR ")]
    assert any("templates/tpl-lone-var.md" in e and "禁止孤立标为 style_tier: variant" in e for e in errors)

    # 2. Multi-template styled slot: missing default & missing journal_style/style_tier are rejected
    cfg_multi = _make_v56_wiki(tmp_path / "multi")
    _write_tpl(cfg_multi, "tpl-v1", status="draft", style_tier="variant", journal_style="Style1")
    _write_tpl(cfg_multi, "tpl-v2", status="draft", style_tier=None, journal_style=None)
    errors_multi = [line for line in lint(cfg_multi) if line.startswith("ERROR ")]
    assert any("缺少 style_tier: default" in e for e in errors_multi)
    assert any("tpl-v2" in e and "合法 style_tier" in e for e in errors_multi)
    assert any("tpl-v2" in e and "非空 journal_style" in e for e in errors_multi)

    # 3. Multi-template slot: variant missing default's primary tag is rejected; aligned tags pass
    cfg_tags = _make_v56_wiki(tmp_path / "tags")
    _write_tpl(
        cfg_tags,
        "tpl-def",
        status="draft",
        style_tier="default",
        journal_style="Standard",
        tags=["single-cell"],
    )
    _write_tpl(
        cfg_tags,
        "tpl-var-bad-tag",
        status="draft",
        style_tier="variant",
        journal_style="Cancer Discovery",
        tags=["transcriptomics"],
    )
    errors_tags = [line for line in lint(cfg_tags) if line.startswith("ERROR ")]
    assert any("templates/tpl-var-bad-tag.md" in e and "主标签 'single-cell'" in e for e in errors_tags)

    # Fix variant tags to include primary tag -> 0 slot errors
    _write_tpl(
        cfg_tags,
        "tpl-var-bad-tag",
        status="draft",
        style_tier="variant",
        journal_style="Cancer Discovery",
        tags=["single-cell", "transcriptomics"],
    )
    errors_fixed = [line for line in lint(cfg_tags) if line.startswith("ERROR ")]
    assert errors_fixed == []

    # 4. Legacy unstyled slot (neither style_tier nor journal_style) stays compatible
    cfg_legacy = _make_v56_wiki(tmp_path / "legacy")
    _write_tpl(cfg_legacy, "tpl-leg-1", status="draft", style_tier=None, journal_style=None, tags=["transcriptomics"])
    _write_tpl(cfg_legacy, "tpl-leg-2", status="draft", style_tier=None, journal_style=None, tags=[])
    assert [line for line in lint(cfg_legacy) if line.startswith("ERROR ")] == []

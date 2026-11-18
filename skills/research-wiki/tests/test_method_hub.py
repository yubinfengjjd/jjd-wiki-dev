"""Tests for Method Hub aggregation, additive multi-branch next protocol, and HTTP/MCP endpoints."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import write_config, write_interface
from rwiki.cli import main as cli_main
from rwiki.config import Config
from rwiki.method_hub import build_method_hub, list_method_hubs
from rwiki.pages import read_page, write_page
from rwiki.server import create_app
from rwiki.suggest import format_next_steps, suggest_next_steps

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _write_template(
    wiki: Path,
    tid: str,
    *,
    title: str,
    tables: dict,
    primary_method: str | None = None,
    language: str = "r",
    chart_types: list[str] | None = None,
    status: str = "ready",
    sources: list[str] | None = None,
    with_preview: bool = True,
    aliases: list[str] | None = None,
) -> None:
    tpl_dir = wiki / "templates" / tid
    (tpl_dir / "code").mkdir(parents=True, exist_ok=True)
    if language == "python":
        (tpl_dir / "code/__init__.py").write_text("", encoding="utf-8")
        (tpl_dir / "code/panel.py").write_text("def draw(*a, **kw): pass\n", encoding="utf-8")
        (tpl_dir / "code/render.py").write_text("print('ok')\n", encoding="utf-8")
        spec = {
            "entry": "code/render.py",
            "panel": "code/panel.py",
            "language": "python",
            "tables": tables,
            "style": {"palette": "NPG"},
        }
    else:
        (tpl_dir / "code/render.r").write_text("cat('ok\\n')\n", encoding="utf-8")
        spec = {
            "entry": "code/render.r",
            "language": "r",
            "tables": tables,
            "style": {"palette": "NPG"},
        }
    (tpl_dir / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    if with_preview:
        (tpl_dir / "preview.png").write_bytes(TINY_PNG)

    meta: dict = {
        "type": "template",
        "id": tid,
        "title": title,
        "status": status,
        "sources": sources or ["recipes/rec-unmapped"],
        "panels": [],
        "language": language,
        "chart_types": chart_types or ["volcano"],
        "tags": ["单细胞分析"],
        "favorite": False,
    }
    if primary_method is not None:
        meta["primary_method"] = primary_method
    if aliases:
        meta["aliases"] = aliases
    write_page(
        wiki / "templates" / f"{tid}.md",
        meta,
        f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n测试模板。\n<!-- user:start -->\n<!-- user:end -->\n",
    )


def _write_recipe(wiki: Path, rid: str, *, title: str, item: str, status: str = "ready", chart_types: list[str] | None = None) -> None:
    rec_dir = wiki / "recipes" / rid / "source"
    rec_dir.mkdir(parents=True, exist_ok=True)
    (rec_dir / f"{item}.Rmd").write_text("plot(1:3)\n", encoding="utf-8")
    (wiki / "recipes" / rid / "preview.png").write_bytes(TINY_PNG)
    write_page(
        wiki / "recipes" / f"{rid}.md",
        {
            "type": "recipe",
            "id": rid,
            "title": title,
            "status": status,
            "source": {"id": "figureya", "item": item, "commit": "abc123"},
            "license": "CC-BY-NC-SA-4.0",
            "language": "r",
            "runner": "rmd-knit",
            "entry": f"{item}.Rmd",
            "tags": ["transcriptomics"],
            "chart_types": chart_types or ["volcano"],
            "favorite": False,
        },
        f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n{title}\n<!-- user:start -->\n<!-- user:end -->\n",
    )


@pytest.fixture
def hub_env(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    for folder in ("methods", "templates", "recipes", "interfaces", "scenarios", "projects", "sources", "layouts"):
        (wiki / folder).mkdir(parents=True, exist_ok=True)
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text('{"scenarios": {}}', encoding="utf-8")

    # Interfaces
    write_interface(wiki, "deg-result-table", {"gene": {"type": "str", "description": "基因"}, "log2fc": {"type": "float", "description": "倍数"}}, "差异基因表")
    write_interface(wiki, "highlight-gene-sets", {"gene": {"type": "str", "description": "高亮基因"}}, "高亮基因集")
    write_interface(wiki, "pathway-score-table", {"pathway": {"type": "str", "description": "通路"}, "score": {"type": "float", "description": "打分"}}, "通路打分表")
    write_interface(wiki, "render-de-results", {"gene": {"type": "str", "description": "基因"}}, "火山图渲染表")
    write_interface(wiki, "render-group-heatmap", {"gene": {"type": "str", "description": "基因"}}, "分组热图渲染表")
    write_interface(wiki, "render-group-summaries", {"group": {"type": "str", "description": "分组"}}, "分组摘要渲染表")
    write_interface(wiki, "survival-time-event-group", {"time": {"type": "float", "description": "时间"}}, "生存输入表")

    # Recipes
    _write_recipe(wiki, "rec-shared", title="通用火山图配方", item="FigureYa59volcanov2")
    _write_recipe(wiki, "rec-multi", title="多亚型GSEA与差异共享配方", item="FigureYa109subtypeGSEA")
    _write_recipe(wiki, "rec-hidden", title="被筛选隐藏的配方", item="FigureYaHidden")
    _write_recipe(wiki, "rec-unmapped", title="纯配色工具配方", item="FigureYa28color")

    # Curation hiding rec-hidden (and any template sourced solely from it)
    (wiki / "sources" / "figureya-curation.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "decisions": {
                    "figureya:FigureYaHidden": {"decision": "removed", "updated_at": "2026-11-18T00:00:00+00:00"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # method-map.json with many-to-many & unmapped
    (wiki / "recipes" / "method-map.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "unmapped": ["rec-unmapped"],
                "mappings": {
                    "rec-shared": {
                        "methods": ["differential-expression"],
                        "confidence": "curated",
                        "note": "火山图差异分析源码配方。",
                    },
                    "rec-multi": {
                        "methods": ["differential-expression", "gene-set-enrichment"],
                        "confidence": "curated",
                        "note": "多对多挂载：同时服务差异分析与富集分析。",
                    },
                    "rec-hidden": {
                        "methods": ["differential-expression"],
                        "confidence": "curated",
                        "note": "应被 curation 隐藏过滤。",
                    },
                    "rec-unmapped": {
                        "methods": [],
                        "confidence": "curated",
                        "note": "未映射辅助工具。",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Methods:
    # 1. differential-expression (analysis, multi-domain, with alias, figure_relations, render_bridges, next_steps)
    write_page(
        wiki / "methods/differential-expression.md",
        {
            "type": "method",
            "id": "differential-expression",
            "aliases": ["legacy-de-method"],
            "title": "差异表达分析",
            "status": "ready",
            "tags": ["单细胞分析", "转录组"],
            "data_domains": ["single-cell", "bulk-transcriptomics"],
            "purposes": ["差异与功能分析"],
            "summary": "在对比组之间检验基因表达差异。",
            "data_contract": {"input": "标准化表达矩阵与分组", "output": "deg-result-table"},
            "inputs": [],
            "outputs": ["deg-result-table"],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "method_kind": "analysis",
            "render_bridges": [
                {
                    "interface": "render-de-results",
                    "from_output": "deg-result-table",
                    "extractor_note": "映射 gene/log2FC/p_val_adj 列到火山图渲染长表。",
                    "unit": "基因 × 对比组",
                },
                {
                    "interface": "render-group-heatmap",
                    "from_output": "deg-result-table",
                    "extractor_note": "按分组聚合差异基因平均表达到分组热图长表。",
                },
            ],
            "figure_relations": [
                {
                    "figure": "templates/tpl-de-adaptable",
                    "compatibility": "adaptable",
                    "reason": "需转换为 render-de-results 列名。",
                    "prerequisites": ["group1 单一"],
                    "adaptation": "导出 render-de-results.csv",
                    "evidence": ["methods/differential-expression.md#输出"],
                    "verification": {"state": "not_run", "scope": "仅核对接口", "evidence": []},
                }
            ],
            "next_steps": [
                {
                    "direction": "方向 1：功能富集分析",
                    "when": "已获得显著差异基因列表，需要解析通路富集时",
                    "hypothesis": "差异基因在特定生物通路显著富集",
                    "analysis_templates": ["methods/gene-set-enrichment", "recipes/rec-multi"],
                    "intermediate_interface": "pathway-score-table",
                    "viz_templates": ["templates/tpl-de-primary-unreviewed"],
                },
                {
                    "direction": "方向 2：临床生存队列投射",
                    "when": "评估候选差异靶基因在临床队列中的预后价值时",
                    "analysis_templates": ["methods/survival-prognosis-analysis"],
                    "intermediate_interface": "survival-time-event-group",
                    "viz_templates": ["templates/tpl-km-survival"],
                },
            ],
        },
        "<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n差异表达分析。\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    # 2. gene-set-enrichment (analysis, consumes deg-result-table -> full match)
    write_page(
        wiki / "methods/gene-set-enrichment.md",
        {
            "type": "method",
            "id": "gene-set-enrichment",
            "title": "基因集富集分析",
            "status": "ready",
            "tags": ["单细胞分析", "转录组"],
            "data_domains": ["single-cell", "bulk-transcriptomics"],
            "purposes": ["差异与功能分析"],
            "summary": "ORA 与 GSEA 通路富集分析。",
            "inputs": ["deg-result-table"],
            "outputs": ["pathway-score-table"],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "method_kind": "analysis",
        },
        "<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n通路富集。\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    # 3. survival-prognosis-analysis (analysis, clinical-prognosis, consumes deg-result-table AND survival-time-event-group -> partial match from DE)
    write_page(
        wiki / "methods/survival-prognosis-analysis.md",
        {
            "type": "method",
            "id": "survival-prognosis-analysis",
            "title": "生存与预后分析",
            "status": "ready",
            "tags": ["生存分析"],
            "data_domains": ["clinical-prognosis"],
            "purposes": ["生存与预后建模"],
            "summary": "KM 生存曲线与 Cox 预后建模。",
            "inputs": ["deg-result-table", "survival-time-event-group"],
            "outputs": ["survival-time-event-group"],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "method_kind": "analysis",
        },
        "<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n生存分析。\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    # 4. Hidden / excluded method kinds (technical, workflow, archived) that also declare input=deg-result-table
    for mid, mkind, mstatus in (
        ("tech-de-helper", "technical", "ready"),
        ("wf-de-pipeline", "workflow", "ready"),
        ("archived-de-downstream", "analysis", "archived"),
    ):
        meta = {
            "type": "method",
            "id": mid,
            "title": f"Excluded {mid}",
            "status": mstatus,
            "tags": ["单细胞分析"],
            "data_domains": ["single-cell"],
            "inputs": ["deg-result-table"],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "method_kind": mkind,
        }
        if mstatus == "archived":
            meta["archived_from"] = "ready"
        write_page(
            wiki / "methods" / f"{mid}.md",
            meta,
            "<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n不应出现。\n<!-- user:start -->\n<!-- user:end -->\n",
        )

    # Templates:
    # A. Curated via figure_relation (adaptable) + render_bridged via render-de-results
    _write_template(
        wiki,
        "tpl-de-adaptable",
        title="适配火山图",
        tables={"de": {"interface": "render-de-results", "description": "渲染差异表"}},
        primary_method="differential-expression",
        chart_types=["volcano"],
    )
    # B. Primary method declared ONLY (NO figure_relation) -> MUST remain unreviewed / not_run
    _write_template(
        wiki,
        "tpl-de-primary-unreviewed",
        title="未审查主归属热图",
        tables={"heatmap": {"interface": "render-group-heatmap", "description": "分组热图"}},
        primary_method="differential-expression",
        chart_types=["heatmap"],
    )
    # C. Object-compatible FULL match (required deg-result-table, optional highlight-gene-sets)
    _write_template(
        wiki,
        "tpl-obj-full-optional",
        title="对象全匹配火山图（含可选表）",
        tables={
            "de": {"interface": "deg-result-table", "description": "差异结果"},
            "hl": {"interface": "highlight-gene-sets", "description": "可选高亮", "required": False},
        },
        primary_method="gene-set-enrichment",
        chart_types=["volcano"],
    )
    # D. Object-compatible PARTIAL match (requires deg-result-table AND pathway-score-table)
    _write_template(
        wiki,
        "tpl-obj-partial",
        title="对象部分匹配图（需额外通路表）",
        tables={
            "de": {"interface": "deg-result-table", "description": "差异结果"},
            "pw": {"interface": "pathway-score-table", "description": "通路打分"},
        },
        primary_method="gene-set-enrichment",
        chart_types=["dotplot"],
    )
    # E. Render-bridged PARTIAL match (requires render-group-heatmap AND render-group-summaries)
    _write_template(
        wiki,
        "tpl-bridge-partial",
        title="桥接部分匹配热图",
        tables={
            "hm": {"interface": "render-group-heatmap", "description": "热图长表"},
            "sm": {"interface": "render-group-summaries", "description": "摘要长表"},
        },
        primary_method="gene-set-enrichment",
        chart_types=["heatmap"],
    )
    # F. Downstream KM template for survival-prognosis-analysis
    _write_template(
        wiki,
        "tpl-km-survival",
        title="KM 生存曲线",
        tables={"surv": {"interface": "survival-time-event-group", "description": "生存表"}},
        primary_method="survival-prognosis-analysis",
        chart_types=["km-curve"],
    )
    # G. Excluded templates: archived and curation-hidden
    _write_template(
        wiki,
        "tpl-archived",
        title="已归档模板",
        tables={"de": {"interface": "deg-result-table", "description": "差异结果"}},
        status="ready",
    )
    t_arch_path = wiki / "templates/tpl-archived.md"
    t_arch_meta, t_arch_body = read_page(t_arch_path)
    t_arch_meta["archived_from"] = "ready"
    t_arch_meta["status"] = "archived"
    write_page(t_arch_path, t_arch_meta, t_arch_body)

    _write_template(
        wiki,
        "tpl-curation-hidden",
        title="被 curation 隐藏模板",
        tables={"de": {"interface": "deg-result-table", "description": "差异结果"}},
        sources=["recipes/rec-hidden"],
    )

    cfg_path = write_config(tmp_path / "config.json", wiki)
    cfg = Config(
        wiki,
        gallery,
        taxonomy,
        Path(sys.executable),
        Path("Rscript"),
        8765,
        work_root=tmp_path / "work",
    )
    return cfg, cfg_path, tmp_path


def test_list_method_hubs_filters_canonical_domains_legacy_tags_purposes_and_query(hub_env):
    cfg, _, _ = hub_env
    all_hubs = list_method_hubs(cfg)
    assert all_hubs["total"] == 3
    ids = {m["id"] for m in all_hubs["methods"]}
    assert ids == {"differential-expression", "gene-set-enrichment", "survival-prognosis-analysis"}
    # technical / workflow / archived methods must not appear
    assert "tech-de-helper" not in ids
    assert "wf-de-pipeline" not in ids
    assert "archived-de-downstream" not in ids
    # unmapped recipes reported cleanly without hidden/curation ones
    assert [r["id"] for r in all_hubs["unmapped_recipes"]] == ["rec-unmapped"]
    assert all_hubs["unmapped_recipes_count"] == 1

    with TestClient(create_app(cfg)) as client:
        # 1. Filter by 7-domain canonical slug
        r_bulk = client.get("/api/method-hubs", params={"domain": "bulk-transcriptomics"})
        assert r_bulk.status_code == 200
        assert {m["id"] for m in r_bulk.json()["methods"]} == {
            "differential-expression",
            "gene-set-enrichment",
        }

        # 2. Filter by legacy tag alias
        r_legacy = client.get("/api/method-hubs", params={"domain": "生存分析"})
        assert r_legacy.status_code == 200
        assert [m["id"] for m in r_legacy.json()["methods"]] == ["survival-prognosis-analysis"]

        # 3. Filter by 12-purpose vocabulary
        r_purpose = client.get("/api/method-hubs", params={"purpose": "差异与功能分析"})
        assert r_purpose.status_code == 200
        assert {m["id"] for m in r_purpose.json()["methods"]} == {
            "differential-expression",
            "gene-set-enrichment",
        }

        # 4. Filter by query q
        r_q = client.get("/api/method-hubs", params={"q": "Cox"})
        assert r_q.status_code == 200
        assert [m["id"] for m in r_q.json()["methods"]] == ["survival-prognosis-analysis"]


def test_single_method_hub_attached_viz_semantic_boundary_bridges_and_recipes(hub_env):
    cfg, _, _ = hub_env
    # Resolve via canonical ID AND via legacy alias
    hub_canonical = build_method_hub(cfg, "differential-expression")
    hub_alias = build_method_hub(cfg, "legacy-de-method")
    assert hub_canonical["id"] == "differential-expression"
    assert hub_alias["id"] == "differential-expression"
    assert hub_alias["requested_id"] == "legacy-de-method"

    viz = hub_canonical["attached_visualizations"]

    # 1. Unified curated: includes both templates AND non-duplicated mapped FigureYa visualizations
    curated_by_id = {item["id"]: item for item in viz["curated"]}
    assert set(curated_by_id) == {"tpl-de-adaptable", "tpl-de-primary-unreviewed", "rec-shared", "rec-multi"}
    assert curated_by_id["tpl-de-adaptable"]["compatibility"] == "adaptable"
    assert curated_by_id["tpl-de-adaptable"]["primary"] is True
    assert curated_by_id["tpl-de-adaptable"]["verification"]["state"] == "not_run"
    assert curated_by_id["rec-shared"]["kind"] == "recipe"
    assert curated_by_id["rec-shared"]["compatibility"] == "curated"

    unreviewed = curated_by_id["tpl-de-primary-unreviewed"]
    assert unreviewed["primary"] is True
    assert unreviewed["compatibility"] == "unreviewed"
    assert unreviewed["verification"]["state"] == "not_run"

    # 2. Object compatible: strict full (with optional table!) vs partial, excluding curated/archived/hidden
    obj_by_id = {item["id"]: item for item in viz["object_compatible"]}
    assert "tpl-archived" not in obj_by_id
    assert "tpl-curation-hidden" not in obj_by_id
    assert "tpl-de-adaptable" not in obj_by_id  # curated excluded from object_compatible
    assert obj_by_id["tpl-obj-full-optional"]["match_type"] == "full"
    assert obj_by_id["tpl-obj-full-optional"]["matched_interfaces"] == ["deg-result-table"]
    assert obj_by_id["tpl-obj-full-optional"]["missing_required_interfaces"] == []

    assert obj_by_id["tpl-obj-partial"]["match_type"] == "partial"
    assert obj_by_id["tpl-obj-partial"]["matched_interfaces"] == ["deg-result-table"]
    assert obj_by_id["tpl-obj-partial"]["missing_required_interfaces"] == ["pathway-score-table"]

    # 3. Render bridges: full vs partial
    bridge_by_id = {item["id"]: item for item in viz["render_bridged"]}
    assert bridge_by_id["tpl-de-adaptable"]["via_bridge"] == "render-de-results"
    assert bridge_by_id["tpl-de-adaptable"]["from_output"] == "deg-result-table"
    assert bridge_by_id["tpl-de-adaptable"]["match_type"] == "full"
    assert bridge_by_id["tpl-de-primary-unreviewed"]["via_bridge"] == "render-group-heatmap"
    assert bridge_by_id["tpl-de-primary-unreviewed"]["match_type"] == "full"
    assert bridge_by_id["tpl-bridge-partial"]["match_type"] == "partial"
    assert bridge_by_id["tpl-bridge-partial"]["missing_required_interfaces"] == ["render-group-summaries"]

    # 4. Preview strip deduplicated, curated first, max 6
    preview_ids = [p["id"] for p in viz["all_previews"]]
    assert len(preview_ids) == len(set(preview_ids)) <= 6
    assert preview_ids[:2] == ["tpl-de-adaptable", "tpl-de-primary-unreviewed"]

    # 5. Many-to-many recipes mounted & curation-hidden recipe excluded
    recipe_ids = {r["id"] for r in hub_canonical["reference_recipes"]}
    assert recipe_ids == {"rec-shared", "rec-multi"}
    assert "rec-hidden" not in recipe_ids
    gsea_hub = build_method_hub(cfg, "gene-set-enrichment")
    assert {r["id"] for r in gsea_hub["reference_recipes"]} == {"rec-multi"}

    # 6. HTTP /api/methods/{method_id}/hub supports alias and returns 404 on non-analysis / archived
    with TestClient(create_app(cfg)) as client:
        ok = client.get("/api/methods/legacy-de-method/hub")
        assert ok.status_code == 200
        assert ok.json()["id"] == "differential-expression"
        assert "next" in ok.json()
        assert client.get("/api/methods/tech-de-helper/hub").status_code == 404
        assert client.get("/api/methods/archived-de-downstream/hub").status_code == 404
        assert client.get("/api/methods/does-not-exist/hub").status_code == 404


def test_suggest_next_steps_v2_cli_http_mcp_consistency(hub_env, capsys):
    cfg, cfg_path, _ = hub_env
    import mcp_server

    nxt = suggest_next_steps(cfg, "legacy-de-method")
    # Backward-compatible keys
    assert nxt["node_id"] == "differential-expression"
    assert nxt["requested_id"] == "legacy-de-method"
    assert nxt["kind"] == "method"
    assert nxt["outputs"] == ["deg-result-table"]
    assert len(nxt["next_steps"]) == 2
    assert len(nxt["structural_matches"]) >= 1

    # Additive v2 keys
    assert nxt["schema_version"] == 2
    assert nxt["decision_mode"] == "multi_branch_optional"
    assert nxt["current_node"]["id"] == "differential-expression"
    assert nxt["current_node"]["data_domains"] == ["single-cell", "bulk-transcriptomics"]
    assert nxt["agent_guidance"]

    # Curated branches
    assert len(nxt["curated_branches"]) == 2
    b0 = nxt["curated_branches"][0]
    assert b0["branch_id"]
    assert b0["hypothesis"] == "差异基因在特定生物通路显著富集"
    assert b0["produced_interface"] == "pathway-score-table"
    assert [m["id"] for m in b0["next_methods"]] == ["gene-set-enrichment"]
    assert [r["id"] for r in b0["reference_recipes"]] == ["rec-multi"]
    assert [v["id"] for v in b0["viz_templates"]] == ["tpl-de-primary-unreviewed"]
    assert b0["viz_templates"][0]["compatibility"] == "unreviewed"

    # Object-compatible candidates exclude technical, workflow, archived, curation-hidden
    cand_ids = {c["id"] for c in nxt["object_compatible_candidates"]}
    assert "tech-de-helper" not in cand_ids
    assert "wf-de-pipeline" not in cand_ids
    assert "archived-de-downstream" not in cand_ids
    assert "tpl-archived" not in cand_ids
    assert "tpl-curation-hidden" not in cand_ids

    cand_by_id = {(c["kind"], c["id"]): c for c in nxt["object_compatible_candidates"]}
    assert cand_by_id[("method", "gene-set-enrichment")]["match_type"] == "full"
    assert cand_by_id[("method", "gene-set-enrichment")]["source"] == "object_inferred"
    assert cand_by_id[("method", "survival-prognosis-analysis")]["match_type"] == "partial"
    assert cand_by_id[("method", "survival-prognosis-analysis")]["missing_required_interfaces"] == [
        "survival-time-event-group"
    ]
    assert cand_by_id[("method", "survival-prognosis-analysis")]["downstream_viz"][0]["id"] == "tpl-km-survival"
    assert cand_by_id[("template", "tpl-obj-full-optional")]["match_type"] == "full"
    assert cand_by_id[("template", "tpl-obj-partial")]["match_type"] == "partial"

    # Attached visualizations present on v2 payload (templates + unified FigureYa visualizations)
    assert {item["id"] for item in nxt["attached_visualizations"]["curated"]} == {
        "tpl-de-adaptable",
        "tpl-de-primary-unreviewed",
        "rec-shared",
        "rec-multi",
    }

    # Format text output includes multi-branch guidance & match type
    formatted = format_next_steps(nxt)
    assert "分析假设" in formatted
    assert "[full]" in formatted and "[partial]" in formatted

    # CLI / HTTP / MCP consistency
    assert cli_main(["--config", str(cfg_path), "next", "differential-expression", "--json"]) == 0
    cli_payload = json.loads(capsys.readouterr().out)

    with TestClient(create_app(cfg)) as client:
        http_payload = client.get("/api/next/differential-expression").json()

    mcp_resp = mcp_server.dispatch_mcp_request(
        cfg,
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "rwiki_next", "arguments": {"node_id": "differential-expression"}},
        },
    )
    mcp_payload = mcp_resp["result"]["structuredContent"]

    for key in (
        "schema_version",
        "node_id",
        "decision_mode",
        "curated_branches",
        "object_compatible_candidates",
        "attached_visualizations",
    ):
        assert cli_payload[key] == http_payload[key] == mcp_payload[key]


def test_promoted_template_deduplicates_source_recipe_across_methods(hub_env):
    cfg, _, _ = hub_env
    wiki = cfg.wiki_root
    # Register a mapped recipe rec-shared-converted spanning two methods, and promote it via fy-converted
    _write_recipe(wiki, "rec-converted", title="多方法转换测试配方", item="FigureYaConverted")
    mmap_path = wiki / "recipes" / "method-map.json"
    mmap = json.loads(mmap_path.read_text(encoding="utf-8"))
    mmap["mappings"]["rec-converted"] = {
        "methods": ["differential-expression", "gene-set-enrichment"],
        "confidence": "curated",
        "note": "已被 fy-converted 模板化的多方法配方。",
    }
    mmap_path.write_text(json.dumps(mmap, ensure_ascii=False, indent=2), encoding="utf-8")

    _write_template(
        wiki,
        "fy-converted",
        title="原生转换图",
        tables={"de": {"interface": "render-de-results", "description": "渲染差异表"}},
        primary_method="differential-expression",
        sources=["recipes/rec-converted"],
        chart_types=["volcano"],
    )

    de_curated = {item["id"]: item for item in build_method_hub(cfg, "differential-expression")["attached_visualizations"]["curated"]}
    gse_curated = {item["id"]: item for item in build_method_hub(cfg, "gene-set-enrichment")["attached_visualizations"]["curated"]}
    assert "fy-converted" in de_curated and de_curated["fy-converted"]["kind"] == "template"
    assert "rec-converted" not in de_curated
    assert "fy-converted" in gse_curated and gse_curated["fy-converted"]["kind"] == "template"
    assert "rec-converted" not in gse_curated
    assert "rec-multi" in gse_curated and gse_curated["rec-multi"]["kind"] == "recipe"


"""Tests for Research Wiki v5 unified template style_tier/journal_style & scenario step requires."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import write_config
from rwiki.config import Config
from rwiki.finder import catalog_records
from rwiki.lint import lint
from rwiki.pages import write_page
from rwiki.server import create_app


def _make_minimal_wiki(tmp_path: Path) -> Config:
    wiki = tmp_path / "wiki"
    for folder in (
        "methods",
        "templates",
        "recipes",
        "interfaces",
        "scenarios",
        "projects",
        "sources",
        "layouts",
        "chart-types",
    ):
        (wiki / folder).mkdir(parents=True, exist_ok=True)
    gallery = tmp_path / "gallery"
    gallery.mkdir(exist_ok=True)
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text('{"scenarios": {"single-cell": {"label": "单细胞分析"}}}', encoding="utf-8")
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
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "method_kind": "analysis",
            "purposes": ["注释与参考映射"],
            "summary": "测试细胞类型注释分析家族。",
            "data_contract": {"input": "标准 Seurat 对象", "output": "带细胞类型标签的元数据表"},
        },
        "# 细胞类型注释\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    return Config(wiki, gallery, taxonomy, Path(sys.executable), Path("Rscript"), 8765, work_root=tmp_path / "work")


def _write_template(wiki: Path, tid: str, extra_meta: dict) -> None:
    meta = {
        "type": "template",
        "id": tid,
        "title": f"模板 {tid}",
        "status": "draft",
        "layouts": [],
        "sources": ["methods/cell-type-annotation"],
        "panels": [],
        "language": "r",
        "primary_method": "cell-type-annotation",
        "tags": ["single-cell"],
        "chart_types": ["umap"],
        "favorite": False,
        **extra_meta,
    }
    write_page(
        wiki / f"templates/{tid}.md",
        meta,
        f"# 模板 {tid}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n测试\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    tdir = wiki / "templates" / tid
    (tdir / "code").mkdir(parents=True, exist_ok=True)
    (tdir / "code" / "render.R").write_text("# test render\n", encoding="utf-8")
    (tdir / "spec.json").write_text(
        json.dumps(
            {
                "entry": "code/render.R",
                "language": "r",
                "tables": {
                    "main": {
                        "interface": None,
                        "description": "主输入表",
                        "columns": {"x": {"type": "str", "description": "x"}},
                    }
                },
                "style": {},
            }
        ),
        encoding="utf-8",
    )


def test_template_style_tier_and_journal_style_validation(tmp_path: Path):
    cfg = _make_minimal_wiki(tmp_path)
    _write_template(cfg.wiki_root, "tpl-default", {"style_tier": "default", "journal_style": "Cai2026-npjPO"})
    _write_template(cfg.wiki_root, "tpl-variant", {"style_tier": "variant", "journal_style": "Cai2026-npjPO"})

    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert errors == []

    _write_template(cfg.wiki_root, "tpl-bad-tier", {"style_tier": "gold"})
    _write_template(cfg.wiki_root, "tpl-bad-journal", {"style_tier": "variant", "journal_style": ""})

    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert any("templates/tpl-bad-tier.md" in e and "style_tier" in e for e in errors)
    assert any("templates/tpl-bad-journal.md" in e and "journal_style" in e for e in errors)


def test_scenario_step_requires_validation(tmp_path: Path):
    cfg = _make_minimal_wiki(tmp_path)
    write_page(
        cfg.wiki_root / "scenarios/test-playbook.md",
        {
            "type": "scenario",
            "id": "test-playbook",
            "title": "测试分支树",
            "picks": [{"id": "methods/cell-type-annotation", "note": "注释"}],
            "steps": [
                {
                    "id": "branch-7",
                    "title": "空间微环境汇合",
                    "method_id": "cell-type-annotation",
                    "requires": ["scrna-annotated-cells", "visium-spatial-object"],
                    "next_steps": [],
                }
            ],
        },
        "# 测试分支树\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert errors == []

    write_page(
        cfg.wiki_root / "scenarios/bad-playbook.md",
        {
            "type": "scenario",
            "id": "bad-playbook",
            "title": "非法 requires 分支树",
            "picks": [],
            "steps": [
                {"id": "s1", "title": "bad1", "requires": "scrna-annotated-cells"},
                {"id": "s2", "title": "bad2", "requires": [""]},
            ],
        },
        "# 非法\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert any("scenarios/bad-playbook.md" in e and "steps[0].requires" in e for e in errors)
    assert any("scenarios/bad-playbook.md" in e and "steps[1].requires" in e for e in errors)


def test_catalog_record_exposes_style_tier_and_journal_style(tmp_path: Path):
    cfg = _make_minimal_wiki(tmp_path)
    _write_template(cfg.wiki_root, "tpl-styled", {"style_tier": "variant", "journal_style": "Cai2026-npjPO"})
    _write_template(cfg.wiki_root, "tpl-plain", {})

    by_id = {rec["id"]: rec for rec in catalog_records(cfg) if rec["kind"] == "template"}
    assert by_id["tpl-styled"]["style_tier"] == "variant"
    assert by_id["tpl-styled"]["journal_style"] == "Cai2026-npjPO"
    assert "style_tier" not in by_id["tpl-plain"]


def test_server_exposes_style_tier_journal_style_and_requires(tmp_path: Path):
    cfg = _make_minimal_wiki(tmp_path)
    _write_template(cfg.wiki_root, "tpl-styled", {"style_tier": "default", "journal_style": "Cai2026-npjPO"})
    write_page(
        cfg.wiki_root / "scenarios/stromal-playbook.md",
        {
            "type": "scenario",
            "id": "stromal-playbook",
            "title": "基质微环境分支树",
            "picks": [],
            "steps": [
                {
                    "id": "b7",
                    "title": "空转汇合分支",
                    "method_id": "cell-type-annotation",
                    "templates": ["tpl-styled"],
                    "requires": ["scrna-annotated-cells", "visium-spatial-object"],
                    "next_steps": [],
                }
            ],
        },
        "# 基质微环境分支树\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    with TestClient(create_app(cfg)) as client:
        pages_resp = client.get("/api/pages")
        assert pages_resp.status_code == 200
        tpl = next(p for p in pages_resp.json() if p["path"] == "templates/tpl-styled.md")
        assert tpl["meta"]["style_tier"] == "default"
        assert tpl["meta"]["journal_style"] == "Cai2026-npjPO"
        assert tpl["style_tier"] == "default"
        assert tpl["journal_style"] == "Cai2026-npjPO"

        pb_resp = client.get("/api/playbooks")
        assert pb_resp.status_code == 200
        pb = next(x for x in pb_resp.json()["playbooks"] if x["id"] == "stromal-playbook")
        assert pb["steps"][0]["requires"] == ["scrna-annotated-cells", "visium-spatial-object"]


def test_lint_rejects_duplicate_default_style_tier_per_primary_method(tmp_path: Path):
    cfg = _make_minimal_wiki(tmp_path)
    _write_template(cfg.wiki_root, "tpl-default-a", {"style_tier": "default", "journal_style": "StyleA"})
    _write_template(cfg.wiki_root, "tpl-default-b", {"style_tier": "default", "journal_style": "StyleB"})

    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert any("templates/tpl-default-a.md" in e and "style_tier: default" in e for e in errors)
    assert any("templates/tpl-default-b.md" in e and "style_tier: default" in e for e in errors)


def test_playbooks_respect_explicit_empty_next_and_typed_refs_and_subtree(tmp_path: Path):
    cfg = _make_minimal_wiki(tmp_path)
    _write_template(cfg.wiki_root, "tpl-styled", {"style_tier": "default", "journal_style": "Cai2026-npjPO"})
    write_page(
        cfg.wiki_root / "scenarios/branch-playbook.md",
        {
            "type": "scenario",
            "id": "branch-playbook",
            "title": "显式终结分支与子树测试",
            "picks": [],
            "steps": [
                {
                    "id": "branch-a",
                    "title": "终端分支 A",
                    "method_id": "cell-type-annotation",
                    "templates": ["methods/cell-type-annotation", "templates/tpl-styled"],
                    "next_steps": [],
                },
                {
                    "id": "branch-b",
                    "title": "子树汇合分支 B",
                    "method_id": "cell-type-annotation",
                    "subtree": "scenarios/sub-tree",
                    "requires": ["scrna-annotated-cells", "visium-spatial-object"],
                    "next_steps": [],
                },
            ],
        },
        "# 分支测试\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    with TestClient(create_app(cfg)) as client:
        data = client.get("/api/playbooks").json()
        graph = data["graph"]
        edges = {(e["source"], e["target"], e["label"]) for e in graph["edges"]}
        node_paths = {n["id"]: n["path"] for n in graph["nodes"]}
        assert ("branch-a", "branch-b", "next") not in edges
        assert ("branch-b", "sub-tree", "subtree") in edges
        assert node_paths["tpl-styled"] == "templates/tpl-styled.md"
        assert not any(p.startswith("templates/templates/") for p in node_paths.values())
        pb = next(x for x in data["playbooks"] if x["id"] == "branch-playbook")
        assert pb["steps"][1]["subtree"] == "scenarios/sub-tree"
        assert "_has_explicit_next" not in pb["steps"][0]

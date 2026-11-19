"""Tests for v5.1 Backend Governance & Batch-Confirm API."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from conftest import complete_sections, write_config, write_interface
from rwiki.config import Config
from rwiki.dedup import assert_no_high_duplicate, check_duplicates
from rwiki.errors import WikiError
from rwiki.facts import method_facts, refresh_facts
from rwiki.lint import lint
from rwiki.pages import get_block, read_page, write_page
from rwiki.search import export_index, rank_export, search
from rwiki.server import create_app
from rwiki.store import init, save
from rwiki.studio import get_playbooks
from rwiki.templates import verify_template


def _make_git_wiki(tmp_path: Path) -> Config:
    wiki = tmp_path / "wiki"
    gallery = tmp_path / "gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text(
        json.dumps({"scenarios": {"single-cell": {"label": "单细胞分析"}}}, ensure_ascii=False),
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
    write_interface(
        wiki,
        "deg-table",
        {"gene": {"type": "str", "description": "基因"}, "log2fc": {"type": "float", "description": "倍数"}},
        "差异基因表",
    )
    write_page(
        wiki / "methods/cell-type-annotation.md",
        {
            "type": "method",
            "id": "cell-type-annotation",
            "title": "细胞类型注释",
            "status": "draft",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": ["deg-table"],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "method_kind": "analysis",
            "purposes": ["注释与参考映射"],
            "summary": "单细胞类型注释方法。",
            "data_contract": {"input": "单细胞表达矩阵", "output": "deg-table"},
        },
        "# 细胞类型注释\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        "## 用途\n注释。\n\n## 适用\n单细胞。\n\n## 不适用\n无。\n\n"
        "## 输入\n无。\n\n## 怎么做\n步骤。\n\n## 代码\n无。\n\n"
        "## 输出\ndeg-table。\n\n## 知识关联检查\n无图原因：测试夹具。\n\n"
        "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    save(cfg, "init v51 test wiki")
    return cfg


def _write_python_template(
    cfg: Config,
    tid: str,
    *,
    title: str | None = None,
    chart_types: list[str] | None = None,
    style_tier: str | None = None,
    journal_style: str | None = None,
    status: str = "draft",
    with_verifiable_code: bool = False,
) -> Path:
    wiki = cfg.wiki_root
    meta: dict = {
        "type": "template",
        "id": tid,
        "title": title or f"模板 {tid}",
        "status": status,
        "layouts": [],
        "sources": ["methods/cell-type-annotation"],
        "panels": [],
        "language": "python",
        "primary_method": "cell-type-annotation",
        "tags": ["single-cell"],
        "chart_types": chart_types if chart_types is not None else ["umap"],
        "favorite": False,
    }
    if style_tier is not None:
        meta["style_tier"] = style_tier
    if journal_style is not None:
        meta["journal_style"] = journal_style

    page = wiki / f"templates/{tid}.md"
    write_page(
        page,
        meta,
        f"# {meta['title']}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        "## 适用\n单细胞特征分布展示。\n\n"
        "## 不适用\n非单细胞矩阵。\n\n"
        "## 知识关联检查\n绑定 cell-type-annotation。\n\n"
        "## 数据要求\n\n模板化后生成。\n\n"
        "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    tdir = wiki / "templates" / tid
    (tdir / "code").mkdir(parents=True, exist_ok=True)
    (tdir / "example").mkdir(parents=True, exist_ok=True)
    (tdir / "example/deg-table.csv").write_text("gene,log2fc\nTP53,1.8\n", encoding="utf-8")
    (tdir / "spec.json").write_text(
        json.dumps(
            {
                "entry": "code/render.py",
                "panel": "code/panel.py",
                "language": "python",
                "tables": {"deg": {"interface": "deg-table", "description": "差异表"}},
                "style": {"palette": "NPG"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tdir / "code/__init__.py").write_text("", encoding="utf-8")
    (tdir / "code/panel.py").write_text("def draw(*args, **kwargs):\n    pass\n", encoding="utf-8")
    if with_verifiable_code:
        (tdir / "code/render.py").write_text(
            "import argparse\n"
            "from pathlib import Path\n"
            "from PIL import Image\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--data', type=Path)\n"
            "p.add_argument('--out', type=Path)\n"
            "p.add_argument('--style', type=Path)\n"
            "a = p.parse_args()\n"
            "a.out.mkdir(parents=True, exist_ok=True)\n"
            "Image.new('RGB', (8, 8), 'red').save(a.out / 'figure.png')\n"
            "(a.out / 'figure.svg').write_text('<svg/>', encoding='utf-8')\n"
            "(a.out / 'figure.pdf').write_text('%PDF-1.4', encoding='utf-8')\n",
            encoding="utf-8",
        )
    else:
        (tdir / "code/render.py").write_text("print('stub')\n", encoding="utf-8")
    return page


# ------------------------------------------------------------------ 1. Scenario DAG Topology & Default Uniqueness


def test_scenario_dag_topology_lint_valid_and_broken_refs_and_cycles(tmp_path: Path):
    cfg = _make_git_wiki(tmp_path)
    wiki = cfg.wiki_root

    write_page(
        wiki / "scenarios/sub-flow.md",
        {"type": "scenario", "id": "sub-flow", "title": "子分支", "picks": []},
        "# 子分支\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    write_page(
        wiki / "scenarios/valid-dag.md",
        {
            "type": "scenario",
            "id": "valid-dag",
            "title": "合法 DAG",
            "picks": [],
            "steps": [
                {"id": "s1", "title": "Step 1", "next_steps": ["s2"]},
                {"id": "s2", "title": "Step 2", "subtree": "scenarios/sub-flow", "next_steps": []},
            ],
        },
        "# 合法 DAG\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert errors == []

    # Broken next_steps target, broken subtree, and cycle
    write_page(
        wiki / "scenarios/bad-next.md",
        {
            "type": "scenario",
            "id": "bad-next",
            "title": "断链 next",
            "picks": [],
            "steps": [
                {"id": "s1", "title": "Step 1", "next_steps": ["missing-step"]},
            ],
        },
        "# 断链\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    write_page(
        wiki / "scenarios/bad-subtree.md",
        {
            "type": "scenario",
            "id": "bad-subtree",
            "title": "断链 subtree",
            "picks": [],
            "steps": [
                {"id": "s1", "title": "Step 1", "subtree": "scenarios/no-such-scenario", "next_steps": []},
            ],
        },
        "# 断链子树\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    write_page(
        wiki / "scenarios/cyclic-dag.md",
        {
            "type": "scenario",
            "id": "cyclic-dag",
            "title": "有向环",
            "picks": [],
            "steps": [
                {"id": "a", "title": "A", "next_steps": ["b"]},
                {"id": "b", "title": "B", "next_steps": ["a"]},
            ],
        },
        "# 有向环\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    # Archived scenario with broken refs/cycle should be ignored
    write_page(
        wiki / "scenarios/archived-bad.md",
        {
            "type": "scenario",
            "id": "archived-bad",
            "title": "归档环",
            "status": "archived",
            "picks": [],
            "steps": [
                {"id": "x", "title": "X", "next_steps": ["x", "ghost"], "subtree": "scenarios/nope"},
            ],
        },
        "# 归档\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert any("scenarios/bad-next.md" in e and "missing-step" in e for e in errors)
    assert any("scenarios/bad-subtree.md" in e and "no-such-scenario" in e for e in errors)
    assert any("scenarios/cyclic-dag.md" in e and ("环" in e or "cycle" in e.lower()) for e in errors)
    assert not any("scenarios/archived-bad.md" in e for e in errors)


def test_default_style_tier_allows_one_per_chart_type_and_rejects_same_chart_type(tmp_path: Path):
    cfg = _make_git_wiki(tmp_path)
    _write_python_template(cfg, "tpl-umap-default", chart_types=["umap"], style_tier="default", journal_style="StyleA")
    _write_python_template(cfg, "tpl-heat-default", chart_types=["heatmap"], style_tier="default", journal_style="StyleA")

    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert errors == []

    _write_python_template(cfg, "tpl-umap-dup", chart_types=["umap"], style_tier="default", journal_style="StyleB")
    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert any("templates/tpl-umap-default.md" in e and "style_tier: default" in e for e in errors)
    assert any("templates/tpl-umap-dup.md" in e and "style_tier: default" in e for e in errors)
    assert not any("templates/tpl-heat-default.md" in e for e in errors)


# ------------------------------------------------------------------ 2. External Requires Computation


def test_get_playbooks_computes_external_requires(tmp_path: Path):
    cfg = _make_git_wiki(tmp_path)
    write_page(
        cfg.wiki_root / "scenarios/spatial-playbook.md",
        {
            "type": "scenario",
            "id": "spatial-playbook",
            "title": "空转联合分析分支树",
            "picks": [],
            "steps": [
                {
                    "id": "s1-anno",
                    "title": "单细胞注释",
                    "method_id": "cell-type-annotation",
                    "interface": "scrna-annotated-cells",
                    "outputs": ["deg-table"],
                    "requires": ["raw-counts-h5"],
                    "next_steps": ["s2-spatial"],
                },
                {
                    "id": "s2-spatial",
                    "title": "空转微环境汇合",
                    "method_id": "cell-type-annotation",
                    "requires": ["scrna-annotated-cells", "deg-table", "visium-spatial-object"],
                    "next_steps": [],
                },
            ],
        },
        "# 分支树\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    data = get_playbooks(cfg)
    pb = next(x for x in data["playbooks"] if x["id"] == "spatial-playbook")
    assert pb["steps"][0]["external_requires"] == ["raw-counts-h5"]
    assert pb["steps"][1]["requires"] == ["scrna-annotated-cells", "deg-table", "visium-spatial-object"]
    assert pb["steps"][1]["external_requires"] == ["visium-spatial-object"]

    with TestClient(create_app(cfg)) as client:
        resp = client.get("/api/playbooks")
        assert resp.status_code == 200
        api_pb = next(x for x in resp.json()["playbooks"] if x["id"] == "spatial-playbook")
        assert api_pb["steps"][1]["external_requires"] == ["visium-spatial-object"]


# ------------------------------------------------------------------ 3. Style-Aware Dedup


def test_style_aware_dedup_downgrades_different_journal_style(tmp_path: Path):
    cfg = _make_git_wiki(tmp_path)
    _write_python_template(
        cfg,
        "cai-stromal-umap",
        title="基质亚群分面降维图谱",
        chart_types=["umap"],
        style_tier="default",
        journal_style="Cai2026-npjPO",
    )

    # Same journal_style (or empty) with high similarity -> stays high & blocked
    same_style = check_duplicates(
        cfg,
        kind="template",
        entry_id="cai-stromal-umap",
        title="基质亚群分面降维图谱变体",
        primary_method="cell-type-annotation",
        chart_types=["umap"],
        interfaces=["deg-table"],
        journal_style="Cai2026-npjPO",
    )
    assert same_style["blocked"] is True
    assert same_style["candidates"][0]["severity"] == "high"

    # Different non-empty journal_style, distinct ID & non-exact title -> downgraded to medium with reason
    diff_style = check_duplicates(
        cfg,
        kind="template",
        entry_id="nature-stromal-umap",
        title="基质亚群分面降维图谱变体",
        primary_method="cell-type-annotation",
        chart_types=["umap"],
        interfaces=["deg-table"],
        journal_style="Nature2025",
    )
    assert diff_style["blocked"] is False
    assert diff_style["high_count"] == 0
    cand = diff_style["candidates"][0]
    assert cand["severity"] == "medium"
    assert "不同期刊画风变体，可按 variant 共存" in cand["reasons"]

    # Same entry_id collision stays blocked even with a different journal_style
    same_id_diff_style = check_duplicates(
        cfg,
        kind="template",
        entry_id="cai-stromal-umap",
        title="基质亚群分面降维图谱变体",
        primary_method="cell-type-annotation",
        chart_types=["umap"],
        interfaces=["deg-table"],
        journal_style="Nature2025",
    )
    assert same_id_diff_style["blocked"] is True

    # assert_no_high_duplicate passes when different journal_style + distinct ID is provided, raises when same
    report = assert_no_high_duplicate(
        cfg,
        kind="template",
        entry_id="nature-stromal-umap",
        title="基质亚群分面降维图谱变体",
        primary_method="cell-type-annotation",
        chart_types=["umap"],
        interfaces=["deg-table"],
        journal_style="Nature2025",
    )
    assert report["blocked"] is False

    with pytest.raises(WikiError, match="入库查重发现高相似既有条目"):
        assert_no_high_duplicate(
            cfg,
            kind="template",
            entry_id="cai-stromal-umap",
            title="基质亚群分面降维图谱变体",
            primary_method="cell-type-annotation",
            chart_types=["umap"],
            interfaces=["deg-table"],
            journal_style="Cai2026-npjPO",
        )

    # Exact title remains high even with a different journal_style
    exact_diff = check_duplicates(
        cfg,
        kind="template",
        entry_id="other-umap-id",
        title="基质亚群分面降维图谱",
        primary_method="cell-type-annotation",
        chart_types=["umap"],
        journal_style="Nature2025",
    )
    assert exact_diff["blocked"] is True
    assert exact_diff["candidates"][0]["severity"] == "high"


# ------------------------------------------------------------------ 4. Panel Coverage Manifest


def test_panel_manifest_validation_and_facts(tmp_path: Path):
    from rwiki.panel_manifest import load_panel_manifest, manifest_facts_lines

    cfg = _make_git_wiki(tmp_path)
    _write_python_template(cfg, "tpl-fig1a", chart_types=["umap"])
    _write_python_template(cfg, "tpl-fig2a", chart_types=["heatmap"])

    wf_path = cfg.wiki_root / "methods/demo-paper-workflow.md"
    write_page(
        wf_path,
        {
            "type": "method",
            "id": "demo-paper-workflow",
            "title": "示例文献复刻流程",
            "status": "draft",
            "method_kind": "workflow",
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Demo 2026"],
            "favorite": False,
            "summary": "示例文献复刻流程摘要。",
            "data_contract": {"input": "原始单细胞与空转数据", "output": "复刻图表"},
        },
        "# 示例文献复刻流程\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        "## 用途\n测试。\n\n## 适用\n测试。\n\n## 不适用\n无。\n\n"
        "## 输入\n无。\n\n## 怎么做\n步骤。\n\n## 代码\n无。\n\n"
        "## 输出\n无。\n\n## 知识关联检查\n无。\n\n"
        "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    manifest_dir = cfg.wiki_root / "methods/demo-paper-workflow"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "panel-manifest.yaml"
    manifest_payload = {
        "schema_version": 1,
        "paper_id": "2026-demo-paper",
        "doi": "10.1000/demo.2026",
        "license": "CC-BY-4.0",
        "panels": [
            {"figure": "Fig. 1", "panel": "1A", "evidence_tier": "original_table", "template_id": "tpl-fig1a", "methods": ["cell-type-annotation"]},
            {"figure": "Fig. 1", "panel": "1B", "evidence_tier": "local_recompute", "template_id": "tpl-fig1a"},
            {"figure": "Fig. 2", "panel": "2A", "evidence_tier": "proxy", "template_id": "tpl-fig2a"},
            {"figure": "Fig. 2", "panel": "2B", "evidence_tier": "excluded_wet_lab", "template_id": None, "note": "wet lab"},
        ],
    }
    manifest_file.write_text(yaml.safe_dump(manifest_payload, allow_unicode=True), encoding="utf-8")

    loaded = load_panel_manifest(manifest_file)
    assert loaded["paper_id"] == "2026-demo-paper"
    assert len(loaded["panels"]) == 4

    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert errors == []

    lines = manifest_facts_lines(cfg, wf_path)
    assert lines == ["- 面板覆盖清单：2 张图 / 4 条面板条目（实测/补表 1、本地重算 1、代理 1、剔除湿实验 1），引用 2 套去重模板"]

    meta, _ = read_page(wf_path)
    facts_text = method_facts(cfg, meta)
    assert "- 面板覆盖清单：2 张图 / 4 条面板条目（实测/补表 1、本地重算 1、代理 1、剔除湿实验 1），引用 2 套去重模板" in facts_text

    refresh_facts(cfg)
    _, updated_body = read_page(wf_path)
    assert "面板覆盖清单：2 张图 / 4 条面板条目" in get_block(updated_body, "facts")

    # Broken manifest: invalid tier, empty panel, missing template_id target
    bad_payload = {
        "paper_id": "2026-demo-paper",
        "doi": "10.1000/demo.2026",
        "license": "CC-BY-4.0",
        "panels": [
            {"figure": "Fig. 1", "panel": "", "evidence_tier": "invalid_tier", "template_id": "missing-tpl"},
        ],
    }
    manifest_file.write_text(yaml.safe_dump(bad_payload, allow_unicode=True), encoding="utf-8")
    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert any("methods/demo-paper-workflow.md" in e and "panel" in e for e in errors)
    assert any("methods/demo-paper-workflow.md" in e and "evidence_tier" in e for e in errors)
    assert any("methods/demo-paper-workflow.md" in e and "missing-tpl" in e for e in errors)


# ------------------------------------------------------------------ 5. Template Single & Batch Confirm API + Search Tie-Break


def test_template_single_and_batch_confirm_api(tmp_path: Path):
    cfg = _make_git_wiki(tmp_path)
    p1 = _write_python_template(cfg, "tpl-confirm-1", with_verifiable_code=True)
    p2 = _write_python_template(cfg, "tpl-confirm-2", with_verifiable_code=True)
    p3 = _write_python_template(cfg, "tpl-unverified", with_verifiable_code=False)
    save(cfg, "add templates for confirm tests")

    verify_template(cfg, "tpl-confirm-1")
    verify_template(cfg, "tpl-confirm-2")

    with TestClient(create_app(cfg)) as client:
        # Single confirm
        r_single = client.post("/api/templates/tpl-confirm-1/confirm")
        assert r_single.status_code == 200, r_single.text
        assert read_page(p1)[0]["status"] == "ready"
        assert (p1.with_suffix("") / "acceptance.json").is_file()

        # Re-confirming ready template fails with 409
        assert client.post("/api/templates/tpl-confirm-1/confirm").status_code == 409

        # Batch confirm must reject confirmed=False with 422
        r_unconfirmed = client.post(
            "/api/templates/batch-confirm",
            json={"ids": ["tpl-confirm-2"], "confirmed": False},
        )
        assert r_unconfirmed.status_code == 422

        # Batch confirm atomic failure if any template is unverified
        r_atomic = client.post(
            "/api/templates/batch-confirm",
            json={"ids": ["tpl-confirm-2", "tpl-unverified"], "confirmed": True},
        )
        assert r_atomic.status_code == 409
        assert read_page(p2)[0]["status"] == "draft"
        assert read_page(p3)[0]["status"] == "draft"

        # Batch confirm succeeds when all templates pass gates
        r_batch = client.post(
            "/api/templates/batch-confirm",
            json={"ids": ["tpl-confirm-2"], "confirmed": True},
        )
        assert r_batch.status_code == 200, r_batch.text
        assert r_batch.json() == {"confirmed": ["tpl-confirm-2"], "count": 1}
        assert read_page(p2)[0]["status"] == "ready"


def test_search_rank_export_tie_breaks_ready_and_default_first(tmp_path: Path):
    cfg = _make_git_wiki(tmp_path)
    _write_python_template(
        cfg,
        "a-draft-variant",
        title="唯一检索词 xyzstyleprobe",
        style_tier="variant",
        journal_style="StyleA",
        status="draft",
    )
    _write_python_template(
        cfg,
        "b-ready-variant",
        title="唯一检索词 xyzstyleprobe",
        style_tier="variant",
        journal_style="StyleB",
        status="ready",
    )
    _write_python_template(
        cfg,
        "c-ready-default",
        title="唯一检索词 xyzstyleprobe",
        style_tier="default",
        journal_style="StyleC",
        status="ready",
    )

    exported = export_index(cfg)
    ranked = rank_export(exported, "xyzstyleprobe", kind="template")
    assert [r["id"] for r in ranked] == ["c-ready-default", "b-ready-variant", "a-draft-variant"]

    live = search(cfg, "xyzstyleprobe", kind="template")["results"]
    assert [r["id"] for r in live] == ["c-ready-default", "b-ready-variant", "a-draft-variant"]


def test_batch_confirm_rejects_non_template_ids(tmp_path: Path):
    cfg = _make_git_wiki(tmp_path)
    with TestClient(create_app(cfg)) as client:
        resp = client.post(
            "/api/templates/batch-confirm",
            json={"ids": ["cell-type-annotation"], "confirmed": True},
        )
        assert resp.status_code == 400
        assert read_page(cfg.wiki_root / "methods/cell-type-annotation.md")[0]["status"] == "draft"


def test_lint_catches_duplicate_step_ids_and_implicit_hybrid_cycle(tmp_path: Path):
    cfg = _make_git_wiki(tmp_path)
    write_page(
        cfg.wiki_root / "scenarios/implicit-cycle.md",
        {
            "type": "scenario",
            "id": "implicit-cycle",
            "title": "隐式顺序边环测试",
            "picks": [],
            "steps": [
                {"id": "s1", "title": "S1", "method_id": "cell-type-annotation"},
                {"id": "s2", "title": "S2", "method_id": "cell-type-annotation", "next_steps": ["s1"]},
                {"id": "s2", "title": "S2 dup", "method_id": "cell-type-annotation", "next_steps": []},
            ],
        },
        "# 环测试\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert any("重复节点 ID" in e for e in errors)
    assert any("存在有向环" in e for e in errors)


def test_panel_manifest_guards_unhashable_tier_duplicates_and_bad_method(tmp_path: Path):
    from rwiki.panel_manifest import manifest_facts_lines, panel_manifest_errors

    cfg = _make_git_wiki(tmp_path)
    _write_python_template(cfg, "tpl-valid", chart_types=["umap"])
    wf_dir = cfg.wiki_root / "methods/wf-bad-manifest"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "panel-manifest.yaml").write_text(
        """
doi: "10.1000/test"
panels:
  - figure: "Fig. 1"
    panel: "1A"
    evidence_tier: ["proxy"]
    template_id: "tpl-valid"
    methods: ["nonexistent-method"]
  - figure: "Fig. 1"
    panel: "1A"
    evidence_tier: "proxy"
    template_id: "tpl-valid"
""",
        encoding="utf-8",
    )
    errs = panel_manifest_errors(cfg, "wf-bad-manifest")
    assert any("evidence_tier 非法" in e for e in errs)
    assert any("nonexistent-method" in e for e in errs)
    assert any("重复面板条目" in e for e in errs)
    lines = manifest_facts_lines(cfg, "wf-bad-manifest")
    assert len(lines) == 1 and "面板条目" in lines[0]


def test_project_tracker_parses_stage_headings_and_finder_formats_style_tier_and_inline_columns(tmp_path: Path):
    from rwiki.finder import format_find, format_show, show
    from rwiki.project_tracker import parse_steps

    stage_md = (
        "## 走线\n"
        "### Stage 1（Main Fig. 1）：多中心整合\n"
        "- **【所用分析方法与可切换模板】**：[[templates/stromal-hull-umap]]\n"
        "- **【原文结论与本地小规模边界】**：小规模子集验证。\n"
        "- **【触发下一步分叉】**：进入 Stage 2。\n"
        "### Stage 2（Main Fig. 2）：空间对齐\n"
        "- **【所用模板】**：[[templates/spatial-feature-grid]]\n"
    )
    parsed = parse_steps(stage_md)
    assert len(parsed) == 2
    assert parsed[0]["step"] == 1 and "stromal-hull-umap" in parsed[0]["templates"]
    assert parsed[0]["observation"] == "小规模子集验证。"
    assert parsed[0]["next_branch"] == "进入 Stage 2。"
    assert parsed[1]["step"] == 2
    assert parsed[1]["observation"] == ""

    cfg = _make_git_wiki(tmp_path)
    _write_python_template(cfg, "tpl-inline-cols", chart_types=["heatmap"], style_tier="default", journal_style="Cai2026-npjPO")
    spec_path = cfg.wiki_root / "templates/tpl-inline-cols/spec.json"
    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    tkey = next(iter(spec_data["tables"]))
    spec_data["tables"][tkey]["interface"] = ""
    spec_data["tables"][tkey]["filename"] = "roe_cox_input.csv"
    spec_data["tables"][tkey]["columns"] = {
        "canonical_subcluster": {"type": "str", "description": "亚群", "required": True},
        "tcga_HR": {"type": "float", "description": "HR", "required": False},
    }
    spec_path.write_text(json.dumps(spec_data, ensure_ascii=False), encoding="utf-8")

    detail = show(cfg, "tpl-inline-cols")
    shown = format_show(detail)
    assert "主推默认 (default)" in shown
    assert "Cai2026-npjPO" in shown
    assert "roe_cox_input.csv" in shown
    assert "canonical_subcluster" in shown
    assert "→ 接口 ：" not in shown

    found_txt = format_find(
        [
            {
                "id": "tpl-inline-cols",
                "kind": "template",
                "level": "L2",
                "status": "ready",
                "usable": True,
                "style_tier": "default",
                "journal_style": "Cai2026-npjPO",
                "title": "测试模板",
                "why": ["正文 BM25"],
                "use": "wiki.py use tpl-inline-cols --project <课题目录>",
            }
        ]
    )
    assert "绘图模板" in found_txt
    assert "主推默认" in found_txt
    assert "Cai2026-npjPO" in found_txt
    assert "[L2" not in found_txt


def test_suggest_next_steps_inherits_downstream_compat_splits_mixed_refs_and_prints_requires_subtree(tmp_path: Path):
    from rwiki.suggest import format_next_steps, suggest_next_steps

    cfg = _make_git_wiki(tmp_path)
    _write_python_template(
        cfg,
        "tpl-spatial-grid",
        chart_types=["spatial"],
        style_tier="default",
        journal_style="Cai2026-npjPO",
        status="ready",
    )
    write_page(
        cfg.wiki_root / "methods/spatial-downstream.md",
        {
            "type": "method",
            "id": "spatial-downstream",
            "title": "空间微环境解析",
            "status": "ready",
            "method_kind": "analysis",
            "purposes": ["空间微环境与生态位"],
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test 2026"],
            "favorite": False,
            "summary": "空间微环境解析方法。",
            "data_contract": {"input": "Visium", "output": "空间权重"},
            "figure_relations": [
                {
                    "figure": "templates/tpl-spatial-grid",
                    "compatibility": "adaptable",
                    "reason": "空间网格图适配。",
                    "prerequisites": ["spot 坐标对齐"],
                    "adaptation": "导出 spatial_grid.csv",
                    "evidence": ["templates/tpl-spatial-grid/spec.json"],
                    "verification": {"state": "not_run", "scope": "test", "evidence": []},
                }
            ],
        },
        "# 空间微环境解析\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    write_page(
        cfg.wiki_root / "scenarios/demo-pb.md",
        {
            "type": "scenario",
            "id": "demo-pb",
            "title": "演示分支树",
            "picks": [],
            "steps": [
                {
                    "id": "b7",
                    "title": "Branch 7 空转汇合",
                    "method_id": "spatial-downstream",
                    "requires": ["scrna-annotated-cells", "visium-spatial-object"],
                    "subtree": "scenarios/demo-pb",
                    "templates": ["methods/spatial-downstream", "templates/tpl-spatial-grid"],
                    "next_steps": [],
                }
            ],
        },
        "# 演示分支树\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    payload = suggest_next_steps(cfg, "demo-pb")
    branch = payload["curated_branches"][0]
    assert [m["id"] for m in branch["next_methods"]] == ["spatial-downstream"]
    assert [v["id"] for v in branch["viz_templates"]] == ["tpl-spatial-grid"]
    assert branch["viz_templates"][0]["compatibility"] == "adaptable"
    assert branch["viz_templates"][0]["style_tier"] == "default"
    assert branch["requires"] == ["scrna-annotated-cells", "visium-spatial-object"]
    assert branch["subtree"] == "scenarios/demo-pb"
    assert branch["branch_id"] == "b7"

    rendered = format_next_steps(payload)
    assert "多上游汇合前提：scrna-annotated-cells + visium-spatial-object" in rendered
    assert "专题子分支树：scenarios/demo-pb" in rendered
    assert "tpl-spatial-grid(default, adaptable)" in rendered
    assert "spatial-downstream(unreviewed)" not in rendered


def test_spec_required_any_of_column_groups_and_suggest_alias_compat(tmp_path: Path):
    from rwiki.spec import check_table_data
    from rwiki.suggest import suggest_next_steps

    table = {
        "required": True,
        "required_any_of": [["pair_label"], ["source", "target"]],
        "columns": {
            "pair_label": {"type": "str", "required": False},
            "source": {"type": "str", "required": False},
            "target": {"type": "str", "required": False},
            "interaction": {"type": "str", "required": True},
            "prob": {"type": "float", "required": True},
        },
    }
    valid_pair = tmp_path / "valid_pair.csv"
    valid_pair.write_text("pair_label,interaction,prob\nA->B,L_R,0.5\n", encoding="utf-8")
    check_table_data("lr", table, valid_pair)

    valid_st = tmp_path / "valid_st.csv"
    valid_st.write_text("source,target,interaction,prob\nA,B,L_R,0.5\n", encoding="utf-8")
    check_table_data("lr", table, valid_st)

    invalid_missing = tmp_path / "invalid_missing.csv"
    invalid_missing.write_text("interaction,prob\nL_R,0.5\n", encoding="utf-8")
    with pytest.raises(WikiError, match="缺必选列组"):
        check_table_data("lr", table, invalid_missing)

    invalid_partial = tmp_path / "invalid_partial.csv"
    invalid_partial.write_text("source,interaction,prob\nA,L_R,0.5\n", encoding="utf-8")
    with pytest.raises(WikiError, match="缺必选列组"):
        check_table_data("lr", table, invalid_partial)

    # Alias-resolved downstream method still inherits adaptable relation compatibility
    cfg = _make_git_wiki(tmp_path / "w")
    _write_python_template(cfg, "tpl-aliased", chart_types=["spatial"], style_tier="default", status="ready")
    write_page(
        cfg.wiki_root / "methods/canonical-spatial.md",
        {
            "type": "method",
            "id": "canonical-spatial",
            "aliases": ["legacy-spatial-alias"],
            "title": "规范空间方法",
            "status": "ready",
            "method_kind": "analysis",
            "purposes": ["空间微环境与生态位"],
            "tags": ["single-cell"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test 2026"],
            "favorite": False,
            "summary": "规范空间方法。",
            "data_contract": {"input": "Visium", "output": "权重"},
            "figure_relations": [
                {
                    "figure": "templates/tpl-aliased",
                    "compatibility": "adaptable",
                    "reason": "别名方法适配。",
                    "prerequisites": ["坐标"],
                    "adaptation": "导出表",
                    "evidence": ["templates/tpl-aliased/spec.json"],
                    "verification": {"state": "not_run", "scope": "test", "evidence": []},
                }
            ],
        },
        "# 规范空间方法\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    write_page(
        cfg.wiki_root / "scenarios/alias-pb.md",
        {
            "type": "scenario",
            "id": "alias-pb",
            "title": "别名继承测试",
            "picks": [],
            "steps": [
                {
                    "id": "step-alias",
                    "title": "通过旧别名引用方法",
                    "method_id": "legacy-spatial-alias",
                    "templates": ["templates/tpl-aliased"],
                    "next_steps": [],
                }
            ],
        },
        "# 别名\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    payload = suggest_next_steps(cfg, "alias-pb")
    br = payload["curated_branches"][0]
    assert br["branch_id"] == "step-alias"
    assert br["viz_templates"][0]["compatibility"] == "adaptable"

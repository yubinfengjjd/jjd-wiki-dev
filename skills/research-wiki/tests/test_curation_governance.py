"""Tests for pre-ingestion dedup, naming hygiene, method-map lint, and closed-loop curation CLI."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from rwiki.acceptance import record_acceptance
from rwiki.cli import main as cli_main
from rwiki.config import Config
from rwiki.curation_workflow import curate_audit, map_method, scaffold_native_template
from rwiki.dedup import check_duplicates
from rwiki.errors import WikiError
from rwiki.lint import lint
from rwiki.methods import scaffold_method
from rwiki.naming import title_hygiene_issues, validate_new_id
from rwiki.pages import read_page, write_page
from rwiki.recipes import promote
from rwiki.sources import add_source, fetch_source, scan_source
from rwiki.store import init, save
from rwiki.templates import scaffold_from_recipe


def _write_method(wiki: Path, mid: str, title: str, *, method_kind: str = "analysis", status: str = "ready") -> None:
    meta = {
        "type": "method",
        "id": mid,
        "title": title,
        "status": status,
        "method_kind": method_kind,
        "tags": ["bulk-transcriptomics"],
        "data_domains": ["bulk-transcriptomics"],
        "summary": f"{title}（测试）。",
        "data_contract": {"input": "表达矩阵", "output": "deg-result-table"},
        "inputs": ["deg-result-table"] if method_kind == "analysis" else [],
        "outputs": ["deg-result-table"] if method_kind == "analysis" else [],
        "source": {"kind": "written"},
        "license": "MIT",
        "cite": ["Test Ref 2026"],
        "favorite": False,
    }
    if method_kind == "analysis":
        meta["purposes"] = ["差异与功能分析"]
    write_page(
        wiki / "methods" / f"{mid}.md",
        meta,
        f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        "## 用途\n测试方法。\n\n## 适用\n转录组。\n\n## 不适用\n无。\n\n"
        "## 输入\ndeg-result-table。\n\n## 怎么做\n步骤。\n\n## 代码\n无。\n\n"
        "## 输出\ndeg-result-table。\n\n## 知识关联检查\n无图原因：测试夹具。\n\n"
        "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )


def _setup_workspace(tmp_path: Path):
    wiki = tmp_path / "wiki"
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text(
        json.dumps({"scenarios": {"bulk-transcriptomics": "Bulk 转录组", "transcriptomics": "转录组"}}),
        encoding="utf-8",
    )
    config = Config(
        wiki,
        gallery,
        taxonomy,
        Path(sys.executable),
        Path("Rscript"),
        8765,
        sources_root=tmp_path / "sources",
        work_root=tmp_path / "work",
    )
    init(config)
    write_page(
        wiki / "interfaces" / "deg-result-table.md",
        {
            "type": "interface",
            "slug": "deg-result-table",
            "title": "差异表达结果表",
            "columns": {"gene": {"type": "str", "description": "基因"}, "log2fc": {"type": "float", "description": "倍数"}},
        },
        "# 差异表达结果表\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 含义\n基因差异倍数与显著性。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    _write_method(wiki, "differential-expression", "差异表达分析")
    _write_method(wiki, "tech-helper", "辅助技术页", method_kind="technical")
    save(config, "init governance fixture")
    for mid in ("differential-expression", "tech-helper"):
        record_acceptance(config, wiki / "methods" / f"{mid}.md")
    save(config, "record method acceptance")
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "wiki_root": str(wiki),
                "gallery_root": str(gallery),
                "taxonomy": str(taxonomy),
                "python_exe": sys.executable,
                "rscript_exe": "Rscript",
                "port": 8765,
                "sources_root": str(tmp_path / "sources"),
                "work_root": str(tmp_path / "work"),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return config, cfg_path


def test_validate_new_id_and_title_hygiene():
    assert validate_new_id("template", "bulk-de-volcano") == []
    assert validate_new_id("template", "pca-3d-scatter") == []
    assert any("--" in msg for msg in validate_new_id("template", "fig--volcano"))
    assert any("fy" in msg for msg in validate_new_id("template", "fy-volcano"))
    assert any("版本号" in msg for msg in validate_new_id("template", "de-volcano-v2"))
    assert any("update" in msg for msg in validate_new_id("template", "de-volcano-update"))
    assert any("plus" in msg for msg in validate_new_id("template", "pancancer-boxplot-plus"))

    assert title_hygiene_issues("分组差异火山图", entry_id="bulk-de-volcano") == []
    assert title_hygiene_issues("FigureYa59 火山图")
    assert title_hygiene_issues("单panel：差异火山图")
    assert title_hygiene_issues("分组箱线图 v2")
    assert title_hygiene_issues("volcano", entry_id="bulk-de-volcano", chart_types=["volcano"], strict_content_name=True)


def test_native_scaffold_enforces_dedup_gate_and_allows_explicit_diff(tmp_path: Path):
    config, cfg_path = _setup_workspace(tmp_path)

    tid1 = scaffold_native_template(
        config,
        "bulk-de-volcano",
        chart_type="volcano",
        title="转录组差异表达火山图",
        primary_method="differential-expression",
        tags=["transcriptomics"],
    )
    assert tid1 == "bulk-de-volcano"

    # Near-duplicate template under same method + chart-type + similar title is blocked cleanly until diff explained
    with pytest.raises(WikiError, match="入库查重发现高相似既有条目"):
        scaffold_native_template(
            config,
            "bulk-de-volcano-alt",
            chart_type="volcano",
            title="转录组差异表达火山图",
            primary_method="differential-expression",
            tags=["transcriptomics"],
        )

    # Supplying dedup_note unblocks and records rationale directly into 知识关联检查
    tid2 = scaffold_native_template(
        config,
        "bulk-de-volcano-label",
        chart_type="volcano",
        title="转录组差异表达火山图",
        primary_method="differential-expression",
        tags=["transcriptomics"],
        dedup_note="专门用于高亮候选转录因子并叠加密度边缘图",
    )
    meta2, body2 = read_page(config.wiki_root / "templates" / f"{tid2}.md")
    assert meta2["primary_method"] == "differential-expression"
    assert "高亮候选转录因子" in body2

    # Unrelated chart-type under same method must NOT false-block
    tid3 = scaffold_native_template(
        config,
        "bulk-de-heatmap",
        chart_type="heatmap",
        title="差异基因分组热图",
        primary_method="differential-expression",
        tags=["transcriptomics"],
    )
    assert tid3 == "bulk-de-heatmap"

    # CLI check-dup json returns high match cleanly
    assert cli_main([
        "--config", str(cfg_path),
        "check-dup", "--kind", "template",
        "--title", "转录组差异表达火山图",
        "--primary-method", "differential-expression",
        "--chart-type", "volcano",
        "--json",
    ]) == 0


def test_method_map_lint_and_closed_loop_map_method_cli(tmp_path: Path, capsys):
    config, cfg_path = _setup_workspace(tmp_path)

    # Create minimal local bare git source & promote one recipe
    upstream = tmp_path / "upstream"
    item_dir = upstream / "FigureYa99demo"
    item_dir.mkdir(parents=True)
    (item_dir / "FigureYa99demo.Rmd").write_text("---\ntitle: Demo\n---\n## 需求描述\n差异表达火山图。\n```r\nplot(1:3)\n```\n", encoding="utf-8")
    import subprocess
    subprocess.run(["git", "-C", str(upstream), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(upstream), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(upstream), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(upstream), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(upstream), "commit", "-m", "init"], check=True, capture_output=True)

    add_source(config, "fy", title="FigureYa", url=upstream.as_uri(), license="CC-BY-NC-SA-4.0", adapter="figureya", trusted=True, cite=["FigureYa Ref 2026"])
    fetch_source(config, "fy")
    scan_source(config, "fy")
    promote(config, "fy", ["FigureYa99demo"])

    # Invalid method-map pointing to non-analysis technical method must fail lint
    mmap_path = config.wiki_root / "recipes" / "method-map.json"
    mmap_path.write_text(
        json.dumps({"schema_version": 1, "unmapped": [], "mappings": {"figureya-99demo": {"methods": ["tech-helper"], "confidence": "curated", "note": "bad"}}}),
        encoding="utf-8",
    )
    assert any("method-map.json" in line and "ERROR" in line for line in lint(config))

    # Fix mapping via CLI `map-method`
    assert cli_main([
        "--config", str(cfg_path),
        "map-method",
        "--recipe", "figureya-99demo",
        "--methods", "differential-expression",
        "--note", "绑定差异表达分析",
    ]) == 0
    assert not [x for x in lint(config) if x.startswith("ERROR")]

    # scaffold-from-recipe with --id infers primary_method automatically from method-map.json
    tid = scaffold_from_recipe(
        config,
        "figureya-99demo",
        "volcano",
        "差异基因气泡火山图",
        template_id="de-bubble-volcano",
    )
    assert tid == "de-bubble-volcano"
    tmeta, _ = read_page(config.wiki_root / "templates" / f"{tid}.md")
    assert tmeta["primary_method"] == "differential-expression"
    de_spec = config.wiki_root / "templates" / tid / "spec.json"
    spec_data = json.loads(de_spec.read_text(encoding="utf-8"))
    spec_data["tables"] = {"de": {"interface": "deg-result-table", "description": "差异表达表"}}
    de_spec.write_text(json.dumps(spec_data, ensure_ascii=False), encoding="utf-8")

    # curate-audit JSON reflects clean health
    audit = curate_audit(config)
    assert audit["method_map_errors"] == []
    assert audit["methods_without_viz"] == []
    assert audit["templates_missing_primary_method"] == []

    # Legacy polluted ID creates non-blocking audit warning in check-entry without breaking lint
    legacy_path = config.wiki_root / "templates" / "fy-legacy-v2.md"
    legacy_dir = config.wiki_root / "templates" / "fy-legacy-v2"
    (legacy_dir / "code").mkdir(parents=True)
    (legacy_dir / "example").mkdir()
    (legacy_dir / "code" / "render.R").write_text("cat('ok')\n", encoding="utf-8")
    (legacy_dir / "spec.json").write_text(
        json.dumps({"entry": "code/render.R", "language": "r", "tables": {"de": {"interface": "deg-result-table", "description": "差异表达表"}}, "style": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    write_page(
        legacy_path,
        {
            "type": "template",
            "id": "fy-legacy-v2",
            "title": "FigureYa 火山图 v2",
            "status": "draft",
            "layouts": [],
            "sources": ["recipes/figureya-99demo"],
            "panels": [],
            "language": "r",
            "primary_method": "differential-expression",
            "tags": ["transcriptomics"],
            "chart_types": ["volcano"],
            "favorite": False,
        },
        "# FigureYa 火山图 v2\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n测试。\n\n## 不适用\n无。\n\n## 知识关联检查\n测试。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    save(config, "add legacy draft fixture")
    assert not [x for x in lint(config) if x.startswith("ERROR")]
    capsys.readouterr()
    cli_main(["--config", str(cfg_path), "check-entry", "fy-legacy-v2"])
    entry_report = json.loads(capsys.readouterr().out)
    assert any("fy" in w or "版本号" in w or "噪声" in w for w in entry_report["warnings"])

    # scaffold_method rejects noisy titles or duplicate methods
    with pytest.raises(WikiError, match="重复|高相似"):
        scaffold_method(config, "differential-expression-copy", "差异表达分析", "MIT", written=True)

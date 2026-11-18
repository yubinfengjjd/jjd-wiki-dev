"""Tests for rwiki paper replication pipeline (trace -> fetch -> parse -> plan -> publish)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf
import pytest

from rwiki.acceptance import record_acceptance
from rwiki.cli import main as cli_main
from rwiki.config import Config
from rwiki.errors import WikiError
from rwiki.lint import lint
from rwiki.pages import read_page, write_page
from rwiki.paper import build_plan, extract_identifiers, fetch_paper, paper_status, parse_paper_pdf, publish_paper_workflow, trace_paper
from rwiki.store import init, save


def _setup_workspace(tmp_path: Path):
    wiki = tmp_path / "wiki"
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text(
        json.dumps({"scenarios": {"single-cell": "单细胞分析", "transcriptomics": "转录组"}}),
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
        wiki / "methods" / "differential-expression.md",
        {
            "type": "method",
            "id": "differential-expression",
            "title": "差异表达分析",
            "status": "ready",
            "method_kind": "analysis",
            "tags": ["single-cell"],
            "data_domains": ["single-cell"],
            "purposes": ["差异与功能分析"],
            "inputs": [],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "summary": "差异表达检验。",
            "data_contract": {"input": "矩阵", "output": "deg"},
        },
        "# 差异表达分析\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        "## 用途\n测试。\n\n## 适用\n单细胞。\n\n## 不适用\n无。\n\n"
        "## 输入\n无。\n\n## 怎么做\n步骤。\n\n## 代码\n无。\n\n"
        "## 输出\n无。\n\n## 知识关联检查\n无图原因：测试。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    save(config, "init paper workspace")
    record_acceptance(config, wiki / "methods" / "differential-expression.md")
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


def _create_sample_paper_pdf(dest: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    text = (
        "Single-cell co-expression atlas in hypothalamic neurons\n\n"
        "Methods\n\n"
        "Mice were housed in groups and xenograft tumors were measured for\n"
        "Western blot and IHC validation.\n\n"
        "For single-cell RNA-seq analysis, raw counts from GSE212345 were processed\n"
        "with Seurat v4 using NormalizeData, PCA, UMAP, and FindClusters.\n\n"
        "Co-expression modules were identified via hdWGCNA and WGCNA soft power\n"
        "thresholding, followed by enrichR pathway enrichment and Wilcoxon\n"
        "differential expression testing.\n\n"
        "Data and Code Availability\n\n"
        "Analysis scripts are publicly available at\n"
        "https://github.com/example-lab/scrna-hdwgcna-paper and GSE212345.\n\n"
        "Figure 1: Single-cell UMAP clustering and hdWGCNA sphere network of modules.\n"
        "Figure 2: Western blot validation and mouse tumor growth curves.\n"
        "Supplementary Figure 1: Pathway enrichment comparison across modules.\n"
    )
    page.insert_text((50, 50), text, fontsize=9)
    doc.save(str(dest))
    doc.close()
    return dest


def test_extract_identifiers():
    found = extract_identifiers(
        "Reference DOI 10.1038/s41467-021-21246-9 PMID: 33589633 PMC7884775 "
        "code at https://github.com/sqjin/CellChat and data GSE123456."
    )
    assert found["dois"] == ["10.1038/s41467-021-21246-9"]
    assert found["pmids"] == ["33589633"]
    assert found["pmcids"] == ["PMC7884775"]
    assert found["repo_urls"] == ["https://github.com/sqjin/CellChat"]
    assert found["data_accessions"] == ["GSE123456"]


def test_paywall_fetch_blocks_honestly_and_user_pdf_flow_succeeds(tmp_path: Path, monkeypatch):
    config, cfg_path = _setup_workspace(tmp_path)

    post_file = tmp_path / "wechat_post.md"
    post_file.write_text(
        "本文解读经典单细胞研究 https://github.com/example-lab/scrna-hdwgcna-paper DOI: 10.1016/j.crmeth.2023.100511",
        encoding="utf-8",
    )
    meta = trace_paper(
        config,
        paper_id="2023-example-hdwgcna",
        query="Single-cell co-expression atlas",
        source_text_path=post_file,
        offline=True,
    )
    assert meta["paper_id"] == "2023-example-hdwgcna"
    assert meta["doi"] == "10.1016/j.crmeth.2023.100511"
    assert "https://github.com/example-lab/scrna-hdwgcna-paper" in meta["repo_urls"]

    # Attempting remote OA fetch with no OA link or blocked HTTP must raise WikiError & mark blocked_paywall
    with pytest.raises(WikiError, match="无法直接下载公开 OA PDF"):
        fetch_paper(config, "2023-example-hdwgcna", clone_repo=False)
    blocked = paper_status(config, "2023-example-hdwgcna")
    assert blocked["status"] == "blocked_paywall"

    # Provide valid local PDF (and skip network git clone in offline unit test)
    sample_pdf = _create_sample_paper_pdf(tmp_path / "source_paper.pdf")
    fetched = fetch_paper(config, "2023-example-hdwgcna", pdf_path=sample_pdf, clone_repo=False)
    assert fetched["status"] == "fetched"
    assert fetched["pdf_sha256"]

    # Parse PDF: separates wet-lab vs computational, detects GSE212345, renders page image, filters Figure 2 (WB/mice)
    parsed = parse_paper_pdf(config, "2023-example-hdwgcna", render_pages=True)
    assert parsed["status"] == "parsed"
    assert "GSE212345" in parsed["data_accessions"]
    assert parsed["parsed_summary"]["excluded_wet_lab_chunks"] >= 1
    assert parsed["parsed_summary"]["computational_chunks"] >= 1
    assert parsed["parsed_summary"]["rendered_pages"] == 1

    # Build replication plan via CLI without supp figures
    assert cli_main([
        "--config", str(cfg_path),
        "paper", "plan", "2023-example-hdwgcna",
        "--max-cells", "2000", "--json",
    ]) == 0
    planned = paper_status(config, "2023-example-hdwgcna")
    assert planned["status"] == "planned"
    assert Path(planned["plan_path"]).is_file()
    step_ids = {s["step_id"] for s in planned["steps"]}
    assert "differential-expression" in step_ids
    assert "coexpression-ppi-network" in step_ids
    # Wet-lab Figure 2 & Supplementary Figure 1 must be excluded from Main bioinfo figure targets
    fig_names = [f["figure"] for f in planned["figures"]]
    assert "Figure 1" in fig_names
    assert "Figure 2" not in fig_names
    assert "Supplementary Figure 1" not in fig_names

    # Publish workflow into Wiki & validate lint passes cleanly
    wid = publish_paper_workflow(
        config,
        "2023-example-hdwgcna",
        workflow_id="paper-hdwgcna-hypothalamus-workflow",
        title="下丘脑单细胞共表达文献复刻流程",
        derived_methods=["differential-expression"],
    )
    assert wid == "paper-hdwgcna-hypothalamus-workflow"
    wmeta, wbody = read_page(config.wiki_root / "methods" / f"{wid}.md")
    assert wmeta["method_kind"] == "workflow"
    assert "GSE212345" in wbody
    assert not [line for line in lint(config) if line.startswith("ERROR ")]

"""Regression tests for Codex audit & Hydrogen QA fixes (v5.7 hardening)."""
from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from conftest import write_config
from rwiki.config import Config
from rwiki.errors import WikiError
from rwiki.finder import CATALOG, write_catalog
from rwiki.lint import lint
from rwiki.method_implementations import implementation_status
from rwiki.method_manifest import method_manifest_errors
from rwiki.method_verify import _sanitize_text, _validate_output_rel, verify_method
from rwiki.pages import read_page, write_page
from rwiki.panel_manifest import panel_manifest_errors
from rwiki.push_guard import ABS_RE
from rwiki.read_cache import backlinks_index, invalidate_cache
from rwiki.runtime_contract import branch_closure_hash, closure_hash, runtime_facts
from rwiki.search import search, tokenize
from rwiki.server import create_app
from rwiki.store import init, save


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_wiki(tmp_path: Path) -> Config:
    wiki = tmp_path / "wiki"
    gallery = tmp_path / "gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text(
        json.dumps(
            {
                "scenarios": {
                    "single-cell": {"label": "单细胞分析"},
                    "transcriptomics": {"label": "转录组"},
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
    return cfg


def _write_method(
    cfg: Config,
    mid: str,
    title: str,
    *,
    method_kind: str = "analysis",
    status: str = "ready",
    implementations: list[dict] | None = None,
    aliases: list[str] | None = None,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    body_extra: str = "",
) -> Path:
    meta: dict = {
        "type": "method",
        "id": mid,
        "title": title,
        "status": status,
        "method_kind": method_kind,
        "tags": ["single-cell"],
        "inputs": inputs or [],
        "outputs": outputs or [],
        "source": {"kind": "written"},
        "license": "MIT",
        "cite": ["Test 2026"],
        "favorite": False,
        "summary": f"{title} 摘要。",
        "data_contract": {"input": "matrix", "output": "table"},
        "implementations": implementations if implementations is not None else [],
    }
    if method_kind == "analysis":
        meta["purposes"] = ["注释与参考映射"]
    if aliases:
        meta["aliases"] = aliases
    page = cfg.wiki_root / f"methods/{mid}.md"
    write_page(
        page,
        meta,
        f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n{title}。\n{body_extra}\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    return page


def _write_template(
    cfg: Config,
    tid: str,
    title: str,
    *,
    status: str = "draft",
    primary_method: str | None = "cell-type-annotation",
    chart_types: list[str] | None = None,
    style_tier: str | None = None,
    journal_style: str | None = None,
    interface_slug: str | None = None,
    sources: list[str] | None = None,
    body_extra: str = "",
) -> Path:
    meta: dict = {
        "type": "template",
        "id": tid,
        "title": title,
        "status": status,
        "layouts": [],
        "sources": sources if sources is not None else ["methods/cell-type-annotation"],
        "panels": [],
        "language": "python",
        "tags": ["single-cell"],
        "chart_types": chart_types if chart_types is not None else ["umap"],
        "favorite": False,
    }
    if status == "archived":
        meta["archived_from"] = "draft"
    if primary_method is not None:
        meta["primary_method"] = primary_method
    if style_tier is not None:
        meta["style_tier"] = style_tier
    if journal_style is not None:
        meta["journal_style"] = journal_style
    page = cfg.wiki_root / f"templates/{tid}.md"
    write_page(
        page,
        meta,
        f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n{title}。\n{body_extra}\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    tdir = cfg.wiki_root / f"templates/{tid}"
    (tdir / "code").mkdir(parents=True, exist_ok=True)
    (tdir / "code/render.py").write_text("print('ok')\n", encoding="utf-8")
    table_def: dict = {"interface": interface_slug, "description": "main"}
    if not interface_slug:
        table_def["columns"] = {"x": {"type": "str", "description": "x"}}
    (tdir / "spec.json").write_text(
        json.dumps({"entry": "code/render.py", "language": "python", "tables": {"main": table_def}, "style": {}}),
        encoding="utf-8",
    )
    return page


# ------------------------------------------------------------------ 1. Search metadata, synonyms & backlinks cache


def test_search_indexes_implementations_metadata_and_chinese_synonyms(tmp_path: Path):
    cfg = _make_wiki(tmp_path)
    _write_method(
        cfg,
        "cell-type-annotation",
        "细胞类型注释",
        implementations=[
            {
                "id": "scimap-gmm-phenotyping",
                "title": "CyCIF 空间蛋白 GMM 表型注释",
                "language": "Python",
                "impl_tier": "variant",
                "modality": "Spatial Proteomics (CyCIF)",
                "source_paper": "2022-nirmal-melanoma-spatial",
                "entrypoint": "code/scimap_gmm_phenotyping.py:run_scimap_gmm_phenotyping",
                "dependencies": ["scikit-learn"],
            }
        ],
    )
    _write_method(
        cfg,
        "differential-expression",
        "差异表达分析",
        implementations=[
            {
                "id": "deseq2-mrseq-de",
                "title": "DESeq2 差异表达检验",
                "language": "R",
                "impl_tier": "variant",
                "modality": "Bulk / mrSEQ",
                "source_paper": "2022-nirmal-melanoma-spatial",
                "entrypoint": "code/deseq2_mrseq_de.R:run_deseq2_mrseq_de",
                "dependencies": ["DESeq2"],
            }
        ],
    )
    _write_method(
        cfg,
        "gene-set-scoring",
        "基因集打分",
        implementations=[
            {
                "id": "progeny-pathway-activity",
                "title": "PROGENy 通路打分与活性推断",
                "language": "R",
                "impl_tier": "variant",
                "modality": "scRNA-seq",
                "source_paper": "2026-cai-stromal-tme",
                "entrypoint": "code/progeny_pathway_activity.R:run_progeny",
                "dependencies": ["progeny"],
            }
        ],
    )
    _write_method(
        cfg,
        "spatial-transcriptomics-microenvironment",
        "空间微环境分析",
        implementations=[
            {
                "id": "scimap-rcn-spatial-lda",
                "title": "Spatial-LDA 重复细胞邻域 RCN 聚类",
                "language": "Python",
                "impl_tier": "default",
                "modality": "Spatial Proteomics (CyCIF)",
                "source_paper": "2022-nirmal-melanoma-spatial",
                "entrypoint": "code/scimap_rcn_spatial_lda.py:run_spatial_lda",
                "dependencies": ["scikit-learn"],
            }
        ],
    )
    _write_method(
        cfg,
        "cell-proportion-composition",
        "细胞比例与组成分析",
        implementations=[
            {
                "id": "roe-tissue-enrichment",
                "title": "Ro/e 组织富集比分析",
                "language": "R",
                "impl_tier": "default",
                "modality": "scRNA-seq",
                "source_paper": "2026-cai-stromal-tme",
                "entrypoint": "code/roe_tissue_enrichment.R:run_roe",
                "dependencies": ["stats"],
            }
        ],
    )
    _write_template(cfg, "stacked-prop-bar", "细胞比例堆叠柱状图", chart_types=["stacked-bar"])

    # Synonyms produce shared alias tokens
    assert set(tokenize("单细胞注释")) & set(tokenize("细胞注释"))
    assert any(tok.startswith("@") for tok in set(tokenize("单细胞注释")) & set(tokenize("细胞注释")))
    assert any(tok.startswith("@") for tok in set(tokenize("堆积柱状图")) & set(tokenize("堆叠柱状图")))

    for query, expected_id in [
        ("scimap", "cell-type-annotation"),
        ("DESeq2", "differential-expression"),
        ("PROGENy 通路打分", "gene-set-scoring"),
        ("CyCIF GMM 表型注释", "cell-type-annotation"),
        ("Spatial-LDA", "spatial-transcriptomics-microenvironment"),
        ("Ro/e", "cell-proportion-composition"),
        ("堆积柱状图", "stacked-prop-bar"),
    ]:
        hits = search(cfg, query, limit=5)["results"]
        top_ids = [item["id"] for item in hits[:2]]
        assert expected_id in top_ids, f"Query {query!r} expected {expected_id} in top-2, got {top_ids}"


def test_backlinks_index_is_cached_and_invalidated_on_page_change(tmp_path: Path, monkeypatch):
    cfg = _make_wiki(tmp_path)
    _write_method(cfg, "target-method", "目标分析方法")
    _write_template(
        cfg,
        "caller-tpl",
        "引用目标方法的模板",
        primary_method="target-method",
        sources=["methods/target-method"],
        body_extra="\n关联 [[methods/target-method|目标分析方法]]。\n",
    )
    save(cfg, "seed backlinks fixture")
    invalidate_cache(cfg.wiki_root)

    import rwiki.links as links_mod

    orig_extract = links_mod.extract_links
    calls = 0

    def counted_extract(text: str):
        nonlocal calls
        calls += 1
        return orig_extract(text)

    monkeypatch.setattr(links_mod, "extract_links", counted_extract)

    with TestClient(create_app(cfg)) as client:
        r1 = client.get("/api/page", params={"path": "methods/target-method.md"})
        assert r1.status_code == 200
        assert any(b["path"] == "templates/caller-tpl.md" for b in r1.json()["backlinks"])
        calls_after_first = calls

        # Second request must hit the cached backlinks_index (0 extra extract_links calls)
        r2 = client.get("/api/page", params={"path": "methods/target-method.md"})
        assert r2.status_code == 200
        assert r2.json()["backlinks"] == r1.json()["backlinks"]
        assert calls == calls_after_first

    # Adding a new linking page updates vault fingerprint and rebuilds backlinks_index automatically
    _write_template(
        cfg,
        "caller-tpl-2",
        "第二个引用模板",
        primary_method="target-method",
        sources=["methods/target-method"],
        body_extra="\n也引用 [[methods/target-method]]。\n",
    )
    idx = backlinks_index(cfg.wiki_root)
    paths = {item["path"] for item in idx.get("methods/target-method.md", [])}
    assert {"templates/caller-tpl.md", "templates/caller-tpl-2.md"} <= paths


# ------------------------------------------------------------------ 2. Multi-impl runtime.json portability isolation


def test_multi_impl_portability_closure_isolation_and_tamper_resistance(tmp_path: Path):
    asset = tmp_path / "methods/demo-multi"
    (asset / "code").mkdir(parents=True)
    f1 = asset / "code/singler.R"
    f1.write_text("run_singler <- function(x) x\n", encoding="utf-8")

    single_manifest = {
        "schema_version": 1,
        "kind": "method",
        "id": "demo-multi",
        "implementations": [
            {
                "id": "scp-singler",
                "entry": "code/singler.R",
                "entry_function": "run_singler",
                "language": "R",
                "runtime_mode": "standalone",
                "files": ["code/singler.R"],
                "resources": [],
                "required_packages": {"R": ["SingleR"]},
                "optional_packages": {"R": {}},
                "evidence": {"portability": "verification/portability.json"},
            }
        ],
    }
    (asset / "runtime.json").write_text(json.dumps(single_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    legacy_hash = closure_hash(asset, single_manifest["implementations"][0])
    (asset / "verification").mkdir(parents=True)
    receipt = {
        "schema_version": 1,
        "kind": "method",
        "implementation": "scp-singler",
        "state": "passed",
        "scope": "Isolated R run",
        "command": "<RSCRIPT> --vanilla run.R",
        "checks": ["ok"],
        "environment": {"R": "4.5.0"},
        "closure_hash": legacy_hash,
        "files": {"code/singler.R": _sha256(f1)},
    }
    (asset / "verification/portability.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    assert runtime_facts(asset, "demo-multi", "method")["implementations"]["scp-singler"]["portability"]["state"] == "verified"

    # Append a 2nd implementation to runtime.json -> branch 1 MUST remain verified!
    f2 = asset / "code/scimap.py"
    f2.write_text("def run_scimap(x):\n    return x\n", encoding="utf-8")
    multi_manifest = deepcopy(single_manifest)
    multi_manifest["implementations"].append(
        {
            "id": "scimap-gmm",
            "entry": "code/scimap.py",
            "entry_function": "run_scimap",
            "language": "Python",
            "runtime_mode": "standalone",
            "files": ["code/scimap.py"],
            "resources": [],
            "required_packages": {"Python": ["numpy"]},
            "optional_packages": {"Python": {}},
        }
    )
    (asset / "runtime.json").write_text(json.dumps(multi_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    facts_multi = runtime_facts(asset, "demo-multi", "method")
    assert facts_multi["implementations"]["scp-singler"]["portability"]["state"] == "verified"
    assert facts_multi["implementations"]["scimap-gmm"]["portability"]["state"] == "declared"

    # Also verify canonical branch_closure_hash is accepted directly
    b_hash = branch_closure_hash(asset, multi_manifest["implementations"][0])
    assert b_hash and b_hash != closure_hash(asset, multi_manifest["implementations"][0])
    receipt_branch = {**receipt, "closure_hash": b_hash}
    (asset / "verification/portability.json").write_text(json.dumps(receipt_branch, indent=2), encoding="utf-8")
    assert runtime_facts(asset, "demo-multi", "method")["implementations"]["scp-singler"]["portability"]["state"] == "verified"

    # Tampering with branch 1's own declaration in runtime.json MUST invalidate receipt!
    tampered_manifest = deepcopy(multi_manifest)
    tampered_manifest["implementations"][0]["required_packages"]["R"].append("ExtraPkg")
    (asset / "runtime.json").write_text(json.dumps(tampered_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert runtime_facts(asset, "demo-multi", "method")["implementations"]["scp-singler"]["portability"]["state"] == "invalid"

    # Restore manifest, then tamper with branch 1's source file -> MUST invalidate receipt!
    (asset / "runtime.json").write_text(json.dumps(multi_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    f1.write_text("run_singler <- function(x) x + 999\n", encoding="utf-8")
    assert runtime_facts(asset, "demo-multi", "method")["implementations"]["scp-singler"]["portability"]["state"] == "invalid"


# ------------------------------------------------------------------ 3. method_implementations & method_verify hardening


def test_method_implementations_defensive_fail_closed_and_receipt_validation(tmp_path: Path):
    cfg = _make_wiki(tmp_path)
    mid = "hardened-method"
    asset = cfg.wiki_root / f"methods/{mid}"
    (asset / "code").mkdir(parents=True)
    src = asset / "code/algo.py"
    src.write_text("def run_algo(x):\n    return x\n", encoding="utf-8")

    def write_rec(extra: dict | None = None):
        verif = asset / "verification/py-algo.json"
        verif.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "implementation": "py-algo",
            "method_id": mid,
            "state": "passed",
            "scope": "unit test",
            "command": "<PYTHON> example/verify_py-algo.py",
            "checks": ["ok"],
            "environment": {"runtime": "Python"},
            "files": {"code/algo.py": _sha256(src)},
            "output_sha256": {"checks.json": "a" * 64},
        }
        if extra:
            payload.update(extra)
        verif.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    good_manifest = {
        "schema_version": 1,
        "kind": "method",
        "id": mid,
        "implementations": [
            {
                "id": "py-algo",
                "entry": "code/algo.py",
                "entry_function": "run_algo",
                "language": "Python",
                "runtime_mode": "standalone",
                "files": ["code/algo.py"],
                "required_packages": {},
            }
        ],
    }
    (asset / "runtime.json").write_text(json.dumps(good_manifest, indent=2), encoding="utf-8")
    write_rec()

    # 1. Malformed dependencies: 7 must NOT raise TypeError
    page = _write_method(
        cfg,
        mid,
        "加固测试方法",
        implementations=[
            {
                "id": "py-algo",
                "title": "Py Algo",
                "language": "Python",
                "entrypoint": "code/algo.py:run_algo",
                "dependencies": 7,  # invalid type!
                "verification": "verification/py-algo.json",
            }
        ],
    )
    st_bad_dep = implementation_status(page)
    assert st_bad_dep[0]["state"] == "invalid"

    # Fix dependencies -> now verified
    meta, body = read_page(page)
    meta["implementations"][0]["dependencies"] = []
    write_page(page, meta, body)
    assert implementation_status(page)[0]["state"] == "verified"

    # 2. Entrypoint function mismatch makes portability=invalid -> branch MUST NOT be verified!
    meta["implementations"][0]["entrypoint"] = "code/algo.py:wrong_func"
    write_page(page, meta, body)
    st_mismatch = implementation_status(page)[0]
    assert st_mismatch["runtime"]["portability"]["state"] == "invalid"
    assert st_mismatch["state"] == "invalid"

    # Restore entrypoint
    meta["implementations"][0]["entrypoint"] = "code/algo.py:run_algo"
    write_page(page, meta, body)
    assert implementation_status(page)[0]["state"] == "verified"

    # 3. Malformed runtime.json on disk -> fail-closed invalid (never silently falls back to whole code/ check!)
    (asset / "runtime.json").write_text("{broken json", encoding="utf-8")
    assert implementation_status(page)[0]["state"] == "invalid"

    # runtime.json exists but omits this branch -> fail-closed invalid!
    other_manifest = deepcopy(good_manifest)
    other_manifest["implementations"][0]["id"] = "other-branch"
    (asset / "runtime.json").write_text(json.dumps(other_manifest, indent=2), encoding="utf-8")
    assert implementation_status(page)[0]["state"] == "invalid"

    # Restore good runtime.json
    (asset / "runtime.json").write_text(json.dumps(good_manifest, indent=2), encoding="utf-8")
    assert implementation_status(page)[0]["state"] == "verified"

    # 4. Receipt method_id mismatch -> invalid
    write_rec({"method_id": "another-method"})
    assert implementation_status(page)[0]["state"] == "invalid"

    # 5. Receipt output_sha256 validation
    for bad_out in [
        "not-a-dict",
        {"../escape.json": "a" * 64},
        {"C:/abs.json": "a" * 64},
        {"checks.json": "not-hex"},
    ]:
        write_rec({"output_sha256": bad_out})
        assert implementation_status(page)[0]["state"] == "invalid"

    write_rec({"output_sha256": {"checks.json": "b" * 64, "sub/table.csv": "c" * 64}})
    assert implementation_status(page)[0]["state"] == "verified"


def test_method_verify_sanitization_toctou_driver_sha256_and_reparse_guards(tmp_path: Path, monkeypatch):
    # Path sanitization covers UNC, /tmp, /Users, and Windows drive paths with spaces
    sample = (
        r"UNC \\fileserver\bio-share\cohort 1\data.csv ; "
        r"WIN C:\Program Files\Bio Tool\run script.py and D:\My Data\patient table.csv ; "
        r"TMP /tmp/rwiki-verify-123/out.csv and /Users/alice/work/test.py ok"
    )
    sanitized = _sanitize_text(sample)
    assert r"\\fileserver" not in sanitized
    assert "Program Files" not in sanitized
    assert "My Data" not in sanitized
    assert "/tmp/" not in sanitized
    assert "/Users/alice" not in sanitized
    assert ABS_RE.search(sanitized) is None

    # Output relative path validation rejects traversal, hidden files, drives
    for bad_rel in ("../evil.csv", ".hidden", "C:/a.csv", r"sub\file.csv", "a/.."):
        with pytest.raises(WikiError):
            _validate_output_rel(bad_rel)

    # Full verify_method flow: driver_sha256, child environment version, TOCTOU, reparse guard
    cfg = _make_wiki(tmp_path)
    mid = "toctou-demo"
    impl_id = "py-safe"
    asset = cfg.wiki_root / f"methods/{mid}"
    (asset / "code").mkdir(parents=True)
    (asset / "example").mkdir(parents=True)
    algo = asset / "code/algo.py"
    algo.write_text("def compute(x):\n    return x * 2\n", encoding="utf-8")

    verify_script = asset / f"example/verify_{impl_id}.py"
    verify_script.write_text(
        "import argparse, json, sys\n"
        "from pathlib import Path\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--code', type=Path, required=True)\n"
        "p.add_argument('--example', type=Path, required=True)\n"
        "p.add_argument('--out', type=Path, required=True)\n"
        "a = p.parse_args()\n"
        "(a.out / 'checks.json').write_text(json.dumps({\n"
        "    'scope': r'Verified on C:\\My Space\\data.csv and \\\\srv\\share\\a.csv and /tmp/x/b.csv',\n"
        "    'checks': ['ok'],\n"
        "}), encoding='utf-8')\n",
        encoding="utf-8",
    )
    _write_method(
        cfg,
        mid,
        "TOCTOU 测试方法",
        implementations=[
            {
                "id": impl_id,
                "title": "Py Safe",
                "language": "Python",
                "impl_tier": "default",
                "modality": "Bulk RNA-seq",
                "entrypoint": "code/algo.py:compute",
                "dependencies": [],
            }
        ],
    )
    (asset / "runtime.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "method",
                "id": mid,
                "implementations": [
                    {
                        "id": impl_id,
                        "entry": "code/algo.py",
                        "entry_function": "compute",
                        "language": "Python",
                        "runtime_mode": "standalone",
                        "files": ["code/algo.py"],
                        "required_packages": {},
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    res = verify_method(cfg, mid, impl_id)
    assert res["driver_sha256"] == _sha256(verify_script)
    receipt_json = json.loads((asset / f"verification/{impl_id}.json").read_text(encoding="utf-8"))
    assert receipt_json["driver_sha256"] == _sha256(verify_script)
    assert receipt_json["environment"].get("python_version")
    assert ABS_RE.search(json.dumps(receipt_json)) is None
    assert r"\\srv" not in receipt_json["scope"]
    assert "/tmp/" not in receipt_json["scope"]

    # TOCTOU: script mutates code/algo.py mid-run -> MUST abort and raise WikiError!
    verify_script.write_text(
        "import argparse, json\n"
        "from pathlib import Path\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--code', type=Path, required=True)\n"
        "p.add_argument('--example', type=Path, required=True)\n"
        "p.add_argument('--out', type=Path, required=True)\n"
        "a = p.parse_args()\n"
        "(a.code / 'algo.py').write_text('def compute(x):\\n    return x * 999\\n', encoding='utf-8')\n"
        "(a.out / 'checks.json').write_text(json.dumps({'scope': 'ok', 'checks': ['ok']}), encoding='utf-8')\n",
        encoding="utf-8",
    )
    with pytest.raises(WikiError, match="TOCTOU"):
        verify_method(cfg, mid, impl_id)

    # Restore clean verify script, then simulate symlink/junction at verification/ dir -> MUST reject!
    verify_script.write_text(
        "import argparse, json\n"
        "from pathlib import Path\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--code', type=Path, required=True)\n"
        "p.add_argument('--example', type=Path, required=True)\n"
        "p.add_argument('--out', type=Path, required=True)\n"
        "a = p.parse_args()\n"
        "(a.out / 'checks.json').write_text(json.dumps({'scope': 'ok', 'checks': ['ok']}), encoding='utf-8')\n",
        encoding="utf-8",
    )
    import rwiki.method_verify as mv

    verif_dir = asset / "verification"
    orig_reparse = mv._is_reparse
    monkeypatch.setattr(mv, "_is_reparse", lambda p: True if p == verif_dir else orig_reparse(p))
    with pytest.raises(WikiError, match="禁止符号链接或目录联接"):
        verify_method(cfg, mid, impl_id)


# ------------------------------------------------------------------ 4. Intake hard gates & slot canonicalization


def test_panel_manifest_and_method_manifest_hard_gates(tmp_path: Path):
    cfg = _make_wiki(tmp_path)
    _write_method(cfg, "cell-type-annotation", "细胞类型注释")
    _write_template(cfg, "archived-tpl", "已归档模板", status="archived")
    wf = _write_method(cfg, "demo-paper-wf", "演示论文流程", method_kind="workflow", status="draft")
    wf_dir = cfg.wiki_root / "methods/demo-paper-wf"
    (wf_dir / "code").mkdir(parents=True, exist_ok=True)
    (wf_dir / "code/01.py").write_text("print('ok')\n", encoding="utf-8")

    # panel-manifest: invalid schema_version (bool, str, <= 0) must produce ERROR
    for bad_sv in (True, False, "2", 0, -1):
        (wf_dir / "panel-manifest.yaml").write_text(
            yaml.safe_dump({"schema_version": bad_sv, "panels": []}, allow_unicode=True),
            encoding="utf-8",
        )
        errs = panel_manifest_errors(cfg, wf)
        assert any("schema_version" in e for e in errs), f"Expected error for schema_version={bad_sv!r}, got {errs}"

    # panel-manifest: reuse_identical referencing archived template must produce ERROR
    (wf_dir / "panel-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "paper_id": "2026-demo",
                "panels": [
                    {
                        "panel_key": "fig01/A",
                        "figure": "Fig. 1",
                        "panel": "1A",
                        "evidence_tier": "local_recompute",
                        "script_path": "code/01.py",
                        "template_disposition": "reuse_identical",
                        "template_id": "archived-tpl",
                        "disposition_note": "尝试复用归档模板",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    errs = panel_manifest_errors(cfg, wf)
    assert any("archived" in e or "已归档" in e for e in errs)

    # method-manifest: empty steps[] and mismatched workflow_id must produce ERROR
    (wf_dir / "method-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "paper_id": "2026-demo",
                "workflow_id": "other-workflow-id",
                "steps": [],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    m_errs = method_manifest_errors(cfg, wf)
    assert any("workflow_id" in e and "demo-paper-wf" in e for e in m_errs)
    assert any("steps" in e and "1 条" in e for e in m_errs)


def test_lint_single_impl_slot_symmetry_and_template_canonical_slot_checks(tmp_path: Path):
    cfg = _make_wiki(tmp_path)
    _write_method(
        cfg,
        "cell-type-annotation",
        "细胞类型注释",
        aliases=["legacy-annot"],
        status="draft",
    )
    # Single impl with modality but missing impl_tier -> ERROR
    _write_method(
        cfg,
        "m-mod-only",
        "单实现缺tier",
        status="draft",
        implementations=[
            {
                "id": "impl-a",
                "title": "A",
                "language": "Python",
                "modality": "scRNA-seq",
                "entrypoint": "code/a.py:run",
                "dependencies": [],
            }
        ],
    )
    # Single impl with impl_tier=default but missing modality -> ERROR
    _write_method(
        cfg,
        "m-tier-only",
        "单实现缺modality",
        status="draft",
        implementations=[
            {
                "id": "impl-b",
                "title": "B",
                "language": "Python",
                "impl_tier": "default",
                "entrypoint": "code/b.py:run",
                "dependencies": [],
            }
        ],
    )
    # Template with style_tier/journal_style missing primary_method -> ERROR
    _write_template(
        cfg,
        "tpl-no-pm",
        "缺主方法的有样式模板",
        primary_method=None,
        chart_types=["umap"],
        style_tier="default",
        journal_style="Standard",
    )
    # Template with style_tier/journal_style missing chart_types[0] -> ERROR
    _write_template(
        cfg,
        "tpl-no-chart",
        "缺图型的有样式模板",
        primary_method="cell-type-annotation",
        chart_types=[],
        style_tier="default",
        journal_style="Standard",
    )
    # Two default templates: one references canonical primary_method, the other references its alias -> MUST collide!
    _write_template(
        cfg,
        "tpl-canon-default",
        "规范主方法默认图",
        primary_method="cell-type-annotation",
        chart_types=["dotplot"],
        style_tier="default",
        journal_style="Standard",
    )
    _write_template(
        cfg,
        "tpl-alias-default",
        "别名主方法默认图",
        primary_method="legacy-annot",
        chart_types=["dotplot"],
        style_tier="default",
        journal_style="Cancer Discovery",
    )

    errors = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert any("m-mod-only" in e and "impl_tier" in e for e in errors)
    assert any("m-tier-only" in e and "modality" in e for e in errors)
    assert any("templates/tpl-no-pm.md" in e and "primary_method" in e for e in errors)
    assert any("templates/tpl-no-chart.md" in e and "chart_types[0]" in e for e in errors)
    assert any("templates/tpl-canon-default.md" in e and "存在多个 style_tier: default" in e for e in errors)
    assert any("templates/tpl-alias-default.md" in e and "存在多个 style_tier: default" in e for e in errors)


# ------------------------------------------------------------------ 5. Incremental save & catalog resilience


def test_write_catalog_defends_non_dict_lines_and_save_prevents_stale_interface_facts(tmp_path: Path):
    cfg = _make_wiki(tmp_path)
    # Create interface + method + template bound to that interface
    iface_page = cfg.wiki_root / "interfaces/demo-iface.md"
    write_page(
        iface_page,
        {
            "type": "interface",
            "slug": "demo-iface",
            "title": "演示接口",
            "columns": {"gene": {"type": "str", "description": "基因名"}},
        },
        "# 演示接口\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 含义\n测试。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    _write_method(cfg, "cell-type-annotation", "细胞类型注释", status="draft", outputs=["demo-iface"])
    tpl_page = _write_template(
        cfg,
        "tpl-bound",
        "绑定接口模板",
        status="draft",
        interface_slug="demo-iface",
    )
    save(cfg, "seed interface and template")

    assert "templates/tpl-bound" in iface_page.read_text(encoding="utf-8")

    # Inject non-dict JSON lines into catalog.jsonl -> incremental write_catalog must NOT crash
    cat_path = cfg.wiki_root / CATALOG
    cat_path.write_text(cat_path.read_text(encoding="utf-8") + "null\n42\n[\"bad\"]\n", encoding="utf-8")
    write_catalog(cfg, changed_paths={tpl_page}, deleted_pages=set())
    parsed_lines = [json.loads(line) for line in cat_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert all(isinstance(rec, dict) for rec in parsed_lines)

    # save() must reject out-of-wiki only_refresh_paths
    outside = tmp_path / "outside.md"
    outside.write_text("hi", encoding="utf-8")
    with pytest.raises(WikiError, match="越出知识库目录"):
        save(cfg, "bad scope", only_refresh_paths={outside})

    # Deleting template with empty only_refresh_paths MUST still refresh affected interface facts!
    tpl_page.unlink()
    save(cfg, "delete bound template", only_refresh_paths=set(), deleted_pages={"templates/tpl-bound.md"})
    iface_after = iface_page.read_text(encoding="utf-8")
    assert "templates/tpl-bound" not in iface_after
    assert "- 使用的模板：无" in iface_after

"""Tests for Research Wiki v5.7 Method Intake Hard Gate, Multi-Impl Receipt Isolation, and `verify-method`."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml

from conftest import write_config
from rwiki.cli import main as cli_main
from rwiki.config import Config
from rwiki.errors import WikiError
from rwiki.lint import lint
from rwiki.method_implementations import implementation_metadata_errors, implementation_status
from rwiki.method_manifest import VALID_METHOD_DISPOSITIONS, method_manifest_errors
from rwiki.method_verify import verify_method
from rwiki.pages import read_page, write_page
from rwiki.push_guard import ABS_RE
from rwiki.store import init


def _make_v57_wiki(tmp_path: Path) -> tuple[Config, Path]:
    wiki = tmp_path / "wiki"
    gallery = tmp_path / "gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text(
        json.dumps(
            {
                "scenarios": {
                    "single-cell": {"label": "单细胞分析"},
                    "spatial-omics": {"label": "空间组学"},
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
    cfg_path = write_config(tmp_path / "config.json", wiki)
    return cfg, cfg_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_method_page(
    cfg: Config,
    mid: str,
    *,
    method_kind: str = "analysis",
    status: str = "draft",
    implementations: list[dict] | None = None,
) -> Path:
    meta: dict = {
        "type": "method",
        "id": mid,
        "title": f"方法 {mid}",
        "status": status,
        "method_kind": method_kind,
        "tags": ["single-cell"],
        "inputs": [],
        "outputs": [],
        "source": {"kind": "written"},
        "license": "MIT",
        "cite": ["Test 2026"],
        "favorite": False,
        "summary": f"{mid} 摘要。",
        "data_contract": {"input": "counts", "output": "table"},
        "implementations": implementations if implementations is not None else [],
    }
    if method_kind == "analysis":
        meta["purposes"] = ["注释与参考映射"]
    if status == "archived":
        meta["archived_from"] = "draft"
    page = cfg.wiki_root / f"methods/{mid}.md"
    write_page(
        page,
        meta,
        f"# 方法 {mid}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n测试。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    return page


def _write_receipt(asset: Path, impl_id: str, files: dict[str, str], *, state: str = "passed", scope: str = "unit test") -> Path:
    verif = asset / f"verification/{impl_id}.json"
    verif.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "implementation": impl_id,
        "state": state,
        "scope": scope,
        "command": f"<PYTHON> -X utf8 example/verify_{impl_id}.py --code code --example example --out <TMP_OUT>",
        "checks": ["assertion passed"],
        "environment": {"runtime": "Python", "runner": "<PYTHON>"},
        "files": files,
    }
    verif.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return verif


# ------------------------------------------------------------------ 1. Multi-Impl Receipt Isolation & Metadata


def test_declared_runtime_receipt_isolation_and_tamper_detection(tmp_path: Path):
    cfg, _ = _make_v57_wiki(tmp_path)
    mid = "cell-type-annotation"
    asset = cfg.wiki_root / f"methods/{mid}"
    (asset / "code").mkdir(parents=True, exist_ok=True)
    f1 = asset / "code/singler.R"
    f1.write_text("run_singler <- function(x) x\n", encoding="utf-8")

    page = _write_method_page(
        cfg,
        mid,
        implementations=[
            {
                "id": "scp-singler",
                "title": "SingleR 参考注释",
                "language": "R",
                "impl_tier": "default",
                "modality": "scRNA-seq",
                "source_paper": "Aran et al. 2019",
                "entrypoint": "code/singler.R:run_singler",
                "dependencies": ["SingleR"],
                "verification": "verification/scp-singler.json",
            }
        ],
    )
    runtime_manifest = {
        "schema_version": 1,
        "kind": "method",
        "id": mid,
        "implementations": [
            {
                "id": "scp-singler",
                "entry": "code/singler.R",
                "entry_function": "run_singler",
                "language": "R",
                "runtime_mode": "standalone",
                "files": ["code/singler.R"],
                "required_packages": {"R": ["SingleR"]},
            }
        ],
    }
    (asset / "runtime.json").write_text(json.dumps(runtime_manifest, indent=2), encoding="utf-8")
    _write_receipt(asset, "scp-singler", {"code/singler.R": _sha256(f1)})

    st1 = implementation_status(page)
    assert st1[0]["state"] == "verified"

    # Adding a 2nd implementation file in code/ MUST NOT invalidate impl 1's receipt
    f2 = asset / "code/scimap_gmm.py"
    f2.write_text("def run_gmm(df):\n    return df\n", encoding="utf-8")
    runtime_manifest["implementations"].append(
        {
            "id": "scimap-gmm",
            "entry": "code/scimap_gmm.py",
            "entry_function": "run_gmm",
            "language": "Python",
            "runtime_mode": "standalone",
            "files": ["code/scimap_gmm.py"],
            "required_packages": {"Python": ["numpy"]},
        }
    )
    (asset / "runtime.json").write_text(json.dumps(runtime_manifest, indent=2), encoding="utf-8")
    meta, body = read_page(page)
    meta["implementations"].append(
        {
            "id": "scimap-gmm",
            "title": "CyCIF GMM 门控注释",
            "language": "Python",
            "impl_tier": "variant",
            "modality": "Spatial Proteomics",
            "source_paper": "Nirmal et al. 2022",
            "entrypoint": "code/scimap_gmm.py:run_gmm",
            "dependencies": ["numpy"],
        }
    )
    write_page(page, meta, body)

    st2 = implementation_status(page)
    assert {item["id"]: item["state"] for item in st2} == {
        "scp-singler": "verified",
        "scimap-gmm": "not_run",
    }

    # Modifying impl 1's own closure file MUST turn impl 1 stale immediately
    f1.write_text("run_singler <- function(x) x + 1\n", encoding="utf-8")
    st3 = implementation_status(page)
    assert {item["id"]: item["state"] for item in st3} == {
        "scp-singler": "stale",
        "scimap-gmm": "not_run",
    }

    # Dropping a declared closure file from receipt MUST turn impl 1 invalid
    f1.write_text("run_singler <- function(x) x\n", encoding="utf-8")
    _write_receipt(asset, "scp-singler", {"code/scimap_gmm.py": _sha256(f2)})
    st4 = implementation_status(page)
    assert st4[0]["state"] == "invalid"


def test_undeclared_runtime_keeps_legacy_whole_code_dir_check_and_metadata_errors(tmp_path: Path):
    cfg, _ = _make_v57_wiki(tmp_path)
    mid = "legacy-method"
    asset = cfg.wiki_root / f"methods/{mid}"
    (asset / "code").mkdir(parents=True, exist_ok=True)
    f1 = asset / "code/first.py"
    f1.write_text("def run(): return 1\n", encoding="utf-8")
    page = _write_method_page(
        cfg,
        mid,
        implementations=[
            {
                "id": "first",
                "title": "First",
                "language": "Python",
                "entrypoint": "code/first.py:run",
                "dependencies": [],
                "verification": "verification/first.json",
            }
        ],
    )
    _write_receipt(asset, "first", {"code/first.py": _sha256(f1)})
    assert implementation_status(page)[0]["state"] == "verified"

    # Without runtime.json, adding another file in code/ invalidates receipt (backward compatible)
    (asset / "code/extra.py").write_text("def other(): return 2\n", encoding="utf-8")
    assert implementation_status(page)[0]["state"] == "invalid"

    # Metadata validator checks impl_tier, modality, source_paper
    errs = implementation_metadata_errors(
        {
            "implementations": [
                {
                    "id": "bad-meta",
                    "title": "Bad",
                    "language": "Python",
                    "entrypoint": "code/first.py:run",
                    "dependencies": [],
                    "impl_tier": "secondary",
                    "modality": "   ",
                    "source_paper": "",
                }
            ]
        }
    )
    assert any("impl_tier" in e for e in errs)
    assert any("modality" in e for e in errs)
    assert any("source_paper" in e for e in errs)


# ------------------------------------------------------------------ 2. Multi-Impl Slot Hard Gate


def test_method_multi_impl_slot_three_rules(tmp_path: Path):
    # Rule 1: Lone implementation marked as variant -> ERROR
    cfg1, _ = _make_v57_wiki(tmp_path / "lone")
    _write_method_page(
        cfg1,
        "m-lone",
        implementations=[
            {
                "id": "only-var",
                "title": "孤立变体",
                "language": "Python",
                "impl_tier": "variant",
                "modality": "scRNA-seq",
                "entrypoint": "code/a.py:run",
                "dependencies": [],
            }
        ],
    )
    errs1 = [line for line in lint(cfg1) if line.startswith("ERROR ")]
    assert any("m-lone" in e and "禁止孤立标为 impl_tier: variant" in e for e in errs1)

    # Rule 2: 2+ impls with 0 default / 2 defaults / missing modality -> ERROR
    cfg2, _ = _make_v57_wiki(tmp_path / "multi_bad")
    _write_method_page(
        cfg2,
        "m-no-def",
        implementations=[
            {
                "id": "v1",
                "title": "V1",
                "language": "R",
                "impl_tier": "variant",
                "modality": "scRNA-seq",
                "entrypoint": "code/a.R:run",
                "dependencies": [],
            },
            {
                "id": "v2",
                "title": "V2",
                "language": "Python",
                "entrypoint": "code/b.py:run",
                "dependencies": [],
            },
        ],
    )
    errs2 = [line for line in lint(cfg2) if line.startswith("ERROR ")]
    assert any("m-no-def" in e and "缺少 impl_tier: default" in e for e in errs2)
    assert any("v2" in e and "合法 impl_tier" in e for e in errs2)
    assert any("v2" in e and "非空 modality" in e for e in errs2)

    cfg3, _ = _make_v57_wiki(tmp_path / "two_defaults")
    _write_method_page(
        cfg3,
        "m-two-def",
        implementations=[
            {
                "id": "d1",
                "title": "D1",
                "language": "R",
                "impl_tier": "default",
                "modality": "scRNA-seq",
                "entrypoint": "code/a.R:run",
                "dependencies": [],
            },
            {
                "id": "d2",
                "title": "D2",
                "language": "Python",
                "impl_tier": "default",
                "modality": "Visium ST",
                "entrypoint": "code/b.py:run",
                "dependencies": [],
            },
        ],
    )
    errs3 = [line for line in lint(cfg3) if line.startswith("ERROR ")]
    assert any("m-two-def" in e and "存在多个 impl_tier: default" in e for e in errs3)

    # Rule 3: Valid multi-impl slot + legacy unslotted method -> 0 ERROR
    cfg4, _ = _make_v57_wiki(tmp_path / "valid")
    _write_method_page(
        cfg4,
        "m-valid",
        implementations=[
            {
                "id": "d1",
                "title": "D1",
                "language": "R",
                "impl_tier": "default",
                "modality": "scRNA-seq",
                "entrypoint": "code/a.R:run",
                "dependencies": [],
            },
            {
                "id": "v1",
                "title": "V1",
                "language": "Python",
                "impl_tier": "variant",
                "modality": "Spatial Proteomics",
                "entrypoint": "code/b.py:run",
                "dependencies": [],
            },
        ],
    )
    _write_method_page(
        cfg4,
        "m-legacy",
        implementations=[
            {"id": "l1", "title": "L1", "language": "R", "entrypoint": "code/a.R:run", "dependencies": []},
            {"id": "l2", "title": "L2", "language": "Python", "entrypoint": "code/b.py:run", "dependencies": []},
        ],
    )
    assert [line for line in lint(cfg4) if line.startswith("ERROR ")] == []


# ------------------------------------------------------------------ 3. Paper Method Manifest Hard Gate


def _seed_analysis_with_impl(
    cfg: Config,
    mid: str,
    impl_id: str,
    *,
    verified: bool = True,
    impl_tier: str | None = "default",
    modality: str | None = "scRNA-seq",
) -> Path:
    asset = cfg.wiki_root / f"methods/{mid}"
    (asset / "code").mkdir(parents=True, exist_ok=True)
    src = asset / f"code/{impl_id}.py"
    src.write_text("def run(x):\n    return x\n", encoding="utf-8")
    impl_entry: dict = {
        "id": impl_id,
        "title": f"实现 {impl_id}",
        "language": "Python",
        "entrypoint": f"code/{impl_id}.py:run",
        "dependencies": [],
    }
    if impl_tier is not None:
        impl_entry["impl_tier"] = impl_tier
    if modality is not None:
        impl_entry["modality"] = modality
    if verified:
        impl_entry["verification"] = f"verification/{impl_id}.json"

    page = _write_method_page(cfg, mid, method_kind="analysis", implementations=[impl_entry])
    (asset / "runtime.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "method",
                "id": mid,
                "implementations": [
                    {
                        "id": impl_id,
                        "entry": f"code/{impl_id}.py",
                        "entry_function": "run",
                        "language": "Python",
                        "runtime_mode": "standalone",
                        "files": [f"code/{impl_id}.py"],
                        "required_packages": {},
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if verified:
        _write_receipt(asset, impl_id, {f"code/{impl_id}.py": _sha256(src)})
    return page


def test_method_manifest_gate_blocks_missing_on_v2_panel_and_validates_all_dispositions(tmp_path: Path):
    assert VALID_METHOD_DISPOSITIONS == frozenset({"method_impl", "reuse_impl", "paper_specific_only"})
    cfg, _ = _make_v57_wiki(tmp_path)
    _seed_analysis_with_impl(cfg, "annot-verified", "gmm-py", verified=True, impl_tier="default", modality="Spatial Proteomics")
    _seed_analysis_with_impl(cfg, "annot-unverified", "notrun-py", verified=False, impl_tier="default", modality="scRNA-seq")
    _seed_analysis_with_impl(cfg, "annot-noslot", "noslot-py", verified=True, impl_tier=None, modality=None)

    wf_path = _write_method_page(cfg, "wf-paper", method_kind="workflow")
    wf_dir = cfg.wiki_root / "methods/wf-paper"
    (wf_dir / "code").mkdir(parents=True, exist_ok=True)
    (wf_dir / "code/01_gmm.py").write_text("print('ok')\n", encoding="utf-8")
    (wf_dir / "code/02_reuse.py").write_text("print('reuse')\n", encoding="utf-8")
    (wf_dir / "code/03_custom.py").write_text("print('custom')\n", encoding="utf-8")

    # 1. schema_version=2 panel-manifest WITHOUT method-manifest -> lint ERROR
    (wf_dir / "panel-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "paper_id": "2026-test",
                "panels": [
                    {
                        "panel_key": "fig01/A",
                        "figure": "Fig. 1",
                        "panel": "1A",
                        "evidence_tier": "excluded_schematic",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    lint_errs = [line for line in lint(cfg) if line.startswith("ERROR ")]
    assert any("methods/wf-paper.md" in e and "method-manifest.yaml" in e for e in lint_errs)

    # 2. Invalid method-manifest cases are all intercepted
    bad_manifest = {
        "schema_version": 0,
        "paper_id": "",
        "workflow_id": "",
        "steps": [
            {
                "step_id": "s1",
                "title": "未验证实现冒充 method_impl",
                "script_path": "code/01_gmm.py",
                "method_disposition": "method_impl",
                "method_id": "annot-unverified",
                "implementation_id": "notrun-py",
            },
            {
                "step_id": "s1",  # duplicate step_id
                "title": "缺 impl_tier/modality 的 method_impl",
                "script_path": "code/missing.py",
                "method_disposition": "method_impl",
                "method_id": "annot-noslot",
                "implementation_id": "noslot-py",
            },
            {
                "step_id": "s3",
                "title": "越界路径与缺 note 的 reuse_impl",
                "script_path": "../secret.py",
                "method_disposition": "reuse_impl",
                "method_id": "annot-unverified",
                "implementation_id": "notrun-py",
                "disposition_note": "  ",
            },
            {
                "step_id": "s4",
                "title": "带 method_id 的 paper_specific_only",
                "script_path": "code/03_custom.py",
                "method_disposition": "paper_specific_only",
                "method_id": "annot-verified",
                "implementation_id": "gmm-py",
            },
            {
                "step_id": "s5",
                "title": "非法 disposition",
                "script_path": "code/03_custom.py",
                "method_disposition": "unknown_mode",
            },
        ],
    }
    (wf_dir / "method-manifest.yaml").write_text(yaml.safe_dump(bad_manifest, allow_unicode=True), encoding="utf-8")
    errs = method_manifest_errors(cfg, wf_path)
    assert any("schema_version" in e for e in errs)
    assert any("paper_id" in e for e in errs)
    assert any("workflow_id" in e for e in errs)
    assert any("实测验证状态必须为 verified" in e for e in errs)
    assert any("重复 step_id" in e for e in errs)
    assert any("code/missing.py" in e for e in errs)
    assert any("impl_tier" in e for e in errs)
    assert any("modality" in e for e in errs)
    assert any("安全的相对路径" in e for e in errs)
    assert any("reuse_impl 时必须声明非空字符串 disposition_note" in e for e in errs)
    assert any("paper_specific_only 时 method_id 必须为 None" in e for e in errs)
    assert any("paper_specific_only 时 implementation_id 必须为 None" in e for e in errs)
    assert any("unknown_mode" in e for e in errs)

    # 3. Valid method-manifest with all 3 dispositions passes lint with 0 ERROR
    good_manifest = {
        "schema_version": 1,
        "paper_id": "2026-test",
        "workflow_id": "wf-paper",
        "steps": [
            {
                "step_id": "step01-gmm",
                "title": "空间蛋白 GMM 细胞注释",
                "script_path": "code/01_gmm.py",
                "method_disposition": "method_impl",
                "method_id": "annot-verified",
                "implementation_id": "gmm-py",
            },
            {
                "step_id": "step02-reuse",
                "title": "复用既有已验证实现",
                "script_path": "code/02_reuse.py",
                "method_disposition": "reuse_impl",
                "method_id": "annot-verified",
                "implementation_id": "gmm-py",
                "disposition_note": "直接复用 gmm-py 独立实现，仅更换靶蛋白列表。",
            },
            {
                "step_id": "step03-custom",
                "title": "队列样本名清洗",
                "script_path": "code/03_custom.py",
                "method_disposition": "paper_specific_only",
                "method_id": None,
                "implementation_id": None,
                "disposition_note": "仅映射原文特定患者编号，无跨论文算法复用价值。",
            },
        ],
    }
    (wf_dir / "method-manifest.yaml").write_text(yaml.safe_dump(good_manifest, allow_unicode=True), encoding="utf-8")
    assert method_manifest_errors(cfg, wf_path) == []
    assert [line for line in lint(cfg) if line.startswith("ERROR ")] == []


# ------------------------------------------------------------------ 4. `rwiki verify-method`


def test_verify_method_runs_real_script_emits_clean_sha256_receipt_and_cli(tmp_path: Path, capsys):
    cfg, cfg_path = _make_v57_wiki(tmp_path)
    mid = "demo-algo"
    impl_id = "py-zscore"
    asset = cfg.wiki_root / f"methods/{mid}"
    (asset / "code").mkdir(parents=True, exist_ok=True)
    (asset / "example").mkdir(parents=True, exist_ok=True)

    algo_file = asset / "code/zscore.py"
    algo_file.write_text(
        "def compute_zscore(values):\n"
        "    mean = sum(values) / len(values)\n"
        "    var = sum((v - mean) ** 2 for v in values) / len(values)\n"
        "    sd = var ** 0.5 or 1.0\n"
        "    return [round((v - mean) / sd, 6) for v in values]\n",
        encoding="utf-8",
    )
    (asset / "example/sample.json").write_text(json.dumps([1.0, 2.0, 3.0, 4.0]), encoding="utf-8")
    (asset / f"example/verify_{impl_id}.py").write_text(
        "import argparse, importlib.util, json\n"
        "from pathlib import Path\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--code', type=Path, required=True)\n"
        "p.add_argument('--example', type=Path, required=True)\n"
        "p.add_argument('--out', type=Path, required=True)\n"
        "a = p.parse_args()\n"
        "spec = importlib.util.spec_from_file_location('zscore', a.code / 'zscore.py')\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "vals = json.loads((a.example / 'sample.json').read_text(encoding='utf-8'))\n"
        "res = mod.compute_zscore(vals)\n"
        "assert len(res) == 4 and abs(sum(res)) < 1e-5\n"
        "(a.out / 'result.json').write_text(json.dumps(res), encoding='utf-8')\n"
        "(a.out / 'checks.json').write_text(json.dumps({\n"
        "    'scope': '4-point numeric fixture zero-mean zscore check',\n"
        "    'checks': ['Output length equals input length', 'Mean of z-scores is within 1e-5 of 0'],\n"
        "}), encoding='utf-8')\n",
        encoding="utf-8",
    )

    page = _write_method_page(
        cfg,
        mid,
        implementations=[
            {
                "id": impl_id,
                "title": "Python Z-score 实现",
                "language": "Python",
                "impl_tier": "default",
                "modality": "Bulk RNA-seq",
                "entrypoint": "code/zscore.py:compute_zscore",
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
                        "entry": "code/zscore.py",
                        "entry_function": "compute_zscore",
                        "language": "Python",
                        "runtime_mode": "standalone",
                        "files": ["code/zscore.py"],
                        "required_packages": {},
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Path traversal / invalid IDs must be rejected
    with pytest.raises(WikiError, match="method_id 非法"):
        verify_method(cfg, "../escape", impl_id)
    with pytest.raises(WikiError, match="impl_id 非法"):
        verify_method(cfg, mid, "../escape")

    # Run via CLI and verify structured JSON summary + clean receipt
    rc = cli_main(["--config", str(cfg_path), "verify-method", mid, "--impl", impl_id])
    assert rc == 0
    cli_out = json.loads(capsys.readouterr().out)
    assert cli_out["method_id"] == mid
    assert cli_out["implementation"] == impl_id
    assert cli_out["state"] == "verified"
    assert cli_out["files"]["code/zscore.py"] == _sha256(algo_file)
    assert "checks.json" in cli_out["output_sha256"]
    assert "result.json" in cli_out["output_sha256"]

    receipt_file = asset / f"verification/{impl_id}.json"
    assert receipt_file.is_file()
    raw_receipt = receipt_file.read_text(encoding="utf-8")
    # Must NEVER contain machine drive paths or /Users/ /home/ paths (gh guard safety)
    assert ABS_RE.search(raw_receipt) is None, f"Absolute path leaked in receipt:\n{raw_receipt}"
    receipt_json = json.loads(raw_receipt)
    assert receipt_json["schema_version"] == 1
    assert receipt_json["state"] == "passed"
    assert receipt_json["command"].startswith("<PYTHON>")
    assert implementation_status(page)[0]["state"] == "verified"

    # Mutating code invalidates receipt to stale
    algo_file.write_text(algo_file.read_text(encoding="utf-8") + "\n# mutated\n", encoding="utf-8")
    assert implementation_status(page)[0]["state"] == "stale"

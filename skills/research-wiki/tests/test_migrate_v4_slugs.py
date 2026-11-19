"""Unit tests for archived docs/archive/migrate_v4_slugs.py."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "docs" / "archive"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from migrate_v4_slugs import SLUGS_MAP, build_mapping, migrate  # noqa: E402
from rwiki.aliases import resolve_page_ref  # noqa: E402
from rwiki.pages import read_page, write_page  # noqa: E402
from rwiki.runtime_contract import closure_hash, read_manifest, runtime_facts  # noqa: E402
from rwiki.verification import digest as sha256_file, replay_available, replay_inputs  # noqa: E402

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)

OLD_SHAP_BAR = "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar"
NEW_SHAP_BAR = "shap-importance-bar"
OLD_VENN = "2026-10-22-scp-example__fig12-venn--venn"
NEW_VENN = "set-venn"
OLD_FIG17 = "2026-10-22-scp-example__fig17-group-heatmap-dot--heatmap"
NEW_FIG17 = "scp-group-dot-heatmap"


def _setup_template(
    wiki: Path,
    tid: str,
    *,
    with_runtime: bool = False,
    portability_state: str | None = None,
    with_code_manifest: bool = False,
    body_extra: str = "",
    user_block: str = "<!-- user:start -->\r\n保留作者笔记 " + OLD_SHAP_BAR + "\r\n<!-- user:end -->",
) -> Path:
    tdir = wiki / "templates" / tid
    (tdir / "code").mkdir(parents=True, exist_ok=True)
    (tdir / "example").mkdir(parents=True, exist_ok=True)
    (tdir / "verify" / "history").mkdir(parents=True, exist_ok=True)
    (tdir / "source").mkdir(parents=True, exist_ok=True)

    spec = {
        "language": "python",
        "entry": "code/render.py",
        "panel": "code/panel.py",
        "tables": {"tbl": {"interface": "demo-iface"}},
        "style": {},
    }
    (tdir / "spec.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    (tdir / "code" / "render.py").write_text("print('ok')\n", encoding="utf-8")
    (tdir / "code" / "panel.py").write_text("def draw(): pass\n", encoding="utf-8")
    (tdir / "example" / "demo-iface.csv").write_text("a\n1\n", encoding="utf-8")
    (tdir / "source" / "orig.py").write_text(f"# {tid}\n", encoding="utf-8")
    (tdir / "preview.png").write_bytes(TINY_PNG)
    for ext in ("png", "pdf", "svg"):
        (tdir / "verify" / f"figure.{ext}").write_bytes(TINY_PNG if ext == "png" else b"%PDF")

    inputs = replay_inputs(tdir)
    outputs = {ext: sha256_file(tdir / "verify" / f"figure.{ext}") for ext in ("png", "pdf", "svg")}
    verify_json = {
        "schema_version": 2,
        "timestamp": "2026-10-25T10:00:00+00:00",
        "exit_code": 0,
        "inputs": inputs,
        "outputs": outputs,
    }
    (tdir / "verify" / "verify.json").write_text(json.dumps(verify_json, indent=2) + "\n", encoding="utf-8")
    (tdir / "verify" / "history" / "old.json").write_text(json.dumps({"old": tid}) + "\n", encoding="utf-8")

    if with_runtime:
        rt = {
            "schema_version": 1,
            "kind": "template",
            "id": tid,
            "entry": "code/render.py",
            "language": "python",
            "runtime_mode": "standalone",
            "files": ["code/panel.py", "code/render.py", "spec.json"],
            "required_packages": {"Python": []},
        }
        (tdir / "runtime.json").write_text(json.dumps(rt, indent=2) + "\n", encoding="utf-8")
        if portability_state is not None:
            rt["evidence"] = {"portability": "verify/runtime-portability.json"}
            (tdir / "runtime.json").write_text(json.dumps(rt, indent=2) + "\n", encoding="utf-8")
            manifest, _ = read_manifest(tdir, tid, "template")
            assert manifest is not None
            chash = closure_hash(tdir, manifest["implementations"][0])
            rp = {
                "schema_version": 1,
                "kind": "template",
                "implementation": tid,
                "state": "passed",
                "scope": "isolated test",
                "closure_hash": chash if portability_state == "verified" else "0" * 64,
                "files": {fn: sha256_file(tdir / fn) for fn in rt["files"]},
                "command": "python code/render.py",
                "environment": {"python": "3.11"},
                "checks": ["isolated run passed"],
                "outputs": {"figure.png": outputs["png"]},
                "executed_at": "2026-10-25T20:29:08+08:00",
            }
            (tdir / "verify" / "runtime-portability.json").write_text(
                json.dumps(rp, indent=2) + "\n", encoding="utf-8"
            )

    if with_code_manifest:
        cm = {
            "files": [
                {
                    "variant": "reusable",
                    "path": "code/panel.py",
                    "verification": {
                        "state": "example",
                        "evidence": [f"templates/{tid}/verify/verify.json"],
                    },
                }
            ]
        }
        (tdir / "code-manifest.json").write_text(json.dumps(cm, indent=2) + "\n", encoding="utf-8")

    (tdir / "acceptance.json").write_text(
        json.dumps({"schema_version": 1, "page": f"templates/{tid}.md", "snapshot": "abc"}, indent=2) + "\n",
        encoding="utf-8",
    )

    body = (
        f"# 模板 {tid}\n\n"
        f"![[templates/{tid}/preview.png]]\n\n"
        f"<!-- facts:start -->\n- facts {tid}\n<!-- facts:end -->\n\n"
        f"## 适用\n\n适用。\n\n"
        f"## 不适用\n\n{body_extra}\n\n"
        f"## 知识关联检查\n\n已检查。\n\n"
        f"{user_block}"
    )
    write_page(
        wiki / "templates" / f"{tid}.md",
        {
            "type": "template",
            "id": tid,
            "title": tid,
            "status": "ready",
            "layouts": ["2026-10-22-scp-example__fig12-venn"],
            "panels": ["A"],
            "language": "python",
            "tags": ["可视化"],
            "chart_types": ["bar"],
            "favorite": False,
        },
        body,
    )
    return tdir


@pytest.fixture
def sample_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    for d in ("templates", "layouts", "methods", "scenarios", "projects", "chart-types", "recipes", "interfaces", "sources"):
        (wiki / d).mkdir(parents=True, exist_ok=True)

    write_page(
        wiki / "interfaces" / "demo-iface.md",
        {
            "type": "interface",
            "slug": "demo-iface",
            "title": "Demo Interface",
            "columns": {"a": {"type": "int", "description": "val"}},
        },
        "# Demo\n\n<!-- facts:start -->\n<!-- facts:end -->\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    (wiki / "sources" / "snapshot.md").write_text(f"untouched {OLD_SHAP_BAR}\n", encoding="utf-8")

    _setup_template(
        wiki,
        OLD_SHAP_BAR,
        with_code_manifest=True,
        body_extra=f"参见 [[templates/{OLD_VENN}|维恩图]]。",
    )
    _setup_template(
        wiki,
        OLD_VENN,
        with_runtime=True,
        portability_state="verified",
        body_extra="来源 layout 2026-10-22-scp-example__fig12-venn 不可误改。",
    )
    _setup_template(
        wiki,
        OLD_FIG17,
        with_runtime=True,
        portability_state="invalid",
    )

    layout_dir = wiki / "layouts" / "2026-08-17-shap-feature-mechanism__fig01-shap-a-f"
    layout_dir.mkdir(parents=True)
    (layout_dir / "layout.json").write_text(
        json.dumps({"canvas": {"width_in": 6, "height_in": 4, "dpi": 150}, "panels": [{"letter": "A", "template": OLD_SHAP_BAR}]}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_page(
        wiki / "layouts" / "2026-08-17-shap-feature-mechanism__fig01-shap-a-f.md",
        {
            "type": "layout",
            "id": "2026-08-17-shap-feature-mechanism__fig01-shap-a-f",
            "title": "SHAP 组图",
            "status": "archived",
            "templates": [OLD_SHAP_BAR],
            "template_panels": {OLD_SHAP_BAR: ["A"]},
        },
        f"# Layout\n\n<!-- facts:start -->\n- {OLD_SHAP_BAR}\n<!-- facts:end -->\n\n参见 [[templates/{OLD_SHAP_BAR}]].\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    write_page(
        wiki / "methods" / "shap-explanation.md",
        {
            "type": "method",
            "id": "shap-explanation",
            "title": "SHAP",
            "status": "ready",
            "figure_relations": [
                {
                    "figure": f"templates/{OLD_SHAP_BAR}",
                    "compatibility": "direct",
                    "evidence": [f"templates/{OLD_SHAP_BAR}/spec.json"],
                }
            ],
            "next_steps": [
                {"direction": "d1", "viz_templates": [f"templates/{OLD_SHAP_BAR}"]}
            ],
        },
        f"# SHAP\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 知识关联检查\n\n[[templates/{OLD_SHAP_BAR}|bar]]\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    write_page(
        wiki / "scenarios" / "model-explanation.md",
        {
            "type": "scenario",
            "id": "model-explanation",
            "title": "模型解释",
            "picks": [{"id": f"templates/{OLD_SHAP_BAR}", "note": "bar"}],
            "steps": [{"id": "s1", "templates": [f"templates/{OLD_VENN}"]}],
        },
        f"# Scenario\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n| [[templates/{OLD_SHAP_BAR}]] |\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    write_page(
        wiki / "projects" / "demo-proj.md",
        {
            "type": "project",
            "slug": "demo-proj",
            "title": "Demo",
            "templates": [OLD_SHAP_BAR, OLD_VENN],
        },
        f"# Project\n\n- [[templates/{OLD_VENN}]]\n",
    )

    write_page(
        wiki / "chart-types" / "bar.md",
        {"type": "chart-type", "slug": "bar", "title": "bar"},
        f"# bar\n\n- [[templates/{OLD_SHAP_BAR}|SHAP]]\n",
    )
    write_page(
        wiki / "recipes" / "r1.md",
        {"type": "recipe", "id": "r1", "title": "r1", "status": "ready"},
        f"# r1\n\n## 知识关联检查\n\n[[templates/{OLD_VENN}|venn]]\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    user_bytes = b"<!-- user:start -->\r\n\xe4\xbf\x9d\xe7\x95\x99\xe4\xbd\x9c\xe8\x80\x85\xe7\xac\x94\xe8\xae\xb0 " + OLD_SHAP_BAR.encode("utf-8") + b"\r\n<!-- user:end -->"
    (wiki / ".protected-hashes.json").write_text(
        json.dumps(
            {"version": 1, "files": {f"templates/{OLD_SHAP_BAR}.md": [hashlib.sha256(user_bytes).hexdigest()]}},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return wiki


def test_build_mapping_is_31_to_31_bijection():
    mapping = build_mapping()
    assert len(mapping) == 31
    assert len(set(mapping.values())) == 31
    assert not (set(mapping.keys()) & set(mapping.values()))
    assert mapping[OLD_SHAP_BAR] == NEW_SHAP_BAR
    assert mapping[OLD_VENN] == NEW_VENN
    assert mapping[OLD_FIG17] == NEW_FIG17


def test_migrate_dry_run_makes_no_disk_changes(sample_wiki: Path):
    subset = {OLD_SHAP_BAR: NEW_SHAP_BAR, OLD_VENN: NEW_VENN, OLD_FIG17: NEW_FIG17}
    before_spec = (sample_wiki / "templates" / OLD_SHAP_BAR / "spec.json").read_bytes()

    report = migrate(sample_wiki, mapping=subset, dry_run=True)

    assert report["dry_run"] is True
    assert len(report["templates_migrated"]) == 3
    assert (sample_wiki / "templates" / f"{OLD_SHAP_BAR}.md").is_file()
    assert not (sample_wiki / "templates" / f"{NEW_SHAP_BAR}.md").exists()
    assert (sample_wiki / "templates" / OLD_SHAP_BAR / "spec.json").read_bytes() == before_spec


def test_migrate_apply_closure_receipts_and_invariants(sample_wiki: Path):
    subset = {OLD_SHAP_BAR: NEW_SHAP_BAR, OLD_VENN: NEW_VENN, OLD_FIG17: NEW_FIG17}
    shap_spec_before = (sample_wiki / "templates" / OLD_SHAP_BAR / "spec.json").read_bytes()
    shap_source_before = (sample_wiki / "templates" / OLD_SHAP_BAR / "source" / "orig.py").read_bytes()
    shap_hist_before = (sample_wiki / "templates" / OLD_SHAP_BAR / "verify" / "history" / "old.json").read_bytes()
    sources_before = (sample_wiki / "sources" / "snapshot.md").read_bytes()
    venn_rp_before = json.loads((sample_wiki / "templates" / OLD_VENN / "verify" / "runtime-portability.json").read_text(encoding="utf-8"))

    report = migrate(sample_wiki, mapping=subset, dry_run=False)

    assert report["dry_run"] is False
    assert len(report["templates_migrated"]) == 3

    # Old files removed, new files created
    assert not (sample_wiki / "templates" / f"{OLD_SHAP_BAR}.md").exists()
    assert not (sample_wiki / "templates" / OLD_SHAP_BAR).exists()
    assert (sample_wiki / "templates" / f"{NEW_SHAP_BAR}.md").is_file()
    assert (sample_wiki / "templates" / NEW_SHAP_BAR).is_dir()

    # Invariants: spec.json, source/, verify/history/, sources/ untouched
    assert (sample_wiki / "templates" / NEW_SHAP_BAR / "spec.json").read_bytes() == shap_spec_before
    assert (sample_wiki / "templates" / NEW_SHAP_BAR / "source" / "orig.py").read_bytes() == shap_source_before
    assert (sample_wiki / "templates" / NEW_SHAP_BAR / "verify" / "history" / "old.json").read_bytes() == shap_hist_before
    assert (sample_wiki / "sources" / "snapshot.md").read_bytes() == sources_before

    # Template markdown: id, aliases, preview embed, cross-link, layout ID not mangled, user block byte-exact
    meta, body = read_page(sample_wiki / "templates" / f"{NEW_SHAP_BAR}.md")
    assert meta["id"] == NEW_SHAP_BAR
    assert meta["aliases"] == [OLD_SHAP_BAR]
    assert meta["layouts"] == ["2026-10-22-scp-example__fig12-venn"]
    assert f"![[templates/{NEW_SHAP_BAR}/preview.png]]" in body
    assert f"[[templates/{NEW_VENN}|维恩图]]" in body
    assert f"<!-- facts:start -->\n- facts {OLD_SHAP_BAR}\n<!-- facts:end -->" in body
    assert f"<!-- user:start -->\r\n保留作者笔记 {OLD_SHAP_BAR}\r\n<!-- user:end -->" in body

    venn_meta, venn_body = read_page(sample_wiki / "templates" / f"{NEW_VENN}.md")
    assert "2026-10-22-scp-example__fig12-venn" in venn_body
    assert venn_meta["aliases"] == [OLD_VENN]

    # Alias resolution works post-migration
    assert resolve_page_ref(sample_wiki, OLD_SHAP_BAR, expected_type="template") == (sample_wiki / "templates" / f"{NEW_SHAP_BAR}.md").resolve()

    # verify.json replay_available() stays True for all 3
    for new_id in (NEW_SHAP_BAR, NEW_VENN, NEW_FIG17):
        assert replay_available(sample_wiki / "templates" / new_id) is True

    # runtime.json & runtime-portability.json: verified stays verified without fabricating timestamps; invalid stays invalid
    venn_rf = runtime_facts(sample_wiki / "templates" / NEW_VENN, NEW_VENN, "template")
    assert venn_rf["portability"]["state"] == "verified"
    venn_rp_after = json.loads((sample_wiki / "templates" / NEW_VENN / "verify" / "runtime-portability.json").read_text(encoding="utf-8"))
    assert venn_rp_after["implementation"] == NEW_VENN
    assert venn_rp_after["executed_at"] == venn_rp_before["executed_at"]
    assert venn_rp_after["command"] == venn_rp_before["command"]
    assert venn_rp_after["environment"] == venn_rp_before["environment"]
    assert venn_rp_after["closure_hash"] != venn_rp_before["closure_hash"]

    fig17_rf = runtime_facts(sample_wiki / "templates" / NEW_FIG17, NEW_FIG17, "template")
    assert fig17_rf["portability"]["state"] == "invalid"
    fig17_rp_after = json.loads((sample_wiki / "templates" / NEW_FIG17 / "verify" / "runtime-portability.json").read_text(encoding="utf-8"))
    assert fig17_rp_after["implementation"] == NEW_FIG17
    assert fig17_rp_after["closure_hash"] == "0" * 64

    # code-manifest.json & acceptance.json
    cm = json.loads((sample_wiki / "templates" / NEW_SHAP_BAR / "code-manifest.json").read_text(encoding="utf-8"))
    assert cm["files"][0]["verification"]["evidence"] == [f"templates/{NEW_SHAP_BAR}/verify/verify.json"]
    acc = json.loads((sample_wiki / "templates" / NEW_SHAP_BAR / "acceptance.json").read_text(encoding="utf-8"))
    assert acc["page"] == f"templates/{NEW_SHAP_BAR}.md"

    # layout.json & layout.md
    lj = json.loads((sample_wiki / "layouts" / "2026-08-17-shap-feature-mechanism__fig01-shap-a-f" / "layout.json").read_text(encoding="utf-8"))
    assert lj["panels"][0]["template"] == NEW_SHAP_BAR
    lmeta, lbody = read_page(sample_wiki / "layouts" / "2026-08-17-shap-feature-mechanism__fig01-shap-a-f.md")
    assert lmeta["templates"] == [NEW_SHAP_BAR]
    assert lmeta["template_panels"] == {NEW_SHAP_BAR: ["A"]}
    assert f"[[templates/{NEW_SHAP_BAR}]]" in lbody

    # method.md, scenario.md, project.md, chart-type.md, recipe.md
    mmeta, mbody = read_page(sample_wiki / "methods" / "shap-explanation.md")
    assert mmeta["figure_relations"][0]["figure"] == f"templates/{NEW_SHAP_BAR}"
    assert mmeta["figure_relations"][0]["evidence"] == [f"templates/{NEW_SHAP_BAR}/spec.json"]
    assert mmeta["next_steps"][0]["viz_templates"] == [f"templates/{NEW_SHAP_BAR}"]
    assert f"[[templates/{NEW_SHAP_BAR}|bar]]" in mbody

    smeta, sbody = read_page(sample_wiki / "scenarios" / "model-explanation.md")
    assert smeta["picks"][0]["id"] == f"templates/{NEW_SHAP_BAR}"
    assert smeta["steps"][0]["templates"] == [f"templates/{NEW_VENN}"]
    assert f"[[templates/{NEW_SHAP_BAR}]]" in sbody

    pmeta, pbody = read_page(sample_wiki / "projects" / "demo-proj.md")
    assert pmeta["templates"] == [NEW_SHAP_BAR, NEW_VENN]
    assert f"[[templates/{NEW_VENN}]]" in pbody

    _, cbody = read_page(sample_wiki / "chart-types" / "bar.md")
    assert f"[[templates/{NEW_SHAP_BAR}|SHAP]]" in cbody

    _, rbody = read_page(sample_wiki / "recipes" / "r1.md")
    assert f"[[templates/{NEW_VENN}|venn]]" in rbody

    # .protected-hashes.json key renamed cleanly
    pdata = json.loads((sample_wiki / ".protected-hashes.json").read_text(encoding="utf-8"))
    assert f"templates/{NEW_SHAP_BAR}.md" in pdata["files"]
    assert f"templates/{OLD_SHAP_BAR}.md" not in pdata["files"]

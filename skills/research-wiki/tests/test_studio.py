"""Tests for Bio-Template Studio, Stepwise Playbook/Next navigation, Project Tracker, TemplateSpec, FTS5, and MCP Server."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import SKILL_ROOT, write_config, write_interface
from rwiki.cli import main as cli_main
from rwiki.config import Config
from rwiki.facts import method_facts
from rwiki.pages import read_page, write_page
from rwiki.server import create_app
from rwiki.template_spec import validate_spec_model

# 1x1 valid PNG bytes
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def studio_env(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    for folder in ("methods", "templates", "recipes", "interfaces", "scenarios", "projects"):
        (wiki / folder).mkdir(parents=True, exist_ok=True)
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text('{"scenarios": {}}', encoding="utf-8")

    # Interfaces
    write_interface(
        wiki,
        "scrna-annotated-cells",
        {
            "cell_id": {"type": "str", "description": "细胞 ID"},
            "cell_type": {"type": "str", "description": "细胞类型"},
            "umap_1": {"type": "float", "description": "UMAP 1"},
            "umap_2": {"type": "float", "description": "UMAP 2"},
        },
        "已注释单细胞表",
    )
    write_interface(
        wiki,
        "cell-proportion-stats",
        {
            "sample_id": {"type": "str", "description": "样本"},
            "cell_type": {"type": "str", "description": "细胞类型"},
            "proportion": {"type": "float", "description": "比例"},
        },
        "细胞比例统计表",
    )

    # Method with next_steps
    write_page(
        wiki / "methods/cell-type-annotation.md",
        {
            "type": "method",
            "id": "cell-type-annotation",
            "title": "细胞类型注释",
            "status": "ready",
            "tags": ["单细胞分析"],
            "inputs": ["scrna-annotated-cells"],
            "outputs": ["scrna-annotated-cells", "cell-proportion-stats"],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "method_kind": "analysis",
            "purposes": ["注释与参考映射"],
            "next_steps": [
                {
                    "direction": "细胞比例与 Ro/e 组织偏好分析",
                    "when": "完成细胞注释后，需要比较不同分组间各亚群比例变化",
                    "analysis_templates": ["cell-proportion-roe"],
                    "intermediate_interface": "cell-proportion-stats",
                    "viz_templates": ["tpl-prop-bar"],
                },
                {
                    "direction": "亚群拟时序轨迹推断",
                    "when": "关注特定细胞类型谱系分化路径",
                    "analysis_templates": ["trajectory-inference"],
                    "intermediate_interface": "scrna-annotated-cells",
                    "viz_templates": ["tpl-prop-bar"],
                },
            ],
        },
        "<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n细胞类型注释。\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    # Downstream method matching input interface
    write_page(
        wiki / "methods/cell-proportion-roe.md",
        {
            "type": "method",
            "id": "cell-proportion-roe",
            "title": "细胞比例与 Ro/e 分析",
            "status": "ready",
            "tags": ["单细胞分析"],
            "inputs": ["cell-proportion-stats"],
            "outputs": [],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "method_kind": "analysis",
            "purposes": ["比较与差异"],
        },
        "<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n比例分析。\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    (wiki / "methods/cell-proportion-roe/code").mkdir(parents=True)
    (wiki / "methods/cell-proportion-roe/code/run.R").write_text("# proportion roe R script\n", encoding="utf-8")

    # Tier 1 Python Template
    tpl_dir = wiki / "templates/tpl-prop-bar"
    (tpl_dir / "code").mkdir(parents=True)
    (tpl_dir / "code/__init__.py").write_text("", encoding="utf-8")
    (tpl_dir / "code/panel.py").write_text(
        "from pathlib import Path\n"
        f"Path('studio_out.png').write_bytes({TINY_PNG!r})\n"
        "print('RENDERED_OK', RWIKI_PARAMS.get('palette'))\n",
        encoding="utf-8",
    )
    (tpl_dir / "code/render.py").write_text("print('render')\n", encoding="utf-8")
    (tpl_dir / "spec.json").write_text(
        json.dumps(
            {
                "entry": "code/render.py",
                "panel": "code/panel.py",
                "language": "python",
                "tables": {
                    "prop": {"interface": "cell-proportion-stats", "description": "比例输入表"},
                },
                "style": {"width_in": 7.5, "height_in": 5.0},
                "parameters": {
                    "palette": {
                        "type": "select",
                        "label": "顶刊配色",
                        "default": "NPG",
                        "choices": ["NPG", "Nature", "Lancet", "NEJM", "JAMA", "Cell"],
                    },
                    "p_cutoff": {"type": "float", "label": "P阈值", "default": 0.05, "min": 0.0, "max": 1.0},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_page(
        wiki / "templates/tpl-prop-bar.md",
        {
            "type": "template",
            "id": "tpl-prop-bar",
            "title": "细胞比例柱状图",
            "status": "ready",
            "sources": ["recipes/rec-demo"],
            "panels": [],
            "language": "python",
            "chart_types": ["bar"],
            "tags": ["单细胞分析"],
            "favorite": False,
        },
        "<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n比例可视化。\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    # Tier 2 L1 Recipe
    rec_dir = wiki / "recipes/rec-demo"
    (rec_dir / "repair").mkdir(parents=True)
    (rec_dir / "repair/FigureYaDemo.Rmd").write_text(
        "---\ntitle: Demo\n---\n```{r}\nmessage('hello')\n```\n",
        encoding="utf-8",
    )
    write_page(
        wiki / "recipes/rec-demo.md",
        {
            "type": "recipe",
            "id": "rec-demo",
            "title": "Demo Rmd 配方",
            "status": "ready",
            "source": {"id": "figureya", "item": "Demo", "commit": "abc123"},
            "license": "CC-BY-NC-SA-4.0",
            "language": "r",
            "runner": "rmarkdown",
            "entry": "FigureYaDemo.Rmd",
            "tags": ["转录组"],
            "chart_types": ["volcano"],
            "favorite": False,
            "inputs": [{"file": "easy_input.csv", "note": "表达矩阵"}],
        },
        "<!-- facts:start -->\n<!-- facts:end -->\n\n## 用途\n测试配方。\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    # Playbook scenario
    write_page(
        wiki / "scenarios/scrna-stepwise-playbook.md",
        {
            "type": "scenario",
            "id": "scrna-stepwise-playbook",
            "title": "单细胞转录组步进决策树",
            "summary": "从 QC 到注释再到 6 大下游分支",
            "picks": [{"id": "cell-type-annotation", "note": "核心注释"}],
            "steps": [
                {
                    "id": "cell-type-annotation",
                    "title": "细胞类型注释",
                    "method_id": "cell-type-annotation",
                    "interface": "scrna-annotated-cells",
                    "templates": ["tpl-prop-bar"],
                    "next": ["cell-proportion-roe"],
                },
                {
                    "id": "cell-proportion-roe",
                    "title": "细胞比例与 Ro/e 分析",
                    "method_id": "cell-proportion-roe",
                    "interface": "cell-proportion-stats",
                    "templates": ["tpl-prop-bar"],
                    "next": [],
                },
            ],
        },
        "## 什么时候用\n单细胞分析。\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    cfg_path = write_config(tmp_path / "config.json", wiki)
    cfg = Config(
        wiki, gallery, taxonomy, Path(sys.executable), Path("Rscript"), 8765,
        work_root=tmp_path / "work",
    )
    return cfg, cfg_path, tmp_path


def test_method_facts_renders_next_steps(studio_env):
    cfg, _, _ = studio_env
    meta, _ = read_page(cfg.wiki_root / "methods/cell-type-annotation.md")
    rendered = method_facts(cfg, meta)
    assert "- 下一步分析导航（Step N → Step N+1）：" in rendered
    assert "细胞比例与 Ro/e 组织偏好分析" in rendered
    assert "cell-proportion-stats" in rendered


def test_cli_next_and_playbooks_api(studio_env, capsys):
    cfg, cfg_path, _ = studio_env
    assert cli_main(["--config", str(cfg_path), "next", "cell-type-annotation", "--q", "拟时序", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["node_id"] == "cell-type-annotation"
    assert len(payload["next_steps"]) == 1
    assert "拟时序" in payload["next_steps"][0]["direction"]

    with TestClient(create_app(cfg)) as client:
        pb = client.get("/api/playbooks")
        assert pb.status_code == 200
        data = pb.json()
        assert data["playbooks"][0]["id"] == "scrna-stepwise-playbook"
        assert data["graph"]["nodes"] and data["graph"]["edges"]

        nxt = client.get("/api/next/cell-type-annotation")
        assert nxt.status_code == 200
        nxt_data = nxt.json()
        assert len(nxt_data["next_steps"]) == 2
        assert any(m["id"] == "tpl-prop-bar" for m in nxt_data["structural_matches"])


def test_studio_sniff_render_dispatch_run_and_projects_api(studio_env, tmp_path):
    cfg, _, root_tmp = studio_env
    csv_file = root_tmp / "expr.csv"
    csv_file.write_text(
        "sample_id,cell_type,proportion\nS1,T_cell,0.42\nS2,B_cell,0.18\nS1,Mac,0.40\n",
        encoding="utf-8",
    )
    proj_dir = root_tmp / "my_study"
    proj_dir.mkdir()

    with TestClient(create_app(cfg)) as client:
        # 1. Sniff
        sniff = client.post("/api/studio/sniff", json={"path": str(csv_file)})
        assert sniff.status_code == 200, sniff.text
        sniff_data = sniff.json()
        assert sniff_data["row_count_estimate"] == 3
        col_types = {c["name"]: c["type"] for c in sniff_data["columns"]}
        assert col_types["proportion"] == "continuous"
        assert col_types["cell_type"] == "discrete"

        # 2. Tier 1 render-code
        r1 = client.post("/api/studio/render-code", json={
            "id": "tpl-prop-bar",
            "project_dir": str(proj_dir),
            "data_file": str(csv_file),
            "bindings": {"sample_id": "sample_id", "cell_type": "cell_type", "proportion": "proportion"},
            "parameters": {"palette": "Lancet", "p_cutoff": 0.01},
        })
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert d1["language"] == "Python"
        assert "Lancet" in d1["code"] and "RWIKI_PALETTE_COLORS" in d1["code"]
        assert d1["bindings_json"]["columns"]["cell_type"] == "cell_type"
        assert d1["spec"]["tier"] == 1

        # 3. Tier 2 recipe render-code
        r2 = client.post("/api/studio/render-code", json={
            "id": "rec-demo",
            "project_dir": str(proj_dir),
            "data_file": str(csv_file),
            "bindings": {},
            "parameters": {"palette": "NPG"},
        })
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        assert d2["language"] == "R"
        assert d2["spec"]["tier"] == 2
        assert "FigureYaDemo.Rmd" in d2["code"]

        # 4. Dispatch
        disp = client.post("/api/studio/dispatch", json={
            "id": "tpl-prop-bar",
            "project_dir": str(proj_dir),
            "data_file": str(csv_file),
            "bindings": {"sample_id": "sample_id", "cell_type": "cell_type", "proportion": "proportion"},
            "parameters": {"palette": "Nature"},
        })
        assert disp.status_code == 200, disp.text
        disp_data = disp.json()
        assert disp_data["ok"] is True
        dest = Path(disp_data["output_dir"])
        assert (dest / "bindings.json").is_file()
        assert (dest / "run_studio.py").is_file()
        assert (dest / "RWIKI-USE.md").is_file()

        # Reject dispatch inside wiki_root
        bad_disp = client.post("/api/studio/dispatch", json={
            "id": "tpl-prop-bar",
            "project_dir": str(cfg.wiki_root),
            "data_file": str(csv_file),
            "bindings": {},
            "parameters": {},
        })
        assert bad_disp.status_code == 400

        # 5. Run local Python template & fetch preview
        run_resp = client.post("/api/studio/run", json={
            "id": "tpl-prop-bar",
            "project_dir": str(proj_dir),
            "data_file": str(csv_file),
            "bindings": {},
            "parameters": {"palette": "NEJM"},
        })
        assert run_resp.status_code == 200, run_resp.text
        run_data = run_resp.json()
        assert run_data["ok"] is True and run_data["exit_code"] == 0
        assert "RENDERED_OK NEJM" in run_data["stdout"]
        assert "studio_out.png" in run_data["output_files"]
        assert run_data["preview_url"]
        img = client.get(run_data["preview_url"])
        assert img.status_code == 200 and img.content == TINY_PNG

        # 6. Projects API
        step_resp = client.post("/api/projects/study-alpha/step", json={
            "title": "细胞比例统计",
            "templates": "tpl-prop-bar",
            "observation": "中性粒细胞升高",
            "next_branch": "细胞通讯分析",
        })
        assert step_resp.status_code == 200, step_resp.text
        proj_list = client.get("/api/projects").json()["projects"]
        assert len(proj_list) == 1
        assert proj_list[0]["id"] == "study-alpha"
        assert proj_list[0]["steps"][0]["templates"] == "tpl-prop-bar"


def test_template_spec_validation_and_fts5_search(studio_env):
    cfg, _, _ = studio_env
    model = validate_spec_model({
        "id": "tpl-prop-bar",
        "language": "python",
        "entry": "code/render.py",
        "tables": {"prop": {"interface": "cell-proportion-stats", "description": "比例"}},
        "parameters": {"palette": {"type": "select", "default": "NPG", "choices": ["NPG", "Nature"]}},
    })
    assert model.id == "tpl-prop-bar"
    assert model.parameters["palette"].default == "NPG"

    from rwiki.search import search
    res = search(cfg, "细胞类型注释")
    assert res["index"]["engine"] == "sqlite3-fts5"
    assert (cfg.work_root / "search/knowledge.sqlite3").is_file()
    assert res["results"][0]["id"] == "cell-type-annotation"


def test_mcp_server_jsonrpc_and_stdio(studio_env):
    cfg, cfg_path, root_tmp = studio_env
    import mcp_server

    init_resp = mcp_server.dispatch_mcp_request(cfg, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init_resp["result"]["serverInfo"]["name"] == "research-wiki-mcp"

    list_resp = mcp_server.dispatch_mcp_request(cfg, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tool_names = {t["name"] for t in list_resp["result"]["tools"]}
    assert tool_names == {
        "rwiki_next",
        "rwiki_search",
        "rwiki_show",
        "rwiki_render_code",
        "rwiki_dispatch",
        "rwiki_add_project_step",
    }

    next_resp = mcp_server.dispatch_mcp_request(cfg, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "rwiki_next", "arguments": {"node_id": "cell-type-annotation"}},
    })
    assert next_resp["result"]["isError"] is False
    assert len(next_resp["result"]["structuredContent"]["next_steps"]) == 2

    step_resp = mcp_server.dispatch_mcp_request(cfg, {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "rwiki_add_project_step",
            "arguments": {"project_id": "mcp-proj", "title": "MCP步骤", "templates": "tpl-prop-bar"},
        },
    })
    assert step_resp["result"]["isError"] is False
    assert (cfg.wiki_root / "projects/mcp-proj.md").is_file()

    # Subprocess stdio smoke test
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(SKILL_ROOT / "mcp_server.py"), "--config", str(cfg_path)],
        input=json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/list"}) + "\n",
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    out_line = json.loads(proc.stdout.strip().splitlines()[0])
    assert out_line["id"] == 9 and len(out_line["result"]["tools"]) == 6


def test_studio_upload_and_load_example_api(studio_env):
    import base64

    cfg, _, _ = studio_env
    # Write a built-in example CSV into the template asset directory
    ex_dir = cfg.wiki_root / "templates/tpl-prop-bar/example"
    ex_dir.mkdir(parents=True, exist_ok=True)
    (ex_dir / "cell-proportion-stats.csv").write_text(
        "sample_id,cell_type,proportion\nS1,Tcell,0.55\nS2,Bcell,0.45\n",
        encoding="utf-8",
    )

    with TestClient(create_app(cfg)) as client:
        ex_resp = client.post("/api/studio/load-example", json={"id": "tpl-prop-bar"})
        assert ex_resp.status_code == 200, ex_resp.text
        ex_data = ex_resp.json()
        assert ex_data["ok"] is True
        assert ex_data["suggested_bindings"]["cell_type"] == "cell_type"
        assert ex_data["sniff"]["row_count_estimate"] == 2

        csv_bytes = b"sample_id,cell_type,proportion\nA1,Mono,0.3\nA2,Neu,0.7\n"
        up_resp = client.post("/api/studio/upload", json={
            "filename": "custom upload.csv",
            "content_base64": base64.b64encode(csv_bytes).decode("ascii"),
        })
        assert up_resp.status_code == 200, up_resp.text
        up_data = up_resp.json()
        assert up_data["ok"] is True
        assert Path(up_data["path"]).is_file()
        assert up_data["sniff"]["row_count_estimate"] == 2

"""CLI tests for lightweight project tracker (`rwiki project list|show|add-step`) and discover-methods."""
import json
from pathlib import Path

from conftest import write_config
from rwiki.cli import main


def run(argv, capsys) -> dict:
    assert main(argv) == 0
    return json.loads(capsys.readouterr().out)


def test_project_tracker_cli_roundtrip(tmp_path, capsys):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "projects").mkdir()
    cfg_path = write_config(tmp_path / "c.json", wiki)

    empty = run(["--config", str(cfg_path), "project", "list", "--json"], capsys)
    assert empty["projects"] == []

    added1 = run([
        "--config", str(cfg_path), "project", "add-step", "asthma-scrna",
        "--project-title", "哮喘单细胞乳酸化课题",
        "--title", "细胞类型注释",
        "--templates", "cell-type-annotation, fig-umap",
        "--observation", "发现巨噬细胞亚群高表达糖酵解",
        "--next", "基因集打分与比例分析",
        "--json",
    ], capsys)
    assert added1["id"] == "asthma-scrna"
    assert len(added1["steps"]) == 1
    assert added1["steps"][0]["step"] == 1

    added2 = run([
        "--config", str(cfg_path), "project", "add-step", "asthma-scrna",
        "--title", "细胞比例与 Ro/e 分析",
        "--templates", "cell-proportion-roe",
        "--observation", "M2 巨噬细胞在模型组显著富集",
        "--next", "拟时序轨迹分析",
        "--json",
    ], capsys)
    assert len(added2["steps"]) == 2
    assert added2["steps"][1]["step"] == 2

    listed = run(["--config", str(cfg_path), "project", "list", "--json"], capsys)
    assert [p["id"] for p in listed["projects"]] == ["asthma-scrna"]

    shown = run(["--config", str(cfg_path), "project", "show", "asthma-scrna", "--json"], capsys)
    assert "### Step 1：细胞类型注释" in shown["body"]
    assert "### Step 2：细胞比例与 Ro/e 分析" in shown["body"]
    assert "**【所用模版】**：cell-proportion-roe" in shown["body"]


def test_discover_methods_cli(tmp_path, capsys):
    from rwiki.config import load_config
    from rwiki.methods import scaffold_method
    from rwiki.pages import read_page, write_page
    from rwiki.store import init

    wiki = tmp_path / "wiki"
    tax = tmp_path / "tax.yaml"
    tax.write_text('{"scenarios": {}}', encoding="utf-8")
    config_path = write_config(tmp_path / "c.json", wiki)
    config = load_config(config_path)
    init(config)
    scaffold_method(config, "dm", "dm", "MIT", written=True)
    page = config.wiki_root / "methods/dm.md"
    meta, body = read_page(page)
    meta.update(
        method_kind="analysis",
        summary="x",
        cite=["s"],
        data_contract={"input": "i", "output": "o"},
        implementations=[{
            "id": "b",
            "title": "b",
            "language": "R",
            "entrypoint": "code/x.R:f",
            "dependencies": [],
        }],
    )
    write_page(page, meta, body)
    code = page.with_suffix("") / "code"
    code.mkdir(parents=True)
    (code / "x.R").write_text("f <- function(x) x\n", encoding="utf-8")
    out = run(["--config", str(config_path), "discover-methods"], capsys)
    cand = next(c for c in out["candidates"] if c["id"] == "dm")
    assert cand["executable"] is False and cand["readiness"]["not_run"] == ["b"]

import csv
import json
from pathlib import Path

from rwiki.config import Config
from rwiki.facts import template_facts
from rwiki.input_binding import prepare_tables
from rwiki.pages import write_page
from rwiki.spec import check_data, load_spec, requirements_markdown
from rwiki.template_spec import load_unified_spec


def _cfg(root: Path) -> Config:
    return Config(
        wiki_root=root,
        gallery_root=root.parent / "gallery",
        taxonomy=root.parent / "taxonomy.yaml",
        python_exe=Path("python"),
        rscript_exe=Path("Rscript"),
        port=8765,
        function_defaults={},
        single_panel_only=True,
    )


def test_inline_table_spec_loads_and_checks_without_interface_md(tmp_path: Path):
    wiki = tmp_path / "wiki"
    tpl_dir = wiki / "templates" / "fy-demo"
    (tpl_dir / "code").mkdir(parents=True)
    (tpl_dir / "example").mkdir(parents=True)
    (tpl_dir / "code" / "render.R").write_text("# render\n", encoding="utf-8")
    (tpl_dir / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    # Trailing space in header cell is tolerated
    with (tpl_dir / "example" / "easy_input.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["group ", "value"])
        w.writerow(["A", "1.5"])

    spec = {
        "entry": "code/render.R",
        "language": "r",
        "tables": {
            "easy_input": {
                "interface": "",
                "filename": "easy_input.csv",
                "description": "演示输入",
                "required": True,
                "columns": {
                    "group": {"type": "str", "description": "分组", "required": True},
                    "value": {"type": "float", "description": "数值", "required": True},
                },
            }
        },
        "style": {"dpi": 200},
    }
    (tpl_dir / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    tpl_meta = {
        "type": "template",
        "id": "fy-demo",
        "title": "演示原生模板",
        "status": "ready",
        "layouts": [],
        "sources": [],
        "panels": [],
        "language": "r",
        "license": "CC-BY-NC-SA-4.0",
        "tags": ["other"],
        "chart_types": ["boxplot"],
        "keywords": [],
        "favorite": False,
    }
    write_page(wiki / "templates" / "fy-demo.md", tpl_meta, "# 演示原生模板\n")

    loaded = load_spec(tpl_dir)
    assert loaded["tables"]["easy_input"]["filename"] == "easy_input.csv"
    check_data(loaded, tpl_dir / "example")
    md = requirements_markdown(loaded)
    assert "模板内联表结构" in md and "easy_input.csv" in md

    cfg = _cfg(wiki)
    unified = load_unified_spec(cfg, "fy-demo")
    assert unified["tables"]["easy_input"]["filename"] == "easy_input.csv"
    assert "group" in unified["tables"]["easy_input"]["columns"]

    facts = template_facts(cfg, tpl_meta)
    assert "未声明" in facts

    work_dir = tmp_path / "work"
    reports = prepare_tables(
        loaded,
        {"tables": {"easy_input": {"file": "easy_input.csv", "columns": {"group": "group ", "value": "value"}}}},
        tpl_dir / "example",
        work_dir,
    )
    assert len(reports) == 1
    assert (work_dir / "easy_input.csv").is_file()

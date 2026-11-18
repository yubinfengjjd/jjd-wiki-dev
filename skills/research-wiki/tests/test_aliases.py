"""TDD tests for type-aware canonical ID & alias resolution and lint validation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import write_config, write_interface
from rwiki.aliases import alias_errors, resolve_asset_subpath, resolve_page_ref
from rwiki.asset_checkout import _page as checkout_page
from rwiki.config import load_config
from rwiki.deletion import prepare as deletion_prepare
from rwiki.errors import WikiError
from rwiki.finder import _page as finder_page, show as finder_show, use as finder_use
from rwiki.links import resolve as link_resolve
from rwiki.lint import lint
from rwiki.pages import read_page, visual_path, write_page
from rwiki.relations import _target as relation_target, relations_for
from rwiki.server import create_app
from rwiki.suggest import _locate_node, suggest_next_steps
from rwiki.template_spec import load_unified_spec
from rwiki.templates import ready_page, render as render_template

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)

OLD_TEMPLATE_ID = "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar"
NEW_TEMPLATE_ID = "shap-bar"
OLD_METHOD_ID = "2026-08-17-old__cell_annot"
NEW_METHOD_ID = "cell-type-annotation"


@pytest.fixture
def alias_env(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    for folder in (
        "templates",
        "methods",
        "recipes",
        "layouts",
        "scenarios",
        "interfaces",
        "chart-types",
        "projects",
        "sources",
    ):
        (wiki / folder).mkdir(parents=True, exist_ok=True)
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text(
        json.dumps({"scenarios": {"visualization": ["单细胞分析"]}}, ensure_ascii=False),
        encoding="utf-8",
    )

    write_interface(
        wiki,
        "feature-importance",
        {
            "feature": {"type": "str", "description": "特征名"},
            "importance": {"type": "float", "description": "重要性"},
        },
        "特征重要性表",
    )
    write_interface(
        wiki,
        "scrna-annotated-cells",
        {
            "cell_id": {"type": "str", "description": "细胞 ID"},
            "cell_type": {"type": "str", "description": "细胞类型"},
        },
        "已注释单细胞表",
    )

    write_page(
        wiki / "chart-types/bar.md",
        {"type": "chart-type", "slug": "bar", "title": "柱状图"},
        "# 柱状图\n",
    )
    write_page(
        wiki / "recipes/volcano-recipe.md",
        {
            "type": "recipe",
            "id": "volcano-recipe",
            "aliases": ["FigureYa59volcanoV2"],
            "title": "火山图配方",
            "status": "ready",
            "source": {"id": "figureya", "item": "FigureYa59volcanoV2", "commit": "abc123"},
            "license": "MIT",
            "language": "r",
            "runner": "knitr",
            "entry": "FigureYa59volcanoV2.Rmd",
            "tags": ["单细胞分析"],
            "chart_types": ["bar"],
            "favorite": False,
        },
        "# 火山图配方\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    (wiki / "recipes/volcano-recipe/source").mkdir(parents=True, exist_ok=True)
    (wiki / "recipes/volcano-recipe/source/FigureYa59volcanoV2.Rmd").write_text(
        "plot(1:5)\n", encoding="utf-8"
    )

    # Canonical template with legacy alias containing `__` and `--`
    tpl_dir = wiki / "templates" / NEW_TEMPLATE_ID
    (tpl_dir / "code").mkdir(parents=True, exist_ok=True)
    (tpl_dir / "example").mkdir(parents=True, exist_ok=True)
    (tpl_dir / "preview.png").write_bytes(TINY_PNG)
    (tpl_dir / "code/__init__.py").write_text("", encoding="utf-8")
    (tpl_dir / "code/panel.py").write_text(
        "def draw(fig, rect, tables, style):\n    pass\n",
        encoding="utf-8",
    )
    (tpl_dir / "code/render.py").write_text(
        "# render SHAP bar\n"
        "import argparse\n"
        "from pathlib import Path\n"
        "ap = argparse.ArgumentParser()\n"
        "ap.add_argument('--data', required=True)\n"
        "ap.add_argument('--out', required=True)\n"
        "ap.add_argument('--style')\n"
        "args = ap.parse_args()\n"
        "out = Path(args.out)\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "for ext in ('png', 'pdf', 'svg'):\n"
        "    (out / f'figure.{ext}').write_bytes(b'ok')\n",
        encoding="utf-8",
    )
    (tpl_dir / "example/feature-importance.csv").write_text(
        "feature,importance\ngeneA,0.9\ngeneB,0.4\n",
        encoding="utf-8",
    )
    (tpl_dir / "spec.json").write_text(
        json.dumps(
            {
                "entry": "code/render.py",
                "panel": "code/panel.py",
                "language": "python",
                "tables": {
                    "main": {
                        "interface": "feature-importance",
                        "description": "特征重要性",
                    }
                },
                "style": {"palette": "NPG"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_page(
        wiki / f"templates/{NEW_TEMPLATE_ID}.md",
        {
            "type": "template",
            "id": NEW_TEMPLATE_ID,
            "aliases": [OLD_TEMPLATE_ID],
            "title": "SHAP 特征条形图",
            "status": "ready",
            "layouts": [],
            "sources": ["recipes/volcano-recipe"],
            "panels": [],
            "language": "python",
            "tags": ["单细胞分析"],
            "chart_types": ["bar"],
            "favorite": False,
        },
        "# SHAP 特征条形图\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        "## 适用\n\n特征重要性展示。\n\n## 不适用\n\n非数值特征。\n\n"
        "## 知识关联检查\n\n已核对。\n\n## 数据要求\n\n待生成。\n\n"
        "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    # Canonical method with legacy alias and relation to template via alias
    write_page(
        wiki / f"methods/{NEW_METHOD_ID}.md",
        {
            "type": "method",
            "id": NEW_METHOD_ID,
            "aliases": [OLD_METHOD_ID],
            "title": "细胞类型注释",
            "status": "ready",
            "tags": ["单细胞分析"],
            "inputs": ["scrna-annotated-cells"],
            "outputs": ["feature-importance"],
            "source": {"kind": "written"},
            "license": "MIT",
            "cite": ["Test Ref 2026"],
            "favorite": False,
            "method_kind": "analysis",
            "purposes": ["注释与参考映射"],
            "next_steps": [
                {
                    "direction": "特征可视化",
                    "when": "完成注释后",
                    "intermediate_interface": "feature-importance",
                    "viz_templates": [NEW_TEMPLATE_ID],
                }
            ],
            "figure_relations": [
                {
                    "figure": f"templates/{OLD_TEMPLATE_ID}",
                    "compatibility": "direct",
                    "reason": "输出特征重要性可直接绘图",
                    "prerequisites": [],
                    "adaptation": "",
                    "evidence": ["sections/output"],
                    "verification": {
                        "state": "not_run",
                        "scope": "接口一致",
                        "evidence": [],
                    },
                }
            ],
        },
        "# 细胞类型注释\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        "## 用途\n\n细胞注释。\n\n## 适用\n\n单细胞矩阵。\n\n## 不适用\n\nBulk。\n\n"
        "## 输入\n\n已注释单细胞表。\n\n## 怎么做\n\n运行注释。\n\n## 代码\n\n示例。\n\n"
        "## 输出\n\n特征重要性。\n\n## 知识关联检查\n\n已核对。\n\n"
        "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )

    (wiki / "log.md").write_text("## [2026-11-18 00:00 UTC] init\n", encoding="utf-8")
    (wiki / "index.md").write_text("# 目录\n", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("TOP_SECRET\n", encoding="utf-8")

    cfg_path = write_config(
        tmp_path / "config.json",
        wiki,
        gallery_root=str(gallery),
        taxonomy=str(taxonomy),
    )
    cfg = load_config(cfg_path)
    return cfg, cfg_path, tmp_path


def test_resolve_page_ref_canonical_and_alias(alias_env):
    cfg, _, _ = alias_env
    root = cfg.wiki_root
    expected_tpl = (root / "templates" / f"{NEW_TEMPLATE_ID}.md").resolve()
    expected_method = (root / "methods" / f"{NEW_METHOD_ID}.md").resolve()

    assert resolve_page_ref(root, NEW_TEMPLATE_ID) == expected_tpl
    assert resolve_page_ref(root, f"templates/{NEW_TEMPLATE_ID}") == expected_tpl
    assert resolve_page_ref(root, f"templates/{NEW_TEMPLATE_ID}.md") == expected_tpl

    assert resolve_page_ref(root, OLD_TEMPLATE_ID) == expected_tpl
    assert resolve_page_ref(root, OLD_TEMPLATE_ID, expected_type="template") == expected_tpl
    assert resolve_page_ref(root, f"templates/{OLD_TEMPLATE_ID}") == expected_tpl
    assert resolve_page_ref(root, f"templates/{OLD_TEMPLATE_ID}.md") == expected_tpl
    assert resolve_page_ref(root, OLD_TEMPLATE_ID, expected_type="method") is None
    assert resolve_page_ref(root, f"templates/{OLD_TEMPLATE_ID}", expected_type="method") is None

    assert resolve_page_ref(root, OLD_METHOD_ID, expected_type="method") == expected_method


def test_resolve_page_ref_rejects_cross_type_ambiguity_when_untyped(alias_env):
    cfg, _, _ = alias_env
    root = cfg.wiki_root
    tpl_path = root / f"templates/{NEW_TEMPLATE_ID}.md"
    method_path = root / f"methods/{NEW_METHOD_ID}.md"

    tm, tb = read_page(tpl_path)
    tm["aliases"].append("shared-legacy-id")
    write_page(tpl_path, tm, tb)

    mm, mb = read_page(method_path)
    mm["aliases"].append("shared-legacy-id")
    write_page(method_path, mm, mb)

    assert resolve_page_ref(root, "shared-legacy-id", expected_type="template") == tpl_path.resolve()
    assert resolve_page_ref(root, "shared-legacy-id", expected_type="method") == method_path.resolve()
    assert resolve_page_ref(root, "templates/shared-legacy-id") == tpl_path.resolve()
    assert resolve_page_ref(root, "shared-legacy-id") is None


def test_resolve_asset_subpath_and_path_confinement(alias_env):
    cfg, _, tmp_path = alias_env
    root = cfg.wiki_root
    expected_preview = (root / "templates" / NEW_TEMPLATE_ID / "preview.png").resolve()
    expected_code = (root / "templates" / NEW_TEMPLATE_ID / "code/render.py").resolve()

    assert resolve_asset_subpath(root, f"templates/{NEW_TEMPLATE_ID}/preview.png") == expected_preview
    assert resolve_asset_subpath(root, f"templates/{OLD_TEMPLATE_ID}/preview.png") == expected_preview
    assert resolve_asset_subpath(root, f"templates/{OLD_TEMPLATE_ID}/code/render.py") == expected_code

    # Path traversal and invalid refs must return None
    for bad in (
        "",
        "   ",
        "../secret.txt",
        "templates/../secret.txt",
        f"templates/{OLD_TEMPLATE_ID}/../secret.txt",
        f"templates/{OLD_TEMPLATE_ID}/../../secret.txt",
        f"templates/{OLD_TEMPLATE_ID}/.git/config",
        "templates\\shap-bar\\preview.png",
        "templates:shap-bar/preview.png",
        str(tmp_path / "secret.txt"),
    ):
        assert resolve_page_ref(root, bad) is None
        assert resolve_asset_subpath(root, bad) is None


def test_entry_points_resolve_aliases_transparently(alias_env):
    cfg, _, tmp_path = alias_env
    root = cfg.wiki_root
    expected_tpl = (root / "templates" / f"{NEW_TEMPLATE_ID}.md").resolve()
    expected_preview = (root / "templates" / NEW_TEMPLATE_ID / "preview.png").resolve()

    # links.py:resolve()
    assert link_resolve(root, f"templates/{OLD_TEMPLATE_ID}").resolve() == expected_tpl
    assert link_resolve(root, f"templates/{OLD_TEMPLATE_ID}/preview.png").resolve() == expected_preview
    assert link_resolve(root, "templates/nonexistent-entry") == root / "templates/nonexistent-entry.md"

    # pages.py:visual_path()
    assert visual_path(root, OLD_TEMPLATE_ID).resolve() == expected_tpl
    assert visual_path(root, OLD_METHOD_ID).resolve() == (root / "methods" / f"{NEW_METHOD_ID}.md").resolve()
    with pytest.raises(WikiError):
        visual_path(root, "bar")  # chart-type is not a visual path

    # finder.py:_page(), show(), use()
    assert finder_page(cfg, OLD_TEMPLATE_ID).resolve() == expected_tpl
    detail = finder_show(cfg, OLD_TEMPLATE_ID)
    assert detail["path"] == f"templates/{NEW_TEMPLATE_ID}.md"
    assert detail["requested_id"] == OLD_TEMPLATE_ID

    project = tmp_path / "proj"
    project.mkdir()
    used = finder_use(cfg, OLD_TEMPLATE_ID, project)
    origin = json.loads((Path(used["copy"]) / "rwiki-origin.json").read_text(encoding="utf-8"))
    assert origin["id"] == NEW_TEMPLATE_ID
    assert origin["page"] == f"templates/{NEW_TEMPLATE_ID}.md"

    # suggest.py:_locate_node() & suggest_next_steps()
    assert _locate_node(cfg, OLD_METHOD_ID).resolve() == (root / "methods" / f"{NEW_METHOD_ID}.md").resolve()
    nxt = suggest_next_steps(cfg, OLD_METHOD_ID)
    assert nxt["node_id"] == NEW_METHOD_ID
    assert nxt["requested_id"] == OLD_METHOD_ID
    assert nxt["page"] == f"methods/{NEW_METHOD_ID}.md"

    # template_spec.py:load_unified_spec()
    spec = load_unified_spec(cfg, OLD_TEMPLATE_ID)
    assert spec["id"] == NEW_TEMPLATE_ID
    assert spec["requested_id"] == OLD_TEMPLATE_ID
    assert spec["page"] == f"templates/{NEW_TEMPLATE_ID}.md"
    assert Path(spec["asset_dir"]).resolve() == (root / "templates" / NEW_TEMPLATE_ID).resolve()

    # relations.py:_target() & relations_for()
    rel_path, rel_meta = relation_target(cfg, f"templates/{OLD_TEMPLATE_ID}")
    assert rel_path.resolve() == expected_tpl
    assert rel_meta["id"] == NEW_TEMPLATE_ID
    rels = relations_for(cfg, f"templates/{OLD_TEMPLATE_ID}.md")
    assert len(rels) == 1
    assert rels[0]["figure"] == f"templates/{NEW_TEMPLATE_ID}.md"

    # templates.py:ready_page() & render(), asset_checkout.py:_page()
    meta, _ = ready_page(cfg, OLD_TEMPLATE_ID)
    assert meta["id"] == NEW_TEMPLATE_ID
    out_dir = tmp_path / "render_out"
    render_template(cfg, OLD_TEMPLATE_ID, root / "templates" / NEW_TEMPLATE_ID / "example", out_dir)
    assert (out_dir / "figure.png").is_file()
    assert checkout_page(cfg, OLD_TEMPLATE_ID).resolve() == expected_tpl

    # deletion.py:prepare() detects alias links
    proj_page = root / "projects/demo.md"
    write_page(
        proj_page,
        {"type": "project", "slug": "demo", "title": "Demo", "templates": [OLD_TEMPLATE_ID]},
        f"# Demo\n\n[[templates/{OLD_TEMPLATE_ID}]]\n![[templates/{OLD_TEMPLATE_ID}/preview.png]]\n"
        "<!-- user:start -->\n<!-- user:end -->\n",
    )
    tpl_meta, tpl_body = read_page(expected_tpl)
    tpl_meta["archived_from"] = tpl_meta["status"]
    tpl_meta["status"] = "archived"
    write_page(expected_tpl, tpl_meta, tpl_body)
    plan, changes, _, _ = deletion_prepare(cfg, expected_tpl)
    assert any(p == proj_page for p, _, _ in changes)
    assert plan["figure_relations_removed"] == 1


def test_http_api_resolves_aliases_and_blocks_traversal(alias_env):
    cfg, _, _ = alias_env
    with TestClient(create_app(cfg)) as client:
        # /api/page
        r_page = client.get("/api/page", params={"path": f"templates/{OLD_TEMPLATE_ID}.md"})
        assert r_page.status_code == 200
        assert r_page.json()["path"] == f"templates/{NEW_TEMPLATE_ID}.md"
        assert r_page.json()["meta"]["id"] == NEW_TEMPLATE_ID

        # /files/wiki asset via alias
        r_img = client.get(f"/files/wiki/templates/{OLD_TEMPLATE_ID}/preview.png")
        assert r_img.status_code == 200
        assert r_img.content == TINY_PNG

        r_code = client.get(f"/files/wiki/templates/{OLD_TEMPLATE_ID}/code/render.py")
        assert r_code.status_code == 200
        assert "render SHAP bar" in r_code.text

        # /api/next/{node_id}
        r_next = client.get(f"/api/next/{OLD_METHOD_ID}")
        assert r_next.status_code == 200
        assert r_next.json()["node_id"] == NEW_METHOD_ID
        assert r_next.json()["requested_id"] == OLD_METHOD_ID

        # /api/studio/load-example & /api/studio/render-code
        r_ex = client.post("/api/studio/load-example", json={"id": OLD_TEMPLATE_ID})
        assert r_ex.status_code == 200
        assert r_ex.json()["id"] == NEW_TEMPLATE_ID
        assert r_ex.json()["requested_id"] == OLD_TEMPLATE_ID

        r_render = client.post("/api/studio/render-code", json={"id": OLD_TEMPLATE_ID})
        assert r_render.status_code == 200
        payload = r_render.json()
        assert payload["id"] == NEW_TEMPLATE_ID
        assert payload["requested_id"] == OLD_TEMPLATE_ID
        assert payload["spec"]["id"] == NEW_TEMPLATE_ID

        # /api/relations?path=templates/<old>.md
        r_rel = client.get("/api/relations", params={"path": f"templates/{OLD_TEMPLATE_ID}.md"})
        assert r_rel.status_code == 200
        assert len(r_rel.json()) == 1

        # Security traversal blocks
        assert client.get("/api/page", params={"path": "templates/../secret.md"}).status_code == 404
        assert client.get("/files/wiki/templates/../secret.txt").status_code == 404
        assert client.get(f"/files/wiki/templates/{OLD_TEMPLATE_ID}/../secret.txt").status_code == 404


def test_alias_errors_unit_validation():
    seen: dict[tuple[str, str], str] = {}
    canonical = {
        ("template", "volcano"): "templates/volcano.md",
        ("method", "deg"): "methods/deg.md",
    }
    page = Path("templates/shap-bar.md")

    assert alias_errors({"type": "template", "id": "shap-bar", "aliases": ["old__bar--1"]}, page, seen, canonical) == []
    assert ("template", "old__bar--1") in seen

    # Duplicate across same-type pages
    errs = alias_errors({"type": "template", "id": "other", "aliases": ["old__bar--1"]}, Path("templates/other.md"), seen, canonical)
    assert errs

    # Non-list, blank, traversal, invalid char, self-dup, self-cycle
    assert alias_errors({"type": "template", "id": "x", "aliases": "bad"}, Path("templates/x.md"), {}, canonical)
    assert alias_errors({"type": "template", "id": "x", "aliases": [""]}, Path("templates/x.md"), {}, canonical)
    assert alias_errors({"type": "template", "id": "x", "aliases": ["../escape"]}, Path("templates/x.md"), {}, canonical)
    assert alias_errors({"type": "template", "id": "x", "aliases": ["a/b"]}, Path("templates/x.md"), {}, canonical)
    assert alias_errors({"type": "template", "id": "x", "aliases": ["a\\b"]}, Path("templates/x.md"), {}, canonical)
    assert alias_errors({"type": "template", "id": "x", "aliases": ["a:b"]}, Path("templates/x.md"), {}, canonical)
    assert alias_errors({"type": "template", "id": "x", "aliases": ["-bad"]}, Path("templates/x.md"), {}, canonical)
    assert alias_errors({"type": "template", "id": "x", "aliases": ["dup", "dup"]}, Path("templates/x.md"), {}, canonical)
    assert alias_errors({"type": "template", "id": "x", "aliases": ["x"]}, Path("templates/x.md"), {}, canonical)

    # Same-type and cross-type collision with existing canonical id
    assert alias_errors({"type": "template", "id": "x", "aliases": ["volcano"]}, Path("templates/x.md"), {}, canonical)
    assert alias_errors({"type": "template", "id": "x", "aliases": ["deg"]}, Path("templates/x.md"), {}, canonical)


@pytest.mark.parametrize(
    "bad_aliases",
    [
        "not-a-list",
        [""],
        ["../bad"],
        ["a/b"],
        ["a:b"],
        ["dup", "dup"],
        [NEW_TEMPLATE_ID],  # self-cycle
        ["bar"],  # cross-type canonical chart-type slug collision
        [NEW_METHOD_ID],  # cross-type canonical method id collision
    ],
)
def test_lint_rejects_invalid_aliases(alias_env, bad_aliases):
    cfg, _, _ = alias_env
    extra_path = cfg.wiki_root / "templates/aaa-bad.md"
    write_page(
        extra_path,
        {
            "type": "template",
            "id": "aaa-bad",
            "aliases": bad_aliases,
            "title": "Bad Alias",
            "status": "draft",
            "layouts": [],
            "sources": ["recipes/volcano-recipe"],
            "panels": [],
            "language": "r",
            "tags": ["单细胞分析"],
            "chart_types": ["bar"],
            "favorite": False,
        },
        "# Bad\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    findings = lint(cfg)
    assert any(line.startswith("ERROR templates/aaa-bad.md:") for line in findings)


def test_lint_rejects_same_type_canonical_collision_and_cross_page_duplicate_alias(alias_env):
    cfg, _, _ = alias_env
    # Alphabetically before NEW_TEMPLATE_ID ("shap-bar")
    early = cfg.wiki_root / "templates/aaa-colliding.md"
    write_page(
        early,
        {
            "type": "template",
            "id": "aaa-colliding",
            "aliases": [NEW_TEMPLATE_ID],
            "title": "Collides With Canonical",
            "status": "draft",
            "layouts": [],
            "sources": ["recipes/volcano-recipe"],
            "panels": [],
            "language": "r",
            "tags": ["单细胞分析"],
            "chart_types": ["bar"],
            "favorite": False,
        },
        "# A\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n",
    )
    findings = lint(cfg)
    assert any("ERROR templates/aaa-colliding.md:" in line and NEW_TEMPLATE_ID in line for line in findings)

    # Now duplicate another template's alias
    meta, body = read_page(early)
    meta["aliases"] = [OLD_TEMPLATE_ID]
    write_page(early, meta, body)
    findings = lint(cfg)
    assert any("ERROR " in line and OLD_TEMPLATE_ID in line for line in findings)

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEV_ROOT = SKILL_ROOT.parents[1]
ENTRY_ID = "2026-08-17-shap-feature-mechanism__fig01-shap-a-f"
sys.path.insert(0, str(SKILL_ROOT))


def run_cli(config_path, *args):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SKILL_ROOT / "wiki.py"),
         "--config", str(config_path), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def commit_count(wiki_root):
    return int(subprocess.check_output(
        ["git", "-C", str(wiki_root), "rev-list", "--count", "HEAD"],
        text=True, encoding="utf-8",
    ))


def update_gallery(config, **changes):
    path = config.gallery_root / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta.update(changes)
    if changes.get('status') == 'approved':
        meta['approved_version'] = meta['version']
    path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8", newline="\n")


def complete_sections(path):
    """Finish a software fixture, without pretending it is scientific evidence."""
    from rwiki.pages import read_page, section_text, write_page
    from rwiki.acceptance import HEADINGS
    from rwiki.errors import WikiError
    meta, body = read_page(path)
    for heading in HEADINGS.get(meta['type'], ()):
        try:
            content = section_text(body, heading)
        except WikiError:
            content = ''
        if not content:
            note = '隔离软件夹具的说明；不代表科学有效或真实课题结果。'
            if heading == '知识关联检查':
                note = ('检查范围：本隔离夹具已有方法与图样；按各测试声明关系，无其他科学关联。'
                        '无图原因：夹具未提供对应模板时不配图。')
            marker = f'## {heading}\n'
            if marker in body:
                body = body.replace(marker, marker + '\n' + note + '\n', 1)
            else:
                body = body.replace('<!-- user:start -->', f'## {heading}\n\n{note}\n\n<!-- user:start -->', 1)
    write_page(path, meta, body)


def seal_replay(target):
    """Synthetic receipts isolate metadata tests; execution is tested separately."""
    from rwiki.verification import record_preview
    (target / 'verify').mkdir(exist_ok=True)
    raw = (target / 'preview.png').read_bytes()
    for ext in ('png', 'pdf', 'svg'):
        (target / f'verify/figure.{ext}').write_bytes(raw)
    record_preview(target)


def record_ready_receipt(config, page):
    """A fixture page written as ready gets the receipt mark-ready would have recorded."""
    from rwiki.acceptance import record_acceptance
    record_acceptance(config, page)


def write_interface(root, slug, columns, title="数值接口"):
    from rwiki.pages import write_page

    write_page(root / "interfaces" / f"{slug}.md", {
        "type": "interface", "slug": slug, "title": title, "columns": columns},
        f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 含义\n\n"
        "<!-- user:start -->\n<!-- user:end -->\n")


@pytest.fixture
def workspace(tmp_path):
    from rwiki.config import load_config
    from rwiki.store import init

    gallery = tmp_path / "gallery"
    # Every test copies the gallery; skip the article page, comparison sheet and vector exports
    # (~17 MB of the 20 MB) that no test reads.
    shutil.copytree(DEV_ROOT / "test-gallery", gallery, ignore=shutil.ignore_patterns(
        "article_images", "*.html", "compare", "source_crop", "__pycache__", "*.svg", "*.pdf"))
    path = gallery / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["figure"]["panel_map"] = {"A": "bar", "B": "beeswarm", "C": "radial_bar",
                                   "D": "bar", "E": "beeswarm", "F": "radial_bar"}
    path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8", newline="\n")
    taxonomy = tmp_path / "taxonomy.yaml"
    shutil.copyfile(DEV_ROOT / "spec/scenario_taxonomy.yaml", taxonomy)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "wiki_root": str(tmp_path / "wiki"),
        "gallery_root": str(gallery),
        "taxonomy": str(taxonomy),
        "python_exe": sys.executable,
        "rscript_exe": "D:/R-4.5.0/bin/Rscript.exe",
        "port": 8765,
    }), encoding="utf-8", newline="\n")
    config = load_config(config_path)
    init(config)
    return config, config_path


@pytest.fixture
def ingested(workspace):
    from rwiki.ingest import ingest_figure

    config, config_path = workspace
    ingest_figure(config, ENTRY_ID)
    return config, config_path


@pytest.fixture
def layout_workspace(workspace):
    from PIL import Image
    from rwiki.ingest import ingest_figure
    from rwiki.pages import read_page, write_page

    config, config_path = workspace
    update_gallery(config, status="approved")
    ingest_figure(config, ENTRY_ID)
    root = config.wiki_root
    page = root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(page)
    meta["panels"] = {"A": "bar", "B": "dot"}
    meta["chart_types"] = ["bar", "dot"]
    meta["templates"] = [f"{ENTRY_ID}--bar", f"{ENTRY_ID}--dot"]
    meta["template_panels"] = {meta["templates"][0]: ["A"], meta["templates"][1]: ["B"]}
    write_page(page, meta, body)
    write_interface(root, "values", {"value": {"type": "int", "description": "计数"}})
    for chart, color in (("bar", "red"), ("dot", "blue")):
        tid = f"{ENTRY_ID}--{chart}"
        target = root / "templates" / tid
        (target / "code").mkdir(parents=True)
        (target / "example").mkdir()
        (target / "code/__init__.py").write_text("", encoding="utf-8")
        # Same module name, distinct content: a global 'helper' import would collide.
        (target / "code/helper.py").write_text(f"COLOR = '{color}'\n", encoding="utf-8")
        (target / "code/panel.py").write_text('''from .helper import COLOR
def draw(fig, rect, tables, style):
    assert list(tables['values']['value']) == [2]
    ax = fig.add_axes(rect)
    ax.set_facecolor(style['color'] or COLOR)
    ax.set_xticks([])
    ax.set_yticks([])
''', encoding="utf-8")
        (target / "code/render.py").write_text('''import argparse
import importlib.util
import json
import sys
from pathlib import Path
from uuid import uuid4
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
p = argparse.ArgumentParser()
for flag in ('data', 'out'):
    p.add_argument('--' + flag, type=Path, required=True)
p.add_argument('--style', type=Path)
a = p.parse_args()
spec = json.loads(Path('spec.json').read_text(encoding='utf-8'))
style = spec['style']
if a.style:
    style.update(json.loads(a.style.read_text(encoding='utf-8')))
name = 'standalone_' + uuid4().hex
package_spec = importlib.util.spec_from_file_location(name, 'code/__init__.py', submodule_search_locations=[str(Path('code').resolve())])
package = importlib.util.module_from_spec(package_spec)
sys.modules[name] = package
package_spec.loader.exec_module(package)
panel_spec = importlib.util.spec_from_file_location(name + '.panel', spec['panel'])
panel = importlib.util.module_from_spec(panel_spec)
panel_spec.loader.exec_module(panel)
tables = {key: pd.read_csv(a.data / f"{value['interface']}.csv") for key, value in spec['tables'].items()}
fig = plt.figure(figsize=(style['width_in'], style['height_in']), dpi=style['dpi'])
panel.draw(fig, [0.1, 0.1, 0.8, 0.8], tables, style)
a.out.mkdir(parents=True, exist_ok=True)
for ext in ('png', 'pdf', 'svg'):
    fig.savefig(a.out / ('figure.' + ext))
plt.close(fig)
''', encoding="utf-8", newline="\n")
        spec = {"entry": "code/render.py", "panel": "code/panel.py", "language": "python",
                "tables": {"values": {"interface": "values", "description": "计数"}},
                "style": {"color": None, "width_in": 2, "height_in": 2, "dpi": 50}}
        (target / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        (target / "example/values.csv").write_text("value\n2\n", encoding="utf-8")
        write_page(root / f"templates/{tid}.md", {
            "type": "template", "id": tid, "title": chart, "status": "ready", "layouts": [ENTRY_ID],
            "panels": ["A" if chart == "bar" else "B"], "language": "python", "tags": meta["tags"],
            "chart_types": [chart], "favorite": False},
            f"# {chart}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n\n说明\n\n"
            "## 不适用\n\n## 数据要求\n\n## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n")
        Image.new("RGB", (8, 8), color).save(target / "preview.png")
        complete_sections(target.with_suffix('.md'))
        seal_replay(target)
        record_ready_receipt(config, target.with_suffix('.md'))
    target = root / "layouts" / ENTRY_ID
    (target / "example").mkdir()
    (target / "example/values.csv").write_text("value\n2\n", encoding="utf-8")
    layout = {"canvas": {"width_in": 4, "height_in": 2, "dpi": 50}, "panels": [
        {"letter": "A", "template": meta["templates"][0], "rect": [0.05, 0.1, 0.4, 0.8],
         "tables": {"values": "values.csv"}, "style": {}},
        {"letter": "B", "template": meta["templates"][1], "rect": [0.55, 0.1, 0.4, 0.8],
         "tables": {"values": "values.csv"}, "style": {}}],
        "labels": [{"text": "A", "x": 0.01, "y": 0.96, "size": 8,
                    "weight": "bold", "family": "Arial"}]}
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    complete_sections(page)
    return config, config_path, target, layout



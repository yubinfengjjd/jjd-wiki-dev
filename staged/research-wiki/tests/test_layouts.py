import json
import subprocess
import textwrap
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from conftest import ENTRY_ID, SKILL_ROOT, commit_count, run_cli, update_gallery
from rwiki.errors import WikiError
from rwiki.ingest import ingest_figure
from rwiki.pages import read_page, write_page

DRAW_PYTHON = Path("C:/Users/86186/.codex/venvs/sci-figure-replica/Scripts/python.exe")


@pytest.mark.parametrize("field,value,message", [
    ("template", "unknown", "template"), ("letter", "Z", "letter"),
    ("letter", "A", "重复"), ("tables", {"bad": "values.csv"}, "tables"),
    ("tables", {}, "tables"), ("style", {"unknown": 1}, "style"),
    ("rect", [0, 0, -1, 0.5], "rect"), ("rect", [0.9, 0, 0.5, 0.5], "rect"),
])
def test_load_layout_reports_panel_item(layout_workspace, field, value, message):
    from rwiki.layouts import load_layout
    _, _, target, layout = layout_workspace
    layout["panels"][1 if message == "重复" else 0][field] = value
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    with pytest.raises(WikiError, match=message):
        load_layout(target)


def test_load_layout_rejects_template_assigned_to_a_different_letter(layout_workspace):
    from rwiki.layouts import load_layout
    _, _, target, layout = layout_workspace
    layout["panels"][0]["template"] = ENTRY_ID + "--dot"
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    with pytest.raises(WikiError, match="template_panels"):
        load_layout(target)


def test_load_layout_accepts_mapping_and_rejects_bad_canvas(layout_workspace):
    from rwiki.layouts import load_layout
    _, _, target, layout = layout_workspace
    assert load_layout(target) == layout
    layout["canvas"]["dpi"] = 0
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    with pytest.raises(WikiError, match="canvas.dpi"):
        load_layout(target)


@pytest.mark.parametrize("field", ["weight", "family"])
@pytest.mark.parametrize("present,value", [
    pytest.param(False, None, id="missing"),
    pytest.param(True, None, id="null"),
    pytest.param(True, 700, id="number"),
    pytest.param(True, True, id="boolean"),
    pytest.param(True, [], id="list"),
    pytest.param(True, {}, id="object"),
])
def test_load_layout_requires_string_label_font(layout_workspace, field, present, value):
    from rwiki.layouts import load_layout
    _, _, target, layout = layout_workspace
    layout["labels"][0].pop(field)
    if present:
        layout["labels"][0][field] = value
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    with pytest.raises(WikiError, match=rf"labels\[0\].*{field}"):
        load_layout(target)


@pytest.mark.compose
def test_compose_label_anchor_weight_and_fonts_before_figure(layout_workspace, tmp_path):
    config, _, target, layout = layout_workspace
    layout["labels"] = [
        {"text": "A", "x": 0.1, "y": 0.2, "size": 12, "weight": "bold", "family": "Arial"},
        {"text": "B", "x": 0.6, "y": 0.7, "size": 9, "weight": "normal", "family": "DejaVu Sans"},
    ]
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    out = tmp_path / "label-output"
    # Observe real figure creation and artists in the plotting interpreter. Seed
    # incompatible defaults so omitted or late rcParams updates cannot pass.
    probe = textwrap.dedent('''
        import json
        import sys
        from pathlib import Path
        sys.path.insert(0, sys.argv.pop(1))
        from rwiki import compose_runner as runner
        runner.matplotlib.rcParams.update({
            'pdf.fonttype': 3, 'svg.fonttype': 'path', 'font.family': ['DejaVu Serif']})
        original_figure = runner.plt.figure
        observed = {}
        def create_figure(*args, **kwargs):
            observed['fonts_at_creation'] = {
                key: runner.matplotlib.rcParams[key]
                for key in ('pdf.fonttype', 'svg.fonttype')
            }
            fig = original_figure(*args, **kwargs)
            observed['figure'] = fig
            return fig
        runner.plt.figure = create_figure
        runner.main()
        fig = observed.pop('figure')
        fig.canvas.draw()
        observed['labels'] = [
            {'text': label.get_text(), 'position': label.get_position(),
             'size': label.get_fontsize(), 'weight': label.get_fontweight(),
             'family': label.get_fontfamily(),
             'va': label.get_verticalalignment(), 'ha': label.get_horizontalalignment(),
             'bottom': label.get_window_extent().y0,
             'anchor_y': fig.transFigure.transform(label.get_position())[1]}
            for label in fig.texts
        ]
        out = Path(sys.argv[sys.argv.index('--out') + 1])
        (out / 'probe.json').write_text(json.dumps(observed), encoding='utf-8')
    ''')
    result = subprocess.run([
        str(DRAW_PYTHON), "-X", "utf8", "-c", probe, str(SKILL_ROOT),
        "--wiki", str(config.wiki_root), "--layout", str(target / "layout.json"),
        "--data", str(target / "example"), "--out", str(out),
    ], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    observed = json.loads((out / "probe.json").read_text(encoding="utf-8"))
    assert observed["fonts_at_creation"] == {"pdf.fonttype": 42, "svg.fonttype": "none"}
    for label, expected in zip(observed["labels"], layout["labels"], strict=True):
        assert label["text"] == expected["text"]
        assert label["position"] == [expected["x"], expected["y"]]
        assert label["size"] == expected["size"]
        assert label["weight"] == expected["weight"]
        assert label["family"] == [expected["family"]]
        assert label["va"] == "bottom" and label["ha"] == "left"
        assert label["bottom"] == pytest.approx(label["anchor_y"])
    assert b"/FontFile2" in (out / "figure.pdf").read_bytes()
    import xml.etree.ElementTree as ET
    svg = ET.parse(out / "figure.svg")
    assert [text.text for text in svg.findall(".//{http://www.w3.org/2000/svg}text")] == ["A", "B"]


@pytest.mark.compose
def test_compose_relative_imports_styles_and_three_real_formats(layout_workspace):
    from rwiki.layouts import verify_layout, render_layout
    config, _, target, layout = layout_workspace
    config = replace(config, python_exe=DRAW_PYTHON)
    layout["panels"][0]["style"] = {"color": "green"}
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    (target / "example/style.json").write_text('{"A": {"color": "yellow"}}', encoding="utf-8")
    count = commit_count(config.wiki_root)
    mean, comparison = verify_layout(config, ENTRY_ID)
    assert 0 <= mean <= 255 and comparison.is_file()
    assert commit_count(config.wiki_root) == count + 1
    for ext in ("png", "pdf", "svg"):
        assert (target / f"verify/figure.{ext}").stat().st_size > 100
    with Image.open(target / "preview.png") as image:
        assert image.size == (200, 100)
        assert image.convert("RGB").getpixel((50, 50)) == (255, 255, 0)
        assert image.convert("RGB").getpixel((150, 50)) == (0, 0, 255)
    record = json.loads((target / "verify/verify.json").read_text(encoding="utf-8"))
    assert record["exit_code"] == 0 and record["timestamp"]
    assert record["mean_absolute_difference"] == mean
    page = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(page)
    meta["status"] = "ready"
    write_page(page, meta, body)
    out = target / "new-output"
    render_layout(config, ENTRY_ID, target / "example", out)
    with Image.open(out / "figure.png") as image:
        assert image.convert("RGB").getpixel((50, 50)) == (0, 128, 0)


@pytest.mark.compose
def test_compose_uses_layout_filenames_instead_of_interface_filenames(layout_workspace, tmp_path):
    from rwiki.layouts import compose

    config, _, target, layout = layout_workspace
    config = replace(config, python_exe=DRAW_PYTHON)
    (target / "example/values.csv").unlink()
    for panel in layout["panels"]:
        filename = f"panel-{panel['letter']}.csv"
        panel["tables"]["values"] = filename
        (target / "example" / filename).write_text("value\n2\n", encoding="utf-8")
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    out = tmp_path / "mapped-layout"
    compose(config, target, target / "example", out, None)
    assert all((out / f"figure.{extension}").is_file() for extension in ("png", "pdf", "svg"))
    with Image.open(out / "figure.png") as image:
        assert image.convert("RGB").getpixel((50, 50)) == (255, 0, 0)
        assert image.convert("RGB").getpixel((150, 50)) == (0, 0, 255)


@pytest.mark.parametrize("style,message", [({"Z": {}}, "Z"), ({"A": {"bad": 1}}, "bad"),
                                          ({"A": []}, "A"), ([], "style")])
def test_render_layout_rejects_style_before_process(layout_workspace, tmp_path, style, message):
    from rwiki.layouts import render_layout
    config, _, target, _ = layout_workspace
    path = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(path)
    meta["status"] = "ready"
    write_page(path, meta, body)
    override = tmp_path / "style.json"
    override.write_text(json.dumps(style), encoding="utf-8")
    with pytest.raises(WikiError, match=message):
        render_layout(config, ENTRY_ID, target / "example", tmp_path / "out", override)
    assert not (tmp_path / "out").exists()


def test_render_layout_checks_status_and_mapped_csv(layout_workspace, tmp_path):
    from rwiki.layouts import render_layout
    config, _, target, _ = layout_workspace
    with pytest.raises(WikiError, match="ready"):
        render_layout(config, ENTRY_ID, target / "example", tmp_path / "out")
    page = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(page)
    meta["status"] = "ready"
    write_page(page, meta, body)
    (target / "example/values.csv").write_text("wrong\n2\n", encoding="utf-8")
    with pytest.raises(WikiError, match="缺列"):
        render_layout(config, ENTRY_ID, target / "example", tmp_path / "out")
    (target / "example/values.csv").unlink()
    with pytest.raises(WikiError, match="不存在"):
        render_layout(config, ENTRY_ID, target / "example", tmp_path / "out")


@pytest.mark.compose
def test_python_panel_standalone_verify_calls_draw(layout_workspace):
    from rwiki.templates import verify_template
    config, _, _, _ = layout_workspace
    config = replace(config, python_exe=DRAW_PYTHON)
    tid = ENTRY_ID + "--bar"
    target = config.wiki_root / "templates" / tid
    (target / "example/style.json").write_text('{"color": "green"}', encoding="utf-8")
    verify_template(config, tid)
    with Image.open(target / "preview.png") as image:
        assert image.size == (100, 100)
        assert image.convert("RGB").getpixel((50, 50)) == (0, 128, 0)
    assert not (target / "verify/compare.png").exists()


def test_layout_comparison_exact_metric_dimensions_and_gap(tmp_path):
    from rwiki.verification import compare_images
    left, right = tmp_path / "original.png", tmp_path / "figure.png"
    Image.new("RGB", (4, 8), "blue").save(left)
    Image.new("RGB", (2, 4), "red").save(right)
    mean, path = compare_images(left, right)
    assert mean == 170
    with Image.open(path) as image:
        assert image.size == (28, 4)
        assert image.getpixel((2, 0)) == (255, 255, 255)

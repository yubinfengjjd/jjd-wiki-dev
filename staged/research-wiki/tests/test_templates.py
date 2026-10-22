import json
import pytest
from PIL import Image

from conftest import ENTRY_ID as LAYOUT_ID, commit_count, run_cli, update_gallery, write_interface, complete_sections
from rwiki.errors import WikiError
from rwiki.ingest import ingest_figure
from rwiki.pages import get_block, read_page, set_block, write_page
from rwiki.store import git
from rwiki.templates import mark_ready, render, scaffold_template, verify_template

ENTRY_ID = LAYOUT_ID + "--bar"


@pytest.fixture
def approved(workspace):
    config, path = workspace
    update_gallery(config, status="approved")
    ingest_figure(config, LAYOUT_ID)
    return config, path


@pytest.fixture
def fake_template(approved):
    config, config_path = approved
    scaffold_template(config, LAYOUT_ID, "bar", ["A", "D"])
    target = config.wiki_root / "templates" / ENTRY_ID
    (target / "code/panel.py").write_text("", encoding="utf-8")
    (target / "example/values.csv").write_text("value\n2\n", encoding="utf-8")
    write_interface(config.wiki_root, "values", {"value": {"type": "int", "description": "计数"}})
    spec = {"entry": "code/render.py", "panel": "code/panel.py", "language": "python", "tables": {
        "values": {"description": "示例", "interface": "values"}},
        "style": {"color": "red"}}
    (target / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    (target / "code/render.py").write_text('''import argparse
import csv
import json
from pathlib import Path
from PIL import Image
p = argparse.ArgumentParser()
p.add_argument('--data', type=Path)
p.add_argument('--out', type=Path)
p.add_argument('--style', type=Path)
a = p.parse_args()
spec = json.loads(Path('spec.json').read_text(encoding='utf-8'))
style = spec['style']
if a.style:
    style.update(json.loads(a.style.read_text(encoding='utf-8')))
table = spec['tables']['values']
with (a.data / f"{table['interface']}.csv").open(encoding='utf-8') as stream:
    count = int(next(csv.DictReader(stream))['value'])
Image.new('RGB', (count, 4), style['color']).save(a.out / 'figure.png')
(a.out / 'figure.pdf').write_text('pdf', encoding='utf-8')
(a.out / 'figure.svg').write_text('svg', encoding='utf-8')
''', encoding="utf-8", newline="\n")
    gallery = config.gallery_root / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f"
    Image.new("RGB", (4, 8), "blue").save(gallery / "output/replica.png")
    complete_sections(target.with_suffix('.md'))
    return config, config_path, target


def test_pending_lists_only_pending_template(approved):
    config, path = approved
    for status in ("pending_signoff", "ready", "archived"):
        write_page(config.wiki_root / f"layouts/{status}.md", {"id": status, "status": status}, "")
    result = run_cli(path, "pending")
    assert result.returncode == 0, result.stderr
    assert result.stdout == LAYOUT_ID + "\n"
    page = config.wiki_root / f"layouts/{LAYOUT_ID}.md"
    meta, body = read_page(page)
    meta["status"] = "ready"
    write_page(page, meta, body)
    # A raw ready flag cannot hide missing template coverage from remaining work.
    assert run_cli(path, "pending").stdout == LAYOUT_ID + "\n"


def test_scaffold_rejects_wrong_state(ingested):
    config, _ = ingested
    with pytest.raises(WikiError, match="pending_template"):
        scaffold_template(config, LAYOUT_ID, "bar", ["A", "D"])


def test_scaffold_copies_csv_prints_columns_and_matching_interfaces_and_saves(approved):
    config, config_path = approved
    data = config.gallery_root / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/data"
    (data / "types.csv").write_text("count,value,name\n1,1.5,A\n2,2.0,B\n", encoding="utf-8")
    columns = {"count": {"type": "int", "description": "计数"},
               "value": {"type": "float", "description": "数值"},
               "name": {"type": "str", "description": "名称"}}
    write_interface(config.wiki_root, "matching", columns)
    write_interface(config.wiki_root, "different", {"other": {"type": "str", "description": "其他"}})
    result = run_cli(config_path, "scaffold-template", LAYOUT_ID, "--chart-type", "bar", "--panels", "A,D")
    assert result.returncode == 0, result.stderr
    target = config.wiki_root / "templates" / ENTRY_ID
    for source in data.glob("*.csv"):
        assert (target / "example" / source.name).read_bytes() == source.read_bytes()
    spec = json.loads((target / "spec.json").read_text(encoding="utf-8"))
    assert spec["entry"] == "code/render.py" and spec["style"] == {}
    assert spec["tables"]["types"] == {"interface": "", "description": ""}
    report = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    inferred = next(item for item in report if item["file"] == "types.csv")
    assert inferred["columns"] == {
        "count": {"type": "int", "description": "待作者确认"},
        "value": {"type": "float", "description": "待作者确认"},
        "name": {"type": "str", "description": "待作者确认"}}
    assert inferred["interfaces"] == ["matching"]
    assert inferred["filename_convention"] == "<interface>.csv"
    assert "example" in inferred["next_step"] and "改名" in inferred["next_step"]
    assert [p.name for p in (target / "code").iterdir()] == ["__init__.py"]
    assert commit_count(config.wiki_root) == 3
    columns_path = config.wiki_root.parent / "inferred-columns.json"
    columns_path.write_text(json.dumps(inferred["columns"]), encoding="utf-8")
    added = run_cli(config_path, "add-interface", "inferred", "--title", "待确认的推断接口",
                    "--columns", str(columns_path))
    assert added.returncode == 0, added.stderr
    with pytest.raises(WikiError, match="已存在"):
        scaffold_template(config, LAYOUT_ID, "bar", ["A", "D"])


@pytest.mark.parametrize("name", ["code", "example", "spec.json"])
def test_scaffold_preserves_existing_work(approved, name):
    config, _ = approved
    target = config.wiki_root / "templates" / ENTRY_ID / name
    if name == "spec.json":
        target.parent.mkdir(parents=True)
        target.write_text("agent work", encoding="utf-8")
    else:
        target.mkdir(parents=True)
    with pytest.raises(WikiError, match="已存在"):
        scaffold_template(config, LAYOUT_ID, "bar", ["A", "D"])
    assert commit_count(config.wiki_root) == 2


def test_scaffold_r_entry_follows_gallery_language(approved):
    config, _ = approved
    update_gallery(config, language="r")
    scaffold_template(config, LAYOUT_ID, "bar", ["A", "D"])
    spec = json.loads((config.wiki_root / "templates" / ENTRY_ID / "spec.json").read_text(encoding="utf-8"))
    assert spec["entry"] == "code/render.R" and spec["language"] == "r"


def test_render_runs_real_python_with_style_and_no_save(fake_template, tmp_path):
    config, config_path, target = fake_template
    style = tmp_path / "style.json"
    style.write_text('{"color": "green"}', encoding="utf-8")
    out = tmp_path / "rendered"
    result = run_cli(config_path, "render", ENTRY_ID, "--data", str(target / "example"),
                     "--out", str(out), "--style", str(style))
    assert result.returncode == 0, result.stderr
    assert all((out / f"figure.{ext}").is_file() for ext in ("png", "pdf", "svg"))
    with Image.open(out / "figure.png") as image:
        assert image.size == (2, 4)
        assert image.getpixel((0, 0)) == (0, 128, 0)
    assert commit_count(config.wiki_root) == 3


def test_render_reads_interface_filename_when_table_key_differs(fake_template, tmp_path):
    config, _, target = fake_template
    write_interface(config.wiki_root, "method-values", {"value": {"type": "int", "description": "计数"}})
    spec_path = target / "spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["tables"]["values"]["interface"] = "method-values"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    (target / "example/values.csv").rename(target / "example/method-values.csv")
    out = tmp_path / "method-figure"
    render(config, ENTRY_ID, target / "example", out)
    with Image.open(out / "figure.png") as image:
        assert image.size == (2, 4)


def test_render_rejects_unknown_style_before_execution(fake_template, tmp_path):
    config, _, target = fake_template
    style = tmp_path / "style.json"
    style.write_text('{"unknown": "green"}', encoding="utf-8")
    with pytest.raises(WikiError, match="未知 style 键: unknown"):
        render(config, ENTRY_ID, target / "example", tmp_path / "out", style)
    assert not (tmp_path / "out").exists()


def test_render_exit_error_has_command_code_and_only_stderr_tail(fake_template, tmp_path):
    config, config_path, target = fake_template
    (target / "code/render.py").write_text(
        "import sys\nfor i in range(25):\n    print(f'error-{i:02}', file=sys.stderr)\nsys.exit(7)\n", encoding="utf-8")
    result = run_cli(config_path, "render", ENTRY_ID, "--data", str(target / "example"),
                     "--out", str(tmp_path / "out"))
    assert result.returncode == 1
    for expected in (str(config.python_exe), "code/render.py", "--data", "退出码: 7", "error-05", "error-24"):
        assert expected in result.stderr
    assert "error-04" not in result.stderr and "Traceback" not in result.stderr


def test_render_requires_fresh_three_outputs(fake_template, tmp_path):
    config, _, target = fake_template
    out = tmp_path / "out"
    render(config, ENTRY_ID, target / "example", out)
    script = target / "code/render.py"
    script.write_text(script.read_text(encoding="utf-8").split("(a.out / 'figure.svg')")[0], encoding="utf-8")
    with pytest.raises(WikiError, match="figure.svg"):
        render(config, ENTRY_ID, target / "example", out)


@pytest.mark.r
def test_r_dispatch(fake_template, tmp_path):
    config, _, target = fake_template
    spec_path = target / "spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec.update(entry="code/render.R", language="r")
    spec.pop("panel")
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    (target / "code/render.R").write_text('''args <- commandArgs(trailingOnly=TRUE)
data <- args[match("--data", args) + 1]
out <- args[match("--out", args) + 1]
stopifnot(file.exists("spec.json"))
stopifnot(read.csv(file.path(data, "values.csv"))$value[1] == 2)
for (ext in c("png", "pdf", "svg")) writeLines("r output", file.path(out, paste0("figure.", ext)))
''', encoding="utf-8")
    # A wrong dispatch uses Python on R syntax and fails.
    render(config, ENTRY_ID, target / "example", tmp_path / "r-out")
    assert (tmp_path / "r-out/figure.svg").read_text().strip() == "r output"


def test_verify_panel_preview_commit_and_ignore(fake_template):
    config, config_path, target = fake_template
    result = run_cli(config_path, "verify-template", ENTRY_ID)
    assert result.returncode == 0, result.stderr
    record = json.loads((target / "verify/verify.json").read_text(encoding="utf-8"))
    # Replay evidence is bound to the exact inputs and outputs, not just exit status.
    assert record["schema_version"] == 2
    assert record["exit_code"] == 0 and record["timestamp"]
    assert set(record["inputs"]) and set(record["outputs"]) == {"png", "pdf", "svg"}
    assert record["environment"]["executable"]
    assert not (target / "verify/compare.png").exists()
    assert (target / "preview.png").read_bytes() == (target / "verify/figure.png").read_bytes()
    assert commit_count(config.wiki_root) == 4
    # The receipt and the outputs it hashes are the evidence ready depends on, so they are versioned.
    tracked = git(config.wiki_root, "ls-files")
    assert f"templates/{ENTRY_ID}/verify/verify.json" in tracked
    assert f"templates/{ENTRY_ID}/verify/figure.png" in tracked and "/preview.png" in tracked


def test_verify_uses_example_style_for_replay(fake_template):
    config, _, target = fake_template
    (target / "example/style.json").write_text('{"color": "blue"}', encoding="utf-8")
    verify_template(config, ENTRY_ID)
    with Image.open(target / "verify/figure.png") as image:
        assert image.getpixel((0, 0)) == (0, 0, 255)


def test_mark_ready_rejects_wrong_state(ingested):
    config, _ = ingested
    with pytest.raises(WikiError, match="pending_template"):
        mark_ready(config, LAYOUT_ID)


def test_mark_ready_requires_preview_and_valid_spec(fake_template):
    config, _, target = fake_template
    with pytest.raises(WikiError, match="preview.png"):
        mark_ready(config, ENTRY_ID)
    (target / "preview.png").write_bytes(b"preview")
    (target / "code/render.py").unlink()
    with pytest.raises(WikiError, match="entry"):
        mark_ready(config, ENTRY_ID)


def test_mark_ready_replaces_only_data_section_and_saves(fake_template):
    config, config_path, target = fake_template
    verify_template(config, ENTRY_ID)
    page = config.wiki_root / f"templates/{ENTRY_ID}.md"
    meta, body = read_page(page)
    body = set_block(body, "user", "\n作者的原文\n")
    body = body.replace("## 适用\n", "## 适用\n\n作者确认。\n")
    write_page(page, meta, body)
    before, after = body.split("## 数据要求", 1)[0], body.split("## 使用记录", 1)[1]
    result = run_cli(config_path, "mark-ready", ENTRY_ID)
    assert result.returncode == 0, result.stderr
    updated, new_body = read_page(page)
    assert updated == dict(meta, status="ready")
    assert new_body.split("## 数据要求", 1)[0].replace(
        f"![[templates/{ENTRY_ID}/preview.png]]\n\n", "") == before
    assert new_body.split("## 使用记录", 1)[1] == after
    assert get_block(new_body, "user") == get_block(body, "user")
    for expected in ("values.csv", "| value | int | 计数 |", "color"):
        assert expected in new_body
    assert "模板化后生成" not in new_body
    assert commit_count(config.wiki_root) == 5

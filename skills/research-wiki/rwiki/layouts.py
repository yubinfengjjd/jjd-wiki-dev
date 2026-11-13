import math
from pathlib import Path

from .config import Config, read_json
from .errors import WikiError
from .pages import read_page
from .process import run
from .spec import check_table_data, load_spec
from .store import save
from .verification import compare_images, record_preview


def number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def load_layout(layout_dir: Path) -> dict:
    layout = read_json(layout_dir / "layout.json")
    meta, _ = read_page(layout_dir.with_suffix(".md"))
    if not isinstance(layout, dict) or not isinstance(layout.get("canvas"), dict):
        raise WikiError("layout.canvas 必须为对象")
    for key in ("width_in", "height_in", "dpi"):
        value = layout["canvas"].get(key)
        if not number(value) or value <= 0:
            raise WikiError(f"layout.canvas.{key} 必须为正数")
    if not isinstance(layout.get("panels"), list) or not layout["panels"]:
        raise WikiError("layout.panels 必须为非空列表")
    seen = set()
    for index, panel in enumerate(layout["panels"]):
        prefix = f"layout.panels[{index}]"
        if not isinstance(panel, dict):
            raise WikiError(f"{prefix} 必须为对象")
        letter, tid = panel.get("letter"), panel.get("template")
        if not isinstance(letter, str) or letter not in meta["panels"]:
            raise WikiError(f"{prefix}.letter 不在版式 panels 中: {letter}")
        if letter in seen:
            raise WikiError(f"{prefix}.letter 重复: {letter}")
        seen.add(letter)
        if not isinstance(tid, str) or tid not in meta["templates"]:
            raise WikiError(f"{prefix}.template 不在版式 templates 中: {tid}")
        if letter not in (meta.get("template_panels") or {}).get(tid, []):
            raise WikiError(f"{prefix}.template 与 template_panels 归属不一致: {letter} / {tid}")
        spec = load_spec(layout_dir.parents[1] / "templates" / tid)
        if spec["language"] != "python":
            raise WikiError(f"{prefix}.template 组合版式只支持 Python: {tid}")
        tables = panel.get("tables")
        if not isinstance(tables, dict) or tables.keys() != spec["tables"].keys():
            raise WikiError(f"{prefix}.tables 必须包含模板的全部表名: {', '.join(spec['tables'])}")
        # Table files are read from the data folder the caller passes, never from elsewhere.
        if any(not isinstance(value, str) or not value or value != Path(value).name
               or value.startswith(".") for value in tables.values()):
            raise WikiError(f"{prefix}.tables 文件名必须为数据目录内的普通文件名")
        style = panel.get("style")
        if not isinstance(style, dict):
            raise WikiError(f"{prefix}.style 必须为对象")
        unknown = style.keys() - spec["style"].keys()
        if unknown:
            raise WikiError(f"{prefix}.style 未知键: {', '.join(sorted(unknown))}")
        rect = panel.get("rect")
        if (not isinstance(rect, list) or len(rect) != 4 or not all(number(v) for v in rect)
                or min(rect[:2]) < 0 or min(rect[2:]) <= 0
                or rect[0] + rect[2] > 1 or rect[1] + rect[3] > 1):
            raise WikiError(f"{prefix}.rect 必须为画布内的 [x, y, w, h]")
    labels = layout.get("labels")
    if not isinstance(labels, list):
        raise WikiError("layout.labels 必须为列表")
    for index, label in enumerate(labels):
        if (not isinstance(label, dict) or not isinstance(label.get("text"), str)
                or not isinstance(label.get("weight"), str)
                or not isinstance(label.get("family"), str)
                or any(not number(label.get(key)) for key in ("x", "y", "size"))
                or not 0 <= label["x"] <= 1 or not 0 <= label["y"] <= 1 or label["size"] <= 0):
            raise WikiError(f"layout.labels[{index}] 的 text/x/y/size/weight/family 非法")
    return layout


def compose(config: Config, target: Path, data: Path, out: Path, style: Path | None) -> None:
    layout = load_layout(target)
    specs = {panel["letter"]: load_spec(config.wiki_root / "templates" / panel["template"])
             for panel in layout["panels"]}
    if style is not None:
        overrides = read_json(style)
        if not isinstance(overrides, dict):
            raise WikiError("style 必须为字母到样式对象的映射")
        for letter, values in overrides.items():
            if letter not in specs:
                raise WikiError(f"style 字母不在 layout 中: {letter}")
            if not isinstance(values, dict):
                raise WikiError(f"style.{letter} 必须为对象")
            unknown = values.keys() - specs[letter]["style"].keys()
            if unknown:
                raise WikiError(f"style.{letter} 未知键: {', '.join(sorted(unknown))}")
    for panel in layout["panels"]:
        for name, filename in panel["tables"].items():
            check_table_data(name, specs[panel["letter"]]["tables"][name], data / filename)
    command = [str(config.python_exe), "-X", "utf8", str(Path(__file__).with_name("compose_runner.py")),
               "--wiki", str(config.wiki_root), "--layout", str((target / "layout.json").resolve()),
               "--data", str(data.resolve()), "--out", str(out.resolve())]
    if style is not None:
        command.extend(["--style", str(style.resolve())])
    out.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf", "svg"):
        (out / f"figure.{extension}").unlink(missing_ok=True)
    run(command, target)
    missing = [f"figure.{ext}" for ext in ("png", "pdf", "svg") if not (out / f"figure.{ext}").is_file()]
    if missing:
        raise WikiError(f"版式缺少输出文件: {', '.join(missing)}")


def render_layout(config: Config, entry_id: str, data: Path, out: Path, style: Path | None = None) -> None:
    meta, _ = read_page(config.wiki_root / "layouts" / f"{entry_id}.md")
    if meta["status"] != "ready":
        raise WikiError(f"版式必须为 ready: {entry_id}")
    compose(config, config.wiki_root / "layouts" / entry_id, data, out, style)


def verify_layout(config: Config, entry_id: str) -> tuple[float, Path]:
    from .verification import start_replay
    target = config.wiki_root / "layouts" / entry_id
    style = target / "example/style.json"
    inputs = start_replay(target)
    compose(config, target, target / "example", target / "verify", style if style.is_file() else None)
    meta, _ = read_page(target.with_suffix(".md"))
    replica = config.gallery_root / meta["gallery_entry"] / "output/replica.png"
    if not replica.is_file():
        raise WikiError(f"画廊缺少复刻图，无法对照回放: {replica}")
    mean, comparison = compare_images(replica, target / "verify/figure.png")
    record_preview(target, mean, inputs=inputs, executable=config.python_exe)
    print(f"平均绝对像素差 (0–255): {mean:.6f}\n{comparison}")
    save(config, f"verify {entry_id}")
    return mean, comparison

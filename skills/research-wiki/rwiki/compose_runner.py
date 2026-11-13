"""Standalone runner executed by the configured plotting interpreter."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path
from uuid import uuid4

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# This runner is also loaded by file path from unrelated working directories.
_sizing_spec = importlib.util.spec_from_file_location(
    "_compose_sizing", Path(__file__).with_name("sizing.py"))
_sizing = importlib.util.module_from_spec(_sizing_spec)
_sizing_spec.loader.exec_module(_sizing)
check_region = _sizing.check_region


def load_panel(template: Path, panel: str):
    name = "panel_" + uuid4().hex
    package_spec = importlib.util.spec_from_file_location(
        name, template / "code/__init__.py", submodule_search_locations=[str(template / "code")])
    package = importlib.util.module_from_spec(package_spec)
    sys.modules[name] = package
    package_spec.loader.exec_module(package)
    module_name = name + "." + Path(panel).stem
    module_spec = importlib.util.spec_from_file_location(module_name, template / panel)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module.draw


def main():
    parser = argparse.ArgumentParser()
    for flag in ("wiki", "layout", "data", "out"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--style", type=Path)
    args = parser.parse_args()
    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    overrides = json.loads(args.style.read_text(encoding="utf-8")) if args.style else {}
    canvas = layout["canvas"]
    matplotlib.rcParams.update({"pdf.fonttype": 42, "svg.fonttype": "none"})
    fig = plt.figure(figsize=(canvas["width_in"], canvas["height_in"]), dpi=canvas["dpi"])
    for panel in layout["panels"]:
        target = args.wiki / "templates" / panel["template"]
        spec = json.loads((target / "spec.json").read_text(encoding="utf-8"))
        tables = {name: pd.read_csv(args.data / filename) for name, filename in panel["tables"].items()}
        style = dict(spec["style"])
        for values in [panel["style"], overrides.get(panel["letter"], {})]:
            for key, value in values.items():
                style[key] = (style.get(key, {}) | value) if key == "sizing" and isinstance(value, dict) else value
        if "sizing" in style:
            check_region(fig, panel["rect"], tables, style)
        load_panel(target, spec["panel"])(fig, panel["rect"], tables, style)
    for label in layout["labels"]:
        fig.text(label["x"], label["y"], label["text"], fontsize=label["size"],
                 fontweight=label["weight"], fontfamily=label["family"], va="bottom")
    args.out.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf", "svg"):
        fig.savefig(args.out / f"figure.{extension}", dpi=canvas["dpi"])
    plt.close(fig)


if __name__ == "__main__":
    main()

"""Column-type sniffing and R/Python visualization code generation.

Derived from two cloned upstream repositories:
- ``dreamRs/esquisse`` (``R/utils.R``, ``R/geometries.R``, ``R/ggcall.R``, ``R/scales.R``):
  column-type classification (``discrete``, ``continuous``, ``time``, ``id``),
  ``potential_geoms_ref`` geometry recommendation matrix, and ``ggcall`` ggplot2 AST/code builder.
- ``visualpython/visualpython`` (``visualpython/data/m_visualize/seabornLibrary.js``,
  ``visualpython/js/m_visualize/Seaborn.js``, ``visualpython/js/m_visualize/Chart.js``):
  Seaborn and Matplotlib visualization code generation patterns.

Integrates ``ggsci_palettes.json`` (extracted from ``nanxstats/ggsci``) for
publication-ready journal color palettes across R (ggplot2/ggsci) and Python (Seaborn/Matplotlib).
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# Default path to extracted ggsci_palettes.json (can be overridden by caller)
_DEFAULT_PALETTES_JSON = Path(__file__).with_name("ggsci_palettes.json")

_ISO_DATE_RE = re.compile(
    r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[T ]\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)

# ---------------------------------------------------------------------------
# 1. Column-type sniffing (ported from dreamRs/esquisse R/utils.R::col_type)
# ---------------------------------------------------------------------------


def _is_number(val: str) -> bool:
    try:
        float(val)
        return True
    except (TypeError, ValueError):
        return False


def _is_bool_str(val: str) -> bool:
    return val.strip().lower() in {"true", "false", "t", "f", "yes", "no"}


def _is_datetime_str(val: str) -> bool:
    s = val.strip()
    if not _ISO_DATE_RE.match(s):
        return False
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            datetime.strptime(s[:19], fmt)
            return True
        except ValueError:
            continue
    return True


def col_type(values: list[Any], no_id: bool = False) -> str:
    """Port of ``esquisse::col_type(x, no_id = FALSE)`` from ``R/utils.R``.

    Classifies a column's values into ``'discrete'``, ``'continuous'``,
    ``'time'``, ``'id'``, or ``'unknown'``.

    Exact upstream heuristic for string/categorical vectors:
    ``if (u / n < 0.99 or u <= 30 or no_id) -> 'discrete' else -> 'id'``.
    """
    non_empty = [
        str(v).strip()
        for v in values
        if v is not None and str(v).strip() != "" and str(v).strip().lower() not in {"na", "nan", "null", "none"}
    ]
    if not non_empty:
        return "unknown"

    # Logical / boolean strings behave as discrete in esquisse
    if all(_is_bool_str(v) for v in non_empty):
        return "discrete"

    # Datetime / Date check (esquisse Date/POSIXct -> 'time')
    if all(_is_datetime_str(v) for v in non_empty):
        return "time"

    # Numeric check (esquisse numeric/integer/double -> 'continuous')
    if all(_is_number(v) for v in non_empty):
        return "continuous"

    # Character / factor heuristic from esquisse R/utils.R lines 189-197
    n = len(non_empty)
    u = len(set(non_empty))
    if (u / n) < 0.99 or u <= 30 or no_id:
        return "discrete"
    return "id"


def sniff_csv_columns(
    path: str | Path,
    *,
    max_scan_rows: int = 500,
    preview_limit: int = 12,
    sample_limit: int = 5,
) -> dict[str, Any]:
    """Sniff a CSV/TSV file and return Studio-compatible column metadata.

    Matches the ``POST /api/studio/sniff`` contract:
    ``{ columns: [{ name, type, samples, unique_count, non_null_count }], row_count_estimate, preview_rows }``.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Data file not found: {p}")

    delimiter = "\t" if p.suffix.lower() in {".tsv", ".txt"} else ","
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        sample_head = fh.read(4096)
        fh.seek(0)
        if p.suffix.lower() not in {".tsv", ".csv"} and "\t" in sample_head and "," not in sample_head:
            delimiter = "\t"
        reader = csv.DictReader(fh, delimiter=delimiter)
        fieldnames = list(reader.fieldnames or [])
        col_values: dict[str, list[str]] = {c: [] for c in fieldnames}
        preview_rows: list[dict[str, str]] = []
        row_count = 0
        for row in reader:
            row_count += 1
            if len(preview_rows) < preview_limit:
                preview_rows.append({c: (row.get(c) or "") for c in fieldnames})
            if row_count <= max_scan_rows:
                for c in fieldnames:
                    col_values[c].append(row.get(c) or "")

    columns = []
    for name in fieldnames:
        vals = col_values[name]
        non_empty = [v.strip() for v in vals if v and v.strip() != ""]
        seen: list[str] = []
        for v in non_empty:
            if v not in seen:
                seen.append(v)
            if len(seen) >= sample_limit:
                break
        columns.append(
            {
                "name": name,
                "type": col_type(vals),
                "samples": seen,
                "unique_count": len(set(non_empty)),
                "non_null_count": len(non_empty),
            }
        )

    return {
        "path": str(p),
        "delimiter": delimiter,
        "columns": columns,
        "row_count_estimate": row_count,
        "preview_rows": preview_rows,
    }


# ---------------------------------------------------------------------------
# 2. Potential geometries matrix (ported from esquisse R/geometries.R)
# ---------------------------------------------------------------------------

POTENTIAL_GEOMS_REF: list[tuple[str, str, str, bool]] = [
    ("continuous", "empty", "histogram", True),
    ("continuous", "empty", "boxplot", False),
    ("continuous", "empty", "violin", False),
    ("continuous", "empty", "density", False),
    ("discrete", "empty", "bar", True),
    ("time", "empty", "histogram", True),
    ("time", "empty", "bar", False),
    ("continuous", "discrete", "boxplot", False),
    ("continuous", "discrete", "point", False),
    ("continuous", "discrete", "jitter", False),
    ("continuous", "discrete", "violin", False),
    ("continuous", "discrete", "bar", True),
    ("discrete", "continuous", "col", True),
    ("discrete", "continuous", "bar", False),
    ("discrete", "continuous", "boxplot", False),
    ("discrete", "continuous", "point", False),
    ("discrete", "continuous", "jitter", False),
    ("discrete", "continuous", "violin", False),
    ("discrete", "continuous", "text", False),
    ("discrete", "continuous", "label", False),
    ("continuous", "continuous", "point", True),
    ("continuous", "continuous", "jitter", False),
    ("continuous", "continuous", "line", False),
    ("continuous", "continuous", "step", False),
    ("continuous", "continuous", "path", False),
    ("continuous", "continuous", "area", False),
    ("continuous", "continuous", "smooth", False),
    ("continuous", "continuous", "text", False),
    ("continuous", "continuous", "label", False),
    ("discrete", "discrete", "tile", True),
    ("time", "continuous", "line", True),
    ("time", "continuous", "point", False),
    ("time", "continuous", "step", False),
    ("time", "continuous", "area", False),
    ("time", "continuous", "bar", False),
    ("time", "continuous", "smooth", False),
    ("empty", "continuous", "line", True),
    ("empty", "continuous", "step", False),
    ("empty", "continuous", "path", False),
    ("empty", "continuous", "area", False),
    ("continuous", "continuous", "tile", False),
    ("discrete", "time", "tile", False),
    ("time", "discrete", "tile", False),
]


def potential_geoms(
    x_type: str | None = None,
    y_type: str | None = None,
    *,
    auto: bool = False,
) -> list[str]:
    """Port of ``esquisse::potential_geoms`` (``R/geometries.R``).

    Given sniffed ``x_type`` and ``y_type`` (``'discrete'``, ``'continuous'``,
    ``'time'``, or ``None``), returns compatible ggplot2 geom names.
    """
    xt = None if x_type in (None, "", "empty") else ("discrete" if x_type == "id" else x_type)
    yt = None if y_type in (None, "", "empty") else ("discrete" if y_type == "id" else y_type)

    if xt is None and yt is not None:
        if yt != "continuous":
            xt = yt
            yt = "empty"
        else:
            xt = "empty"
    elif xt is not None and yt is None:
        yt = "empty"
    elif xt is None and yt is None:
        return []

    matches = [
        geom
        for (gx, gy, geom, is_auto) in POTENTIAL_GEOMS_REF
        if gx == xt and gy == yt and (not auto or is_auto)
    ]
    return matches


# ---------------------------------------------------------------------------
# 3. Palette helpers backed by extracted ggsci_palettes.json
# ---------------------------------------------------------------------------


def load_ggsci_palettes(palettes_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(palettes_path) if palettes_path else _DEFAULT_PALETTES_JSON
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("palettes", {})


def resolve_palette(name: str, palettes: dict[str, Any] | None = None) -> dict[str, Any]:
    pal_db = palettes if palettes is not None else load_ggsci_palettes()
    norm = (name or "NPG").strip().lower()
    for pid, entry in pal_db.items():
        if pid.lower() == norm:
            return entry
    return pal_db.get(
        "NPG",
        {
            "id": "NPG",
            "colors": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4"],
            "r_scale_color": "ggsci::scale_color_npg()",
            "r_scale_fill": "ggsci::scale_fill_npg()",
        },
    )


def _r_str(value: Any) -> str:
    s = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _format_r_args(args: dict[str, Any]) -> str:
    parts = []
    for k, v in args.items():
        if v is None or v == "":
            continue
        if isinstance(v, bool):
            parts.append(f"{k} = {'TRUE' if v else 'FALSE'}")
        elif isinstance(v, (int, float)):
            parts.append(f"{k} = {v}")
        elif isinstance(v, (list, tuple)):
            inner = ", ".join(_r_str(x) if isinstance(x, str) else str(x) for x in v)
            parts.append(f"{k} = c({inner})")
        else:
            parts.append(f"{k} = {_r_str(v)}")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# 4. R ggplot2 code generator (ported from dreamRs/esquisse R/ggcall.R + scales.R)
# ---------------------------------------------------------------------------


def generate_ggplot2_code(
    data_var: str = "df",
    mapping: dict[str, str] | None = None,
    geom: str | list[str] = "point",
    geom_args: dict[str, Any] | list[dict[str, Any]] | None = None,
    *,
    palette: str = "NPG",
    labs: dict[str, str] | None = None,
    theme: str = "theme_minimal",
    theme_args: dict[str, Any] | None = None,
    facet: str | list[str] | None = None,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    data_file: str | None = None,
    output_file: str | None = None,
    width: float = 8.0,
    height: float = 6.0,
    palettes_db: dict[str, Any] | None = None,
) -> str:
    """Generate clean, reproducible R ggplot2 + ggsci script modeled on ``esquisse::ggcall``."""
    mapping = {k: v for k, v in (mapping or {}).items() if v}
    geoms = [geom] if isinstance(geom, str) else list(geom)
    if isinstance(geom_args, list):
        g_args_list = geom_args
    elif isinstance(geom_args, dict):
        g_args_list = [geom_args]
    else:
        g_args_list = [{} for _ in geoms]

    pal = resolve_palette(palette, palettes_db)
    lines: list[str] = [
        "library(ggplot2)",
        "library(ggsci)",
        "",
    ]
    if data_file:
        sep = "\\t" if str(data_file).lower().endswith(".tsv") else ","
        lines.append(
            f'{data_var} <- read.delim({_r_str(data_file)}, sep = "{sep}", check.names = FALSE)'
        )

    # ggplot(data) + aes(...)
    aes_parts = [f"{k} = {v}" for k, v in mapping.items()]
    plot_expr: list[str] = [f"p <- ggplot({data_var})"]
    if aes_parts:
        plot_expr.append(f"  aes({', '.join(aes_parts)})")

    # geoms
    for idx, g_nm in enumerate(geoms):
        fn = g_nm if g_nm.startswith("geom_") else f"geom_{g_nm}"
        args = g_args_list[idx] if idx < len(g_args_list) else {}
        arg_str = _format_r_args(args)
        plot_expr.append(f"  {fn}({arg_str})")

    # ggsci / color scales (from esquisse::which_pal_scale + ggsci)
    if any(k in mapping for k in ("color", "colour")):
        plot_expr.append(f"  {pal.get('r_scale_color', 'ggsci::scale_color_npg()')}")
    if "fill" in mapping:
        plot_expr.append(f"  {pal.get('r_scale_fill', 'ggsci::scale_fill_npg()')}")

    # labs
    clean_labs = {k: v for k, v in (labs or {}).items() if v}
    if clean_labs:
        plot_expr.append(f"  labs({_format_r_args(clean_labs)})")

    # theme
    if theme:
        th = theme if theme.startswith("theme_") else f"theme_{theme}"
        plot_expr.append(f"  {th}()")

    # theme_args (esquisse clears legend.position when no color/fill/size/shape mapped)
    t_args = dict(theme_args or {})
    if not any(k in mapping for k in ("fill", "colour", "color", "size", "shape")):
        t_args.pop("legend.position", None)
    t_str = _format_r_args(t_args)
    if t_str:
        plot_expr.append(f"  theme({t_str})")

    # facet_wrap
    if facet:
        facets = [facet] if isinstance(facet, str) else list(facet)
        vars_str = ", ".join(facets)
        plot_expr.append(f"  facet_wrap(vars({vars_str}))")

    if xlim and len(xlim) == 2:
        plot_expr.append(f"  xlim({xlim[0]}, {xlim[1]})")
    if ylim and len(ylim) == 2:
        plot_expr.append(f"  ylim({ylim[0]}, {ylim[1]})")

    lines.append(" +\n".join(plot_expr))

    if output_file:
        lines.append("")
        lines.append(
            f"ggsave({_r_str(output_file)}, plot = p, width = {width}, height = {height}, dpi = 300)"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 5. Python Seaborn/Matplotlib code generator (ported from visualpython)
# ---------------------------------------------------------------------------

# Chart specs derived from visualpython/data/m_visualize/seabornLibrary.js
SEABORN_CHART_SPECS: dict[str, dict[str, Any]] = {
    "scatterplot": {"fn": "sns.scatterplot", "params": ["data", "x", "y", "hue"]},
    "lineplot": {"fn": "sns.lineplot", "params": ["data", "x", "y", "hue"]},
    "histplot": {"fn": "sns.histplot", "params": ["data", "x", "y", "hue", "bins", "kde", "stat"]},
    "kdeplot": {"fn": "sns.kdeplot", "params": ["data", "x", "y", "hue"]},
    "stripplot": {"fn": "sns.stripplot", "params": ["data", "x", "y", "hue"]},
    "swarmplot": {"fn": "sns.swarmplot", "params": ["data", "x", "y", "hue"]},
    "boxplot": {"fn": "sns.boxplot", "params": ["data", "x", "y", "hue"]},
    "violinplot": {"fn": "sns.violinplot", "params": ["data", "x", "y", "hue"]},
    "pointplot": {"fn": "sns.pointplot", "params": ["data", "x", "y", "hue"]},
    "barplot": {"fn": "sns.barplot", "params": ["data", "x", "y", "hue", "orient"]},
    "countplot": {"fn": "sns.countplot", "params": ["data", "x", "y", "hue"]},
    "heatmap": {"fn": "sns.heatmap", "params": ["data", "annot"]},
}

# Matplotlib chart kinds derived from visualpython/js/m_visualize/Chart.js
MATPLOTLIB_CHART_KINDS = ("plot", "bar", "barh", "hist", "boxplot", "scatter", "errorbar")


def generate_python_viz_code(
    kind: str = "scatterplot",
    data_var: str = "df",
    mapping: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    *,
    library: str = "seaborn",
    palette: str = "NPG",
    data_file: str | None = None,
    output_file: str | None = None,
    palettes_db: dict[str, Any] | None = None,
) -> str:
    """Generate Python Seaborn/Matplotlib code derived from VisualPython's codegen patterns."""
    mapping = {k: v for k, v in (mapping or {}).items() if v}
    params = dict(params or {})
    pal = resolve_palette(palette, palettes_db)
    colors = pal.get("colors", ["#E64B35", "#4DBBD5", "#00A087", "#3C5488"])

    width = params.get("width", 8)
    height = params.get("height", 6)
    font_size = params.get("font_size", 11)
    title = params.get("title", "")
    xlabel = params.get("xlabel", mapping.get("x", ""))
    ylabel = params.get("ylabel", mapping.get("y", ""))
    dpi = params.get("dpi", 300)

    lines: list[str] = [
        "import pandas as pd",
        "import matplotlib.pyplot as plt",
        "from matplotlib import rcParams",
    ]
    if library == "seaborn":
        lines.append("import seaborn as sns")

    lines.extend(
        [
            "",
            f"PALETTE = {json.dumps(colors)}",
            f"rcParams['font.size'] = {font_size}",
            "rcParams['axes.unicode_minus'] = False",
        ]
    )
    if library == "seaborn":
        lines.append("sns.set_theme(style='ticks', palette=PALETTE)")

    if data_file:
        sep = "\\t" if str(data_file).lower().endswith(".tsv") else ","
        lines.append(f"{data_var} = pd.read_csv({data_file!r}, sep={sep!r})")

    lines.append(f"fig, ax = plt.subplots(figsize=({width}, {height}))")

    if library == "matplotlib" and kind in MATPLOTLIB_CHART_KINDS:
        x_col = mapping.get("x")
        y_col = mapping.get("y")
        if kind in ("hist",):
            lines.append(f"ax.hist({data_var}[{x_col!r}].dropna(), color=PALETTE[0])")
        elif kind == "boxplot" and x_col and y_col:
            lines.append(f"{data_var}.boxplot(column={y_col!r}, by={x_col!r}, ax=ax)")
        elif x_col and y_col:
            lines.append(f"ax.{kind}({data_var}[{x_col!r}], {data_var}[{y_col!r}], color=PALETTE[0])")
        else:
            lines.append(f"{data_var}.plot(kind={kind!r}, ax=ax, color=PALETTE)")
    else:
        spec = SEABORN_CHART_SPECS.get(kind, SEABORN_CHART_SPECS["scatterplot"])
        call_args = [f"data={data_var}"]
        hue_col = mapping.get("hue") or mapping.get("color") or mapping.get("fill")
        if mapping.get("x") and "x" in spec["params"]:
            call_args.append(f"x={mapping['x']!r}")
        if mapping.get("y") and "y" in spec["params"]:
            call_args.append(f"y={mapping['y']!r}")
        if hue_col and "hue" in spec["params"]:
            call_args.append(f"hue={hue_col!r}")
            call_args.append("palette=PALETTE")
        for opt_key in ("bins", "kde", "stat", "orient", "annot"):
            if opt_key in spec["params"] and opt_key in params and params[opt_key] not in (None, ""):
                call_args.append(f"{opt_key}={params[opt_key]!r}")
        call_args.append("ax=ax")
        lines.append(f"{spec['fn']}({', '.join(call_args)})")

    if title:
        lines.append(f"ax.set_title({title!r})")
    if xlabel:
        lines.append(f"ax.set_xlabel({xlabel!r})")
    if ylabel:
        lines.append(f"ax.set_ylabel({ylabel!r})")
    if params.get("grid"):
        lines.append("ax.grid(True, alpha=0.3, linestyle='--')" )
    lines.append("fig.tight_layout()")
    if output_file:
        lines.append(f"fig.savefig({str(output_file)!r}, dpi={dpi}, bbox_inches='tight')")
    else:
        lines.append("plt.show()")
    return "\n".join(lines) + "\n"

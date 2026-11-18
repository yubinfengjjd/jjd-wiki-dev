"""Convert FigureYa L1 recipes into standalone native L2 templates verified with synthetic inputs.

Usage:
  python convert_figureya_templates.py --dry-run
  python convert_figureya_templates.py --apply [--limit N] [--only id1,id2]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import shutil
import sys
from pathlib import Path
from typing import Any

DEV_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = DEV_ROOT / "skills" / "research-wiki"
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

from rwiki.acceptance import entry_errors, record_acceptance
from rwiki.config import load_config
from rwiki.facts import template_facts
from rwiki.pages import read_page, set_block, write_page
from rwiki.templates import record_preview, render, start_replay

_CHUNK_START_RE = re.compile(r"^```\{\s*[rR]\b([^}]*)\}\s*$")
_CHUNK_END_RE = re.compile(r"^```\s*$")
_QUOTED_STR_RE = re.compile(r"""['"]([A-Za-z0-9_.\-+:/]{2,64})['"]""")
_DROP_LINE_PATTERNS = (
    re.compile(r'source\s*\(\s*["\']install_dependencies\.R["\']', re.I),
    re.compile(r'\binstall\.packages\s*\(', re.I),
    re.compile(r'\bBiocManager::install\s*\(', re.I),
    re.compile(r'\bdevtools::install_', re.I),
    re.compile(r'\bremotes::install_', re.I),
    re.compile(r'\bsetwd\s*\(', re.I),
    re.compile(r'\brm\s*\(\s*list\s*=\s*ls\s*\(', re.I),
    re.compile(r'\bsessionInfo\s*\(', re.I),
    re.compile(r'\bView\s*\(', re.I),
    re.compile(r'\bbrowseURL\s*\(', re.I),
)

UNIVERSAL_RENDER_R = """# Portable FigureYa native template renderer.
# Usage: Rscript code/render.R --data <dir> --out <dir> [--style <json>]
args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(name, default = NULL) {
  i <- match(name, args)
  if (is.na(i) || i >= length(args)) default else args[i + 1]
}
script_arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_path <- sub("^--file=", "", script_arg[1])
root <- dirname(dirname(normalizePath(script_path)))
data_dir <- get_arg("--data")
out_dir <- get_arg("--out")
if (is.null(data_dir) || is.null(out_dir)) {
  stop("Usage: Rscript code/render.R --data <dir> --out <dir> [--style <json>]")
}
if (!dir.exists(data_dir)) stop("Data directory not found: ", data_dir)

spec <- jsonlite::fromJSON(file.path(root, "spec.json"), simplifyVector = FALSE)
style <- if (is.null(spec$style)) list() else spec$style
style_file <- get_arg("--style")
if (!is.null(style_file) && file.exists(style_file)) {
  override <- jsonlite::fromJSON(style_file, simplifyVector = FALSE)
  for (key in names(override)) {
    style[[key]] <- override[[key]]
  }
}

dpi <- if (is.null(style$dpi)) 200 else as.numeric(style$dpi)
w_in <- if (is.null(style$width_in)) 8 else as.numeric(style$width_in)
h_in <- if (is.null(style$height_in)) 6 else as.numeric(style$height_in)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_dir_abs <- normalizePath(out_dir, mustWork = FALSE)

wd <- tempfile("rwiki_fy_")
dir.create(wd, recursive = TRUE, showWarnings = FALSE)
on.exit(unlink(wd, recursive = TRUE, force = TRUE), add = TRUE)

code_dir <- file.path(root, "code")
for (f in list.files(code_dir, full.names = TRUE)) {
  bn <- basename(f)
  if (bn %in% c("render.R", "plot_figureya.R")) next
  if (dir.exists(f)) {
    file.copy(f, wd, recursive = TRUE)
  } else {
    file.copy(f, file.path(wd, bn), overwrite = TRUE)
  }
}

for (f in list.files(data_dir, full.names = TRUE)) {
  if (file.exists(f) && !dir.exists(f)) {
    file.copy(f, file.path(wd, basename(f)), overwrite = TRUE)
  }
}

before_pdfs <- list.files(wd, pattern = "\\\\.pdf$", ignore.case = TRUE, recursive = TRUE, full.names = TRUE)
before_info <- if (length(before_pdfs)) file.info(before_pdfs)$mtime else as.POSIXct(character(0))

fallback_pdf <- file.path(wd, "__rwiki_fallback__.pdf")
assign("rwiki_style", style, envir = globalenv())
assign("rwiki_title", if (is.null(style$title)) "" else as.character(style$title), envir = globalenv())
assign("rwiki_palette", if (is.null(style$palette)) "NPG" else as.character(style$palette), envir = globalenv())
assign("rwiki_width_in", w_in, envir = globalenv())
assign("rwiki_height_in", h_in, envir = globalenv())
# Shadow screen-only dev.copy2pdf so offscreen cairo_pdf runs capture plots without failing
assign("dev.copy2pdf", function(...) invisible(NULL), envir = globalenv())

old_wd <- getwd()
setwd(wd)
on.exit(setwd(old_wd), add = TRUE)

grDevices::cairo_pdf(fallback_pdf, width = w_in, height = h_in, bg = "white")
fallback_dev <- grDevices::dev.cur()
script_err <- NULL
tryCatch({
  source(file.path(code_dir, "plot_figureya.R"), local = FALSE, chdir = FALSE, print.eval = TRUE)
}, error = function(e) {
  script_err <<- e
})
while (grDevices::dev.cur() > 1L) {
  try(grDevices::dev.off(), silent = TRUE)
}
setwd(old_wd)
if (!is.null(script_err)) stop(script_err)

after_pdfs <- list.files(wd, pattern = "\\\\.pdf$", ignore.case = TRUE, recursive = TRUE, full.names = TRUE)
generated_pdfs <- setdiff(after_pdfs, c(before_pdfs, normalizePath(fallback_pdf, mustWork = FALSE)))
generated_pdfs <- generated_pdfs[!grepl("(^|[\\\\/])(__rwiki_fallback__|Rplots)\\\\.pdf$", generated_pdfs, ignore.case = TRUE)]
has_pages <- function(p) {
  if (!file.exists(p) || file.info(p)$size <= 512) return(FALSE)
  tryCatch(pdftools::pdf_length(p) > 0L, error = function(e) FALSE)
}
generated_pdfs <- generated_pdfs[vapply(generated_pdfs, has_pages, logical(1))]

chosen_pdf <- NULL
if (length(generated_pdfs) > 0) {
  sizes <- file.info(generated_pdfs)$size
  chosen_pdf <- generated_pdfs[which.max(sizes)]
} else if (has_pages(fallback_pdf)) {
  chosen_pdf <- fallback_pdf
}
if (is.null(chosen_pdf)) {
  stop("FigureYa script did not produce a non-empty PDF output")
}

target_pdf <- file.path(out_dir_abs, "figure.pdf")
target_png <- file.path(out_dir_abs, "figure.png")
target_svg <- file.path(out_dir_abs, "figure.svg")
file.copy(chosen_pdf, target_pdf, overwrite = TRUE)

psize <- tryCatch(pdftools::pdf_pagesize(target_pdf)[1, ], error = function(e) list(width = w_in * 72, height = h_in * 72))
pw_in <- max(2, min(24, as.numeric(psize$width) / 72))
ph_in <- max(2, min(24, as.numeric(psize$height) / 72))

bmp <- pdftools::pdf_convert(target_pdf, format = "png", pages = 1, dpi = dpi, filenames = target_png, verbose = FALSE)
img <- png::readPNG(target_png)

if (requireNamespace("svglite", quietly = TRUE)) {
  svglite::svglite(target_svg, width = pw_in, height = ph_in, bg = "white")
  svg_dev <- "svglite"
} else {
  grDevices::svg(target_svg, width = pw_in, height = ph_in, bg = "white")
  svg_dev <- "grDevices::svg"
}
grid::grid.newpage()
grid::grid.raster(img, width = grid::unit(1, "npc"), height = grid::unit(1, "npc"))
grDevices::dev.off()

sizing <- list(width_in = round(pw_in, 2), height_in = round(ph_in, 2), dpi = dpi, svg_device = svg_dev)
jsonlite::write_json(sizing, file.path(out_dir_abs, "sizing.json"), auto_unbox = TRUE, pretty = TRUE)
cat("Wrote", target_png, "from", basename(chosen_pdf), "\\n")
"""


def _slug_for_recipe(rid: str, taken: set[str]) -> str:
    # e.g. figureya-162boxviolin -> fy162-boxviolin -> or fy-boxviolin if unique
    m = re.match(r"^figureya-(\d+)(plus)?-?(.*?)(?:-update)?$", rid)
    if m:
        num, plus, tail = m.group(1), m.group(2), m.group(3) or f"fig{num}"
        tail_clean = re.sub(r"[^a-z0-9]+", "-", tail.lower()).strip("-") or f"fig{num}"
        base = f"fy-{tail_clean}"
        if plus:
            base = f"{base}-plus"
    else:
        base = "fy-" + re.sub(r"^figureya-", "", rid)
    base = re.sub(r"-+", "-", base).strip("-")[:40].strip("-")
    candidate = base
    if candidate in taken:
        num_suffix = re.search(r"figureya-(\d+)", rid)
        candidate = f"{base}-{num_suffix.group(1)}" if num_suffix else f"{base}-2"
    i = 2
    while candidate in taken:
        candidate = f"{base}-{i}"
        i += 1
    taken.add(candidate)
    return candidate


def _extract_rmd_r_code(rmd_path: Path) -> str:
    lines = rmd_path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[str] = []
    in_chunk = False
    skip_chunk = False
    for line in lines:
        if not in_chunk:
            m = _CHUNK_START_RE.match(line)
            if m:
                in_chunk = True
                opts = m.group(1)
                skip_chunk = bool(re.search(r"\beval\s*=\s*(?:FALSE|F)\b", opts))
                continue
        else:
            if _CHUNK_END_RE.match(line):
                in_chunk = False
                skip_chunk = False
                out.append("")
                continue
            if skip_chunk:
                continue
            if any(pat.search(line) for pat in _DROP_LINE_PATTERNS):
                continue
            out.append(line)
    # Remove noisy knitr::opts_chunk$set lines
    cleaned = [ln for ln in out if "knitr::opts_chunk" not in ln]
    return "\n".join(cleaned).strip() + "\n"


def _infer_col_type(values: list[str]) -> str:
    vals = [v.strip() for v in values if v.strip() not in ("", "NA", "NaN", "null", "NULL")]
    if not vals:
        return "str"
    try:
        nums = [float(v) for v in vals]
        if all(re.fullmatch(r"-?\d+", v) for v in vals):
            return "int"
        if nums:
            return "float"
    except ValueError:
        pass
    return "str"


def _synthesize_or_compact_table(
    src_path: Path,
    dest_path: Path,
    referenced_tokens: set[str],
    max_rows: int = 1800,
    max_cols: int = 400,
) -> tuple[dict[str, dict[str, Any]], int]:
    """Build compact synthetic/example CSV/TXT under size cap while preserving schema & referenced IDs."""
    text = src_path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    if not lines:
        dest_path.write_text("", encoding="utf-8", newline="\n")
        return {}, 0

    first = lines[0]
    if src_path.suffix.lower() in (".tsv", ".txt") and "\t" in first:
        delim = "\t"
    elif "," in first:
        delim = ","
    else:
        # Whitespace or single-column TXT: keep up to 2 MB under 5 MB push-guard cap
        kept_lines = lines if (src_path.stat().st_size <= 2_000_000) else lines[: max_rows + 1]
        dest_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8", newline="\n")
        return {}, max(0, len(kept_lines) - 1)

    reader = csv.reader(lines, delimiter=delim)
    rows = list(reader)
    if not rows:
        dest_path.write_text("", encoding="utf-8", newline="\n")
        return {}, 0

    header = rows[0]
    body = rows[1:]
    need_trim = src_path.stat().st_size > 2_000_000

    if not need_trim:
        dest_path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
        chosen_header = header
        chosen_body = body
    else:
        keep_cols = list(range(min(len(header), max_cols)))
        for ci, col_name in enumerate(header):
            if ci not in keep_cols and col_name in referenced_tokens and len(keep_cols) < max_cols + 12:
                keep_cols.append(ci)
        keep_cols = sorted(set(keep_cols))

        matched_idx: list[int] = []
        other_idx: list[int] = []
        for ri, row in enumerate(body):
            row_vals = {c.strip() for c in row[:4] if c.strip()}
            if row_vals & referenced_tokens:
                matched_idx.append(ri)
            else:
                other_idx.append(ri)
        take_matched = matched_idx[:max_rows]
        rem = max(0, max_rows - len(take_matched))
        if rem > 0 and other_idx:
            step = max(1, len(other_idx) // rem)
            sampled = other_idx[::step][:rem]
        else:
            sampled = []
        chosen_rows_idx = sorted(set(take_matched + sampled))

        chosen_header = [header[ci] for ci in keep_cols]
        chosen_body = [
            [row[ci] if ci < len(row) else "" for ci in keep_cols]
            for ri in chosen_rows_idx
            for row in [body[ri]]
        ]
        with dest_path.open("w", encoding="utf-8", newline="") as fout:
            writer = csv.writer(fout, delimiter=delim, lineterminator="\n")
            writer.writerow(chosen_header)
            writer.writerows(chosen_body)

    # Extract column schema only when header is unambiguous and <= 15 non-empty named columns
    cols_schema: dict[str, dict[str, Any]] = {}
    if 0 < len(chosen_header) <= 15 and all(c.strip() for c in chosen_header):
        sample_rows = chosen_body[:12]
        for ci, col_name in enumerate(chosen_header):
            cname = col_name.strip()
            if cname in cols_schema:
                continue
            col_vals = [r[ci] for r in sample_rows if ci < len(r)]
            cols_schema[cname] = {
                "type": _infer_col_type(col_vals),
                "description": f"示例列 {cname}",
                "required": True,
            }
    return cols_schema, len(chosen_body)


def _find_candidates(wiki_root: Path) -> list[dict[str, Any]]:
    already_promoted: dict[str, str] = {}
    taken_slugs: set[str] = set()
    for tmd in sorted((wiki_root / "templates").glob("*.md")):
        tm, _ = read_page(tmd)
        taken_slugs.add(tm["id"])
        for al in tm.get("aliases") or []:
            taken_slugs.add(str(al))
        for src in tm.get("sources") or []:
            already_promoted[str(src).removesuffix(".md")] = tm["id"]

    mmap = json.loads((wiki_root / "recipes/method-map.json").read_text(encoding="utf-8"))["mappings"]
    candidates = []
    for rmd in sorted((wiki_root / "recipes").glob("figureya-*.md")):
        meta, _ = read_page(rmd)
        rid = meta["id"]
        if meta.get("status") != "ready" or f"recipes/{rid}" in already_promoted:
            continue
        src_dir = rmd.with_suffix("") / "source"
        if not src_dir.is_dir():
            continue
        rmds = sorted(p for p in src_dir.glob("*") if p.is_file() and p.suffix.lower() in (".rmd", ".r") and p.name.lower() != "install_dependencies.r")
        tables = sorted(p for p in src_dir.glob("*") if p.is_file() and p.suffix.lower() in (".csv", ".txt", ".tsv"))
        if not rmds or not tables:
            continue
        slug = _slug_for_recipe(rid, taken_slugs)
        methods = mmap.get(rid, {}).get("methods") or []
        candidates.append({
            "rid": rid,
            "rmd_meta": meta,
            "rmd_path": rmd,
            "src_dir": src_dir,
            "scripts": rmds,
            "tables": tables,
            "slug": slug,
            "primary_method": methods[0] if methods else "",
        })
    return candidates


def _convert_one(config, item: dict[str, Any]) -> tuple[bool, str]:
    wiki_root = config.wiki_root
    slug = item["slug"]
    rid = item["rid"]
    meta = item["rmd_meta"]
    src_dir: Path = item["src_dir"]

    tpl_md = wiki_root / "templates" / f"{slug}.md"
    tpl_dir = wiki_root / "templates" / slug
    code_dir = tpl_dir / "code"
    example_dir = tpl_dir / "example"
    verify_dir = tpl_dir / "verify"

    # Prepare clean directory
    if tpl_dir.exists():
        shutil.rmtree(tpl_dir)
    code_dir.mkdir(parents=True, exist_ok=True)
    example_dir.mkdir(parents=True, exist_ok=True)
    verify_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extract primary Rmd (or R script) -> code/plot_figureya.R, copy helper .R & small data deps
    main_rmds = [p for p in item["scripts"] if p.suffix.lower() == ".rmd"]
    if main_rmds:
        r_code = _extract_rmd_r_code(main_rmds[0])
        helper_r = [p for p in item["scripts"] if p.suffix.lower() == ".r"]
    else:
        r_code = item["scripts"][0].read_text(encoding="utf-8", errors="replace")
        helper_r = item["scripts"][1:]

    # Strip any absolute Windows paths that might exist in raw comments/examples
    r_code = re.sub(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s"\'\n\r]+', ".", r_code)
    (code_dir / "plot_figureya.R").write_text(r_code, encoding="utf-8", newline="\n")
    (code_dir / "render.R").write_text(UNIVERSAL_RENDER_R, encoding="utf-8", newline="\n")

    for hp in helper_r:
        shutil.copyfile(hp, code_dir / hp.name)

    # Copy small non-table auxiliary assets (< 500 KB) referenced in source_dir (e.g. .gmt, .rda, .rds, .xlsx)
    skip_suffixes = {".rmd", ".r", ".csv", ".txt", ".tsv", ".pdf", ".png", ".jpg", ".jpeg", ".log", ".html"}
    for extra in src_dir.iterdir():
        if extra.is_file() and extra.suffix.lower() not in skip_suffixes and extra.stat().st_size <= 500_000:
            shutil.copyfile(extra, code_dir / extra.name)
        elif extra.is_dir() and extra.name.lower() not in ("__pycache__", "runs"):
            total_sub = sum(f.stat().st_size for f in extra.rglob("*") if f.is_file())
            if total_sub <= 500_000:
                shutil.copytree(extra, code_dir / extra.name, dirs_exist_ok=True)

    referenced_tokens = set(_QUOTED_STR_RE.findall(r_code))

    # 2. Synthesize / compact example input tables -> example/<filename> + build spec.json tables
    spec_tables: dict[str, Any] = {}
    for idx, tpath in enumerate(item["tables"]):
        tkey = "data" if idx == 0 else f"table_{idx + 1}"
        # Keep safe clean table key matching identifier
        safe_key = re.sub(r"[^a-zA-Z0-9_]+", "_", tpath.stem).strip("_").lower() or tkey
        if safe_key in spec_tables:
            safe_key = f"{safe_key}_{idx + 1}"
        cols_schema, _nrows = _synthesize_or_compact_table(tpath, example_dir / tpath.name, referenced_tokens)
        spec_tables[safe_key] = {
            "interface": "",
            "filename": tpath.name,
            "description": f"{meta['title']}输入数据表（{tpath.name}）",
            "required": True,
            "columns": cols_schema,
        }

    spec = {
        "entry": "code/render.R",
        "language": "r",
        "tables": spec_tables,
        "style": {
            "dpi": 200,
            "width_in": 8.0,
            "height_in": 6.0,
            "palette": "NPG",
            "title": "",
        },
        "parameters": {
            "palette": {
                "type": "select",
                "label": "顶刊配色主题 (ggsci)",
                "default": "NPG",
                "choices": ["NPG", "Nature", "Lancet", "NEJM", "JAMA", "Cell"],
                "description": "选择 Nature/Lancet/NEJM/JAMA/Cell 配色方案",
            },
            "width": {"type": "number", "label": "画布宽度 (inch)", "default": 8.0, "min": 3.0, "max": 20.0, "step": 0.5},
            "height": {"type": "number", "label": "画布高度 (inch)", "default": 6.0, "min": 3.0, "max": 20.0, "step": 0.5},
            "title": {"type": "string", "label": "图标题", "default": ""},
        },
    }
    (tpl_dir / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    # 3. Write template markdown page
    tpl_meta: dict[str, Any] = {
        "type": "template",
        "id": slug,
        "title": meta["title"],
        "status": "ready",
        "layouts": [],
        "sources": [f"recipes/{rid}"],
        "panels": [],
        "language": "r",
        "license": meta.get("license") or "CC-BY-NC-SA-4.0",
        "tags": meta.get("tags") or ["other"],
        "chart_types": meta.get("chart_types") or ["other"],
        "keywords": meta.get("keywords") or [],
        "favorite": False,
    }
    if item["primary_method"]:
        tpl_meta["primary_method"] = item["primary_method"]

    table_summary = "、".join(f"`{t['filename']}`" for t in spec_tables.values())
    body = (
        f"# {meta['title']}\n\n"
        f"![[templates/{slug}/preview.png]]\n\n"
        f"> 许可：{tpl_meta['license']}（由 [[recipes/{rid}|{meta['title']}]] 整理为独立可调用原生模板；"
        f"`example/` 内含精简/虚拟测试数据用于端到端回归测试）。\n\n"
        f"<!-- facts:start -->\n<!-- facts:end -->\n\n"
        f"## 适用\n\n"
        f"适用于与 [[recipes/{rid}|{meta['title']}]] 相同图型与表格输入结构的科研可视化绘图；"
        f"已将上游 R Markdown 抽离为独立可调用脚本 `code/render.R`，可通过 Studio 或 CLI 传入自定义表格。\n\n"
        f"## 不适用\n\n"
        f"模板脚本仅承接绘图渲染与既定展示统计，不替代上游全流程统计建模前提审查；若数据结构或列名与示例表差异较大，须先整理匹配列结构。\n\n"
        f"## 知识关联检查\n\n"
        f"派生自已过审 L1 配方 [[recipes/{rid}]]，输入表采用模板内联表结构（{table_summary}），"
        f"{'已按 method-map 挂载至分析方法 [[methods/' + item['primary_method'] + ']]。' if item['primary_method'] else '暂归通用辅助可视化模板。'}\n\n"
        f"## 数据要求\n\n"
        f"输入表文件：{table_summary}（详见 `spec.json` 与 `example/` 示例表）。\n\n"
        f"<!-- user:start -->\n<!-- user:end -->\n"
    )
    write_page(tpl_md, tpl_meta, body)

    # 4. Run real R verification with synthetic/example input data
    try:
        inputs = start_replay(tpl_dir)
        render(config, slug, example_dir, verify_dir)
        record_preview(tpl_dir, inputs=inputs, executable=config.rscript_exe)
        facts = template_facts(config, tpl_meta)
        cur_meta, cur_body = read_page(tpl_md)
        write_page(tpl_md, cur_meta, set_block(cur_body, "facts", facts))
        errs = entry_errors(config, tpl_md, replay=True)
        if errs:
            raise RuntimeError("entry_errors: " + "; ".join(errs))
        record_acceptance(config, tpl_md)
        return True, "ok"
    except Exception as exc:
        # Clean up failed partial template so wiki stays 0 ERRORs
        if tpl_md.exists():
            tpl_md.unlink()
        if tpl_dir.exists():
            shutil.rmtree(tpl_dir)
        return False, str(exc).replace("\n", " ")[-450:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEV_ROOT / "skills" / "research-wiki" / "config.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", type=str, default="")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    items = _find_candidates(cfg.wiki_root)
    if args.only:
        wanted = {x.strip() for x in args.only.split(",") if x.strip()}
        items = [it for it in items if it["rid"] in wanted or it["slug"] in wanted]
    if args.limit > 0:
        items = items[: args.limit]

    if not args.apply:
        print(json.dumps({
            "mode": "dry-run",
            "candidate_count": len(items),
            "sample": [(i["rid"], i["slug"], i["primary_method"]) for i in items[:15]],
        }, ensure_ascii=False, indent=2))
        return 0

    passed, failed = [], []
    for idx, it in enumerate(items, 1):
        ok, msg = _convert_one(cfg, it)
        status = "PASS" if ok else "FAIL"
        print(f"[{idx}/{len(items)}] {status} {it['rid']} -> {it['slug']}: {msg}", flush=True)
        if ok:
            passed.append((it["rid"], it["slug"]))
        else:
            failed.append((it["rid"], it["slug"], msg))

    summary_path = cfg.work_root / "fy_convert_summary.json" if cfg.work_root else Path("fy_convert_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps({"passed": passed, "failed": failed}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSUMMARY: passed={len(passed)}, failed={len(failed)}, total={len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

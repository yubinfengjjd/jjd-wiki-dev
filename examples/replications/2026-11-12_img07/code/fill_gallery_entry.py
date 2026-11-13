#!/usr/bin/env python3
"""Populate the local test-gallery entry from one formal run (outputs, data, code, spec, run.log, thumb, meta)."""
import argparse, datetime, glob, json, os, shutil
from PIL import Image
ap = argparse.ArgumentParser()
for k in ("entry", "outroot", "code_dir", "ts"): ap.add_argument("--" + k, required=True)
a = ap.parse_args(); E = a.entry
for f in glob.glob(os.path.join(a.code_dir, "*")):
    if os.path.isfile(f): shutil.copy2(f, os.path.join(E, "code"))
with open(os.path.join(E, "code", "replica.R"), "w") as fh:
    fh.write('#!/usr/bin/env Rscript\n# Gallery entry point: re-plot from ../data (full pipeline: run_all.sh, see METHOD.md v2.2).\n'
             'args <- commandArgs(FALSE); here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", args, value = TRUE)[1])))\n'
             'rc <- system2("Rscript", c(file.path(here, "02_plot_network_go.R"), "--datadir", file.path(here, "..", "data"),\n'
             '                           "--outdir", file.path(here, "..", "output")))\nquit(status = rc)\n')
for f in glob.glob(os.path.join(a.outroot, "data", "*.tsv")): shutil.copy2(f, os.path.join(E, "data"))
for ext in ("png", "pdf", "svg"): shutil.copy2(os.path.join(a.outroot, "output", f"replica.{ext}"), os.path.join(E, "output"))
shutil.copy2(os.path.join(a.outroot, "compare", "side_by_side.png"), os.path.join(E, "compare"))
with open(os.path.join(E, "run.log"), "w") as fh:
    for f in (f"steps_{a.ts}.tsv", f"plot_{a.ts}.log"):
        p = os.path.join(a.outroot, "logs", f)
        if os.path.exists(p): fh.write(f"==> {f}\n" + open(p).read() + "\n")
im = Image.open(os.path.join(a.outroot, "output", "replica.png"))
im.resize((480, round(im.size[1] * 480 / im.size[0])), Image.LANCZOS).save(os.path.join(E, "thumb.png"))
spec = {
  "unit": "whole img07 as one logical panel (network main plot + linked per-module GO bar grid), COS task card #1",
  "version": "v2.2", "run_id": a.ts,
  "source_full_image": {"path": "source/fig07.png", "bbox": [0, 0, 3216, 2160], "icc_profile": "Display P3 (converted to sRGB for palette and metrics)"},
  "canvas_px": [3216, 2160], "dpi": 300, "font": "Liberation Sans",
  "left": {"type": "network", "nodes": "top-60 kME hub genes per module", "edges": "per node top-5 within-module + top-1 between-module real TOM neighbours (union)",
           "layout": "MDS module centres + Kamada-Kawai, within-module edge weight x3, seed 42", "labels": "module:top GO term, same colour, ggrepel with nodes as obstacles"},
  "right": {"type": "faceted horizontal bars", "bars": "top-5 GO terms by raw P, x = -log10(P), shared axis auto-capped"},
  "palette": "code/palette_img07.tsv (1-14: img07 strip colours converted Display P3 -> sRGB; 15-17 added)",
  "data_provenance_note": "real hdWGCNA tutorial data (Zhou 2020 human cortex INH subset); not the original figure's data; nothing estimated or synthesised",
  "estimated_data_csv": "not applicable"}
json.dump(spec, open(os.path.join(E, "data", "figure_spec.json"), "w"), indent=2, ensure_ascii=False)
mp = os.path.join(E, "meta.json"); m = json.load(open(mp))
m["figure"]["panels"] = ["img07 (network + linked GO bar grid, one logical unit)"]
m["files"].update({"replica_png": "output/replica.png", "replica_pdf": "output/replica.pdf", "replica_svg": "output/replica.svg",
                   "compare": "compare/side_by_side.png", "thumb": "thumb.png", "code": "code/replica.R",
                   "spec": "data/figure_spec.json", "qa_report": "qa_report.md", "run_log": "run.log"})
m["status"] = "review"; m["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
json.dump(m, open(mp, "w"), indent=2, ensure_ascii=False)
print("filled", E)

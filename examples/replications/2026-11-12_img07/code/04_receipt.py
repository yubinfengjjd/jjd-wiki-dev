#!/usr/bin/env python3
"""Write runs/<ts>.json: commands, input/output sha256, R/package versions, timings, exit codes, metrics."""
import argparse, csv, glob, hashlib, json, os, platform, subprocess, datetime

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def _net(outroot):
    p = os.path.join(outroot, "data", "hub_edges_tom.tsv")
    if not os.path.exists(p): return None
    rows = list(csv.DictReader(open(p), delimiter="\t"))
    w = [r.get("within_module") == "TRUE" for r in rows]
    nodes = sum(1 for _ in open(os.path.join(outroot, "data", "hub_nodes.tsv"))) - 1
    return dict(n_nodes=nodes, n_edges=len(rows), within_module_edges=sum(w), within_module_fraction=sum(w) / len(rows) if rows else None)
def _qc(outroot):
    p = os.path.join(outroot, "qa", "qa_check_mechanical.md")
    if not os.path.exists(p): return None
    t = open(p, encoding="utf-8").read().splitlines()
    rows = [l for l in t if l.startswith("| ") and (" PASS |" in l or " FAIL |" in l)]
    return dict(pass_=sum(" PASS |" in l for l in rows), fail=[l.split("|")[1].strip() for l in rows if " FAIL |" in l], report="qa/qa_check_mechanical.md")
def _tm(outroot, ts):
    p = os.path.join(outroot, "qa", f"text_measure_{ts}.json")
    return json.load(open(p)) if os.path.exists(p) else None

ap = argparse.ArgumentParser()
for k in ("outroot", "ts", "obj", "tom", "original", "code_dir", "steps", "metrics"): ap.add_argument("--" + k, required=True)
ap.add_argument("--cmdline", default=None, help="exact run_all.sh invocation incl. optional flags such as --v1")
a = ap.parse_args()
steps = []
with open(a.steps) as f:
    for r in csv.DictReader(f, delimiter="\t"):
        steps.append(dict(step=r["step"], command=r["command"], exit_code=int(r["exit_code"]),
                          elapsed_s=round(float(r["end_epoch"]) - float(r["start_epoch"]), 2),
                          log=os.path.relpath(os.path.join(a.outroot, "logs", f"{r['step']}_{a.ts}.log"), a.outroot)))
rver = subprocess.run(["Rscript", "-e", "pk<-c('hdWGCNA','Seurat','SeuratObject','WGCNA','clusterProfiler','org.Hs.eg.db','GO.db','AnnotationDbi','igraph','ggplot2','patchwork','ggrepel','ragg','svglite','dplyr');"
                       "ip<-installed.packages();cat(R.version.string,'\\n');for(p in pk)cat(p,ip[p,'Version'],'\\n');"
                       "cat('GO.db source date', tryCatch(GO.db::GO_dbInfo()[GO.db::GO_dbInfo()$name=='GOSOURCEDATE','value'],error=function(e)'NA'),'\\n');"
                       "cat('org.Hs.eg.db GO source date', tryCatch({x<-org.Hs.eg.db::org.Hs.eg_dbInfo();x[x$name=='GOSOURCEDATE','value']},error=function(e)'NA'),'\\n')"],
                      capture_output=True, text=True)
versions = {}
for line in rver.stdout.strip().splitlines():
    if line.startswith("R version"): versions["R"] = line.strip()
    else:
        parts = line.strip().rsplit(" ", 1)
        if len(parts) == 2: versions[parts[0]] = parts[1]
outs = sorted(set(glob.glob(os.path.join(a.outroot, "data", "*")) + glob.glob(os.path.join(a.outroot, "output", "*")) +
                  glob.glob(os.path.join(a.outroot, "compare", "*")) + [a.metrics] +
                  glob.glob(os.path.join(a.outroot, "qa", f"text_measure_{a.ts}.json"))))
code = sorted(glob.glob(os.path.join(a.code_dir, "*")))
m = json.load(open(a.metrics)) if os.path.exists(a.metrics) else None
rc = dict(
    receipt_version=1, task="Builder task card #1 — img07 hdWGCNA hub network + per-module GO bars (replica v2)", version="v2",
    run_id=a.ts, written_at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    host=dict(platform=platform.platform(), conda_env="rwiki-r", python=platform.python_version()),
    command=a.cmdline or f"bash {os.path.join(a.code_dir, 'run_all.sh')} --obj {a.obj} --tom {a.tom} --outroot {a.outroot}",
    steps=steps, overall_exit_code=max((s["exit_code"] for s in steps), default=None),
    total_elapsed_s=round(sum(s["elapsed_s"] for s in steps), 2),
    inputs={os.path.abspath(p): sha(p) for p in (a.obj, a.tom, a.original)},
    code={os.path.relpath(p, os.path.dirname(a.code_dir)): sha(p) for p in code if os.path.isfile(p)},
    outputs={os.path.relpath(p, a.outroot): dict(sha256=sha(p), bytes=os.path.getsize(p)) for p in outs if os.path.isfile(p)},
    versions=versions,
    acceptance=None if m is None else dict(
        aspect_rel_err=m["aspect"]["rel_err"], aspect_pass=m["aspect"]["pass_"],
        strip_palette_median_dE00=m["strip_palette"]["median"], strip_palette_pass=m["strip_palette"]["pass_"],
        global_palette_median_dE00=m["global_palette"]["median"], global_palette_weighted_median_dE00=m["global_palette"]["weighted_median"],
        global_palette_pass=m["global_palette"]["pass_"], overall_pass=m["overall_pass"],
        bar_fill_median_dE00_supplementary=m.get("bar_fill_supplementary", {}).get("median"),
        colour_management=m.get("colour_management")),
    qa_check=_qc(a.outroot),
    network=_net(a.outroot), text_measure=_tm(a.outroot, a.ts),
    status="review (awaiting QA re-run and jb visual sign-off; not ready, not merged)")
os.makedirs(os.path.join(a.outroot, "runs"), exist_ok=True)
json.dump(rc, open(os.path.join(a.outroot, "runs", f"v2.2_{a.ts}.json"), "w"), indent=1, ensure_ascii=False)
print("ok")

"""Reproduce fixed-corpus retrieval metrics; labels predate engine implementation.
Run with D:/anaconda/python.exe -X utf8 run_benchmark.py --phase before|after.
Before uses entire original finder.py from fixed BASELINE_SHA and request-local read cache;
cache changes reads, never ranking. No dependencies installed or sources altered.
"""
import argparse,json,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEV=next(p for p in HERE.parents if (p / ".git").exists())
SKILL=DEV / "skills/research-wiki"
if not SKILL.exists(): SKILL=DEV / "staged/research-wiki"
BASELINE_SHA="76d4bd7cbc8ad0bb57cf45e4b9fb078866d2d864"
sys.path.insert(0,str(SKILL))
from rwiki.config import load_config
from rwiki.read_cache import read_session
from rwiki import finder
from rwiki.search import search, INDEX_VERSION

def metrics(rows):
    return {"cases":len(rows),"recall_at_3":sum(bool(r["rank"] and r["rank"]<=3) for r in rows)/len(rows),
            "recall_at_5":sum(bool(r["rank"] and r["rank"]<=5) for r in rows)/len(rows),
            "recall_at_10":sum(bool(r["rank"]) for r in rows)/len(rows),
            "mrr_at_10":sum(1/r["rank"] if r["rank"] else 0 for r in rows)/len(rows)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase",choices=("before","after"),required=True)
    args=ap.parse_args()
    cfg=load_config(SKILL / "config.json")
    engine=finder.find
    head=subprocess.check_output(["git","-C",str(DEV),"rev-parse","HEAD"],text=True).strip()
    if args.phase=="before":
        source=subprocess.check_output(["git","-C",str(DEV),"show",BASELINE_SHA+":staged/research-wiki/rwiki/finder.py"],text=True,encoding="utf-8")
        namespace={"__package__":"rwiki", "__name__":"rwiki._benchmark_legacy_finder"}
        exec(compile(source,"legacy-finder-"+BASELINE_SHA,"exec"),namespace)
        engine=namespace["find"]
    rows=[]
    with read_session():
        for case in json.loads((HERE/"queries.json").read_text(encoding="utf-8"))["cases"]:
            started=time.perf_counter()
            hits=(engine(cfg,case["query"],kind=case["kind"],limit=10) if args.phase=="before" else
                  search(cfg,case["query"],kind=case["kind"],limit=10)["results"])
            ids=[r["id"] for r in hits]
            rank=next((i+1 for i,x in enumerate(ids) if x in case["expected_ids"]),None)
            rows.append({**case,"ids":ids,"rank":rank,"duration_ms":round((time.perf_counter()-started)*1000,2)})
            print(len(rows),rank,case["query"],flush=True)
    result={"engine":"legacy finder" if args.phase=="before" else f"section BM25 index v{INDEX_VERSION}","baseline_head":BASELINE_SHA,"current_head":head,
            "metrics":metrics(rows),"by_category":{c:metrics([r for r in rows if r["category"]==c]) for c in {r["category"] for r in rows}},"cases":rows}
    (HERE/(args.phase+".json")).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result["metrics"]))
if __name__=="__main__": main()

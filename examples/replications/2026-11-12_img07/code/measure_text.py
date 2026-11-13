#!/usr/bin/env python3
"""Measure text-line pixel heights in facet bar rows and strips (same method on any image).
For each detected strip (03_qa_metrics.detect_strips): region below it down to the next strip; rows with
>= min_px dark pixels (lum<110) form text-line runs; report run heights (ascender..descender extent incl.
parentheses). Heights are bimodal (lines whose '(GO:..)' falls inside the measured left 55% are taller), so
p10 (no-parenthesis lines) and p90 (parenthesis lines) are compared as well as the median. Strip text: pixels with dE76 > 40 from strip colour inside the strip box."""
import argparse, json, importlib.util, os
import numpy as np
spec = importlib.util.spec_from_file_location("q", os.path.join(os.path.dirname(__file__), "03_qa_metrics.py"))
q = importlib.util.module_from_spec(spec); spec.loader.exec_module(q)
def runs(mask_rows, min_len=4):
    out, s = [], None
    for i, v in enumerate(mask_rows):
        if v and s is None: s = i
        if not v and s is not None:
            if i - s >= min_len: out.append((s, i))
            s = None
    return out
def measure(path):
    rgb = q.load_rgb(path); h, w, _ = rgb.shape; st = q.detect_strips(rgb)
    bar_h, strip_h = [], []
    for s in st:
        nxt = [t["y"] for t in st if t["y"] > s["y"] + s["h"] + 5]
        y1 = min(nxt) - 4 if nxt else min(h, s["y"] + int(0.13 * h))
        reg = rgb[s["y"] + s["h"] + 3:y1, s["x"] + 2:s["x"] + int(s["w"] * 0.55)]
        dark = reg.mean(2) < 110
        rr = runs(dark.sum(1) >= 3)
        bar_h += [b - a for a, b in rr if (b - a) < 0.03 * h]
        box = rgb[s["y"] + 2:s["y"] + s["h"] - 2, s["x"] + 4:s["x"] + s["w"] - 4]
        d = np.sqrt(((box - np.array(s["rgb"])) ** 2).sum(2)) > 60
        r2 = runs(d.sum(1) >= 2, 3)
        if r2: strip_h.append(max(b - a for a, b in r2))
    return dict(path=path, h=h, n_strips=len(st), bar_text_px_median=float(np.median(bar_h)) if bar_h else None,
                bar_text_rel=float(np.median(bar_h)) / h if bar_h else None, n_bar_lines=len(bar_h),
                bar_text_px_p90=float(np.percentile(bar_h, 90)) if bar_h else None,
                bar_text_px_p10=float(np.percentile(bar_h, 10)) if bar_h else None,
                strip_text_px_median=float(np.median(strip_h)) if strip_h else None,
                strip_text_rel=float(np.median(strip_h)) / h if strip_h else None)
ap = argparse.ArgumentParser(); ap.add_argument("images", nargs="+"); ap.add_argument("--out")
a = ap.parse_args(); res = [measure(p) for p in a.images]
print(json.dumps(res, indent=1))
if a.out: json.dump(res, open(a.out, "w"), indent=1)

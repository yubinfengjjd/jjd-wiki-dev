#!/usr/bin/env python3
"""img07 replica QA metrics (aspect ratio + CIEDE2000). Pure numpy/scipy/Pillow.

v2.2: images with an embedded ICC profile are converted to sRGB first (see to_srgb); --no_icc reproduces v1/v2.
Metrics (declared before rendering; thresholds from task card #1: aspect <=2%, median dE00 <=10):
  aspect_rel_err = |(rw/rh)/(ow/oh) - 1|   (same formula as skill qa_check.py)
  A. strip palette dE00: detect facet strip boxes (uniform colour bands, >=12% of image width, 15-80 px tall,
     in the right 40% of the image, with a dark box border at/just outside the top and bottom edges) on BOTH images with the same detector, order row-major, pair slot k
     with slot k (k = 1..min(n_orig, n_rep)); colour = median RGB of the strip interior; report median dE00.
  B. global data-colour palette dE00: drop near-white background pixels (L*>93 and C*<6), k-means (k=16,
     fixed seed) in CIELAB on each image; for each ORIGINAL cluster centre take dE00 to the nearest replica
     centre; report the unweighted median and the pixel-share-weighted median.
  C. (supplementary, not part of PASS) bar-fill dE00: below each detected strip, the modal uniform
     non-white colour = that facet's bar fill. Original facets are in alphabetical order of their labels
     (M1, M10, M11, M12, M13, M14, M2, ..., M9; read from the strip labels) -> --original_facet_order;
     replica facets are M1..Mn. Pair by module number.
  PASS requires aspect <= 0.02 AND median(A) <= 10 AND median(B, unweighted) <= 10.
"""
import argparse, json, sys
import numpy as np
from PIL import Image
from scipy import ndimage

ICC_MODE = {"convert": True, "log": {}}

def to_srgb(im, path):
    """v2.2: if the PNG embeds an ICC profile (img07 = Display P3), convert pixels to sRGB with LittleCMS
    (Pillow ImageCms, relative colorimetric) before any colour math. Replica PNGs carry no profile = sRGB."""
    icc = im.info.get("icc_profile")
    if not icc or not ICC_MODE["convert"]:
        ICC_MODE["log"][path] = "no ICC profile (treated as sRGB)" if not icc else "ICC present but conversion disabled (--no_icc)"
        return im
    from PIL import ImageCms
    import io
    src = ImageCms.ImageCmsProfile(io.BytesIO(icc)); desc = ImageCms.getProfileDescription(src).strip()
    a = im.getchannel("A") if im.mode == "RGBA" else None
    rgb = ImageCms.profileToProfile(im.convert("RGB"), src, ImageCms.createProfile("sRGB"),
                                    renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC, outputMode="RGB")
    if a is not None: rgb.putalpha(a)
    ICC_MODE["log"][path] = f"{desc} -> sRGB (LittleCMS, relative colorimetric)"
    return rgb

def load_rgb(p, max_side=None):
    im = to_srgb(Image.open(p), p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
    im = bg.convert("RGB")
    if max_side and max(im.size) > max_side:
        s = max_side / max(im.size); im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.LANCZOS)
    return np.asarray(im).astype(float)

def rgb2lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

def de2000(l1, l2):
    L1, a1, b1 = np.moveaxis(np.asarray(l1, float), -1, 0); L2, a2, b2 = np.moveaxis(np.asarray(l2, float), -1, 0)
    C1 = np.hypot(a1, b1); C2 = np.hypot(a2, b2); Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360; h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1; dCp = C2p - C1p
    dh = h2p - h1p; dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)); dh = np.where(C1p * C2p == 0, 0, dh)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp = (L1 + L2) / 2; Cbp = (C1p + C2p) / 2
    hs = h1p + h2p
    hbp = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63))
    dtheta = 30 * np.exp(-(((hbp - 275) / 25) ** 2)); Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2); Sc = 1 + 0.045 * Cbp; Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))

def selftest():
    # Sharma et al. 2005 reference pairs
    pairs = [((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425), ((50, -1.3802, -84.2814), (50, 0, -82.7485), 1.0000),
             ((50, 2.5, 0), (73, 25, -18), 27.1492), ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082)]
    for a, b, ref in pairs:
        assert abs(de2000(a, b) - ref) < 1e-3, (a, b, de2000(a, b), ref)

def detect_strips(rgb):
    h, w, _ = rgb.shape
    x0 = int(w * 0.60); reg = rgb[:, x0:]
    sat = reg.max(2) - reg.min(2)
    # uniform coloured pixels: saturated or dark-but-coloured, and horizontally uniform with neighbours
    dx = np.abs(np.diff(reg, axis=1)).sum(2); dx = np.pad(dx, ((0, 0), (0, 1)))
    mask = (sat > 25) & (dx < 6)
    mask = ndimage.binary_opening(mask, structure=np.ones((3, 9)))
    lab, n = ndimage.label(mask)
    out = []
    for sl in ndimage.find_objects(lab):
        hh = sl[0].stop - sl[0].start; ww = sl[1].stop - sl[1].start
        if ww >= 0.12 * w and 0.006 * h <= hh <= 0.04 * h:  # v2.2: 0.06 -> 0.12 (a 0.065w bar was taken as a strip after ICC conversion)
            # facet strips are boxed: a dark border row within 4 px above AND below (bars sit on white)
            ys, xs_ = sl[0], slice(sl[1].start + 3, sl[1].stop - 3)
            lum = reg[..., :].mean(2)
            # windows straddle the component edge because an antialiased dark-coloured border can join the component
            above = lum[max(ys.start - 4, 0):ys.start + 3, xs_].mean(1).min()
            below = lum[ys.stop - 3:min(ys.stop + 4, h), xs_].mean(1).min()
            if not (above < 150 and below < 150):
                continue
            blk = reg[sl]
            m = mask[sl]
            col = np.median(blk[m], 0)
            out.append(dict(y=int(sl[0].start), x=int(sl[1].start + x0), w=int(ww), h=int(hh), rgb=[int(round(c)) for c in col]))
    # merge fragments of the same strip (text splits a strip into left/right pieces)
    out.sort(key=lambda d: (d["y"], d["x"]))
    merged = []
    for d in out:
        for m in merged:
            if abs(m["y"] - d["y"]) <= 0.01 * h and abs(m["x"] - d["x"]) < 0.17 * w and de2000(rgb2lab(np.array(m["rgb"], float)), rgb2lab(np.array(d["rgb"], float))) < 3:
                break
        else:
            merged.append(d)
    # row-major order: group by row (y within 1% of height), then x
    rows = []
    for d in sorted(merged, key=lambda d: d["y"]):
        if rows and abs(rows[-1][0]["y"] - d["y"]) <= 0.01 * h: rows[-1].append(d)
        else: rows.append([d])
    return [d for r in rows for d in sorted(r, key=lambda d: d["x"])]

def bar_fills(rgb, strips):
    h, w, _ = rgb.shape
    out = []
    for i, st in enumerate(strips):
        nxt = [t["y"] for t in strips if t["y"] > st["y"] + st["h"] + 5]
        y1 = min(nxt) - 3 if nxt else min(h, st["y"] + int(0.13 * h))
        reg = rgb[st["y"] + st["h"] + 4:y1, st["x"] + 4:st["x"] + st["w"] - 4]
        sat = reg.max(2) - reg.min(2); dx = np.abs(np.diff(reg, axis=1)).sum(2); dx = np.pad(dx, ((0, 0), (0, 1)))
        m = (sat > 12) & (dx < 4) & (reg.min(2) < 250)
        px = reg[m]
        if len(px) == 0: out.append(None); continue
        q = (px // 4).astype(int); keys = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
        vals, cnt = np.unique(keys, return_counts=True); top = vals[cnt.argmax()]
        out.append([int(round(c)) for c in np.median(px[keys == top], 0)])
    return out

def kmeans_lab(lab, k=16, seed=0, iters=30):
    rng = np.random.default_rng(seed)
    X = lab.reshape(-1, 3)
    if len(X) > 200000: X = X[rng.choice(len(X), 200000, replace=False)]
    C = X[rng.choice(len(X), k, replace=False)]
    for _ in range(iters):
        d = ((X[:, None, :] - C[None]) ** 2).sum(2); a = d.argmin(1)
        C = np.array([X[a == j].mean(0) if np.any(a == j) else C[j] for j in range(k)])
    share = np.bincount(a, minlength=k) / len(a)
    return C, share

def wmedian(v, w):
    o = np.argsort(v); v, w = v[o], w[o]; c = np.cumsum(w) / w.sum(); return float(v[np.searchsorted(c, 0.5)])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--original", required=True); ap.add_argument("--replica", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--k", type=int, default=16)
    ap.add_argument("--no_icc", action="store_true", help="v2 behaviour: ignore embedded ICC profiles")
    ap.add_argument("--original_facet_order", default="1,10,11,12,13,14,2,3,4,5,6,7,8,9")
    a = ap.parse_args()
    selftest()
    ICC_MODE["convert"] = not a.no_icc
    o = load_rgb(a.original); r = load_rgb(a.replica)
    oh, ow = o.shape[:2]; rh, rw = r.shape[:2]
    aspect = abs((rw / rh) / (ow / oh) - 1)
    so, sr = detect_strips(o), detect_strips(r)
    n = min(len(so), len(sr))
    deA = [float(de2000(rgb2lab(np.array(so[i]["rgb"], float)), rgb2lab(np.array(sr[i]["rgb"], float)))) for i in range(n)]
    bo, br = bar_fills(o, so), bar_fills(r, sr)
    order = [int(x) for x in a.original_facet_order.split(",")]
    deC = {}
    for slot, mod in enumerate(order[:len(bo)]):
        if mod - 1 < len(br) and bo[slot] is not None and br[mod - 1] is not None:
            deC[f"M{mod}"] = dict(original=bo[slot], replica=br[mod - 1],
                                  dE00=float(de2000(rgb2lab(np.array(bo[slot], float)), rgb2lab(np.array(br[mod - 1], float)))))
    # global palette on 1200-px downsample
    ol = rgb2lab(load_rgb(a.original, 1200)); rl = rgb2lab(load_rgb(a.replica, 1200))
    def fg(l):
        X = l.reshape(-1, 3); C = np.hypot(X[:, 1], X[:, 2]); return X[~((X[:, 0] > 93) & (C < 6))]
    Co, wo = kmeans_lab(fg(ol), a.k); Cr, wr = kmeans_lab(fg(rl), a.k)
    dmat = de2000(Co[:, None, :], Cr[None, :, :]); nearest = dmat.min(1)
    res = dict(
        original=dict(path=a.original, w=ow, h=oh), replica=dict(path=a.replica, w=rw, h=rh),
        aspect=dict(original=ow / oh, replica=rw / rh, rel_err=aspect, threshold=0.02, pass_=bool(aspect <= 0.02)),
        strip_palette=dict(n_original=len(so), n_replica=len(sr), n_paired=n, dE00=deA,
                           median=float(np.median(deA)) if deA else None, max=float(max(deA)) if deA else None,
                           original_strips=so, replica_strips=sr, threshold=10,
                           pass_=bool(deA and np.median(deA) <= 10)),
        global_palette=dict(k=a.k, nearest_dE00=[float(x) for x in nearest], original_share=[float(x) for x in wo],
                            median=float(np.median(nearest)), weighted_median=wmedian(nearest, wo), threshold=10,
                            pass_=bool(np.median(nearest) <= 10)),
        bar_fill_supplementary=dict(per_module=deC, median=float(np.median([v["dE00"] for v in deC.values()])) if deC else None,
                                    note="supplementary; not part of PASS rule"),
        colour_management=ICC_MODE["log"],
        de2000_selftest="Sharma 2005 reference pairs OK")
    res["overall_pass"] = bool(res["aspect"]["pass_"] and res["strip_palette"]["pass_"] and res["global_palette"]["pass_"])
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps({k: (v if k == "overall_pass" else {kk: vv for kk, vv in v.items() if kk in ("rel_err", "median", "weighted_median", "max", "n_original", "n_replica", "pass_")}) for k, v in res.items() if isinstance(v, (dict, bool)) and k not in ("original", "replica")}, indent=1))

if __name__ == "__main__":
    main()

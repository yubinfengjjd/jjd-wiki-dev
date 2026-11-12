#!/usr/bin/env python3
"""Original / v1 / v2 side by side, equal height, white gaps, labels. Pure Pillow; never a visual verdict."""
import argparse
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument("--images", nargs="+", required=True); ap.add_argument("--labels", nargs="+", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--height", type=int, default=1080)
a = ap.parse_args()
ims = []
for p in a.images:
    im = Image.open(p).convert("RGBA"); bg = Image.new("RGBA", im.size, "white"); bg.alpha_composite(im); im = bg.convert("RGB")
    ims.append(im.resize((round(im.size[0] * a.height / im.size[1]), a.height), Image.LANCZOS))
gap, top = 24, 48
W = sum(i.size[0] for i in ims) + gap * (len(ims) + 1); H = a.height + top + gap
out = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(out)
try: font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 30)
except Exception: font = ImageFont.load_default()
x = gap
for im, lab in zip(ims, a.labels):
    out.paste(im, (x, top)); d.text((x, 8), lab, fill="black", font=font); x += im.size[0] + gap
out.save(a.out)
print("wrote", a.out, out.size)

#!/usr/bin/env python3
"""Write an sRGB copy of an image whose PNG embeds an ICC profile (img07: Display P3), for display/compare only.
The original file is never modified. Pillow ImageCms (LittleCMS), relative colorimetric."""
import argparse, io
from PIL import Image, ImageCms
ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
im = Image.open(a.inp); icc = im.info.get("icc_profile")
if not icc:
    im.save(a.out); print("no ICC profile; copied"); raise SystemExit
src = ImageCms.ImageCmsProfile(io.BytesIO(icc)); alpha = im.getchannel("A") if im.mode == "RGBA" else None
out = ImageCms.profileToProfile(im.convert("RGB"), src, ImageCms.createProfile("sRGB"),
                                renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC, outputMode="RGB")
if alpha is not None: out.putalpha(alpha)
out.save(a.out)
print(ImageCms.getProfileDescription(src).strip(), "-> sRGB:", a.out)

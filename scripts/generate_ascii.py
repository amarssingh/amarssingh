#!/usr/bin/env python3
"""Portrait -> ASCII art (assets/generated/ascii.txt).

Steps: crop -> estimate background from the corners -> mask it out ->
contrast boost -> map luminance to a character ramp.
Run manually only when the portrait or its settings change.
"""
import json, pathlib, sys
import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "config/profile.json").read_text())["ascii"]
RAMP = cfg.get("ramp", " .:-=+*#%@")

img = Image.open(ROOT / cfg["source"]).convert("RGB")
W, H = img.size
l, t, r, b = cfg["crop"]
img = img.crop((int(l*W), int(t*H), int(r*W), int(b*H)))

cols = cfg["cols"]
rows = round(cols * img.height / img.width * cfg["char_aspect"])
small = img.resize((cols*2, rows*2), Image.LANCZOS)
arr = np.asarray(small).astype(float)

patch = np.concatenate([arr[:6, :6].reshape(-1, 3), arr[:6, -6:].reshape(-1, 3)])
bg = np.median(patch, axis=0)
dist = np.sqrt(((arr - bg) ** 2).sum(axis=2))
mask = Image.fromarray((dist > cfg["bg_threshold"]).astype(np.uint8) * 255)
mask = mask.filter(ImageFilter.MedianFilter(5)).resize((cols, rows), Image.BILINEAR)
mask = np.asarray(mask) > 127

gray = ImageOps.grayscale(small.resize((cols, rows), Image.LANCZOS))
a = np.asarray(gray).astype(float)
# 1) global: rank-normalise luminance over the subject only (ignores background)
vals = np.sort(a[mask])
if cfg.get("tone") == "linear" and len(vals):   # keeps skin mid-tone -> features stay visible
    lo, hi = np.percentile(vals, 2), np.percentile(vals, 99.5)
    base = np.clip((a - lo) / (hi - lo + 1e-6), 0, 1)
else:
    base = np.interp(a, vals, np.linspace(0, 1, len(vals))) if len(vals) else a / 255
# 2) local: difference from a blurred copy brings out eyes, brows, nose, beard edges
blur = np.asarray(gray.filter(ImageFilter.GaussianBlur(cfg.get("local_radius", 2.5)))).astype(float)
local = np.clip(0.5 + (a - blur) / 255 * cfg.get("local_gain", 6), 0, 1)
g = (1 - cfg.get("local_mix", 0.45)) * base + cfg.get("local_mix", 0.45) * local
g = np.clip(g, 0, 1) ** cfg["gamma"]
g = cfg["floor"] + (1 - cfg["floor"]) * g

lines = []
for y in range(rows):
    lines.append("".join(RAMP[int(g[y, x] * (len(RAMP) - 1))] if mask[y, x] else " " for x in range(cols)).rstrip())
out = ROOT / "assets/generated/ascii.txt"
out.write_text("\n".join(lines) + "\n")
print(f"wrote {out} ({cols}x{rows})")
if "--preview" in sys.argv:
    print("\n".join(lines))

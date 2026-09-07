#!/usr/bin/env python3
"""Build mobile JPEG derivative of county hillshade + update bounds metadata."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "lidar" / "web"
src = WEB / "county-hillshade.png"
im = Image.open(src)
print("src", im.size, im.mode, src.stat().st_size)
max_dim = 1600
w, h = im.size
scale = min(1.0, max_dim / max(w, h))
nw, nh = int(round(w * scale)), int(round(h * scale))
im2 = im.resize((nw, nh), Image.Resampling.LANCZOS)
bg = Image.new("RGB", im2.size, (13, 12, 10))  # match county outside-mask; alpha→dark not olive holes
bg.paste(im2, mask=im2.split()[3] if im2.mode == "RGBA" else None)
out_jpg = WEB / "county-hillshade.jpg"
bg.save(out_jpg, "JPEG", quality=78, optimize=True, progressive=True)
print("jpg", nw, nh, out_jpg.stat().st_size, round(out_jpg.stat().st_size / 1024 / 1024, 3), "MB")

bounds_path = WEB / "county-bounds.json"
if bounds_path.is_file():
    meta = json.loads(bounds_path.read_text(encoding="utf-8"))
    meta["web_asset"] = "county-hillshade.jpg"
    meta["web_pixels"] = [nw, nh]
    meta["web_mb"] = round(out_jpg.stat().st_size / 1024 / 1024, 3)
    meta["web_note"] = "Mobile JPEG derivative (max dim 1600, q78); full PNG retained"
    bounds_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("updated", bounds_path)
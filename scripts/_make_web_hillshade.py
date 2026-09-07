#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
ROOT = Path("/workspace/wiltshire-long-barrows")
WEB = ROOT / "lidar" / "web"
src = WEB / "county-hillshade.png"
im = Image.open(src)
print("src", im.size, im.mode, src.stat().st_size)
max_dim = 1600
w, h = im.size
scale = min(1.0, max_dim / max(w, h))
nw, nh = int(round(w * scale)), int(round(h * scale))
im2 = im.resize((nw, nh), Image.Resampling.LANCZOS)
bg = Image.new("RGB", im2.size, (13, 12, 10))
bg.paste(im2, mask=im2.split()[3] if im2.mode == "RGBA" else None)
out_jpg = WEB / "county-hillshade.jpg"
bg.save(out_jpg, "JPEG", quality=78, optimize=True, progressive=True)
print("jpg", nw, nh, out_jpg.stat().st_size, round(out_jpg.stat().st_size / 1024 / 1024, 3), "MB")

#!/usr/bin/env python3
"""Download EA LIDAR Composite DTM via WCS in strips; merge to GeoTIFF.

Default bbox: Stonehenge / Salisbury Plain long-barrow cluster from gazetteer
extent for that cluster + margin (first manageable chalk tile). Override with
env WILTS_LB_BBOX=e0,e1,n0,n1 (OSGB metres).
"""
from __future__ import annotations

import json
import math
import os
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.merge import merge

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT_DIR = ROOT / "lidar" / "ea1m"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WCS = "https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs"
COVERAGE = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"
UA = {"User-Agent": "wiltshire-long-barrows/1.0 (sarsen.org research)"}
PAD_M = 800.0


def cluster_bbox(cluster_substr: str = "Stonehenge") -> tuple[float, float, float, float]:
    rows = json.loads((DATA / "long_barrows.json").read_text(encoding="utf-8"))
    pts = [
        (float(r["easting"]), float(r["northing"]))
        for r in rows
        if cluster_substr.lower() in (r.get("cluster") or "").lower()
    ]
    if not pts:
        # fallback: dense chalk core
        return 409000.0, 416000.0, 140000.0, 146000.0
    es = [p[0] for p in pts]
    ns = [p[1] for p in pts]
    return min(es) - PAD_M, max(es) + PAD_M, min(ns) - PAD_M, max(ns) + PAD_M


def fetch_strip(e0, e1, n0, n1, out: Path, scalefactor: float | None = 0.5) -> Path:
    e0, e1 = int(math.floor(e0)), int(math.ceil(e1))
    n0, n1 = int(math.floor(n0)), int(math.ceil(n1))
    params = [
        ("SERVICE", "WCS"),
        ("VERSION", "2.0.1"),
        ("REQUEST", "GetCoverage"),
        ("COVERAGEID", COVERAGE),
        ("SUBSET", f"E({e0},{e1})"),
        ("SUBSET", f"N({n0},{n1})"),
        ("FORMAT", "image/tiff"),
        ("SUBSETTINGCRS", "http://www.opengis.net/def/crs/EPSG/0/27700"),
        ("OUTPUTCRS", "http://www.opengis.net/def/crs/EPSG/0/27700"),
    ]
    if scalefactor is not None:
        params.append(("SCALEFACTOR", str(scalefactor)))
    url = WCS + "?" + urllib.parse.urlencode(params)
    print(f"GET E{e0}-{e1} N{n0}-{n1} scale={scalefactor}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    print(f"  {len(data)/1e6:.2f} MB  {ctype}")
    if b"<?xml" in data[:80] or b"Exception" in data[:400]:
        out.with_suffix(".error.xml").write_bytes(data[:80000])
        raise SystemExit(f"XML error → {out.with_suffix('.error.xml')}")
    out.write_bytes(data)
    with rasterio.open(out) as ds:
        from rasterio.windows import Window
        w = min(64, ds.width)
        h = min(64, ds.height)
        arr = ds.read(1, window=Window(ds.width - w, ds.height - h, w, h))
        print(f"  ok {ds.width}x{ds.height} res={ds.res} last-block mean={float(np.mean(arr)):.2f}")
    return out


def main() -> None:
    env = os.environ.get("WILTS_LB_BBOX")
    if env:
        parts = [float(x) for x in env.split(",")]
        e0, e1, n0, n1 = parts
    else:
        e0, e1, n0, n1 = cluster_bbox("Stonehenge")
        # Cap first download to ~8 km E × ~7 km N if cluster is huge
        if (e1 - e0) > 9000:
            mid = (e0 + e1) / 2
            e0, e1 = mid - 4500, mid + 4500
        if (n1 - n0) > 8000:
            mid = (n0 + n1) / 2
            n0, n1 = mid - 4000, mid + 4000
    print(f"target E {e0:.0f}–{e1:.0f} N {n0:.0f}–{n1:.0f}")

    strips_dir = OUT_DIR / "strips"
    strips_dir.mkdir(exist_ok=True)
    strip_w = 2200.0
    paths = []
    e = e0
    idx = 0
    while e < e1:
        ee = min(e + strip_w, e1)
        out = strips_dir / f"strip_{idx:02d}.tif"
        if out.is_file() and out.stat().st_size > 500_000:
            try:
                with rasterio.open(out) as ds:
                    from rasterio.windows import Window
                    ds.read(1, window=Window(ds.width - 32, ds.height - 32, 32, 32))
                print("reuse", out)
                paths.append(out)
                e = ee
                idx += 1
                continue
            except Exception:
                print("bad cache", out, "— redownloading")
        fetch_strip(e, ee, n0, n1, out, scalefactor=0.5)
        paths.append(out)
        e = ee
        idx += 1

    print("merging", len(paths), "strips…")
    srcs = [rasterio.open(p) for p in paths]
    try:
        mosaic, transform = merge(srcs, nodata=np.nan)
        meta = srcs[0].meta.copy()
    finally:
        for s in srcs:
            s.close()
    meta.update(
        {
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": transform,
            "compress": "lzw",
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
            "nodata": -9999.0,
        }
    )
    grid = mosaic[0].astype(np.float32)
    grid[~np.isfinite(grid)] = -9999.0
    grid[grid < -1000] = -9999.0
    out = OUT_DIR / "wiltshire_lb_dtm.tif"
    with rasterio.open(out, "w", **meta) as dst:
        dst.write(grid, 1)
    print("wrote", out, f"{out.stat().st_size/1e6:.1f} MB", grid.shape)
    with rasterio.open(out) as ds:
        print("bounds", ds.bounds, "res", ds.res)


if __name__ == "__main__":
    main()

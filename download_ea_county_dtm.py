#!/usr/bin/env python3
"""Download county-wide EA LIDAR Composite DTM via WCS (heavily downsampled).

Default OSGB bbox covers all gazetteer barrows (E378k–430k N119k–187k) + margin.
SCALEFACTOR 0.05 → ~20 m cells so a full-county mosaic stays manageable.
Override with WILTS_COUNTY_BBOX=e0,e1,n0,n1.
"""
from __future__ import annotations

import math
import os
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "lidar" / "county"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WCS = "https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs"
COVERAGE = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"
UA = {"User-Agent": "wiltshire-long-barrows/1.0 (sarsen.org research)"}

# Gazetteer envelope + ~2 km margin (task: E378000–430000 N119000–187000 + margin)
DEFAULT_BBOX = (376000.0, 432000.0, 117000.0, 189000.0)
SCALEFACTOR = 0.05  # 1 m × 0.05 → ~20 m
STRIP_W_M = 14000.0  # wide strips OK at 20 m


def fetch_strip(e0, e1, n0, n1, out: Path, scalefactor: float) -> Path:
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
        ("SCALEFACTOR", str(scalefactor)),
    ]
    url = WCS + "?" + urllib.parse.urlencode(params)
    print(f"GET E{e0}-{e1} N{n0}-{n1} scale={scalefactor}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=900) as resp:
        data = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    print(f"  {len(data)/1e6:.2f} MB  {ctype}")
    if b"<?xml" in data[:80] or b"Exception" in data[:400]:
        err = out.with_suffix(".error.xml")
        err.write_bytes(data[:80000])
        raise SystemExit(f"XML error → {err}")
    out.write_bytes(data)
    with rasterio.open(out) as ds:
        w = min(64, ds.width)
        h = min(64, ds.height)
        arr = ds.read(1, window=Window(ds.width - w, ds.height - h, w, h))
        print(f"  ok {ds.width}x{ds.height} res={ds.res} last-block mean={float(np.mean(arr)):.2f}")
    return out


def main() -> None:
    env = os.environ.get("WILTS_COUNTY_BBOX")
    if env:
        e0, e1, n0, n1 = [float(x) for x in env.split(",")]
    else:
        e0, e1, n0, n1 = DEFAULT_BBOX
    print(f"county target E {e0:.0f}–{e1:.0f} N {n0:.0f}–{n1:.0f}  SCALEFACTOR={SCALEFACTOR}")

    strips_dir = OUT_DIR / "strips"
    strips_dir.mkdir(exist_ok=True)
    paths: list[Path] = []
    e = e0
    idx = 0
    while e < e1:
        ee = min(e + STRIP_W_M, e1)
        out = strips_dir / f"strip_{idx:02d}.tif"
        if out.is_file() and out.stat().st_size > 50_000:
            try:
                with rasterio.open(out) as ds:
                    ds.read(1, window=Window(ds.width - 32, ds.height - 32, 32, 32))
                print("reuse", out)
                paths.append(out)
                e = ee
                idx += 1
                continue
            except Exception:
                print("bad cache", out, "— redownloading")
        fetch_strip(e, ee, n0, n1, out, SCALEFACTOR)
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
    out = OUT_DIR / "wiltshire_county_dtm.tif"
    with rasterio.open(out, "w", **meta) as dst:
        dst.write(grid, 1)
    print("wrote", out, f"{out.stat().st_size/1e6:.1f} MB", grid.shape)
    with rasterio.open(out) as ds:
        print("bounds", ds.bounds, "res", ds.res)


if __name__ == "__main__":
    main()

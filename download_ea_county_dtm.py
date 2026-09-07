#!/usr/bin/env python3
"""Download county-wide EA LIDAR Composite DTM via WCS (heavily downsampled).

Default OSGB bbox covers ceremonial Wiltshire outline (geojson) + ~2 km margin.
SCALEFACTOR 0.05 → ~20 m cells so a full-county mosaic stays manageable.
Override with WILTS_COUNTY_BBOX=e0,e1,n0,n1.

IMPORTANT: full-height easting strips make EA WCS return large rectangular nodata
holes in the north (probe: same E window with northern-only N returns 0% nodata).
Tile in BOTH easting and northing with overlap; merge prefers valid data; then
fill ANY residual interior nodata so the web JPEG has continuous terrain.
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

# Ceremonial Wiltshire outline OSGB ~E374.5–435.9k N116.2–200.5k + ~2 km margin
DEFAULT_BBOX = (372000.0, 438000.0, 114000.0, 203000.0)
SCALEFACTOR = 0.05  # 1 m × 0.05 → ~20 m
STRIP_W_M = 14000.0
STRIP_H_M = 36000.0  # northing band height — keep WCS payloads modest
STRIP_OVERLAP_M = 3000.0  # easting + northing overlap between tiles
NODATA = -9999.0


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
        a = ds.read(1)
        nd = ds.nodata
        bad = ~np.isfinite(a) | (a < -1000)
        if nd is not None:
            bad |= a == nd
        print(
            f"  ok {ds.width}x{ds.height} res={ds.res} "
            f"nodata%={100.0 * bad.mean():.1f} last-block mean={float(np.mean(arr)):.2f}"
        )
    return out


def main() -> None:
    env = os.environ.get("WILTS_COUNTY_BBOX")
    if env:
        e0, e1, n0, n1 = [float(x) for x in env.split(",")]
    else:
        e0, e1, n0, n1 = DEFAULT_BBOX
    print(
        f"county target E {e0:.0f}–{e1:.0f} N {n0:.0f}–{n1:.0f}  "
        f"SCALEFACTOR={SCALEFACTOR}  tile {STRIP_W_M:.0f}×{STRIP_H_M:.0f}  "
        f"overlap={STRIP_OVERLAP_M:.0f} m"
    )

    strips_dir = OUT_DIR / "strips"
    strips_dir.mkdir(exist_ok=True)
    # Drop obsolete full-height strip caches (ov1000 / ov2000 single-band)
    for old in strips_dir.glob("strip_*.tif"):
        if not old.name.startswith("strip_t2_"):
            print("remove obsolete strip", old.name)
            old.unlink(missing_ok=True)

    paths: list[Path] = []
    ov = int(STRIP_OVERLAP_M)
    step_e = STRIP_W_M - STRIP_OVERLAP_M
    step_n = STRIP_H_M - STRIP_OVERLAP_M
    if step_e <= 0 or step_n <= 0:
        raise SystemExit("STRIP_OVERLAP_M must be < strip W/H")

    iy = 0
    n = n0
    while n < n1:
        nn = min(n + STRIP_H_M, n1)
        ix = 0
        e = e0
        while e < e1:
            ee = min(e + STRIP_W_M, e1)
            out = strips_dir / f"strip_t2_ov{ov}_{iy:02d}_{ix:02d}.tif"
            if out.is_file() and out.stat().st_size > 50_000:
                try:
                    with rasterio.open(out) as ds:
                        ds.read(1, window=Window(ds.width - 32, ds.height - 32, 32, 32))
                    print("reuse", out.name)
                    paths.append(out)
                except Exception:
                    print("bad cache", out.name, "— redownloading")
                    fetch_strip(e, ee, n, nn, out, SCALEFACTOR)
                    paths.append(out)
            else:
                fetch_strip(e, ee, n, nn, out, SCALEFACTOR)
                paths.append(out)
            if ee >= e1:
                break
            e = e + step_e
            ix += 1
        if nn >= n1:
            break
        n = n + step_n
        iy += 1

    print("merging", len(paths), "tiles (normalize EA float-min nodata → -9999, method=first)…")
    norm_dir = strips_dir / "_norm"
    norm_dir.mkdir(exist_ok=True)
    # clear old norms
    for old in norm_dir.glob("*.tif"):
        old.unlink(missing_ok=True)
    norm_paths: list[Path] = []
    for src_path in paths:
        with rasterio.open(src_path) as s:
            a = s.read(1).astype(np.float32)
            nd = s.nodata
            bad = ~np.isfinite(a) | (a < -1000)
            if nd is not None:
                bad |= a == nd
            a[bad] = NODATA
            meta_s = s.meta.copy()
            meta_s.update(dtype="float32", nodata=NODATA, compress="lzw")
            outp = norm_dir / src_path.name
            with rasterio.open(outp, "w", **meta_s) as dst:
                dst.write(a, 1)
            norm_paths.append(outp)

    srcs = [rasterio.open(p) for p in norm_paths]
    try:
        mosaic, transform = merge(srcs, nodata=NODATA, method="first")
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
            "nodata": NODATA,
            "dtype": "float32",
        }
    )
    grid = mosaic[0].astype(np.float32)
    bad = ~np.isfinite(grid) | (grid == NODATA) | (grid < -1000)
    n_bad = int(bad.sum())
    print(f"nodata/invalid before fill: {n_bad} ({100.0 * n_bad / grid.size:.3f}%)")
    if n_bad and n_bad < grid.size:
        try:
            from scipy import ndimage

            mask = bad
            idx = ndimage.distance_transform_edt(
                mask, return_distances=False, return_indices=True
            )
            filled = grid[tuple(idx)]
            grid = grid.copy()
            grid[mask] = filled[mask]
            bad = ~np.isfinite(grid) | (grid == NODATA) | (grid < -1000)
            print(f"nodata/invalid after fill-all: {int(bad.sum())} (filled {int(mask.sum())})")
        except ImportError:
            print("scipy unavailable — skip fill-all")
    grid[bad] = NODATA

    out = OUT_DIR / "wiltshire_county_dtm.tif"
    with rasterio.open(out, "w", **meta) as dst:
        dst.write(grid, 1)
    print("wrote", out, f"{out.stat().st_size/1e6:.1f} MB", grid.shape)
    with rasterio.open(out) as ds:
        print("bounds", ds.bounds, "res", ds.res)


if __name__ == "__main__":
    main()

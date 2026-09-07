#!/usr/bin/env python3
"""Fetch EA 1 m DTM chips around each Wiltshire long barrow; write hillshade JPEGs.

Outputs:
  lidar/chips/raw/{id}.tif   — gitignored source DTM
  lidar/chips/web/{id}.jpg   — web hillshade (~380 px side)
  lidar/chips/web/index.json — id → WGS84 leaflet bounds + path

Polite sequential WCS; resume/skip existing valid chips.
"""
from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = ROOT / "lidar" / "chips" / "raw"
WEB = ROOT / "lidar" / "chips" / "web"
RAW.mkdir(parents=True, exist_ok=True)
WEB.mkdir(parents=True, exist_ok=True)

WCS = "https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs"
COVERAGE = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"
UA = {"User-Agent": "wiltshire-long-barrows/1.0 (sarsen.org research)"}

# ~380 m OSGB square centred on barrow → ~380×380 @ 1 m
HALF_M = 190.0
SLEEP_S = 0.6  # polite pause between WCS calls
JPEG_QUALITY = 82
MIN_VALID_FRAC = 0.15
TRANSFORMER = Transformer.from_crs(27700, 4326, always_xy=True)


def fetch_chip(e0: int, e1: int, n0: int, n1: int, out: Path) -> Path:
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
    url = WCS + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    if b"<?xml" in data[:80] or b"Exception" in data[:400] or "tiff" not in ctype.lower():
        err = out.with_suffix(".error.xml")
        err.write_bytes(data[:80000])
        raise RuntimeError(f"WCS error → {err}")
    out.write_bytes(data)
    with rasterio.open(out) as ds:
        w = min(32, ds.width)
        h = min(32, ds.height)
        ds.read(1, window=Window(ds.width - w, ds.height - h, w, h))
    return out


def hillshade_rgb(grid: np.ndarray, cell: float) -> np.ndarray:
    dy, dx = np.gradient(grid, cell, cell)
    azimuth = np.radians(315.0)
    altitude = np.radians(45.0)
    slope = np.pi / 2 - np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    shaded = (
        np.sin(altitude) * np.sin(slope)
        + np.cos(altitude) * np.cos(slope) * np.cos(azimuth - aspect)
    )
    shaded = np.clip(shaded, 0, 1)
    shaded[np.isnan(grid)] = np.nan
    z = grid.copy()
    finite = np.isfinite(z)
    if finite.sum() < 10:
        rgb = np.zeros(grid.shape + (3,), dtype=np.uint8)
        return rgb
    zmin, zmax = np.nanpercentile(z, 2), np.nanpercentile(z, 98)
    zn = np.clip((z - zmin) / (zmax - zmin + 1e-9), 0, 1)
    cmap = plt.get_cmap("terrain")
    rgba = cmap(zn)
    for i in range(3):
        rgba[:, :, i] *= np.where(np.isnan(shaded), 1, 0.35 + 0.65 * shaded)
    # Flatten nodata onto dark map background (#141210)
    bg = np.array([0x14, 0x12, 0x10], dtype=np.float64) / 255.0
    for i in range(3):
        rgba[:, :, i] = np.where(np.isnan(grid), bg[i], rgba[:, :, i])
    return (np.clip(rgba[:, :, :3], 0, 1) * 255).astype(np.uint8)


def process_tif(tif: Path, jpg: Path) -> dict:
    with rasterio.open(tif) as ds:
        data = ds.read(1).astype(np.float64)
        nodata = ds.nodata
        bounds = ds.bounds
        cell = float(ds.res[0])
    if nodata is not None:
        data[data == nodata] = np.nan
    data[~np.isfinite(data)] = np.nan
    data[data < -50] = np.nan
    data[data > 1e4] = np.nan
    valid_frac = float(np.isfinite(data).mean())
    if valid_frac < MIN_VALID_FRAC:
        raise RuntimeError(f"too little valid DTM ({valid_frac:.2%})")
    rgb = hillshade_rgb(data, cell)
    img = Image.fromarray(rgb, "RGB")
    # Prefer ~256–400 px; already ~380 — keep as-is unless huge
    if max(img.size) > 420:
        scale = 400 / max(img.size)
        img = img.resize(
            (max(1, int(img.size[0] * scale)), max(1, int(img.size[1] * scale))),
            Image.Resampling.BILINEAR,
        )
    img.save(jpg, "JPEG", quality=JPEG_QUALITY, optimize=True)
    lon0, lat0 = TRANSFORMER.transform(bounds.left, bounds.bottom)
    lon1, lat1 = TRANSFORMER.transform(bounds.right, bounds.top)
    return {
        "bounds": [[lat0, lon0], [lat1, lon1]],
        "osgb": {
            "e0": bounds.left,
            "e1": bounds.right,
            "n0": bounds.bottom,
            "n1": bounds.top,
        },
        "path": f"lidar/chips/web/{jpg.name}",
        "pixels": [img.size[0], img.size[1]],
        "bytes": jpg.stat().st_size,
        "valid_frac": round(valid_frac, 3),
    }


def tif_ok(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 10_000:
        return False
    try:
        with rasterio.open(path) as ds:
            w = min(16, ds.width)
            h = min(16, ds.height)
            ds.read(1, window=Window(0, 0, w, h))
            return ds.width >= 100 and ds.height >= 100
    except Exception:
        return False


def main() -> None:
    rows = json.loads((DATA / "long_barrows.json").read_text(encoding="utf-8"))
    index: dict[str, dict] = {}
    built = 0
    skipped = 0
    failed: list[str] = []
    t0 = time.time()

    for i, r in enumerate(rows, 1):
        bid = r["id"]
        e = r.get("easting")
        n = r.get("northing")
        if e is None or n is None:
            failed.append(f"{bid}: no coords")
            continue
        e, n = float(e), float(n)
        e0 = int(math.floor(e - HALF_M))
        e1 = int(math.ceil(e + HALF_M))
        n0 = int(math.floor(n - HALF_M))
        n1 = int(math.ceil(n + HALF_M))
        tif = RAW / f"{bid}.tif"
        jpg = WEB / f"{bid}.jpg"

        need_fetch = not tif_ok(tif)
        if need_fetch:
            try:
                print(f"[{i}/{len(rows)}] GET {bid} E{e0}-{e1} N{n0}-{n1}")
                fetch_chip(e0, e1, n0, n1, tif)
                time.sleep(SLEEP_S)
            except Exception as exc:
                print(f"  FAIL fetch {bid}: {exc}")
                failed.append(f"{bid}: fetch {exc}")
                continue
        else:
            print(f"[{i}/{len(rows)}] reuse tif {bid}")

        try:
            meta = process_tif(tif, jpg)
            index[bid] = meta
            built += 1
            if not need_fetch and jpg.is_file():
                skipped += 1
            print(
                f"  → {jpg.name} {meta['pixels'][0]}×{meta['pixels'][1]} "
                f"{meta['bytes']/1024:.1f} KB valid={meta['valid_frac']}"
            )
        except Exception as exc:
            print(f"  FAIL hillshade {bid}: {exc}")
            failed.append(f"{bid}: hillshade {exc}")
            if jpg.is_file():
                jpg.unlink()

    index_path = WEB / "index.json"
    payload = {
        "source": (
            "EA LIDAR Composite DTM 1 m via WCS, ~380 m OSGB squares centred on "
            "each long barrow; hillshade JPEG. Open Government Licence."
        ),
        "half_m": HALF_M,
        "extent_m": HALF_M * 2,
        "cellsize_m": 1.0,
        "n": len(index),
        "chips": index,
    }
    index_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    total_b = sum(m["bytes"] for m in index.values())
    elapsed = time.time() - t0
    print(
        f"\nwrote {index_path}: {len(index)} chips, "
        f"{total_b/1e6:.2f} MB web JPEGs, {elapsed/60:.1f} min"
    )
    if failed:
        print(f"failed ({len(failed)}):")
        for f in failed:
            print(" ", f)


if __name__ == "__main__":
    main()

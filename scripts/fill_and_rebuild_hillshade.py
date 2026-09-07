#!/usr/bin/env python3
"""Fill ALL county DTM nodata, rebuild PNG/JPEG hillshade, visual-gate black holes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
TIF = ROOT / "lidar" / "county" / "wiltshire_county_dtm.tif"
COUNTY_GJ = ROOT / "data" / "wiltshire-county.geojson"
WEB = ROOT / "lidar" / "web"
NODATA = -9999.0
PREVIEW = ROOT / "lidar" / "web" / "county-hillshade-preview.jpg"
MIN_HOLE_W = 40
MIN_HOLE_H = 80
MEAN_L_MAX = 20.0


def fill_all_nodata(grid: np.ndarray, nodata: float) -> tuple[np.ndarray, dict]:
    out = grid.astype(np.float32, copy=True)
    mask = ~np.isfinite(out) | (out == nodata) | (out < -1000)
    before = int(mask.sum())
    stats = {
        "before_count": before,
        "before_pct": 100.0 * before / out.size,
        "size": int(out.size),
    }
    if before == 0 or mask.all():
        stats["after_count"] = before
        stats["after_pct"] = stats["before_pct"]
        stats["filled"] = 0
        return out, stats
    idx = ndimage.distance_transform_edt(mask, return_distances=False, return_indices=True)
    filled = out[tuple(idx)]
    out[mask] = filled[mask]
    after_mask = ~np.isfinite(out) | (out == nodata) | (out < -1000)
    stats["after_count"] = int(after_mask.sum())
    stats["after_pct"] = 100.0 * stats["after_count"] / out.size
    stats["filled"] = before - stats["after_count"]
    return out, stats


def county_mask(shape, transform) -> np.ndarray | None:
    if not COUNTY_GJ.is_file():
        return None
    try:
        from rasterio import features
        from shapely.geometry import shape as shp_shape, mapping
        from shapely.ops import transform as shp_transform
        from pyproj import Transformer
    except ImportError as e:
        print("county mask deps missing:", e)
        return None
    gj = json.loads(COUNTY_GJ.read_text(encoding="utf-8"))
    to_osgb = Transformer.from_crs(4326, 27700, always_xy=True).transform
    geoms = []
    for f in gj.get("features") or []:
        g = f.get("geometry")
        if g:
            geoms.append(mapping(shp_transform(to_osgb, shp_shape(g))))
    if not geoms:
        return None
    mask = features.rasterize(
        [(g, 1) for g in geoms],
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype=np.uint8,
    )
    return mask.astype(bool)


def visual_gate_jpeg(path: Path, footprint: np.ndarray | None) -> list[str]:
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    h, w, _ = im.shape
    L = im.mean(axis=2)
    dark = L < MEAN_L_MAX
    if footprint is not None:
        fp_img = Image.fromarray(footprint.astype(np.uint8) * 255)
        fp_img = fp_img.resize((w, h), Image.Resampling.NEAREST)
        fp = np.asarray(fp_img) > 127
        dark = dark & fp
    fails = []
    labeled, nlab = ndimage.label(dark)
    for lab in range(1, nlab + 1):
        ys, xs = np.where(labeled == lab)
        if ys.size == 0:
            continue
        bw = int(xs.max() - xs.min() + 1)
        bh = int(ys.max() - ys.min() + 1)
        if bw >= MIN_HOLE_W and bh >= MIN_HOLE_H:
            mean_l = float(L[ys, xs].mean())
            if mean_l < MEAN_L_MAX:
                fails.append(
                    f"dark block lab={lab} bbox={bw}x{bh}px meanL={mean_l:.1f} "
                    f"at ({xs.min()},{ys.min()})"
                )
    return fails


def main() -> None:
    if not TIF.is_file():
        raise SystemExit(f"missing {TIF}")
    print(f"loading {TIF}…")
    with rasterio.open(TIF) as ds:
        grid = ds.read(1)
        meta = ds.meta.copy()
        transform = ds.transform
        nodata = ds.nodata if ds.nodata is not None else NODATA

    bad0 = ~np.isfinite(grid) | (grid == nodata) | (grid < -1000)
    before_pct = 100.0 * bad0.mean()
    print(f"nodata before: {before_pct:.3f}%")

    if before_pct > 0.01:
        filled, stats = fill_all_nodata(grid, float(nodata))
        print(
            f"nodata after fill-all: {stats['after_pct']:.3f}% "
            f"(filled {stats['filled']} cells; was {stats['before_pct']:.3f}%)"
        )
        meta.update(dtype="float32", nodata=NODATA, compress="lzw")
        with rasterio.open(TIF, "w", **meta) as dst:
            dst.write(filled, 1)
        print(f"wrote filled DTM {TIF} {TIF.stat().st_size/1e6:.1f} MB")
        after_pct = stats["after_pct"]
    else:
        print("DTM already fully filled — skip rewrite")
        after_pct = before_pct
        stats = {"filled": 0, "before_count": 0, "after_count": 0}

    print("running make_county_hillshade.py…")
    subprocess.check_call([sys.executable, str(ROOT / "make_county_hillshade.py")], cwd=ROOT)
    print("running _make_web_hillshade.py…")
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "_make_web_hillshade.py")], cwd=ROOT)

    fp = county_mask((meta["height"], meta["width"]), transform)
    if fp is not None:
        print(f"county footprint covers {100.0 * fp.mean():.1f}% of DTM grid")

    jpg = WEB / "county-hillshade.jpg"
    Image.open(jpg).save(PREVIEW, quality=85, optimize=True)
    print(f"preview {PREVIEW}")

    fails = visual_gate_jpeg(jpg, fp)
    if fails:
        print("VISUAL GATE FAIL:")
        for f in fails[:20]:
            print(" ", f)
        raise SystemExit(1)
    print("VISUAL GATE PASS: no large dark rectangles (L<20, ≥40×80) in footprint")
    print(
        json.dumps(
            {
                "nodata_before_pct": before_pct,
                "nodata_after_pct": after_pct,
                "filled": stats.get("filled", 0),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

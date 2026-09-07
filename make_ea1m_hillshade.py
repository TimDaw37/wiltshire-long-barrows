#!/usr/bin/env python3
"""Build web hillshade PNG + bounds JSON from EA DTM mosaic."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from rasterio.enums import Resampling

ROOT = Path(__file__).resolve().parent
EA1M = ROOT / "lidar" / "ea1m"
OUT = ROOT / "lidar" / "web"
OUT.mkdir(parents=True, exist_ok=True)

TARGET_CELL_M = 4.0
TIF = EA1M / "wiltshire_lb_dtm.tif"


def load_resampled(tif: Path, cell: float):
    with rasterio.open(tif) as ds:
        scale_x = ds.res[0] / cell
        scale_y = abs(ds.res[1]) / cell
        new_h = max(1, int(round(ds.height * scale_y)))
        new_w = max(1, int(round(ds.width * scale_x)))
        data = ds.read(
            1,
            out_shape=(new_h, new_w),
            resampling=Resampling.bilinear,
        ).astype(np.float64)
        transform = ds.transform * ds.transform.scale(
            (ds.width / new_w), (ds.height / new_h)
        )
        nodata = ds.nodata
        bounds = ds.bounds
        src_res = ds.res[0]
    if nodata is not None:
        data[data == nodata] = np.nan
    data[~np.isfinite(data)] = np.nan
    data[data < -50] = np.nan
    data[data > 1e4] = np.nan
    return data, transform, bounds, src_res


def hillshade_rgba(grid: np.ndarray, cell: float):
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
    zmin, zmax = np.nanpercentile(z, 2), np.nanpercentile(z, 98)
    zn = np.clip((z - zmin) / (zmax - zmin + 1e-9), 0, 1)
    cmap = plt.get_cmap("terrain")
    rgba = cmap(zn)
    for i in range(3):
        rgba[:, :, i] *= np.where(np.isnan(shaded), 1, 0.35 + 0.65 * shaded)
    rgba[np.isnan(grid)] = (0, 0, 0, 0)
    return rgba, float(np.nanmin(grid)), float(np.nanmax(grid))


def main() -> None:
    if not TIF.is_file():
        raise SystemExit(f"missing {TIF} — run download_ea_dtm.py first")
    print(f"resampling to {TARGET_CELL_M} m for web hillshade…")
    grid, transform, bounds, src_res = load_resampled(TIF, TARGET_CELL_M)
    print(f"grid {grid.shape}, nan frac {np.isnan(grid).mean():.4f}, z {np.nanmin(grid):.1f}–{np.nanmax(grid):.1f}")
    rgba, zmin, zmax = hillshade_rgba(grid, TARGET_CELL_M)
    img = Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")
    png = OUT / "ea1m-hillshade.png"
    img.save(png, optimize=True)
    size_mb = png.stat().st_size / (1024 * 1024)
    print(f"wrote {png} {img.size[0]}×{img.size[1]} ({size_mb:.2f} MB)")
    t = Transformer.from_crs(27700, 4326, always_xy=True)
    lon0, lat0 = t.transform(bounds.left, bounds.bottom)
    lon1, lat1 = t.transform(bounds.right, bounds.top)
    meta = {
        "osgb": {"e0": bounds.left, "e1": bounds.right, "n0": bounds.bottom, "n1": bounds.top},
        "wgs84_leaflet": [[lat0, lon0], [lat1, lon1]],
        "source": (
            "EA LIDAR Composite DTM 2022 1m product via WCS "
            f"(SCALEFACTOR→{src_res:g} m mosaic), Open Government Licence"
        ),
        "placeholder": False,
        "cellsize_m": TARGET_CELL_M,
        "source_cellsize_m": src_res,
        "z_range_m_od": [zmin, zmax],
        "png_pixels": [img.size[0], img.size[1]],
        "png_mb": round(size_mb, 3),
    }
    (OUT / "ea1m-bounds.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("bounds", meta["osgb"])


if __name__ == "__main__":
    main()

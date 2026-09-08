#!/usr/bin/env python3
"""Feasibility trial: long-barrow long-axis from 1 m LiDAR chips.

Prefer raw DTM TIFF under lidar/chips/raw/ (local-relief + PCA on mound mask).
Fall back to web JPG hillshade if TIFF missing. Azimuth is undirected 0–180°
from north (image top = north). Marks indistinct when the estimate is unstable
or weakly elongated rather than forcing a bad angle.

Usage:
  .venv/bin/python scripts/orientation_trial.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from PIL import Image
from scipy import ndimage
from skimage.measure import label, regionprops

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "lidar" / "chips" / "raw"
WEB_DIR = ROOT / "lidar" / "chips" / "web"
OUT_DIR = Path(__file__).resolve().parent / "orientation_trial_out"

# Trial sites: stem, display name, existing NHLE PCA az (or None)
TRIAL_SITES = [
    ("SU16NW100", "West Kennet", 85.2),
    ("SU14SW125", "Winterbourne Stoke Crossroads", 34.1),
    ("SU02SW103", "Kitts Grave", None),
]

# Default mound-mask params (stable on clear chalk barrows)
SIGMA = 30.0
R_FRAC = 0.35
PCT = 85.0
MIN_AREA = 40
# Ensemble for stability / indistinct flag
ENSEMBLE = [
    (25.0, 0.32, 82.0),
    (25.0, 0.32, 85.0),
    (25.0, 0.35, 85.0),
    (30.0, 0.32, 85.0),
    (30.0, 0.35, 82.0),
    (30.0, 0.35, 85.0),
    (30.0, 0.35, 88.0),
    (35.0, 0.35, 85.0),
]

CONF_INDISTINCT = 0.65
SPREAD_INDISTINCT = 12.0  # degrees undirected
STD_INDISTINCT = 6.0


@dataclass
class OrientationResult:
    stem: str
    name: str
    source: str
    azimuth_deg: float | None
    confidence: float
    indistinct: bool
    existing_az: float | None
    delta_deg: float | None
    method: str
    eig_ratio: float | None
    ensemble_std_deg: float | None
    ensemble_spread_deg: float | None
    notes: str


def undirected_delta(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return float(min(d, 180.0 - d))


def mean_undirected(azs: np.ndarray) -> tuple[float, float]:
    """Circular mean/std on undirected angles via double-angle trick."""
    ang = np.deg2rad(2.0 * np.asarray(azs, dtype=float))
    c, s = float(np.mean(np.cos(ang))), float(np.mean(np.sin(ang)))
    mean = 0.5 * np.rad2deg(np.arctan2(s, c)) % 180.0
    R = float(np.hypot(c, s))
    std = 0.5 * np.rad2deg(np.sqrt(max(0.0, -2.0 * np.log(max(R, 1e-12)))))
    return float(mean), float(std)


def load_elevation_chip(stem: str) -> tuple[np.ndarray, str]:
    """Return float elevation (or grayscale stand-in) and source label."""
    tif = RAW_DIR / f"{stem}.tif"
    jpg = WEB_DIR / f"{stem}.jpg"
    if tif.exists():
        with rasterio.open(tif) as ds:
            z = ds.read(1).astype(np.float64)
        if np.isfinite(z).sum() > 100 and (np.nanmax(z) - np.nanmin(z)) > 0.05:
            z = np.nan_to_num(z, nan=float(np.nanmedian(z)))
            return z, f"raw_dtm:{tif.name}"
    if jpg.exists():
        im = np.asarray(Image.open(jpg).convert("L"), dtype=np.float64)
        return im, f"web_hillshade:{jpg.name}"
    raise FileNotFoundError(f"No chip for {stem} under {RAW_DIR} or {WEB_DIR}")


def load_preview_rgb(stem: str) -> np.ndarray:
    jpg = WEB_DIR / f"{stem}.jpg"
    if jpg.exists():
        return np.asarray(Image.open(jpg).convert("RGB"))
    z, _ = load_elevation_chip(stem)
    z = (z - z.min()) / (z.max() - z.min() + 1e-9)
    return np.dstack([z, z, z])


def local_relief(z: np.ndarray, sigma: float) -> np.ndarray:
    bg = ndimage.gaussian_filter(z, sigma=sigma)
    return z - bg


def pca_on_mask(mask: np.ndarray) -> tuple[float, float, float, np.ndarray] | None:
    ys, xs = np.nonzero(mask)
    if xs.size < MIN_AREA:
        return None
    pts = np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])
    center = pts.mean(axis=0)
    pts_c = pts - center
    cov = np.cov(pts_c.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    v = eigvecs[:, order[0]]  # image: +x east, +y south
    # Azimuth from north: atan2(ΔE, ΔN) with ΔN = -dy
    az = float(np.degrees(np.arctan2(v[0], -v[1])) % 180.0)
    ratio = float(eigvals[0] / max(eigvals[1], 1e-12))
    conf = float((eigvals[0] - eigvals[1]) / (eigvals[0] + eigvals[1] + 1e-12))
    return az, conf, ratio, center


def select_mound_component(
    lr: np.ndarray, r_frac: float, pct: float
) -> np.ndarray | None:
    h, w = lr.shape
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]
    r = min(h, w) * r_frac
    roi = (yy - cy) ** 2 + (xx - cx) ** 2 <= r**2
    vals = lr[roi]
    if vals.size < 50:
        return None
    thr = float(np.percentile(vals, pct))
    mask = (lr >= thr) & roi
    lab = label(mask)
    props = regionprops(lab)
    best_label = None
    best_score = -1.0
    for p in props:
        if p.area < MIN_AREA:
            continue
        dist = float(np.hypot(p.centroid[0] - cy, p.centroid[1] - cx))
        if dist > r * 0.55:
            continue
        score = p.area / (1.0 + dist / 15.0) * (1.0 + 2.0 * p.eccentricity)
        if score > best_score:
            best_score = score
            best_label = p.label
    if best_label is None:
        # fallback: largest elongated component in ROI
        for p in props:
            if p.area < MIN_AREA:
                continue
            dist = float(np.hypot(p.centroid[0] - cy, p.centroid[1] - cx))
            score = p.area / (1.0 + dist / 15.0) * (1.0 + 2.0 * p.eccentricity)
            if score > best_score:
                best_score = score
                best_label = p.label
    if best_label is None:
        return None
    return lab == best_label


def estimate_once(
    z: np.ndarray, sigma: float, r_frac: float, pct: float
) -> tuple[float, float, float, np.ndarray, np.ndarray] | None:
    lr = local_relief(z, sigma)
    mask = select_mound_component(lr, r_frac, pct)
    if mask is None:
        return None
    pca = pca_on_mask(mask)
    if pca is None:
        return None
    az, conf, ratio, center = pca
    return az, conf, ratio, mask, center


def estimate_orientation(z: np.ndarray) -> dict:
    primary = estimate_once(z, SIGMA, R_FRAC, PCT)
    ensemble_az: list[float] = []
    for sigma, r_frac, pct in ENSEMBLE:
        r = estimate_once(z, sigma, r_frac, pct)
        if r is not None:
            ensemble_az.append(r[0])

    if primary is None and not ensemble_az:
        return {
            "azimuth_deg": None,
            "confidence": 0.0,
            "indistinct": True,
            "eig_ratio": None,
            "ensemble_std_deg": None,
            "ensemble_spread_deg": None,
            "mask": None,
            "center": None,
            "notes": "no mound mask found",
        }

    if primary is None:
        mean_az, std = mean_undirected(np.array(ensemble_az))
        primary_az, primary_conf, primary_ratio = mean_az, 0.0, None
        mask, center = None, None
    else:
        primary_az, primary_conf, primary_ratio, mask, center = primary
        std = mean_undirected(np.array(ensemble_az))[1] if ensemble_az else 0.0

    spread = 0.0
    if len(ensemble_az) >= 2:
        spread = max(
            undirected_delta(a, b) for a in ensemble_az for b in ensemble_az
        )

    indistinct = False
    notes_parts: list[str] = []
    if primary_conf < CONF_INDISTINCT:
        indistinct = True
        notes_parts.append(f"low elongation conf={primary_conf:.2f}")
    if std > STD_INDISTINCT:
        indistinct = True
        notes_parts.append(f"unstable ensemble std={std:.1f}°")
    if spread > SPREAD_INDISTINCT:
        indistinct = True
        notes_parts.append(f"ensemble spread={spread:.1f}°")

    # Soften confidence when unstable
    conf = float(primary_conf)
    if std > 0:
        conf *= float(np.clip(1.0 - std / 20.0, 0.15, 1.0))
    if spread > 0:
        conf *= float(np.clip(1.0 - spread / 40.0, 0.15, 1.0))
    conf = float(np.clip(conf, 0.0, 1.0))

    return {
        "azimuth_deg": float(primary_az),
        "confidence": conf,
        "indistinct": indistinct,
        "eig_ratio": primary_ratio,
        "ensemble_std_deg": float(std) if ensemble_az else None,
        "ensemble_spread_deg": float(spread) if ensemble_az else None,
        "mask": mask,
        "center": center,
        "notes": "; ".join(notes_parts) if notes_parts else "stable mound PCA",
    }


def draw_axis(
    rgb: np.ndarray,
    az_deg: float | None,
    center: np.ndarray | None,
    mask: np.ndarray | None,
    title: str,
    out_path: Path,
    indistinct: bool,
) -> None:
    fig, ax = plt.subplots(figsize=(5.2, 5.2), dpi=120)
    ax.imshow(rgb)
    if mask is not None:
        overlay = np.zeros((*mask.shape, 4), dtype=float)
        overlay[mask, :] = (0.1, 0.85, 0.95, 0.28)
        ax.imshow(overlay)
    if az_deg is not None and center is not None:
        # Line along azimuth: from north, clockwise-ish via atan2(E,N)
        # Direction in image: dx = sin(az), dy = -cos(az)  (y down)
        rad = np.deg2rad(az_deg)
        dx, dy = np.sin(rad), -np.cos(rad)
        length = 0.38 * min(rgb.shape[0], rgb.shape[1])
        cx, cy = float(center[0]), float(center[1])
        color = "#ffcc00" if not indistinct else "#ff6666"
        style = "-" if not indistinct else "--"
        ax.plot(
            [cx - dx * length, cx + dx * length],
            [cy - dy * length, cy + dy * length],
            color=color,
            lw=2.2,
            ls=style,
            solid_capstyle="round",
        )
        ax.plot([cx], [cy], "o", color=color, ms=5)
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])
    # N arrow
    ax.annotate(
        "N",
        xy=(0.92, 0.92),
        xytext=(0.92, 0.78),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        arrowprops=dict(arrowstyle="->", color="white", lw=1.2),
        color="white",
        fontsize=8,
        fontweight="bold",
    )
    fig.tight_layout(pad=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def run_trial() -> list[OrientationResult]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[OrientationResult] = []
    for stem, name, existing in TRIAL_SITES:
        z, source = load_elevation_chip(stem)
        est = estimate_orientation(z)
        az = est["azimuth_deg"]
        delta = None
        if az is not None and existing is not None:
            delta = undirected_delta(az, existing)
        res = OrientationResult(
            stem=stem,
            name=name,
            source=source,
            azimuth_deg=None if est["indistinct"] and est["confidence"] < 0.4 else az,
            confidence=round(est["confidence"], 3),
            indistinct=est["indistinct"],
            existing_az=existing,
            delta_deg=None if delta is None else round(delta, 2),
            method="dtm_local_relief_pca",
            eig_ratio=None
            if est["eig_ratio"] is None
            else round(float(est["eig_ratio"]), 2),
            ensemble_std_deg=None
            if est["ensemble_std_deg"] is None
            else round(float(est["ensemble_std_deg"]), 2),
            ensemble_spread_deg=None
            if est["ensemble_spread_deg"] is None
            else round(float(est["ensemble_spread_deg"]), 2),
            notes=est["notes"],
        )
        # Keep reported azimuth even when indistinct (for transparency), but flag it
        res.azimuth_deg = None if az is None else round(float(az), 1)

        rgb = load_preview_rgb(stem)
        tag = "INDISTINCT" if res.indistinct else f"az={res.azimuth_deg:.1f}°"
        title = f"{stem} {name}\n{tag}  conf={res.confidence:.2f}"
        if existing is not None:
            title += f"  NHLE={existing:.1f}°"
            if res.delta_deg is not None:
                title += f"  Δ={res.delta_deg:.1f}°"
        out_img = OUT_DIR / f"{stem}_axis.png"
        draw_axis(
            rgb,
            az,
            est["center"] if est["center"] is not None else np.array([z.shape[1] / 2, z.shape[0] / 2]),
            est["mask"],
            title,
            out_img,
            res.indistinct,
        )
        results.append(res)
        print(
            f"{stem}: az={res.azimuth_deg} conf={res.confidence} "
            f"indistinct={res.indistinct} delta={res.delta_deg} | {res.notes}"
        )
    return results


def write_report(results: list[OrientationResult], path: Path) -> None:
    clear = [r for r in results if not r.indistinct and r.existing_az is not None]
    deltas = [r.delta_deg for r in clear if r.delta_deg is not None]
    go = False
    if deltas and max(deltas) <= 5.0 and all(not r.indistinct for r in clear):
        # go only if known sites match and we have a working indistinct gate
        go = True
    # Extra: require at least one indistinct on the hard case OR all clear with small deltas
    hard = [r for r in results if r.existing_az is None]
    if hard and not hard[0].indistinct and hard[0].confidence < 0.7:
        go = False

    decision = "GO" if go else "NO-GO"
    rationale = []
    if deltas:
        rationale.append(
            f"Known-site |Δ| vs NHLE PCA: "
            + ", ".join(f"{r.stem} {r.delta_deg:.1f}°" for r in clear)
            + f" (max {max(deltas):.1f}°)."
        )
    else:
        rationale.append("No clear known-site comparisons.")
    indist = [r for r in results if r.indistinct]
    if indist:
        rationale.append(
            "Indistinct gate fired on: "
            + ", ".join(r.stem for r in indist)
            + " — good (avoids forcing bad angles)."
        )
    if go:
        rationale.append(
            "Method is accurate on clear chalk mounds and refuses weak cases; "
            "suitable to batch ~129 chips with human review of indistinct flags."
        )
    else:
        rationale.append(
            "Hold batch until more sites are spot-checked, or tighten params; "
            "do not overwrite NHLE azimuths blindly."
        )

    lines = [
        "# Orientation trial — LiDAR long-axis vs NHLE PCA",
        "",
        f"**Decision: {decision} for batching ~129 chips.**",
        "",
        "## Method",
        "",
        "Prefer `lidar/chips/raw/{stem}.tif` (1 m EA DTM elevation), else web JPG hillshade.",
        "",
        "1. Local residual relief: `z - GaussianBlur(z, σ≈30 px)` to remove regional slope.",
        "2. Circular ROI (~35% of chip half-diagonal) centred on the chip.",
        "3. Threshold positive residuals (85th percentile) → mound mask.",
        "4. Keep the best connected component (area × eccentricity, centre-weighted).",
        "5. PCA on mask pixel coordinates → undirected azimuth `atan2(ΔE, ΔN)` folded to **0–180°** "
        "(image top = north, +x = east).",
        "6. Confidence = eigenvalue anisotropy `(λ1−λ2)/(λ1+λ2)`, down-weighted by ensemble spread.",
        "7. **Indistinct** if conf < 0.65 or ensemble circular std > 6° or pairwise spread > 12° "
        "across a small σ / ROI / percentile grid.",
        "",
        "Script: `scripts/orientation_trial.py`. Annotated previews: `scripts/orientation_trial_out/`.",
        "",
        "## Per-site results",
        "",
        "| Site | Stem | Estimated az (°) | Conf | Indistinct | NHLE PCA az (°) | Δ (°) | Notes |",
        "|------|------|------------------|------|------------|-----------------|-------|-------|",
    ]
    for r in results:
        az_s = "—" if r.azimuth_deg is None else f"{r.azimuth_deg:.1f}"
        ex_s = "—" if r.existing_az is None else f"{r.existing_az:.1f}"
        d_s = "—" if r.delta_deg is None else f"{r.delta_deg:.1f}"
        lines.append(
            f"| {r.name} | `{r.stem}` | {az_s} | {r.confidence:.3f} | "
            f"{'yes' if r.indistinct else 'no'} | {ex_s} | {d_s} | {r.notes} |"
        )

    lines += [
        "",
        "### Detail",
        "",
    ]
    for r in results:
        lines.append(f"#### {r.name} (`{r.stem}`)")
        lines.append("")
        lines.append(f"- Source: `{r.source}`")
        lines.append(f"- Method: `{r.method}`")
        lines.append(
            f"- Estimated azimuth: **{r.azimuth_deg}°** (undirected 0–180 from N)"
            if r.azimuth_deg is not None
            else "- Estimated azimuth: none"
        )
        lines.append(f"- Confidence: **{r.confidence:.3f}**; indistinct: **{r.indistinct}**")
        if r.eig_ratio is not None:
            lines.append(f"- Eigenvalue ratio λ1/λ2: {r.eig_ratio}")
        if r.ensemble_std_deg is not None:
            lines.append(
                f"- Ensemble circular std: {r.ensemble_std_deg}°; "
                f"spread: {r.ensemble_spread_deg}°"
            )
        if r.existing_az is not None:
            lines.append(
                f"- Existing NHLE polygon PCA: {r.existing_az}°; "
                f"|Δ| = {r.delta_deg}°"
            )
        else:
            lines.append("- No existing NHLE azimuth in gazetteer.")
        lines.append(f"- Preview: `scripts/orientation_trial_out/{r.stem}_axis.png`")
        lines.append("")

    lines += [
        "## Go / no-go",
        "",
        f"**{decision}**",
        "",
        *[f"- {x}" for x in rationale],
        "",
        "### Batching notes (if GO)",
        "",
        "- Write LiDAR-derived az to a parallel field (e.g. `azimuth_lidar_deg`) — do not silently replace `azimuth_deg` / `nhle_polygon_pca`.",
        "- Queue all `indistinct=true` rows for manual review.",
        "- Expect modern roads, plough patterns, and multi-barrow chips to inflate false axes; centre ROI assumes the target is chip-centred (true for current chip builder).",
        "",
        "## Re-run",
        "",
        "```bash",
        "cd /workspace/wiltshire-long-barrows",
        ".venv/bin/python scripts/orientation_trial.py",
        "```",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # machine-readable sidecar
    side = OUT_DIR / "results.json"
    side.write_text(
        json.dumps([asdict(r) for r in results], indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    results = run_trial()
    report = ROOT / "docs" / "orientation-trial.md"
    write_report(results, report)
    print(f"\nWrote report: {report}")
    print(f"Annotated images: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

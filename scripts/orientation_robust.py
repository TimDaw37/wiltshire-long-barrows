#!/usr/bin/env python3
"""Robustness package: published axes vs display, and DTM ridge vs solstice.

Read-only on data/long_barrows.json. Writes docs/analysis/fig-1[0-6]* and
tables under scripts/orientation_batch_out/analysis/.

1. Match Roberts et al. IA 47 Table 1 (CC BY) to the gazetteer.
2. Fetch landscape DTM chips (EA 1 m WCS, SCALEFACTOR 0.1 → ~10 m) and
   estimate local ridge/contour orientation from a plane fit on an annulus
   that excludes the mound.
3. Compare display axis vs ridge vs solstice; flag literature disagreements.
"""
from __future__ import annotations

import csv
import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tifffile
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "long_barrows.json"
FIGDIR = ROOT / "docs" / "analysis"
OUTDIR = ROOT / "scripts" / "orientation_batch_out" / "analysis"
CHIPDIR = ROOT / "lidar" / "landscape"
CHIPDIR.mkdir(parents=True, exist_ok=True)

WCS = "https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs"
COVERAGE = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"
UA = {"User-Agent": "wiltshire-long-barrows/1.0 (sarsen.org research)"}
HALF_M = 600.0
SCALEFACTOR = 0.1  # 1 m × 0.1 → ~10 m
SLEEP_S = 0.5

SUNRISE_AZ = {"midsummer": 50.2, "equinox": 89.7, "midwinter": 129.0}
EXCLUDE_PREFER = frozenset({"not_barrow", "leave_indistinct"})
SKIP_IDS = frozenset({"MODERN_ALL_CANNINGS"})

INK = "#1a1814"
MUTED = "#6a6258"
LINE = "#d9d0c4"
DISPLAY = "#2f5d4a"
RIDGE = "#8a5a3a"
SOLAR = "#9a3b32"
AGREE = "#2f5d4a"
LOOK = "#c49212"
DISAGREE = "#9a3b32"

COMPASS_MID = {
    "N-S": 0.0,
    "S-N": 0.0,
    "NNE-SSW": 22.5,
    "SSW-NNE": 22.5,
    "NE-SW": 45.0,
    "SW-NE": 45.0,
    "ENE-WSW": 67.5,
    "WSW-ENE": 67.5,
    "ENE-SSW": 67.5,  # Roberts NET6 (not a true opposite pair)
    "E-W": 90.0,
    "W-E": 90.0,
    "ESE-WNW": 112.5,
    "WNW-ESE": 112.5,
    "SE-NW": 135.0,
    "NW-SE": 135.0,
    "SSE-NNW": 157.5,
    "NNW-SSE": 157.5,
}


def undirected_delta(a: float, b: float) -> float:
    d = abs(float(a) - float(b)) % 180.0
    return float(min(d, 180.0 - d))


def norm_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", s or "").upper()


def load_rows() -> list[dict]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def display_sample(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if r["id"] in SKIP_IDS:
            continue
        if r.get("azimuth_prefer") in EXCLUDE_PREFER:
            continue
        if r.get("azimuth_display_deg") is None:
            continue
        out.append(r)
    return out


def axial_mean_R(deg) -> tuple[float, float]:
    rad = np.deg2rad(np.asarray(deg, dtype=float) * 2.0)
    C = float(np.mean(np.cos(rad)))
    S = float(np.mean(np.sin(rad)))
    R = math.hypot(C, S)
    mean = (math.degrees(math.atan2(S, C)) / 2.0) % 180.0
    return mean, R


def rayleigh_p(deg) -> tuple[float, float, float]:
    n = len(deg)
    mean, R = axial_mean_R(deg)
    Z = n * R * R
    p = math.exp(-Z) * (
        1.0
        + (2.0 * Z - Z * Z) / (4.0 * n)
        - (24.0 * Z - 132.0 * Z * Z + 76.0 * Z**3 - 9.0 * Z**4) / (288.0 * n * n)
    )
    return mean, R, float(min(1.0, max(0.0, p)))


def v_test(deg, theta0: float) -> float:
    n = len(deg)
    rad = np.deg2rad(np.asarray(deg, dtype=float) * 2.0)
    th0 = math.radians(float(theta0) * 2.0)
    C = float(np.mean(np.cos(rad - th0)))
    u = C * math.sqrt(2.0 * n)
    return float(1.0 - norm.cdf(u))


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "font.size": 10,
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
        }
    )


def savefig(fig, stem: str) -> list[str]:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("svg", "png"):
        p = FIGDIR / f"{stem}.{ext}"
        fig.savefig(p)
        paths.append(str(p.relative_to(ROOT)).replace("\\", "/"))
    plt.close(fig)
    return paths


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# --- literature match -------------------------------------------------------

def match_roberts(rows: list[dict]) -> list[dict]:
    index = {}
    for r in rows:
        for k in ("id", "her_alt_ref", "her_ref"):
            if r.get(k):
                index.setdefault(norm_id(str(r[k])), r)
    src = OUTDIR / "LongBarrowsTable1.csv"
    out = []
    with src.open(encoding="cp1252", newline="") as f:
        for raw in csv.DictReader(f):
            abbr = (raw.get("Abbreviation") or "").strip()
            if not abbr:
                continue
            smr = (raw.get("Wilts SMR #") or "").strip()
            ori = (raw.get("Orientation") or "").strip()
            hit = index.get(norm_id(smr))
            try:
                x, y = float(raw["X"]), float(raw["Y"])
            except (TypeError, ValueError, KeyError):
                x = y = None
            nearest = None
            dist = None
            if x is not None:
                nearest = min(
                    rows,
                    key=lambda r: (r["easting"] - x) ** 2 + (r["northing"] - y) ** 2,
                )
                dist = math.hypot(nearest["easting"] - x, nearest["northing"] - y)
            rec = hit or (nearest if dist is not None and dist < 120 else None)
            mid = COMPASS_MID.get(ori)
            display = rec.get("azimuth_display_deg") if rec else None
            delta = (
                round(undirected_delta(display, mid), 1)
                if display is not None and mid is not None
                else None
            )
            if rec is None:
                flag = "unmatched"
            elif dist is not None and dist > 150:
                flag = "identity_mismatch"
            elif display is None:
                flag = "no_display"
            elif mid is None:
                flag = "unmatched"
            elif delta <= 22.5:
                flag = "agree"
            elif delta <= 45:
                flag = "look"
            else:
                flag = "disagree"
            out.append(
                {
                    "roberts_abbr": abbr,
                    "roberts_grinsell": raw.get("Parish / Grinsell number"),
                    "roberts_smr": smr,
                    "roberts_orientation": ori,
                    "roberts_mid_deg": mid,
                    "roberts_x": x,
                    "roberts_y": y,
                    "gazetteer_id": rec["id"] if rec else None,
                    "display_name": rec.get("display_name") if rec else None,
                    "match_dist_m": round(dist, 1) if dist is not None else None,
                    "azimuth_display_deg": display,
                    "azimuth_prefer": rec.get("azimuth_prefer") if rec else None,
                    "azimuth_display_source": rec.get("azimuth_display_source") if rec else None,
                    "delta_vs_roberts_mid": delta,
                    "flag": flag,
                    "status": rec.get("status") if rec else None,
                    "cluster": rec.get("cluster") if rec else None,
                }
            )
    return out


# --- DTM ridge --------------------------------------------------------------

def chip_path(stem: str) -> Path:
    return CHIPDIR / f"{stem}.tif"


def meta_path(stem: str) -> Path:
    return CHIPDIR / f"{stem}.json"


def fetch_landscape_chip(easting: float, northing: float, stem: str) -> Path | None:
    out = chip_path(stem)
    meta = meta_path(stem)
    if out.is_file() and out.stat().st_size > 2000 and meta.is_file():
        return out
    e0 = int(math.floor(easting - HALF_M))
    e1 = int(math.ceil(easting + HALF_M))
    n0 = int(math.floor(northing - HALF_M))
    n1 = int(math.ceil(northing + HALF_M))
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
        ("SCALEFACTOR", str(SCALEFACTOR)),
    ]
    url = WCS + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except Exception as exc:
        print(f"  WCS fail {stem}: {exc}")
        return None
    if b"<?xml" in data[:80] or b"Exception" in data[:400] or "tiff" not in ctype.lower():
        err = out.with_suffix(".error.xml")
        err.write_bytes(data[:80000])
        print(f"  WCS XML {stem} → {err.name}")
        return None
    out.write_bytes(data)
    try:
        z = tifffile.imread(out)
        h, w = int(z.shape[0]), int(z.shape[1])
    except Exception as exc:
        print(f"  tiff read fail {stem}: {exc}")
        return None
    meta.write_text(
        json.dumps(
            {
                "e0": e0,
                "e1": e1,
                "n0": n0,
                "n1": n1,
                "width": w,
                "height": h,
                "scalefactor": SCALEFACTOR,
            }
        ),
        encoding="utf-8",
    )
    return out


def plane_ridge(z: np.ndarray, e0: float, e1: float, n0: float, n1: float, easting: float, northing: float) -> dict:
    """Fit a plane on an annulus (60–350 m) around the barrow.

    Downslope azimuth from north clockwise; ridge = downslope + 90°, folded 0–180.
    GeoTIFF from EA WCS is north-up: row 0 = n1.
    """
    rows, cols = z.shape
    xs = np.linspace(e0, e1, cols, endpoint=False) + (e1 - e0) / (2 * cols)
    ys = np.linspace(n1, n0, rows, endpoint=False) - (n1 - n0) / (2 * rows)
    E, N = np.meshgrid(xs, ys)
    dist = np.hypot(E - easting, N - northing)
    valid = np.isfinite(z) & (z > -50) & (z < 400)
    ring = valid & (dist >= 60.0) & (dist <= 350.0)
    if int(ring.sum()) < 40:
        ring = valid & (dist >= 40.0) & (dist <= 500.0)
    if int(ring.sum()) < 25:
        return {"ok": False, "n": int(ring.sum())}

    x = (E[ring] - easting).astype(float)
    y = (N[ring] - northing).astype(float)
    zz = z[ring].astype(float)
    A = np.column_stack([np.ones(len(zz)), x, y])
    coef, *_ = np.linalg.lstsq(A, zz, rcond=None)
    dz_dE, dz_dN = float(coef[1]), float(coef[2])
    slope = math.hypot(dz_dE, dz_dN)
    slope_deg = math.degrees(math.atan(slope))
    downslope = (math.degrees(math.atan2(dz_dE, dz_dN))) % 360.0
    ridge = (downslope + 90.0) % 180.0
    pred = A @ coef
    rmse = float(np.sqrt(np.mean((zz - pred) ** 2)))
    return {
        "ok": True,
        "n": int(ring.sum()),
        "slope": round(slope, 5),
        "slope_deg": round(slope_deg, 3),
        "downslope_deg": round(downslope, 2),
        "ridge_deg": round(ridge, 2),
        "plane_rmse_m": round(rmse, 3),
        "z_mean_m": round(float(np.mean(zz)), 2),
    }


def ridge_for_row(r: dict) -> dict:
    stem = r["id"]
    path = chip_path(stem)
    meta_file = meta_path(stem)
    if not path.is_file() or not meta_file.is_file():
        return {"ok": False, "reason": "no_chip"}
    try:
        z = tifffile.imread(path).astype(np.float64)
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}
    z[~np.isfinite(z)] = np.nan
    z[(z < -50) | (z > 400)] = np.nan
    rec = plane_ridge(
        z,
        float(meta["e0"]),
        float(meta["e1"]),
        float(meta["n0"]),
        float(meta["n1"]),
        float(r["easting"]),
        float(r["northing"]),
    )
    rec["id"] = stem
    return rec


# --- figures ----------------------------------------------------------------

def fig_roberts_compare(matches: list[dict]) -> list[str]:
    usable = [m for m in matches if m["delta_vs_roberts_mid"] is not None]
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    xs = [m["roberts_mid_deg"] for m in usable]
    ys = [m["azimuth_display_deg"] for m in usable]
    flags = [m["flag"] for m in usable]
    col = {"agree": AGREE, "look": LOOK, "disagree": DISAGREE}
    for flag in ("agree", "look", "disagree"):
        fx = [x for x, f in zip(xs, flags) if f == flag]
        fy = [y for y, f in zip(ys, flags) if f == flag]
        ax.scatter(
            fx,
            fy,
            s=36,
            c=col[flag],
            edgecolors="white",
            linewidths=0.4,
            zorder=3,
            label=f"{flag} (n={len(fx)})",
        )
    ax.plot([0, 180], [0, 180], color=MUTED, lw=0.8)
    ax.fill_between([0, 180], [-22.5, 157.5], [22.5, 202.5], color=AGREE, alpha=0.08, zorder=0)
    ax.set_xlim(0, 180)
    ax.set_ylim(0, 180)
    ax.set_aspect("equal")
    ax.set_xlabel("Roberts et al. IA 47 orientation (quadrant midpoint, °)")
    ax.set_ylabel("This gazetteer display axis (°)")
    ax.set_title("SWHS / environs: eye-reviewed display vs published compass class")
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    # label disagreements
    for m in usable:
        if m["flag"] == "disagree":
            ax.annotate(
                m["roberts_abbr"],
                (m["roberts_mid_deg"], m["azimuth_display_deg"]),
                textcoords="offset points",
                xytext=(4, 4),
                fontsize=7,
                color=DISAGREE,
            )
    return savefig(fig, "fig-10-vs-roberts")


def fig_ridge_delta(ridge_rows: list[dict]) -> list[str]:
    d_ridge = np.array([r["delta_vs_ridge"] for r in ridge_rows])
    d_ms = np.array([r["delta_vs_midsummer"] for r in ridge_rows])
    d_mw = np.array([r["delta_vs_midwinter"] for r in ridge_rows])
    d_sol = np.minimum(d_ms, d_mw)
    n = len(d_ridge)
    bins = np.arange(0, 95, 5)
    # Chance: |Δ| to one random undirected axis is uniform on 0–90.
    expected_one = n * (5.0 / 90.0)
    rng = np.random.default_rng(1)
    u = rng.uniform(0, 180, 200_000)

    def ud(a, b):
        d = np.abs(a - b) % 180.0
        return np.minimum(d, 180.0 - d)

    ns = np.minimum(ud(u, 50.2), ud(u, 129.0))
    exp_sol, _ = np.histogram(ns, bins=bins)
    exp_sol = exp_sol * (n / len(ns))

    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.6), sharey=True)
    specs = [
        (axes[0], d_ridge, RIDGE, "Display vs local ridge", 45.0, expected_one),
        (axes[1], d_ms, SOLAR, "Display vs midsummer sunrise", 45.0, expected_one),
        (axes[2], d_sol, "#6a4a7a", "Display vs nearest solstice", 22.4, None),
    ]
    for ax, data, col, title, chance_med, exp in specs:
        ax.hist(data, bins=bins, color=col, edgecolor="white", linewidth=0.4)
        if exp is None:
            ax.plot(bins[:-1] + 2.5, exp_sol, color=MUTED, ls=":", lw=1.2, label="chance")
        else:
            ax.axhline(exp, color=MUTED, ls=":", lw=1.1, label="chance")
        ax.axvline(chance_med, color=MUTED, ls="--", lw=0.8)
        ax.set_title(f"{title}\nmedian {np.median(data):.0f}°  (chance {chance_med:.0f}°)")
        ax.set_xlabel("|Δ| undirected (°)")
        ax.set_xlim(0, 90)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    axes[0].set_ylabel("Count")
    axes[0].legend(frameon=False, fontsize=7, loc="upper right")
    fig.tight_layout()
    return savefig(fig, "fig-11-ridge-vs-solstice")


def fig_axis_vs_ridge_scatter(ridge_rows: list[dict]) -> list[str]:
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    xs = [r["ridge_deg"] for r in ridge_rows]
    ys = [r["azimuth_display_deg"] for r in ridge_rows]
    sl = [r["slope_deg"] for r in ridge_rows]
    sc = ax.scatter(
        xs,
        ys,
        c=sl,
        cmap="YlOrBr",
        s=28,
        edgecolors="white",
        linewidths=0.3,
        zorder=3,
    )
    ax.plot([0, 180], [0, 180], color=MUTED, lw=0.8)
    ax.set_xlim(0, 180)
    ax.set_ylim(0, 180)
    ax.set_aspect("equal")
    ax.set_xlabel("Local ridge / contour orientation (°)")
    ax.set_ylabel("Display long-axis (°)")
    ax.set_title("Do display axes follow the local ridge?")
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Local slope of fitted plane (°)")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    return savefig(fig, "fig-12-axis-vs-ridge")


def fig_review_queue(matches: list[dict]) -> list[str]:
    q = [m for m in matches if m["flag"] in ("look", "disagree")]
    q.sort(key=lambda m: -(m["delta_vs_roberts_mid"] or 0))
    if not q:
        return []
    fig, ax = plt.subplots(figsize=(8.0, max(2.8, 0.38 * len(q) + 1.2)))
    labels = [
        f"{m['roberts_abbr']}  {m['display_name'] or m['gazetteer_id']}"
        for m in q
    ]
    vals = [m["delta_vs_roberts_mid"] for m in q]
    colours = [DISAGREE if m["flag"] == "disagree" else LOOK for m in q]
    ax.barh(range(len(q)), vals, color=colours, edgecolor="white")
    ax.set_yticks(range(len(q)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.axvline(22.5, color=MUTED, ls="--", lw=0.9)
    ax.axvline(45, color=DISAGREE, ls=":", lw=0.9)
    ax.set_xlabel("Undirected |Δ| vs Roberts quadrant midpoint (°)")
    ax.set_title("Re-review queue: display axis vs published SWHS class")
    ax.invert_yaxis()
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    return savefig(fig, "fig-13-rereview-queue")


def fig_map_ridge(sample: list[dict], ridge_map: dict) -> list[str]:
    fig, ax = plt.subplots(figsize=(7.2, 8.0))
    half = 900.0
    for r in sample:
        rec = ridge_map.get(r["id"])
        if not rec or not rec.get("ok"):
            continue
        az = math.radians(float(r["azimuth_display_deg"]))
        dx, dy = math.sin(az) * half, math.cos(az) * half
        ax.plot(
            [r["easting"] - dx, r["easting"] + dx],
            [r["northing"] - dy, r["northing"] + dy],
            color=DISPLAY,
            lw=1.2,
            solid_capstyle="round",
            zorder=3,
        )
        rz = math.radians(float(rec["ridge_deg"]))
        rx, ry = math.sin(rz) * half * 0.7, math.cos(rz) * half * 0.7
        ax.plot(
            [r["easting"] - rx, r["easting"] + rx],
            [r["northing"] - ry, r["northing"] + ry],
            color=RIDGE,
            lw=0.7,
            alpha=0.7,
            zorder=2,
        )
    ax.plot([], [], color=DISPLAY, lw=2, label="display axis")
    ax.plot([], [], color=RIDGE, lw=1.4, label="local ridge (DTM plane)")
    ax.set_aspect("equal")
    ax.set_xlabel("Easting (OSGB, m)")
    ax.set_ylabel("Northing (OSGB, m)")
    ax.set_title("Display axes (green) against local ridge (brown)")
    ax.legend(frameon=False, loc="lower left", fontsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.ticklabel_format(style="plain")
    return savefig(fig, "fig-14-map-ridge")


def main() -> None:
    setup_style()
    rows = load_rows()
    sample = display_sample(rows)
    print("n_display", len(sample))

    matches = match_roberts(rows)
    write_csv(
        OUTDIR / "roberts_match.csv",
        matches,
        [
            "roberts_abbr",
            "roberts_grinsell",
            "roberts_smr",
            "roberts_orientation",
            "roberts_mid_deg",
            "gazetteer_id",
            "display_name",
            "match_dist_m",
            "azimuth_display_deg",
            "azimuth_prefer",
            "delta_vs_roberts_mid",
            "flag",
            "status",
            "cluster",
        ],
    )
    flags = {}
    for m in matches:
        flags[m["flag"]] = flags.get(m["flag"], 0) + 1
    print("roberts flags", flags)
    for m in matches:
        if m["flag"] in ("look", "disagree"):
            print(
                f"  {m['flag']:9} {m['roberts_abbr']:6} {m['gazetteer_id']} "
                f"pub={m['roberts_orientation']} mid={m['roberts_mid_deg']} "
                f"display={m['azimuth_display_deg']} d={m['delta_vs_roberts_mid']}"
            )

    # Fetch landscape chips
    need = [r for r in sample]
    print(f"fetching landscape DTM for {len(need)} display sites…")
    fetched = 0
    for i, r in enumerate(need, 1):
        p = chip_path(r["id"])
        if p.is_file() and p.stat().st_size > 2000:
            continue
        got = fetch_landscape_chip(r["easting"], r["northing"], r["id"])
        fetched += int(got is not None)
        print(f"  [{i}/{len(need)}] {r['id']} {'ok' if got else 'FAIL'}")
        time.sleep(SLEEP_S)
    print("newly fetched", fetched)

    ridge_rows = []
    ridge_map = {}
    for r in sample:
        rec = ridge_for_row(r)
        ridge_map[r["id"]] = rec
        if not rec.get("ok"):
            print("ridge fail", r["id"], rec)
            continue
        az = float(r["azimuth_display_deg"])
        d_ridge = undirected_delta(az, rec["ridge_deg"])
        d_across = undirected_delta(az, rec["downslope_deg"] % 180.0)
        row = {
            "id": r["id"],
            "display_name": r.get("display_name"),
            "cluster": r.get("cluster"),
            "barrow_type": r.get("barrow_type"),
            "azimuth_display_deg": az,
            "ridge_deg": rec["ridge_deg"],
            "downslope_deg": rec["downslope_deg"],
            "slope_deg": rec["slope_deg"],
            "plane_rmse_m": rec["plane_rmse_m"],
            "delta_vs_ridge": round(d_ridge, 2),
            "delta_vs_downslope": round(d_across, 2),
            "delta_vs_midsummer": round(undirected_delta(az, SUNRISE_AZ["midsummer"]), 2),
            "delta_vs_equinox": round(undirected_delta(az, SUNRISE_AZ["equinox"]), 2),
            "delta_vs_midwinter": round(undirected_delta(az, SUNRISE_AZ["midwinter"]), 2),
        }
        ridge_rows.append(row)

    write_csv(
        OUTDIR / "ridge_vs_axis.csv",
        ridge_rows,
        list(ridge_rows[0].keys()) if ridge_rows else ["id"],
    )

    d_ridge = np.array([r["delta_vs_ridge"] for r in ridge_rows])
    d_sol = np.array(
        [min(r["delta_vs_midsummer"], r["delta_vs_midwinter"]) for r in ridge_rows]
    )
    d_eq = np.array([r["delta_vs_equinox"] for r in ridge_rows])
    steep = [r for r in ridge_rows if r["slope_deg"] >= 1.0]
    d_ridge_steep = np.array([r["delta_vs_ridge"] for r in steep]) if steep else np.array([])

    def summarise(arr):
        if len(arr) == 0:
            return {}
        return {
            "n": int(len(arr)),
            "median": round(float(np.median(arr)), 2),
            "mean": round(float(np.mean(arr)), 2),
            "lt15": int(np.sum(arr <= 15)),
            "lt22_5": int(np.sum(arr <= 22.5)),
            "lt30": int(np.sum(arr <= 30)),
        }

    azs = np.array([r["azimuth_display_deg"] for r in ridge_rows])
    overall_mean, overall_R, overall_p = rayleigh_p(azs)

    stats = {
        "n_display": len(sample),
        "n_ridge_ok": len(ridge_rows),
        "roberts_flags": flags,
        "roberts_n_compared": sum(1 for m in matches if m["delta_vs_roberts_mid"] is not None),
        "delta_vs_ridge": summarise(d_ridge),
        "delta_vs_nearest_solstice": summarise(d_sol),
        "delta_vs_equinox": summarise(d_eq),
        "delta_vs_ridge_slope_ge_1deg": summarise(d_ridge_steep),
        "chance_median_undirected": 45.0,
        "display_rayleigh": {
            "n": int(len(azs)),
            "mean": round(overall_mean, 2),
            "R": round(overall_R, 4),
            "p": overall_p,
        },
        "v_midsummer": v_test(azs, SUNRISE_AZ["midsummer"]),
        "v_equinox": v_test(azs, SUNRISE_AZ["equinox"]),
        "v_midwinter": v_test(azs, SUNRISE_AZ["midwinter"]),
        "ridge_following_lt22": int(np.sum(d_ridge <= 22.5)),
        "across_slope_lt22": int(np.sum(np.array([r["delta_vs_downslope"] for r in ridge_rows]) <= 22.5)),
        "solstice_lt15": int(np.sum(d_sol <= 15)),
        "rereview_axis": [
            {
                "abbr": m["roberts_abbr"],
                "id": m["gazetteer_id"],
                "name": m["display_name"],
                "published": m["roberts_orientation"],
                "display": m["azimuth_display_deg"],
                "delta": m["delta_vs_roberts_mid"],
                "flag": m["flag"],
                "prefer": m["azimuth_prefer"],
                "match_dist_m": m["match_dist_m"],
            }
            for m in matches
            if m["flag"] in ("look", "disagree")
        ],
        "rereview_excluded_but_published": [
            {
                "abbr": m["roberts_abbr"],
                "id": m["gazetteer_id"],
                "name": m["display_name"],
                "published": m["roberts_orientation"],
                "prefer": m["azimuth_prefer"],
                "match_dist_m": m["match_dist_m"],
            }
            for m in matches
            if m["flag"] == "no_display"
        ],
        "identity_mismatch": [
            {
                "abbr": m["roberts_abbr"],
                "id": m["gazetteer_id"],
                "name": m["display_name"],
                "match_dist_m": m["match_dist_m"],
            }
            for m in matches
            if m["flag"] == "identity_mismatch"
        ],
    }
    (OUTDIR / "robust_stats.json").write_text(
        json.dumps(stats, indent=2) + "\n", encoding="utf-8"
    )
    print("ridge", stats["delta_vs_ridge"])
    print("solstice", stats["delta_vs_nearest_solstice"])
    print("equinox", stats["delta_vs_equinox"])
    print("steep ridge", stats["delta_vs_ridge_slope_ge_1deg"])

    fig_roberts_compare(matches)
    fig_review_queue(matches)
    if ridge_rows:
        fig_ridge_delta(ridge_rows)
        fig_axis_vs_ridge_scatter(ridge_rows)
        fig_map_ridge(sample, ridge_map)
    print("wrote", OUTDIR / "robust_stats.json")


if __name__ == "__main__":
    main()

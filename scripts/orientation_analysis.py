#!/usr/bin/env python3
"""Axial analysis of Wiltshire long-barrow display azimuths.

Read-only on data/long_barrows.json (never writes NHLE or display fields).
Writes figures under docs/analysis/ and tables under
scripts/orientation_batch_out/analysis/.

Primary sample: rows with azimuth_display_deg set (n=86). Excludes
prefer=not_barrow and leave_indistinct. Skips MODERN_ALL_CANNINGS if present.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "long_barrows.json"
GEOJSON = ROOT / "data" / "long_barrows.geojson"
FIGDIR = ROOT / "docs" / "analysis"
OUTDIR = ROOT / "scripts" / "orientation_batch_out" / "analysis"

# Same flat-horizon sunrise values as generate.py (≈51.2°N, true solar, no refraction).
SUNRISE_AZ = {
    "midsummer": 50.2,
    "equinox": 89.7,
    "midwinter": 129.0,
}
LAT_REF = 51.2

EXCLUDE_PREFER = frozenset({"not_barrow", "leave_indistinct"})
SKIP_IDS = frozenset({"MODERN_ALL_CANNINGS"})
SEED = 20260908
N_BOOT = 10_000

INK = "#1a1814"
MUTED = "#6a6258"
LINE = "#d9d0c4"
GOLD = "#c9a227"
DISPLAY = "#2f5d4a"
NHLE = "#2c5aa0"
LIDAR = "#c49212"
SOLAR = "#9a3b32"
EARTHEN = "#4a5c6a"
CS = "#8a4a2a"

CLUSTER_COLOUR = {
    "Stonehenge / Salisbury Plain": "#c9a227",
    "Avebury / Pewsey": "#3d7a62",
    "North Wiltshire chalk": "#4a6a9a",
    "Wiltshire chalk": "#8a5a3a",
    "South Wiltshire / Chase fringe": "#6a4a7a",
}


def undirected_delta(a: float, b: float) -> float:
    d = abs(float(a) - float(b)) % 180.0
    return min(d, 180.0 - d)


def axial_mean_R(deg: np.ndarray) -> tuple[float, float]:
    """Mean axis (0–180) and mean resultant length of doubled angles."""
    rad = np.deg2rad(np.asarray(deg, dtype=float) * 2.0)
    C = float(np.mean(np.cos(rad)))
    S = float(np.mean(np.sin(rad)))
    R = math.hypot(C, S)
    mean = (math.degrees(math.atan2(S, C)) / 2.0) % 180.0
    return mean, R


def rayleigh_axial(deg: np.ndarray) -> dict:
    """Rayleigh test of uniformity on doubled (axial) angles.

    p uses the Mardia–Jupp large-n approximation (n ≥ 50 is comfortable).
    """
    n = int(len(deg))
    mean, R = axial_mean_R(deg)
    Z = n * R * R
    p = math.exp(-Z) * (
        1.0
        + (2.0 * Z - Z * Z) / (4.0 * n)
        - (24.0 * Z - 132.0 * Z * Z + 76.0 * Z**3 - 9.0 * Z**4) / (288.0 * n * n)
    )
    p = float(min(1.0, max(0.0, p)))
    circ_sd_doubled = math.sqrt(-2.0 * math.log(max(R, 1e-15)))
    circ_sd_axial = math.degrees(circ_sd_doubled / 2.0)
    return {
        "n": n,
        "mean_deg": round(mean, 2),
        "R": round(R, 4),
        "Z": round(Z, 3),
        "p": p,
        "circ_sd_axial_deg": round(circ_sd_axial, 2),
        "circ_var": round(1.0 - R, 4),
    }


def v_test_axial(deg: np.ndarray, theta0: float) -> dict:
    """V-test of concentration about a specified undirected axis."""
    n = int(len(deg))
    rad = np.deg2rad(np.asarray(deg, dtype=float) * 2.0)
    th0 = math.radians(float(theta0) * 2.0)
    C = float(np.mean(np.cos(rad - th0)))
    u = C * math.sqrt(2.0 * n)
    p = float(1.0 - norm.cdf(u))
    mean, R = axial_mean_R(deg)
    return {
        "theta0_deg": theta0,
        "Vbar": round(C, 4),
        "u": round(u, 3),
        "p": p,
        "mean_deg": round(mean, 2),
        "R": round(R, 4),
    }


def bootstrap_mean_R(deg: np.ndarray, rng: np.random.Generator) -> dict:
    n = len(deg)
    means = np.empty(N_BOOT)
    Rs = np.empty(N_BOOT)
    for i in range(N_BOOT):
        sample = rng.choice(deg, size=n, replace=True)
        m, R = axial_mean_R(sample)
        means[i] = m
        Rs[i] = R
    # Wrap-aware percentile CI around the point mean.
    point_mean, point_R = axial_mean_R(deg)
    wrapped = ((means - point_mean + 90.0) % 180.0) - 90.0
    lo_dev = float(np.percentile(wrapped, 2.5))
    hi_dev = float(np.percentile(wrapped, 97.5))
    span = hi_dev - lo_dev
    # Axial mean is unidentified when bootstrap spread covers half the 0–180 circle.
    if span >= 90.0:
        mean_ci95 = None
        mean_identified = False
    else:
        mean_ci95 = [
            round((point_mean + lo_dev) % 180.0, 2),
            round((point_mean + hi_dev) % 180.0, 2),
        ]
        mean_identified = True
    return {
        "mean_deg": round(point_mean, 2),
        "mean_identified": mean_identified,
        "mean_ci95": mean_ci95,
        "R": round(point_R, 4),
        "R_ci95": [
            round(float(np.percentile(Rs, 2.5)), 4),
            round(float(np.percentile(Rs, 97.5)), 4),
        ],
    }


def bin_counts(deg: np.ndarray, width: float) -> dict:
    edges = np.arange(0.0, 180.0 + width, width)
    counts, _ = np.histogram(deg % 180.0, bins=edges)
    expected = len(deg) / (180.0 / width)
    return {
        "width_deg": width,
        "edges": edges.tolist(),
        "counts": counts.tolist(),
        "expected_uniform": round(expected, 3),
        "max_bin": int(counts.max()) if len(counts) else 0,
        "max_bin_lo": float(edges[int(np.argmax(counts))]) if len(counts) else None,
    }


def nhle_fingerprint(rows: list[dict]) -> str:
    payload = json.dumps(
        [(r["id"], r.get("azimuth_deg"), r.get("azimuth_method")) for r in rows],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


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
            "axes.grid": False,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "figure.dpi": 120,
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
        }
    )


def savefig(fig: plt.Figure, stem: str) -> list[str]:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("svg", "png"):
        p = FIGDIR / f"{stem}.{ext}"
        fig.savefig(p)
        paths.append(str(p.relative_to(ROOT)).replace("\\", "/"))
    plt.close(fig)
    return paths


def solar_lines(ax, ymax: float, *, polar: bool = False) -> None:
    labels = {
        "midsummer": "MS",
        "equinox": "Eq",
        "midwinter": "MW",
    }
    first = True
    for key, az in SUNRISE_AZ.items():
        if polar:
            for a in (az, az + 180.0):
                ax.plot(
                    [math.radians(a), math.radians(a)],
                    [0, ymax],
                    color=SOLAR,
                    lw=1.0,
                    ls="--",
                    alpha=0.85,
                    zorder=3,
                )
            ax.text(
                math.radians(az),
                ymax * 1.06,
                labels[key],
                color=SOLAR,
                fontsize=8,
                ha="left" if key != "equinox" else "left",
                va="bottom",
            )
        else:
            ax.axvline(
                az,
                color=SOLAR,
                lw=1.0,
                ls="--",
                alpha=0.85,
                zorder=2,
                label="flat-horizon sunrise (descriptive)" if first else None,
            )
            first = False


def fig_rose(deg: np.ndarray) -> list[str]:
    width = 10.0
    edges = np.arange(0.0, 180.0 + width, width)
    counts, _ = np.histogram(deg % 180.0, bins=edges)
    theta = np.deg2rad(np.concatenate([edges[:-1], edges[:-1] + 180.0]))
    radii = np.concatenate([counts, counts]).astype(float)
    bar_w = np.deg2rad(width)
    ymax = float(radii.max()) * 1.15

    fig, ax = plt.subplots(figsize=(6.4, 6.4), subplot_kw={"projection": "polar"})
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.bar(
        theta + bar_w / 2.0,
        radii,
        width=bar_w * 0.92,
        align="center",
        color=DISPLAY,
        edgecolor="white",
        linewidth=0.4,
        alpha=0.9,
        zorder=2,
    )
    solar_lines(ax, ymax, polar=True)
    ax.set_ylim(0, ymax)
    ax.set_yticks([2, 4, 6, 8])
    ax.tick_params(axis="y", labelsize=8)
    ax.tick_params(axis="x", labelsize=8)
    ax.set_title(
        "Display long-axis rose (undirected; each barrow drawn both ways)\n"
        "Dashed lines = flat-horizon sunrise, descriptive only — not intent",
        pad=16,
    )
    fig.text(
        0.5,
        0.02,
        f"n = {len(deg)}  ·  10° bins  ·  Wiltshire long barrows",
        ha="center",
        fontsize=8,
        color=MUTED,
    )
    return savefig(fig, "fig-01-rose-display")


def fig_histogram(deg: np.ndarray, width: float, stem: str) -> list[str]:
    edges = np.arange(0.0, 180.0 + width, width)
    counts, _ = np.histogram(deg % 180.0, bins=edges)
    expected = len(deg) / (180.0 / width)
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.bar(
        edges[:-1],
        counts,
        width=width * 0.92,
        align="edge",
        color=DISPLAY,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.axhline(expected, color=MUTED, ls=":", lw=1.1, label=f"uniform expectation ({expected:.1f})")
    ymax = max(float(counts.max()) * 1.18, expected * 1.3)
    solar_lines(ax, ymax * 0.96, polar=False)
    ax.set_xlim(0, 180)
    ax.set_ylim(0, ymax)
    ax.set_xticks(np.arange(0, 181, 15 if width == 15 else 10))
    ax.set_xlabel("Undirected azimuth (° from N, 0–180)")
    ax.set_ylabel("Count")
    ax.set_title(f"Display long-axis histogram ({int(width)}° bins, n={len(deg)})")
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(LINE)
    ax.spines["bottom"].set_color(LINE)
    return savefig(fig, stem)


def fig_deltas(pairs: dict[str, np.ndarray]) -> list[str]:
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.4), sharey=True)
    titles = {
        "display_vs_nhle": "Display vs NHLE",
        "display_vs_lidar": "Display vs LiDAR",
        "nhle_vs_lidar": "NHLE vs LiDAR",
    }
    colours = {
        "display_vs_nhle": NHLE,
        "display_vs_lidar": LIDAR,
        "nhle_vs_lidar": MUTED,
    }
    bins = np.arange(0, 95, 5)
    for ax, key in zip(axes, titles):
        d = pairs[key]
        ax.hist(d, bins=bins, color=colours[key], edgecolor="white", linewidth=0.4)
        ax.set_title(f"{titles[key]}\nn={len(d)}")
        ax.set_xlim(0, 90)
        ax.set_xlabel("|Δ| undirected (°)")
        ax.axvline(15, color=SOLAR, ls="--", lw=0.9, alpha=0.8)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    axes[0].set_ylabel("Count")
    fig.suptitle("Undirected absolute difference (dashed = 15° review threshold)", y=1.03)
    fig.tight_layout()
    return savefig(fig, "fig-04-delta-distributions")


def fig_scatter(rows: list[dict]) -> list[str]:
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 4.2), sharex=True, sharey=True)

    def scatter(ax, xkey, ykey, xlabel, ylabel, colour):
        xs, ys = [], []
        for r in rows:
            if r.get(xkey) is None or r.get(ykey) is None:
                continue
            xs.append(float(r[xkey]))
            ys.append(float(r[ykey]))
        ax.scatter(xs, ys, s=18, c=colour, alpha=0.75, edgecolors="white", linewidths=0.4, zorder=3)
        ax.plot([0, 180], [0, 180], color=MUTED, lw=0.8, zorder=1)
        ax.plot([0, 90], [90, 180], color=LINE, ls=":", lw=0.9, zorder=1)
        ax.plot([90, 180], [0, 90], color=LINE, ls=":", lw=0.9, zorder=1)
        ax.set_xlim(0, 180)
        ax.set_ylim(0, 180)
        ax.set_aspect("equal")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(f"n={len(xs)}")
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

    scatter(axes[0], "azimuth_deg", "azimuth_display_deg", "NHLE PCA (°)", "Display (°)", NHLE)
    scatter(axes[1], "azimuth_lidar_deg", "azimuth_display_deg", "LiDAR PCA (°)", "Display (°)", LIDAR)
    fig.suptitle("Paired axes (solid = identity; dotted = 90° offset / wrap)", y=1.02)
    fig.tight_layout()
    return savefig(fig, "fig-05-display-vs-nhle-lidar")


def fig_by_cluster(rows: list[dict]) -> list[str]:
    clusters = sorted({r.get("cluster") or "—" for r in rows})
    n = len(clusters)
    fig, axes = plt.subplots(1, n, figsize=(2.2 * n, 3.6), subplot_kw={"projection": "polar"})
    if n == 1:
        axes = [axes]
    width = 15.0
    edges = np.arange(0.0, 180.0 + width, width)
    bar_w = np.deg2rad(width)
    ymax_global = 1
    prepared = []
    for cl in clusters:
        deg = np.array(
            [float(r["azimuth_display_deg"]) for r in rows if (r.get("cluster") or "—") == cl]
        )
        counts, _ = np.histogram(deg % 180.0, bins=edges)
        prepared.append((cl, deg, counts))
        ymax_global = max(ymax_global, int(counts.max()))
    ymax = ymax_global * 1.25
    for ax, (cl, deg, counts) in zip(axes, prepared):
        theta = np.deg2rad(np.concatenate([edges[:-1], edges[:-1] + 180.0]))
        radii = np.concatenate([counts, counts]).astype(float)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.bar(
            theta + bar_w / 2.0,
            radii,
            width=bar_w * 0.92,
            align="center",
            color=CLUSTER_COLOUR.get(cl, DISPLAY),
            edgecolor="white",
            linewidth=0.3,
        )
        for az in SUNRISE_AZ.values():
            for a in (az, az + 180.0):
                ax.plot(
                    [math.radians(a), math.radians(a)],
                    [0, ymax],
                    color=SOLAR,
                    lw=0.6,
                    ls="--",
                    alpha=0.7,
                )
        ax.set_ylim(0, ymax)
        ax.set_yticks([])
        ax.tick_params(axis="x", labelsize=6)
        ax.set_title(f"{cl}\nn={len(deg)}", fontsize=8, pad=10)
    fig.suptitle("Display axes by cluster (15° bins; solar dashes descriptive)", y=1.08)
    fig.tight_layout()
    return savefig(fig, "fig-06-by-cluster")


def fig_by_type(rows: list[dict]) -> list[str]:
    earthen = np.array(
        [float(r["azimuth_display_deg"]) for r in rows if r.get("barrow_type") == "earthen"]
    )
    cs = np.array(
        [
            float(r["azimuth_display_deg"])
            for r in rows
            if r.get("barrow_type") == "cotswold_severn"
        ]
    )
    width = 10.0
    edges = np.arange(0.0, 180.0 + width, width)
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.hist(
        earthen,
        bins=edges,
        color=EARTHEN,
        edgecolor="white",
        linewidth=0.4,
        label=f"earthen (n={len(earthen)})",
    )
    if len(cs):
        ax.scatter(
            cs,
            np.full_like(cs, 0.35, dtype=float),
            marker="|",
            s=220,
            c=CS,
            linewidths=1.6,
            zorder=4,
            label=f"Cotswold–Severn (n={len(cs)})",
        )
    ymax = ax.get_ylim()[1]
    solar_lines(ax, ymax * 0.96, polar=False)
    ax.set_xlim(0, 180)
    ax.set_xlabel("Undirected azimuth (° from N)")
    ax.set_ylabel("Count (earthen)")
    ax.set_title("Display axes by barrow type")
    ax.legend(frameon=False, loc="upper right", fontsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    return savefig(fig, "fig-07-by-type")


def fig_map(rows: list[dict], excluded: list[dict]) -> list[str]:
    fig, ax = plt.subplots(figsize=(7.2, 8.0))
    if excluded:
        ax.scatter(
            [r["easting"] for r in excluded],
            [r["northing"] for r in excluded],
            s=12,
            c="#c8c0b6",
            marker="x",
            linewidths=0.6,
            label=f"excluded (n={len(excluded)})",
            zorder=2,
        )
    half = 900.0  # metres: half-length of drawn axis tick
    for r in rows:
        az = math.radians(float(r["azimuth_display_deg"]))
        dx = math.sin(az) * half
        dy = math.cos(az) * half
        col = CLUSTER_COLOUR.get(r.get("cluster") or "", DISPLAY)
        ax.plot(
            [r["easting"] - dx, r["easting"] + dx],
            [r["northing"] - dy, r["northing"] + dy],
            color=col,
            lw=1.15,
            solid_capstyle="round",
            zorder=3,
        )
    # dummy handles for cluster legend
    for cl, col in CLUSTER_COLOUR.items():
        ncl = sum(1 for r in rows if r.get("cluster") == cl)
        if ncl:
            ax.plot([], [], color=col, lw=2.2, label=f"{cl} (n={ncl})")
    ax.set_aspect("equal")
    ax.set_xlabel("Easting (OSGB, m)")
    ax.set_ylabel("Northing (OSGB, m)")
    ax.set_title("Display long-axis ticks (undirected) on the Wiltshire chalk")
    ax.legend(frameon=False, fontsize=7.5, loc="lower left")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.ticklabel_format(style="plain")
    return savefig(fig, "fig-08-map-axes")


def fig_exclusions(rows: list[dict]) -> list[str]:
    c = Counter(r.get("azimuth_prefer") for r in rows)
    order = ["eye", "lidar", "nhle", "leave_indistinct", "not_barrow"]
    labels = {
        "eye": "eye (display)",
        "lidar": "lidar (display)",
        "nhle": "nhle (display)",
        "leave_indistinct": "leave_indistinct",
        "not_barrow": "not_barrow",
    }
    colours = {
        "eye": DISPLAY,
        "lidar": LIDAR,
        "nhle": NHLE,
        "leave_indistinct": "#a09080",
        "not_barrow": "#b07070",
    }
    vals = [c.get(k, 0) for k in order]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    bars = ax.bar(
        [labels[k] for k in order],
        vals,
        color=[colours[k] for k in order],
        edgecolor="white",
    )
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, str(v), ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Gazetteer rows")
    ax.set_title("Human prefer decisions (128/128) — display = eye + lidar + nhle = 86")
    ax.set_ylim(0, max(vals) * 1.18)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    return savefig(fig, "fig-09-prefer-counts")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def group_stats(deg: np.ndarray, rng: np.random.Generator) -> dict:
    if len(deg) < 2:
        mean, R = axial_mean_R(deg) if len(deg) else (None, None)
        return {"n": int(len(deg)), "mean_deg": mean, "R": R}
    st = rayleigh_axial(deg)
    st["bootstrap"] = bootstrap_mean_R(deg, rng)
    st["v_midsummer"] = v_test_axial(deg, SUNRISE_AZ["midsummer"])
    st["v_equinox"] = v_test_axial(deg, SUNRISE_AZ["equinox"])
    st["v_midwinter"] = v_test_axial(deg, SUNRISE_AZ["midwinter"])
    st["bins_10"] = bin_counts(deg, 10.0)
    st["bins_15"] = bin_counts(deg, 15.0)
    return st


def main() -> None:
    setup_style()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)

    rows = load_rows()
    fp_before = nhle_fingerprint(rows)
    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    geo_props = [f["properties"] for f in geo["features"]]
    geo_fp = nhle_fingerprint(geo_props)

    prefer_counts = Counter(r.get("azimuth_prefer") for r in rows)
    display_source = Counter(r.get("azimuth_display_source") for r in rows)
    sample = display_sample(rows)
    excluded = [
        r
        for r in rows
        if r["id"] not in SKIP_IDS and r.get("azimuth_prefer") in EXCLUDE_PREFER
    ]
    modern_in_json = [r["id"] for r in rows if r["id"] in SKIP_IDS]

    deg = np.array([float(r["azimuth_display_deg"]) for r in sample])
    if np.any((deg < 0) | (deg > 180)):
        raise SystemExit("display azimuth outside 0–180")

    rng = np.random.default_rng(SEED)
    overall = group_stats(deg, rng)

    by_type: dict[str, dict] = {}
    for t in ("earthen", "cotswold_severn"):
        d = np.array(
            [float(r["azimuth_display_deg"]) for r in sample if r.get("barrow_type") == t]
        )
        by_type[t] = group_stats(d, rng)

    by_cluster: dict[str, dict] = {}
    for cl in sorted({r.get("cluster") or "—" for r in sample}):
        d = np.array(
            [float(r["azimuth_display_deg"]) for r in sample if (r.get("cluster") or "—") == cl]
        )
        by_cluster[cl] = group_stats(d, rng)

    by_status: dict[str, dict] = {}
    for st in ("certain", "possible"):
        d = np.array(
            [float(r["azimuth_display_deg"]) for r in sample if r.get("status") == st]
        )
        by_status[st] = group_stats(d, rng)

    def pair_delta(a_key: str, b_key: str, extra_filter=None) -> list[dict]:
        out = []
        for r in rows:
            if extra_filter and not extra_filter(r):
                continue
            if r.get(a_key) is None or r.get(b_key) is None:
                continue
            out.append(
                {
                    "id": r["id"],
                    "display_name": r.get("display_name"),
                    "a": float(r[a_key]),
                    "b": float(r[b_key]),
                    "delta": round(undirected_delta(r[a_key], r[b_key]), 2),
                    "prefer": r.get("azimuth_prefer"),
                    "barrow_type": r.get("barrow_type"),
                    "cluster": r.get("cluster"),
                }
            )
        return out

    d_disp_nhle = pair_delta("azimuth_display_deg", "azimuth_deg")
    d_disp_lidar = pair_delta("azimuth_display_deg", "azimuth_lidar_deg")
    d_nhle_lidar = pair_delta("azimuth_deg", "azimuth_lidar_deg")

    def summarise_deltas(items: list[dict]) -> dict:
        if not items:
            return {"n": 0}
        arr = np.array([x["delta"] for x in items])
        return {
            "n": len(arr),
            "median": round(float(np.median(arr)), 2),
            "mean": round(float(np.mean(arr)), 2),
            "p75": round(float(np.percentile(arr, 75)), 2),
            "p90": round(float(np.percentile(arr, 90)), 2),
            "gt15": int(np.sum(arr > 15)),
            "gt30": int(np.sum(arr > 30)),
            "gt60": int(np.sum(arr > 60)),
        }

    # Eye differed from both NHLE and LiDAR (review-queue threshold 15°).
    eye_vs_both = []
    for r in sample:
        if r.get("azimuth_prefer") != "eye":
            continue
        if r.get("azimuth_deg") is None or r.get("azimuth_lidar_deg") is None:
            continue
        dn = undirected_delta(r["azimuth_eye_deg"], r["azimuth_deg"])
        dl = undirected_delta(r["azimuth_eye_deg"], r["azimuth_lidar_deg"])
        rec = {
            "id": r["id"],
            "display_name": r.get("display_name"),
            "eye": r.get("azimuth_eye_deg"),
            "nhle": r.get("azimuth_deg"),
            "lidar": r.get("azimuth_lidar_deg"),
            "delta_vs_nhle": round(dn, 2),
            "delta_vs_lidar": round(dl, 2),
            "cluster": r.get("cluster"),
            "note": r.get("azimuth_prefer_note") or "",
        }
        if dn > 15 and dl > 15:
            rec["flag"] = "eye_differs_both_gt15"
            eye_vs_both.append(rec)
        elif dn > 15 or dl > 15:
            rec["flag"] = "eye_differs_one_gt15"

    orthogonal_nhle = [x for x in d_nhle_lidar if x["delta"] > 60]

    figures = {}
    figures["rose"] = fig_rose(deg)
    figures["hist10"] = fig_histogram(deg, 10.0, "fig-02-histogram-10deg")
    figures["hist15"] = fig_histogram(deg, 15.0, "fig-03-histogram-15deg")
    figures["deltas"] = fig_deltas(
        {
            "display_vs_nhle": np.array([x["delta"] for x in d_disp_nhle]),
            "display_vs_lidar": np.array([x["delta"] for x in d_disp_lidar]),
            "nhle_vs_lidar": np.array([x["delta"] for x in d_nhle_lidar]),
        }
    )
    figures["scatter"] = fig_scatter(sample)
    figures["cluster"] = fig_by_cluster(sample)
    figures["type"] = fig_by_type(sample)
    figures["map"] = fig_map(sample, excluded)
    figures["prefer"] = fig_exclusions(rows)

    sample_rows = []
    for r in sample:
        rec = {
            "id": r["id"],
            "display_name": r.get("display_name"),
            "status": r.get("status"),
            "barrow_type": r.get("barrow_type"),
            "cluster": r.get("cluster"),
            "lat": r.get("lat"),
            "lon": r.get("lon"),
            "easting": r.get("easting"),
            "northing": r.get("northing"),
            "azimuth_display_deg": r.get("azimuth_display_deg"),
            "azimuth_display_source": r.get("azimuth_display_source"),
            "azimuth_prefer": r.get("azimuth_prefer"),
            "azimuth_eye_deg": r.get("azimuth_eye_deg"),
            "azimuth_deg": r.get("azimuth_deg"),
            "azimuth_lidar_deg": r.get("azimuth_lidar_deg"),
            "azimuth_lidar_conf": r.get("azimuth_lidar_conf"),
            "delta_display_vs_nhle": (
                round(undirected_delta(r["azimuth_display_deg"], r["azimuth_deg"]), 2)
                if r.get("azimuth_deg") is not None
                else None
            ),
            "delta_display_vs_lidar": (
                round(undirected_delta(r["azimuth_display_deg"], r["azimuth_lidar_deg"]), 2)
                if r.get("azimuth_lidar_deg") is not None
                else None
            ),
            "azimuth_prefer_note": r.get("azimuth_prefer_note") or "",
        }
        sample_rows.append(rec)

    excl_rows = [
        {
            "id": r["id"],
            "display_name": r.get("display_name"),
            "status": r.get("status"),
            "barrow_type": r.get("barrow_type"),
            "cluster": r.get("cluster"),
            "azimuth_prefer": r.get("azimuth_prefer"),
            "azimuth_display_deg": r.get("azimuth_display_deg"),
            "azimuth_deg": r.get("azimuth_deg"),
            "azimuth_lidar_deg": r.get("azimuth_lidar_deg"),
            "azimuth_prefer_note": r.get("azimuth_prefer_note") or "",
        }
        for r in excluded
    ]

    write_csv(
        OUTDIR / "display_sample.csv",
        sample_rows,
        list(sample_rows[0].keys()) if sample_rows else ["id"],
    )
    write_csv(
        OUTDIR / "exclusions.csv",
        excl_rows,
        list(excl_rows[0].keys()) if excl_rows else ["id"],
    )
    write_csv(
        OUTDIR / "eye_differs_from_both.csv",
        eye_vs_both,
        [
            "id",
            "display_name",
            "eye",
            "nhle",
            "lidar",
            "delta_vs_nhle",
            "delta_vs_lidar",
            "cluster",
            "flag",
            "note",
        ],
    )
    write_csv(
        OUTDIR / "nhle_lidar_near_orthogonal.csv",
        orthogonal_nhle,
        ["id", "display_name", "a", "b", "delta", "prefer", "barrow_type", "cluster"],
    )

    # Re-read gazetteer to prove NHLE untouched by this script.
    rows_after = load_rows()
    fp_after = nhle_fingerprint(rows_after)
    if fp_after != fp_before:
        raise SystemExit("NHLE fingerprint changed — abort")

    stats = {
        "generated_from": str(DATA).replace("\\", "/"),
        "n_gazetteer": len(rows),
        "prefer_counts": dict(prefer_counts),
        "display_source_counts": {str(k): v for k, v in display_source.items()},
        "n_display": len(sample),
        "n_excluded": len(excluded),
        "excluded_prefer_counts": dict(Counter(r.get("azimuth_prefer") for r in excluded)),
        "modern_ids_in_json": modern_in_json,
        "n_display_certain": sum(1 for r in sample if r.get("status") == "certain"),
        "n_display_possible": sum(1 for r in sample if r.get("status") == "possible"),
        "n_display_earthen": sum(1 for r in sample if r.get("barrow_type") == "earthen"),
        "n_display_cotswold_severn": sum(
            1 for r in sample if r.get("barrow_type") == "cotswold_severn"
        ),
        "cotswold_severn_display": [
            {
                "id": r["id"],
                "display_name": r.get("display_name"),
                "azimuth_display_deg": r.get("azimuth_display_deg"),
                "source": r.get("azimuth_display_source"),
            }
            for r in sample
            if r.get("barrow_type") == "cotswold_severn"
        ],
        "cotswold_severn_excluded": [
            {
                "id": r["id"],
                "display_name": r.get("display_name"),
                "prefer": r.get("azimuth_prefer"),
            }
            for r in excluded
            if r.get("barrow_type") == "cotswold_severn"
        ],
        "sunrise_az_flat_horizon": SUNRISE_AZ,
        "lat_ref": LAT_REF,
        "overall": overall,
        "by_type": by_type,
        "by_cluster": by_cluster,
        "by_status": by_status,
        "pairwise": {
            "display_vs_nhle": summarise_deltas(d_disp_nhle),
            "display_vs_lidar": summarise_deltas(d_disp_lidar),
            "nhle_vs_lidar": summarise_deltas(d_nhle_lidar),
        },
        "n_all_three": sum(
            1
            for r in sample
            if r.get("azimuth_deg") is not None and r.get("azimuth_lidar_deg") is not None
        ),
        "eye_differs_from_both_gt15": eye_vs_both,
        "nhle_lidar_delta_gt60": orthogonal_nhle,
        "nhle_fingerprint_sha256_16": fp_before,
        "geojson_nhle_fingerprint_sha256_16": geo_fp,
        "nhle_untouched": fp_before == fp_after,
        "json_geojson_nhle_match": fp_before == geo_fp,
        "figures": figures,
        "seed": SEED,
        "n_boot": N_BOOT,
    }
    (OUTDIR / "stats.json").write_text(
        json.dumps(stats, indent=2, default=str) + "\n", encoding="utf-8"
    )

    print("n_gazetteer", len(rows))
    print("n_display", len(sample))
    print("prefer", dict(prefer_counts))
    print("overall", {k: overall[k] for k in ("n", "mean_deg", "R", "Z", "p", "circ_sd_axial_deg")})
    print("bootstrap", overall["bootstrap"])
    print("pairwise", stats["pairwise"])
    print("eye_vs_both", len(eye_vs_both))
    print("orthogonal_nhle_lidar", len(orthogonal_nhle))
    print("nhle_untouched", stats["nhle_untouched"], fp_before)
    print("wrote", OUTDIR / "stats.json")
    print("figures", FIGDIR)


if __name__ == "__main__":
    main()

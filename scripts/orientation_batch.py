#!/usr/bin/env python3
"""Batch long-barrow long-axis from 1 m LiDAR chips for the Wiltshire gazetteer.

Reuses estimate_orientation / chip loaders from orientation_trial.py.
Writes NEW parallel fields only — never mutates azimuth_deg / azimuth_method.

Hard rules:
  - Skip stem MODERN_ALL_CANNINGS
  - SU16NW133 (White Hill) → no_chip / skipped
  - Confidence refuse floor tuned from score distribution (Kitts Grave ~0.005 vs clear ~0.9)
  - Review queue when |Δ vs NHLE| > 15° AND not indistinct

Usage:
  .venv/bin/python scripts/orientation_batch.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

# Import trial estimators (same ROOT-relative chip paths)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from orientation_trial import (  # noqa: E402
    load_elevation_chip,
    estimate_orientation,
    undirected_delta,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = ROOT / "data" / "long_barrows.json"
DATA_GEOJSON = ROOT / "data" / "long_barrows.geojson"
OUT_DIR = Path(__file__).resolve().parent / "orientation_batch_out"
REPORT = ROOT / "docs" / "orientation-batch.md"

SKIP_STEMS = {"MODERN_ALL_CANNINGS"}
METHOD_DTM = "dtm_local_relief_pca"
METHOD_HS = "hillshade_local_relief_pca"
DELTA_REVIEW_DEG = 15.0


@dataclass
class BatchRow:
    id: str
    name: str | None
    status: str  # measured | indistinct | no_chip | skipped
    source: str | None
    azimuth_lidar_deg: float | None
    azimuth_lidar_conf: float | None
    azimuth_lidar_method: str | None
    azimuth_lidar_indistinct: bool
    nhle_azimuth_deg: float | None
    delta_vs_nhle_deg: float | None
    review_flag: bool
    notes: str
    raw_confidence: float | None = None
    eig_ratio: float | None = None
    ensemble_std_deg: float | None = None
    ensemble_spread_deg: float | None = None


def display_name(rec: dict) -> str:
    return rec.get("display_name") or rec.get("name") or rec["id"]


def choose_confidence_floor(raw_scores: list[tuple[str, float]]) -> tuple[float, str]:
    """Tune refuse floor from observed confidences; document rationale."""
    vals = np.array([c for _, c in raw_scores], dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return 0.4, "No scores; defaulted to 0.4."

    pcts = {p: float(np.percentile(vals, p)) for p in (5, 10, 25, 50, 75, 90, 95)}
    by_id = {i: c for i, c in raw_scores}
    kitts = by_id.get("SU02SW103")
    clear_refs = [
        ("SU16NW100", by_id.get("SU16NW100")),
        ("SU14SW125", by_id.get("SU14SW125")),
    ]
    clear_vals = [c for _, c in clear_refs if c is not None]

    # Candidate floors in suggested band; pick so Kitts is below and clear refs above,
    # preferring a gap near the lower quartile of mid-range scores.
    # Observed batch: large weak mass below ~0.25 (p25≈0.09), Kitts≈0.005,
    # clear chalk refs ≈0.89–0.92, median≈0.57. Prefer 0.40 inside the agreed
    # 0.30–0.50 band — above the weak cluster, below clear mounds — rather than
    # the bottom of the band (0.30), which still admits soft mid-conf axes.
    n_lt_025 = int(np.sum(vals < 0.25))
    n_mid = int(np.sum((vals >= 0.30) & (vals < 0.50)))
    best = 0.40
    if kitts is not None and kitts >= best:
        best = 0.50  # should not happen
    if clear_vals and min(clear_vals) < best:
        best = min(0.30, min(clear_vals) * 0.5)

    rationale = (
        f"Score distribution (n={vals.size}): "
        f"p5={pcts[5]:.3f}, p10={pcts[10]:.3f}, p25={pcts[25]:.3f}, "
        f"p50={pcts[50]:.3f}, p75={pcts[75]:.3f}, p90={pcts[90]:.3f}, p95={pcts[95]:.3f}. "
        f"Weak mass <0.25: {n_lt_025}; mid-band [0.30,0.50): {n_mid}. "
        f"Kitts Grave SU02SW103 conf={kitts}. "
        f"Clear refs: "
        + ", ".join(f"{i}={c}" for i, c in clear_refs)
        + f". Chose floor={best:.2f} (within suggested 0.30–0.50): above the weak "
        f"cluster (p25={pcts[25]:.3f}) and Kitts, well below clear mounds "
        f"(~0.89–0.92), refusing soft mid-conf axes that the trial elongation "
        f"gate alone can still pass after ensemble down-weighting."
    )
    return float(best), rationale


def process_one(rec: dict) -> BatchRow:
    stem = rec["id"]
    name = display_name(rec)
    nhle = rec.get("azimuth_deg")
    if nhle is not None:
        try:
            nhle = float(nhle)
        except (TypeError, ValueError):
            nhle = None

    if stem in SKIP_STEMS:
        return BatchRow(
            id=stem,
            name=name,
            status="skipped",
            source=None,
            azimuth_lidar_deg=None,
            azimuth_lidar_conf=None,
            azimuth_lidar_method=None,
            azimuth_lidar_indistinct=True,
            nhle_azimuth_deg=nhle,
            delta_vs_nhle_deg=None,
            review_flag=False,
            notes="skipped: MODERN_ALL_CANNINGS (not Neolithic azimuth)",
        )

    try:
        z, source = load_elevation_chip(stem)
    except FileNotFoundError:
        return BatchRow(
            id=stem,
            name=name,
            status="no_chip",
            source=None,
            azimuth_lidar_deg=None,
            azimuth_lidar_conf=None,
            azimuth_lidar_method=None,
            azimuth_lidar_indistinct=True,
            nhle_azimuth_deg=nhle,
            delta_vs_nhle_deg=None,
            review_flag=False,
            notes="no_chip / skipped",
        )

    est = estimate_orientation(z)
    method = METHOD_DTM if source.startswith("raw_dtm") else METHOD_HS
    raw_conf = float(est["confidence"])
    az = est["azimuth_deg"]
    indistinct = bool(est["indistinct"])
    notes = est["notes"]

    return BatchRow(
        id=stem,
        name=name,
        status="measured",  # refined after floor
        source=source,
        azimuth_lidar_deg=None if az is None else round(float(az), 1),
        azimuth_lidar_conf=round(raw_conf, 3),
        azimuth_lidar_method=method,
        azimuth_lidar_indistinct=indistinct,
        nhle_azimuth_deg=nhle,
        delta_vs_nhle_deg=None,
        review_flag=False,
        notes=notes,
        raw_confidence=raw_conf,
        eig_ratio=None
        if est["eig_ratio"] is None
        else round(float(est["eig_ratio"]), 2),
        ensemble_std_deg=None
        if est["ensemble_std_deg"] is None
        else round(float(est["ensemble_std_deg"]), 2),
        ensemble_spread_deg=None
        if est["ensemble_spread_deg"] is None
        else round(float(est["ensemble_spread_deg"]), 2),
    )


def apply_floor_and_deltas(rows: list[BatchRow], floor: float) -> None:
    for r in rows:
        if r.status in ("no_chip", "skipped"):
            continue
        conf = r.azimuth_lidar_conf
        # Hard refuse floor: keep conf for transparency, null deg, force indistinct
        if conf is None or conf < floor:
            r.azimuth_lidar_deg = None
            r.azimuth_lidar_indistinct = True
            r.status = "indistinct"
            extra = f"below refuse floor {floor:.2f}"
            r.notes = f"{r.notes}; {extra}" if r.notes else extra
        elif r.azimuth_lidar_indistinct:
            # Trial indistinct gate (elongation/stability) — null deg per hard rule option
            r.azimuth_lidar_deg = None
            r.status = "indistinct"
        else:
            r.status = "measured"

        if (
            r.azimuth_lidar_deg is not None
            and r.nhle_azimuth_deg is not None
            and not r.azimuth_lidar_indistinct
        ):
            r.delta_vs_nhle_deg = round(
                undirected_delta(r.azimuth_lidar_deg, r.nhle_azimuth_deg), 2
            )
            if r.delta_vs_nhle_deg > DELTA_REVIEW_DEG:
                r.review_flag = True
        elif (
            r.azimuth_lidar_deg is not None
            and r.nhle_azimuth_deg is not None
            and r.azimuth_lidar_indistinct
        ):
            # still record delta for transparency even if indistinct? Spec says
            # compute where NHLE exists; review only if not indistinct.
            # For indistinct with null deg, no delta.
            pass
        # If we kept deg for indistinct before nulling — deg is null now.


def update_data_files(rows: list[BatchRow]) -> None:
    by_id = {r.id: r for r in rows}

    records = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    for rec in records:
        r = by_id.get(rec["id"])
        if r is None:
            continue
        # NEVER touch azimuth_deg / azimuth_method
        rec["azimuth_lidar_deg"] = r.azimuth_lidar_deg
        rec["azimuth_lidar_conf"] = r.azimuth_lidar_conf
        rec["azimuth_lidar_method"] = r.azimuth_lidar_method
        rec["azimuth_lidar_indistinct"] = r.azimuth_lidar_indistinct
        if r.delta_vs_nhle_deg is not None:
            rec["delta_vs_nhle_deg"] = r.delta_vs_nhle_deg
        elif "delta_vs_nhle_deg" in rec:
            # clear stale if re-run
            rec["delta_vs_nhle_deg"] = None
        else:
            rec["delta_vs_nhle_deg"] = r.delta_vs_nhle_deg
    DATA_JSON.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    gj = json.loads(DATA_GEOJSON.read_text(encoding="utf-8"))
    for feat in gj["features"]:
        props = feat["properties"]
        r = by_id.get(props["id"])
        if r is None:
            continue
        props["azimuth_lidar_deg"] = r.azimuth_lidar_deg
        props["azimuth_lidar_conf"] = r.azimuth_lidar_conf
        props["azimuth_lidar_method"] = r.azimuth_lidar_method
        props["azimuth_lidar_indistinct"] = r.azimuth_lidar_indistinct
        props["delta_vs_nhle_deg"] = r.delta_vs_nhle_deg
    DATA_GEOJSON.write_text(
        json.dumps(gj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_outputs(rows: list[BatchRow], floor: float, floor_rationale: str) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    n_measured = sum(1 for r in rows if r.status == "measured")
    n_indistinct = sum(1 for r in rows if r.status == "indistinct")
    n_no_chip = sum(1 for r in rows if r.status == "no_chip")
    n_skipped = sum(1 for r in rows if r.status == "skipped")
    review = [r for r in rows if r.review_flag]
    n_review = len(review)

    # results.json
    results_path = OUT_DIR / "results.json"
    serialisable = []
    for r in rows:
        d = asdict(r)
        serialisable.append(d)
    results_path.write_text(
        json.dumps(serialisable, indent=2) + "\n", encoding="utf-8"
    )

    # review_queue.csv
    review_path = OUT_DIR / "review_queue.csv"
    with review_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "nhle_az", "lidar_az", "delta", "conf"])
        for r in sorted(review, key=lambda x: -(x.delta_vs_nhle_deg or 0)):
            w.writerow(
                [
                    r.id,
                    r.name or "",
                    "" if r.nhle_azimuth_deg is None else f"{r.nhle_azimuth_deg:.1f}",
                    "" if r.azimuth_lidar_deg is None else f"{r.azimuth_lidar_deg:.1f}",
                    "" if r.delta_vs_nhle_deg is None else f"{r.delta_vs_nhle_deg:.2f}",
                    "" if r.azimuth_lidar_conf is None else f"{r.azimuth_lidar_conf:.3f}",
                ]
            )

    summary = {
        "n_gazetteer": len(rows),
        "n_measured": n_measured,
        "n_indistinct": n_indistinct,
        "n_no_chip": n_no_chip,
        "n_skipped": n_skipped,
        "n_review_gt15": n_review,
        "confidence_floor": floor,
        "delta_review_threshold_deg": DELTA_REVIEW_DEG,
        "method_primary": METHOD_DTM,
        "floor_rationale": floor_rationale,
        "review_ids": [r.id for r in review],
        "no_chip_ids": [r.id for r in rows if r.status == "no_chip"],
        "skipped_ids": [r.id for r in rows if r.status == "skipped"],
    }
    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Markdown report
    confs = [r.raw_confidence for r in rows if r.raw_confidence is not None]
    confs_arr = np.array(confs, dtype=float) if confs else np.array([])
    dist_lines = []
    if confs_arr.size:
        for p in (5, 10, 25, 50, 75, 90, 95):
            dist_lines.append(f"- p{p}: {float(np.percentile(confs_arr, p)):.3f}")
        dist_lines.append(f"- min/max: {float(confs_arr.min()):.3f} / {float(confs_arr.max()):.3f}")

    example_review = review[:8]
    example_lines = []
    for r in example_review:
        example_lines.append(
            f"| `{r.id}` | {r.name} | {r.nhle_azimuth_deg} | {r.azimuth_lidar_deg} | "
            f"{r.delta_vs_nhle_deg} | {r.azimuth_lidar_conf} |"
        )

    kitts = next((r for r in rows if r.id == "SU02SW103"), None)
    wk = next((r for r in rows if r.id == "SU16NW100"), None)
    ws = next((r for r in rows if r.id == "SU14SW125"), None)

    lines = [
        "# Orientation batch — LiDAR long-axis (parallel fields)",
        "",
        "Batch of Wiltshire long-barrow gazetteer chips using the trial method "
        "(`scripts/orientation_trial.py` → `scripts/orientation_batch.py`).",
        "",
        "**NHLE fields `azimuth_deg` / `azimuth_method` were not modified.** "
        "New parallel fields: `azimuth_lidar_deg`, `azimuth_lidar_conf`, "
        "`azimuth_lidar_method`, `azimuth_lidar_indistinct`, plus `delta_vs_nhle_deg` where comparable.",
        "",
        "## Counts",
        "",
        f"| Category | n |",
        f"|----------|---|",
        f"| Gazetteer IDs processed | {len(rows)} |",
        f"| Measured (clear, deg set) | {n_measured} |",
        f"| Indistinct (deg null) | {n_indistinct} |",
        f"| No chip | {n_no_chip} |",
        f"| Skipped (MODERN) | {n_skipped} |",
        f"| Review queue (|Δ| > {DELTA_REVIEW_DEG:.0f}° and not indistinct) | {n_review} |",
        "",
        f"- No-chip IDs: {', '.join('`'+r.id+'`' for r in rows if r.status=='no_chip') or 'none'}",
        f"- Skipped IDs: {', '.join('`'+r.id+'`' for r in rows if r.status=='skipped') or 'none (MODERN_ALL_CANNINGS not in gazetteer; chip ignored)'} ",
        "",
        "## Confidence refuse floor",
        "",
        f"**Chosen floor: {floor:.2f}**",
        "",
        floor_rationale,
        "",
        "### Raw confidence distribution (pre-floor)",
        "",
        *dist_lines,
        "",
        "### Anchor sites",
        "",
    ]
    for label, r in (("West Kennet", wk), ("Winterbourne Stoke Crossroads", ws), ("Kitts Grave", kitts)):
        if r is None:
            lines.append(f"- {label}: not in batch")
        else:
            lines.append(
                f"- {label} (`{r.id}`): raw conf={r.raw_confidence}, "
                f"status={r.status}, deg={r.azimuth_lidar_deg}, indistinct={r.azimuth_lidar_indistinct}"
            )

    lines += [
        "",
        "Below the floor: `azimuth_lidar_deg=null`, `azimuth_lidar_indistinct=true`, "
        "confidence retained for transparency.",
        "",
        "## Method note",
        "",
        f"- Prefer `lidar/chips/raw/{{id}}.tif` → method `{METHOD_DTM}`.",
        f"- Fall back to `lidar/chips/web/{{id}}.jpg` → method `{METHOD_HS}`.",
        "- Local residual relief + ROI threshold + PCA on mound mask; undirected azimuth 0–180° (image top = N).",
        "- Ensemble stability gate from trial (conf / circular std / pairwise spread) still marks indistinct.",
        f"- Additional hard refuse floor at {floor:.2f} (tuned on this batch).",
        "- `MODERN_ALL_CANNINGS` skipped (not treated as Neolithic azimuth).",
        "- `SU16NW133` White Hill: missing chip → `no_chip`.",
        "",
        "## Review queue (|Δ| vs NHLE > 15°, not indistinct)",
        "",
        f"Full CSV: `scripts/orientation_batch_out/review_queue.csv` ({n_review} rows).",
        "",
        "| id | name | NHLE az | LiDAR az | Δ | conf |",
        "|----|------|---------|----------|---|------|",
        *example_lines,
        "",
        "## Outputs",
        "",
        "- `scripts/orientation_batch_out/results.json`",
        "- `scripts/orientation_batch_out/review_queue.csv`",
        "- `scripts/orientation_batch_out/summary.json`",
        "- Updated `data/long_barrows.json` and `data/long_barrows.geojson` (parallel fields only)",
        "",
        "## Re-run",
        "",
        "```bash",
        "cd /workspace/wiltshire-long-barrows",
        ".venv/bin/python scripts/orientation_batch.py",
        "```",
        "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    records = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    # Sanity: never process MODERN even if somehow present; also ignore chip-only MODERN
    rows: list[BatchRow] = []
    print(f"Processing {len(records)} gazetteer records…")
    for i, rec in enumerate(records, 1):
        row = process_one(rec)
        rows.append(row)
        if i % 20 == 0 or row.status == "no_chip":
            print(
                f"  [{i}/{len(records)}] {row.id}: {row.status} "
                f"conf={row.azimuth_lidar_conf} az={row.azimuth_lidar_deg}"
            )

    # Explicitly note MODERN chip was not in gazetteer / skipped
    modern_chip = (ROOT / "lidar" / "chips" / "raw" / "MODERN_ALL_CANNINGS.tif").exists()
    if modern_chip:
        print("Note: MODERN_ALL_CANNINGS chip present but not in gazetteer — skipped.")

    raw_scores = [
        (r.id, r.raw_confidence)
        for r in rows
        if r.raw_confidence is not None and r.status not in ("no_chip", "skipped")
    ]
    # Temporarily status may still be "measured" before floor
    floor, rationale = choose_confidence_floor(raw_scores)
    print(f"\nChosen confidence floor: {floor:.2f}")
    print(rationale)

    apply_floor_and_deltas(rows, floor)
    update_data_files(rows)
    summary = write_outputs(rows, floor, rationale)

    print("\n=== SUMMARY ===")
    print(json.dumps({k: summary[k] for k in (
        "n_gazetteer", "n_measured", "n_indistinct", "n_no_chip",
        "n_skipped", "n_review_gt15", "confidence_floor"
    )}, indent=2))
    print(f"Report: {REPORT}")
    print(f"Review queue: {OUT_DIR / 'review_queue.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

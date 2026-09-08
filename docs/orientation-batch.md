# Orientation batch — LiDAR long-axis (parallel fields)

Batch of Wiltshire long-barrow gazetteer chips using the trial method (`scripts/orientation_trial.py` → `scripts/orientation_batch.py`).

**NHLE fields `azimuth_deg` / `azimuth_method` were not modified.** New parallel fields: `azimuth_lidar_deg`, `azimuth_lidar_conf`, `azimuth_lidar_method`, `azimuth_lidar_indistinct`, plus `delta_vs_nhle_deg` where comparable.

## Counts

| Category | n |
|----------|---|
| Gazetteer IDs processed | 128 |
| Measured (clear, deg set) | 65 |
| Indistinct (deg null) | 63 |
| No chip | 0 |
| Skipped (MODERN) | 0 |
| Review queue (|Δ| > 15° and not indistinct) | 14 |

- No-chip IDs: none (White Hill `SU16NW133` now measured: 69.8°, conf 0.932)
- Skipped IDs: none (MODERN_ALL_CANNINGS not in gazetteer; chip ignored) 

## Confidence refuse floor

**Chosen floor: 0.40**

Score distribution (n=127): p5=0.012, p10=0.017, p25=0.092, p50=0.572, p75=0.765, p90=0.889, p95=0.921. Weak mass <0.25: 40; mid-band [0.30,0.50): 16. Kitts Grave SU02SW103 conf=0.004838556018061309. Clear refs: SU16NW100=0.9167459525762068, SU14SW125=0.8855483980045137. Chose floor=0.40 (within suggested 0.30–0.50): above the weak cluster (p25=0.092) and Kitts, well below clear mounds (~0.89–0.92), refusing soft mid-conf axes that the trial elongation gate alone can still pass after ensemble down-weighting.

### Raw confidence distribution (pre-floor)

- p5: 0.012
- p10: 0.017
- p25: 0.092
- p50: 0.572
- p75: 0.765
- p90: 0.889
- p95: 0.921
- min/max: 0.002 / 0.990

### Anchor sites

- West Kennet (`SU16NW100`): raw conf=0.9167459525762068, status=measured, deg=84.4, indistinct=False
- Winterbourne Stoke Crossroads (`SU14SW125`): raw conf=0.8855483980045137, status=measured, deg=34.9, indistinct=False
- Kitts Grave (`SU02SW103`): raw conf=0.004838556018061309, status=indistinct, deg=None, indistinct=True

Below the floor: `azimuth_lidar_deg=null`, `azimuth_lidar_indistinct=true`, confidence retained for transparency.

## Method note

- Prefer `lidar/chips/raw/{id}.tif` → method `dtm_local_relief_pca`.
- Fall back to `lidar/chips/web/{id}.jpg` → method `hillshade_local_relief_pca`.
- Local residual relief + ROI threshold + PCA on mound mask; undirected azimuth 0–180° (image top = N).
- Ensemble stability gate from trial (conf / circular std / pairwise spread) still marks indistinct.
- Additional hard refuse floor at 0.40 (tuned on this batch).
- `MODERN_ALL_CANNINGS` skipped (not treated as Neolithic azimuth).
- `SU16NW133` White Hill: chip added; `azimuth_lidar_deg=69.8`, conf=0.932, indistinct=false (NHLE az still null). Preview: `scripts/orientation_batch_out/SU16NW133_axis.png`.

## Review queue (|Δ| vs NHLE > 15°, not indistinct)

Full CSV: `scripts/orientation_batch_out/review_queue.csv` (14 rows).

| id | name | NHLE az | LiDAR az | Δ | conf |
|----|------|---------|----------|---|------|
| `ST83NE100` | Long barrow on Pertwood Down, 1400m north-west of Lower Pertwood | 125.1 | 109.0 | 16.1 | 0.934 |
| `SU14SW129` | Normanton Down 2 | 66.8 | 43.2 | 23.6 | 0.493 |
| `SU14SW126` | Wilsford Down | 2.6 | 60.2 | 57.6 | 0.488 |
| `SU04SE100` | Winterbourne Stoke Down | 90.0 | 53.2 | 36.8 | 0.903 |
| `SU04NW100` | Whitebarrow | 4.0 | 91.7 | 87.7 | 0.838 |
| `ST84NE100` | Colloway Clump long barrow | 10.4 | 127.5 | 62.9 | 0.805 |
| `ST94NW103` | Oxendean Down long barrow | 109.7 | 170.0 | 60.3 | 0.861 |
| `ST95SW102` | Long barrow, Tinhead Hill | 64.3 | 47.4 | 16.9 | 0.889 |

## Outputs

- `scripts/orientation_batch_out/results.json`
- `scripts/orientation_batch_out/review_queue.csv`
- `scripts/orientation_batch_out/summary.json`
- Updated `data/long_barrows.json` and `data/long_barrows.geojson` (parallel fields only)
- `scripts/orientation_batch_out/human_review.html` + `human_review_sheet.csv`
- `docs/grok-build-orientation-protocol.md`

## Re-run

```bash
cd /workspace/wiltshire-long-barrows
.venv/bin/python scripts/orientation_batch.py
```


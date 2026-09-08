# Orientation trial — LiDAR long-axis vs NHLE PCA

**Decision: GO for batching ~129 chips.**

## Method

Prefer `lidar/chips/raw/{stem}.tif` (1 m EA DTM elevation), else web JPG hillshade.

1. Local residual relief: `z - GaussianBlur(z, σ≈30 px)` to remove regional slope.
2. Circular ROI (~35% of chip half-diagonal) centred on the chip.
3. Threshold positive residuals (85th percentile) → mound mask.
4. Keep the best connected component (area × eccentricity, centre-weighted).
5. PCA on mask pixel coordinates → undirected azimuth `atan2(ΔE, ΔN)` folded to **0–180°** (image top = north, +x = east).
6. Confidence = eigenvalue anisotropy `(λ1−λ2)/(λ1+λ2)`, down-weighted by ensemble spread.
7. **Indistinct** if conf < 0.65 or ensemble circular std > 6° or pairwise spread > 12° across a small σ / ROI / percentile grid.

Script: `scripts/orientation_trial.py`. Annotated previews: `scripts/orientation_trial_out/`.

## Per-site results

| Site | Stem | Estimated az (°) | Conf | Indistinct | NHLE PCA az (°) | Δ (°) | Notes |
|------|------|------------------|------|------------|-----------------|-------|-------|
| West Kennet | `SU16NW100` | 84.4 | 0.917 | no | 85.2 | 0.8 | stable mound PCA |
| Winterbourne Stoke Crossroads | `SU14SW125` | 34.9 | 0.886 | no | 34.1 | 0.8 | stable mound PCA |
| Kitts Grave | `SU02SW103` | 9.9 | 0.005 | yes | — | — | low elongation conf=0.22; unstable ensemble std=33.5°; ensemble spread=86.3° |

### Detail

#### West Kennet (`SU16NW100`)

- Source: `raw_dtm:SU16NW100.tif`
- Method: `dtm_local_relief_pca`
- Estimated azimuth: **84.4°** (undirected 0–180 from N)
- Confidence: **0.917**; indistinct: **False**
- Eigenvalue ratio λ1/λ2: 26.92
- Ensemble circular std: 0.1°; spread: 0.31°
- Existing NHLE polygon PCA: 85.2°; |Δ| = 0.76°
- Preview: `scripts/orientation_trial_out/SU16NW100_axis.png`

#### Winterbourne Stoke Crossroads (`SU14SW125`)

- Source: `raw_dtm:SU14SW125.tif`
- Method: `dtm_local_relief_pca`
- Estimated azimuth: **34.9°** (undirected 0–180 from N)
- Confidence: **0.886**; indistinct: **False**
- Eigenvalue ratio λ1/λ2: 18.6
- Ensemble circular std: 0.1°; spread: 0.35°
- Existing NHLE polygon PCA: 34.1°; |Δ| = 0.79°
- Preview: `scripts/orientation_trial_out/SU14SW125_axis.png`

#### Kitts Grave (`SU02SW103`)

- Source: `raw_dtm:SU02SW103.tif`
- Method: `dtm_local_relief_pca`
- Estimated azimuth: **9.9°** (undirected 0–180 from N)
- Confidence: **0.005**; indistinct: **True**
- Eigenvalue ratio λ1/λ2: 1.55
- Ensemble circular std: 33.5°; spread: 86.28°
- No existing NHLE azimuth in gazetteer.
- Preview: `scripts/orientation_trial_out/SU02SW103_axis.png`

## Go / no-go

**GO**

- Known-site |Δ| vs NHLE PCA: SU16NW100 0.8°, SU14SW125 0.8° (max 0.8°).
- Indistinct gate fired on: SU02SW103 — good (avoids forcing bad angles).
- Method is accurate on clear chalk mounds and refuses weak cases; suitable to batch ~129 chips with human review of indistinct flags.

### Batching notes (if GO)

- Write LiDAR-derived az to a parallel field (e.g. `azimuth_lidar_deg`) — do not silently replace `azimuth_deg` / `nhle_polygon_pca`.
- Queue all `indistinct=true` rows for manual review.
- Expect modern roads, plough patterns, and multi-barrow chips to inflate false axes; centre ROI assumes the target is chip-centred (true for current chip builder).

## Re-run

```bash
cd /workspace/wiltshire-long-barrows
.venv/bin/python scripts/orientation_trial.py
```


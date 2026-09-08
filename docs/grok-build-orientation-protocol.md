# Grok Build protocol — Wiltshire long-barrow orientation analysis

Handoff for **Grok Build / Cursor Cloud Agent**. Plumbing (LiDAR batch, human prefer, display promotion, map wiring) is **largely done**. The job **now** is to **analyse and write up** the new human-curated display-azimuth dataset. Paste the final prompt block at the bottom into a new agent run. Author context: Tim Daw / sarsen.org.

## Goal

Produce a **write-up + analysis package** of Wiltshire long-barrow long-axis orientations using `azimuth_display_deg` (human-reviewed preferred axis), with NHLE and LiDAR kept as comparison evidence — suitable for a draft sarsen.org article and distributional / archaeoastronomy / topography tests against literature.

## What’s new vs prior research

- Previous public axes in this gazetteer were mostly **NHLE scheduling-polygon PCA** (`azimuth_deg`). The scheduling outline ≠ mound crest; known **near-orthogonal errors** and other footprint artefacts.
- **New pipeline:** EA Composite DTM **1 m** chip → local-relief mound mask → PCA → parallel fields `azimuth_lidar_*`.
- Then a **full human eye review** of all chips (interactive green axis in the review UI); Tim’s `prefer` decisions promote a curated axis into **`azimuth_display_*`** without destroying NHLE.
- Result: a **human-curated Wiltshire long-barrow long-axis set** (n_display ≈ 86 of 128) suitable for distributional / archaeoastronomy / topography tests against literature (Ruggles; Roberts et al. Internet Archaeology 47; Ashbee; Field; Darvill; etc.).
- **Treat solar claims as hypotheses** — peer consensus for Wiltshire chalk is no clear common astronomical alignment; topography matters. Descriptive solar overlays only; no intent claims.

## Absolute paths

**Tim’s laptop (preferred path style for docs / local open):**

```
C:\Users\timda\Documents\wiltshire-long-barrows\
C:\Users\timda\Documents\wiltshire-long-barrows\data\long_barrows.json
C:\Users\timda\Documents\wiltshire-long-barrows\data\long_barrows.geojson
C:\Users\timda\Documents\wiltshire-long-barrows\generate.py
C:\Users\timda\Documents\wiltshire-long-barrows\index.html
C:\Users\timda\Documents\wiltshire-long-barrows\NOTES.md
C:\Users\timda\Documents\wiltshire-long-barrows\lidar\chips\raw\{id}.tif
C:\Users\timda\Documents\wiltshire-long-barrows\lidar\chips\web\{id}.jpg
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_trial.py
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch.py
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch_out\
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch_out\human_review.html
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch_out\human_review_sheet.csv
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch_out\wiltshire-lb-orientation-prefer-v2.json
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch_out\prefer_applied_summary.json
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch_out\prefer_applied.csv
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch_out\review_queue.csv
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch_out\summary.json
C:\Users\timda\Documents\wiltshire-long-barrows\scripts\orientation_batch_out\SU16NW133_axis.png
C:\Users\timda\Documents\wiltshire-long-barrows\docs\orientation-trial.md
C:\Users\timda\Documents\wiltshire-long-barrows\docs\orientation-batch.md
C:\Users\timda\Documents\wiltshire-long-barrows\docs\grok-build-orientation-protocol.md
C:\Users\timda\Documents\wiltshire-long-barrows\docs\analysis\          (create if needed for figures / article)
```

**Agent box mirror (same tree; Linux paths):**

```
/workspace/wiltshire-long-barrows/
  data/long_barrows.json
  data/long_barrows.geojson
  generate.py
  index.html
  NOTES.md
  lidar/chips/raw/{id}.tif
  lidar/chips/web/{id}.jpg
  scripts/orientation_*.py
  scripts/orientation_batch_out/
  docs/…
```

GitHub: `https://github.com/TimDaw37/wiltshire-long-barrows` (Pages may lag this box/laptop work).

## Data schema (orientation fields)

| Field | Meaning |
|-------|---------|
| `azimuth_deg` | **NHLE** undirected long-axis ° from N, 0–180. **Immutable** — never overwrite. |
| `azimuth_method` | Typically `nhle_polygon_pca` or null. |
| `azimuth_lidar_deg` | LiDAR mound-mask PCA axis, 0–180, or null if refused. |
| `azimuth_lidar_conf` | Confidence (anisotropy × ensemble stability); retained even when refused. |
| `azimuth_lidar_method` | `dtm_local_relief_pca` (raw TIF) or `hillshade_local_relief_pca` (web JPG). |
| `azimuth_lidar_indistinct` | `true` → deg null / do not treat as measured. |
| `delta_vs_nhle_deg` | Undirected \|Δ\| vs NHLE when both NHLE + LiDAR exist. |
| `azimuth_prefer` | Human decision: `eye` \| `lidar` \| `nhle` \| `not_barrow` \| `leave_indistinct` \| `hold`. |
| `azimuth_eye_deg` | Eye-measured axis when prefer=`eye`. |
| `azimuth_display_deg` | **Display / analysis axis** promoted from prefer (null if none). |
| `azimuth_display_source` | `eye` \| `lidar` \| `nhle` when display set. |
| `azimuth_prefer_note` | Optional free-text note from review. |

**Convention:** image top = north, +x = east. Azimuth **undirected**: fold with `atan2(ΔE, ΔN)` into **0–180°**.

**Final prefer counts (128/128, 2026-09-08):** eye 77 · leave_indistinct 21 · not_barrow 21 · lidar 5 · nhle 4 → **n_display = 86**.  
`not_barrow` = no usable long-barrow axis on chip; exclude from orientation analysis with `leave_indistinct`.

Prefer JSON: `scripts/orientation_batch_out/wiltshire-lb-orientation-prefer-v2.json`.

## What is already done

- [x] Parallel `azimuth_lidar_*` fields written; NHLE `azimuth_deg` untouched.
- [x] Refuse floor ~0.40; review queue for \|Δ\| > 15°.
- [x] Human review pack HTML + CSV; full **128/128** prefer answers applied.
- [x] `azimuth_display_deg` / `azimuth_display_source` / `azimuth_prefer` / `azimuth_eye_deg` populated.
- [x] **White Hill `SU16NW133`**: chip present; LiDAR 69.8° / conf 0.932; NHLE still null.
- [x] Skip `MODERN_ALL_CANNINGS` as Neolithic azimuth.
- [x] Map (`generate.py` → `index.html`) wired to **`azimuth_display_deg`** for counts / filters / icons / tooltips / primary detail — **no NHLE fallback** when prefer is not_barrow / leave_indistinct.
- [x] Detail panel shows NHLE PCA + LiDAR auto axis as separate evidence; `NOTES.md` documents schema + counts.
- [x] Pre-prefer backups kept under `data/long_barrows.pre-prefer-*.json` (do not delete unless huge / Tim asks).

## Guardrails

1. **Never overwrite** NHLE `azimuth_deg` / `azimuth_method`.
2. **Skip** `MODERN_ALL_CANNINGS` for Neolithic orientation analysis.
3. **Chambered / Cotswold–Severn traits**: façade / forecourt direction ≠ mound long-axis; typology lives in site notes only — no `barrow_type` binary (see `NOTES.md`).
4. **Plough / track / twin-mound** false axes — prefer eye / leave_indistinct already encodes many of these; don’t “rescue” not_barrow into display.
5. **Undirected 0–180°**, chips **north-up**.
6. **Circular / axial statistics** required for undirected data (do not treat 0–180 as linear Euclidean without axial handling; mean resultant length on doubled angles is the usual approach).
7. Solar azimuths at ~51.2°N = **descriptive overlays only** — no intent claims.
8. **Do not invent citations**; use bibliography in `NOTES.md`; mark gaps explicitly.
9. **No git push** unless Tim asks; **no raw TIFF commits**.
10. Do not delete pre-prefer backup files unless huge and Tim asks.

## Non-goals (this analysis job)

- Re-running the full LiDAR batch or re-doing human prefer (already complete).
- Overwriting display fields from NHLE without Tim’s say-so.
- Claiming astronomical alignments as proven.

## Figures / outputs (suggested locations)

```
docs/analysis/                          # draft article + SVG/PNG figures
scripts/orientation_batch_out/analysis/ # optional compute scratch + exports
```

---

## Paste this prompt (Grok Build / Cloud Agent)

```
Work in /workspace/wiltshire-long-barrows (Tim laptop mirror:
C:\Users\timda\Documents\wiltshire-long-barrows\).

Read docs/grok-build-orientation-protocol.md and NOTES.md. Follow guardrails.

Context — plumbing DONE (do not redo unless broken):
- data/long_barrows.json + .geojson: 128 rows; prefer applied 128/128
  (eye 77, leave_indistinct 21, not_barrow 21, lidar 5, nhle 4) → n_display=86
- Prefer JSON: scripts/orientation_batch_out/wiltshire-lb-orientation-prefer-v2.json
- Map uses azimuth_display_deg (generate.py / index.html); NHLE azimuth_deg immutable
- White Hill SU16NW133 LiDAR done; skip MODERN_ALL_CANNINGS
- NHLE = scheduling-polygon PCA (outline ≠ mound); LiDAR = auto mound-mask PCA;
  display = Tim’s curated preferred axis (eye/lidar/nhle)

YOUR JOB NOW — write-up + analysis package (not more plumbing):

1) Summary statistics of azimuth_display_deg (n=86): rose and/or histogram bins
   10° or 15°; mean resultant length for undirected (axial) data — use proper
   circular/axial stats (e.g. double angles), not naïve linear mean of degrees.

2) Compare display vs NHLE vs LiDAR where all exist: Δ distributions; flag where
   eye differed from both NHLE and LiDAR.

3) Do not split by a Cotswold–Severn / earthen binary; optional splits by cluster/region or by keywords in notes only.

4) Overlay flat-horizon solar azimuths at ~51.2°N (midsummer ~50°, equinox ~90°,
   midwinter ~129°) as DESCRIPTIVE overlays only — no intent claims.

5) Flag / exclude prefer=not_barrow and leave_indistinct from orientation analysis;
   report their counts and that they have no azimuth_display_deg.

6) Draft a markdown article suitable for sarsen.org (methods, results, caveats).
   Put figures as SVG/PNG under docs/analysis/ and/or
   scripts/orientation_batch_out/analysis/.

7) Do not invent citations — use NOTES.md bibliography; mark gaps.

8) No git push unless asked; no raw TIFF commits; never overwrite azimuth_deg /
   azimuth_method; do not delete pre-prefer backups unless huge.

Success criteria:
- [ ] Analysis uses azimuth_display_deg only for primary orientation n (expect ~86)
- [ ] Axial/circular stats documented; rose/histogram figures saved
- [ ] Display vs NHLE vs LiDAR comparison table or plots where pairwise overlap exists
- [ ] Type / cluster splits if data allow; solar overlays clearly labelled non-causal
- [ ] Exclusions (not_barrow / leave_indistinct / modern) stated
- [ ] Draft article in docs/analysis/ with methods, results, caveats; citations from NOTES only
- [ ] NHLE fields unchanged; no push; no TIFF commits
```

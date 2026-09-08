# Notes — Wiltshire long barrows gazetteer

## Sources ranked (v1)

1. **Wiltshire HER certain/possible points** — Zenodo 10.5281/zenodo.11005373  
   (data for Wheatley 1996 viewshed recreation). Gives BNG coords + certainty + some names.  
   *Caveat:* CSV columns labelled Latitude/Longitude are actually easting/northing.  
   Licence: Zenodo CC BY 4.0; underlying Wiltshire HER — research extract, not official HER.

2. **Kutty 2024 Archaeological Features** — Zenodo 10.5281/zenodo.10989406  
   Named Avebury + Stonehenge long barrows with MWI HER URLs. Good for display names.

3. **Historic England NHLE Scheduled Monuments** — OGL  
   ArcGIS FeatureServer layer 6; Name LIKE '%long barrow%'. Polygons → ListEntry, hyperlink,  
   first-pass long-axis via PCA. Scheduling outline ≠ surveyed mound crest.

4. **Peer literature (orientation / catalogues)** — cite, not scraped as tables here:  
   - Ashbee, *The Earthen Long Barrow in Britain*  
   - Kinnes 1992; Darvill (Cotswold/Wessex reviews); Field 2006  
   - Ruggles 1997 (PBA Astronomy and Stonehenge); Ruggles 1999  
   - Roberts et al., Internet Archaeology 47 (Stonehenge WHS long barrows; CC BY)  
   - McOmish et al. 2002 (SPTA)  
   - Burl 1987 lunar-arc claim — contested by Ruggles

5. **EA LiDAR Composite DTM** — OGL  
   WCS: `https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs`  
   - **County terrain** (default map base): SCALEFACTOR 0.05 → ~20 m mosaic over  
     E376000–432000 N117000–189000 → `lidar/web/county-hillshade.png`  
   - **EA detail (Stonehenge)**: existing 2 m mosaic hillshade for WHS cluster  
     → `lidar/web/ea1m-hillshade.png` (toggle)

6. **OSM** — Overpass attempted; endpoint returned HTML error in this run. Optional later enrichment.

## Orientation conventions

- **Undirected** long-axis bearing, **degrees from north**, range **0–180** (`atan2(ΔE, ΔN)` folded).
- `azimuth_deg` / `azimuth_method`: **NHLE scheduling-polygon PCA** — **immutable** in orientation work.
- `azimuth_lidar_*`: auto axis from EA 1 m DTM chip → local-relief mound mask → PCA (parallel fields).
- `azimuth_prefer` / `azimuth_eye_deg` / `azimuth_display_deg` / `azimuth_display_source` / `azimuth_prefer_note`:
  human review promotion (see 2026-09-08 section below).
- `front_end`: **null** (not asserted). Literature often places the wider/higher/forecourt end
  toward the east, but that is site-specific.
- Flat-horizon sunrise ≈51.2°N (true solar, no refraction): midsummer ~50°, equinox ~90°, midwinter ~129°.

Peer consensus for Wiltshire chalk: **no clear common astronomical alignment**; topography matters
(Ruggles; Roberts et al. IA 47; Darvill). Treat solar claims as hypotheses to test against the
human-curated display axes (and LiDAR), not as established intent.

## Typology (no public binary class)

The public map does **not** filter or label sites as Cotswold–Severn vs earthen.
Chambered / earthen / hybrid traits are a **spectrum** (e.g. East Kennet is often treated as hybrid);
plain-language typology lives in each site’s **Notes**, not a hard UI class.

The `barrow_type` field has been **removed** from `long_barrows.json` / `.geojson`. Do not reintroduce a public Cotswold–Severn / earthen binary; keep typology in site notes only.


## LiDAR

- County: `python download_ea_county_dtm.py` then `python make_county_hillshade.py`
- Detail (Stonehenge): `WILTS_LB_BBOX=… python download_ea_dtm.py` then `make_ea1m_hillshade.py`
- Orientation: human-reviewed display axes now preferred over NHLE polygons alone (see sections below).

## Gaps

- Incomplete naming; many HER-only IDs
- Possible HER rows include oval barrows / uncertain cropmarks — keep `status`
- Two seed rows dropped for impossible OSGB (outside chalk envelope)
- Cranborne Chase fringe sites may sit on county borders
- No git push from box

## LiDAR status (2026-09-07 evening)

- EA WCS **full-height** easting strips produced large northern rectangular nodata holes
  (same E window with northern-only N returned 0% nodata — WCS truncation).
- Fixed by **2D tiling** (E×N tiles, 14×36 km, 3 km overlap) → merge nodata **0%** before fill.
- Residual fill-all kept as safety; county alpha mask on PNG; mobile JPEG `?v=4`.
- Visual gate: no axis-aligned dark (L<20) blocks ≥40×80 px inside county footprint.

## Orientation batch + White Hill (2026-09-08)

- Parallel LiDAR fields (`azimuth_lidar_*`) written for the gazetteer; **NHLE `azimuth_deg` not overwritten**.
- Refuse floor **0.40**; review queue **|Δ| > 15°** → 14 sites (`scripts/orientation_batch_out/review_queue.csv`).
- Human review pack: `scripts/orientation_batch_out/human_review.html` + `human_review_sheet.csv`.
- Grok Build handoff: `docs/grok-build-orientation-protocol.md`.
- **White Hill `SU16NW133`**: chip present (`lidar/chips/raw/SU16NW133.tif`, web JPG). Orientation measured — LiDAR **69.8°**, conf **0.932**, indistinct=false; NHLE azimuth still null. Preview `scripts/orientation_batch_out/SU16NW133_axis.png`.
- Skip `MODERN_ALL_CANNINGS`. Undirected 0–180°, chips north-up.

## Orientation human review complete (2026-09-08)

Full chip-by-chip human review of all **128** gazetteer rows; prefer answers applied to
`data/long_barrows.json` + `.geojson` without destroying NHLE.

### Schema (orientation fields)

| Field | Role |
|-------|------|
| `azimuth_deg` | NHLE polygon PCA — **immutable** |
| `azimuth_method` | typically `nhle_polygon_pca` or null |
| `azimuth_lidar_deg` / `_conf` / `_method` / `_indistinct` | auto LiDAR mound-mask PCA |
| `delta_vs_nhle_deg` | undirected \|Δ\| when both NHLE + LiDAR exist |
| `azimuth_prefer` | human decision (see values below) |
| `azimuth_eye_deg` | eye-measured axis when prefer=eye |
| `azimuth_display_deg` | promoted display axis for map / analysis (null if none) |
| `azimuth_display_source` | `eye` \| `lidar` \| `nhle` when display set |
| `azimuth_prefer_note` | optional free-text note |

### Prefer values

`eye` | `lidar` | `nhle` | `not_barrow` | `leave_indistinct` | `hold`

- **`not_barrow`**: no usable long-barrow axis on the chip (exclude from orientation analysis).
- **`leave_indistinct`**: mound too weak / ambiguous — no display axis.
- **`hold`**: reserved; not used in final 128/128 set.

### Final counts (128/128)

| prefer | n |
|--------|---|
| eye | 77 |
| leave_indistinct | 21 |
| not_barrow | 21 |
| lidar | 5 |
| nhle | 4 |

→ **`azimuth_display_deg` set for 86** (77 eye + 5 lidar + 4 nhle). not_barrow / leave_indistinct have no display.

### Source prefer JSON

`scripts/orientation_batch_out/wiltshire-lb-orientation-prefer-v2.json`  
Applied summary: `scripts/orientation_batch_out/prefer_applied_summary.json` (nhle_untouched=true).

### Map

`generate.py` / `index.html` now use **`azimuth_display_deg`** for counts, filters, icons, tooltips and the primary detail value — **no fallback** to NHLE when prefer was not_barrow / leave_indistinct. NHLE PCA and LiDAR auto axes remain as separate evidence lines in the detail panel.

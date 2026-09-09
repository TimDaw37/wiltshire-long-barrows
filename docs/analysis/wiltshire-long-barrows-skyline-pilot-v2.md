# Wiltshire long barrows — skyline perp-zone contours (v2)

**Date:** 9 Sep 2026  
**Sites:** West Kennet (SU16NW100), East Kennet (SU16NW101), Kitchen (SU06SE101), Adam’s Grave (SU16SW102)  
**Script:** [`scripts/skyline_perp_contours.py`](../../scripts/skyline_perp_contours.py)  
**Outputs:** [`analysis/skyline_pilot_v2/`](../../analysis/skyline_pilot_v2/)  
**Extends / replaces corridor-% framing of earlier v2 draft:** main product is now Tim’s **perpendicular-zone contour field**, not a far-corridor percentage table.  
**v1** (approach-corridor scatter) remains under `analysis/skyline_pilot/` and [skyline-pilot.md](wiltshire-long-barrows-skyline-pilot.md).  
**Do not mutate** `data/long_barrows.json`.

---

## Tim’s method (authoritative)

1. Take each long barrow’s **display long-axis** θ (undirected, 0–180°, from `azimuth_display_deg`).
2. Define a zone **perpendicular to that alignment** — viewing azimuths α (observer → crest) within **±30–35° of θ±90°** (the bearings where the **length** shows / broadside silhouette).
3. Inside that zone only, run a **contour plot** of skyline-from-below — a continuous field on a dense observer grid — as the **main product**.
4. Nulls (contour-band / downslope) are **optional secondary**, not the headline.

This is the opposite framing of “sample a named vale then filter for length”: here the **perp wedges are the sample frame**, and the map shows **where** within them the mound sits on the skyline.

---

## Parameters

| Parameter | Value |
|-----------|------:|
| DTM | `lidar/county/wiltshire_county_dtm.tif` (~20 m) |
| Crest Z | 1 m chip max within 25 m of gazetteer **+ 2 m** |
| Eye height | 1.7 m |
| Distance band | **0.3–2.5 km** (EK road-scale; prior 1–5 km was too far) |
| Spacing | ~125 m &lt; 1.5 km; 200 m beyond |
| Half-wedge | **±32.5°** of θ±90° |
| Beyond-crest window | 300 m–5 km |
| Curvature + refraction | yes (k = 0.13) |
| Field | angular clearance (°) = crest elev − max far-horizon elev; skyline hit when far terrain never rises above LOS through crest |

Reproducible dump: [`analysis/skyline_pilot_v2/skyline_params.json`](../../analysis/skyline_pilot_v2/skyline_params.json).

### Display axes

| Site | Axis θ |
|------|-------:|
| West Kennet | 84.5° |
| East Kennet | 139.0° |
| Kitchen | 43.5° |
| Adam’s Grave | 136.0° |

---

## Ground-truth pins (BNG)

| Pin | WGS84 | BNG (E, N) | Heading | Dist to crest |
|-----|-------|------------|--------:|--------------:|
| **Adam’s north** (Lockeridge SV) [Maps](https://maps.app.goo.gl/TfyDEXt5Vmtpux7e7) | 51.3737179, −1.8347412 | **411599.7, 163864.2** | ~245° | ~593 m |
| **East Kennet road** (closer) [Maps](https://maps.app.goo.gl/R94iaSJTpKg4Hoa57) | 51.4058019, −1.8296697 | **411944.4, 167433.2** | ~221.53° | ~678 m |

Both pins fall **inside** the site’s perp wedge and distance band.

Qualitative photo GT (Kitchen south; West Kennet north) remains in [v1 note](wiltshire-long-barrows-skyline-pilot.md) / album [photos.app.goo.gl/CTFFnN9gZJKQZBWU6](https://photos.app.goo.gl/CTFFnN9gZJKQZBWU6).

---

## Results (chip Z + 2 m, perp wedges only)

| Site | n obs | % visible | % skyline | median clr (vis) | null sky % | ratio | GT high-contour? |
|------|------:|----------:|----------:|-----------------:|-----------:|------:|:-----------------|
| **Adam’s Grave** | 224 | 87.5 | **87.5** | +2.66° | 14.3 | **6.1×** | **yes** (clr ≈ +5.38°) |
| **Kitchen** | 230 | 39.1 | **31.7** | +0.59° | 8.1 | **3.9×** | — |
| West Kennet | 226 | 59.7 | 19.0 | −0.29° | 6.1 | 3.1× | — |
| East Kennet | 226 | 44.7 | 18.6 | −0.13° | 7.8 | 2.4× | **yes** (clr ≈ +1.23°) |

### GT pin checks

- **EK road pin:** in perp zone, **high-contour / skyline hit**, nearest-cell clearance **≈ +1.23°**, ~678 m from crest (NE wedge). Matches the “closer road” view Tim flagged.
- **Adam’s north (Lockeridge) pin:** in perp zone, **high-contour / skyline hit**, clearance **≈ +5.38°**, ~593 m NNE of crest. Strong silhouette from the Lockeridge approach.

### Maps

- [Adam’s Grave](../../analysis/skyline_pilot_v2/skyline_SU16SW102.png) — cyan X = Lockeridge GT
- [East Kennet](../../analysis/skyline_pilot_v2/skyline_SU16NW101.png) — cyan X = road GT
- [Kitchen](../../analysis/skyline_pilot_v2/skyline_SU06SE101.png)
- [West Kennet](../../analysis/skyline_pilot_v2/skyline_SU16NW100.png)
- [Multipanel](../../analysis/skyline_pilot_v2/skyline_multipanel.png)
- Summary CSV: [`skyline_summary.csv`](../../analysis/skyline_pilot_v2/skyline_summary.csv)

Contour colour = angular clearance (°); green / &gt;0 ≈ skyline-from-below; red / &lt;0 = crest against rising far ground. Blue dashed = perp wedges; yellow tick = undirected long axis.

---

## Interpretation

Restricting observers to **broadside wedges** at **road-to-ridge scale (0.3–2.5 km)** shows Adam’s Grave and Kitchen as the strongest length-visible skyline markers (high skyline fractions and clear green contour cores, well above contour-band nulls). West and East Kennet are weaker overall in the same frame, but **East Kennet’s nearer NE wedge** does host a coherent positive-clearance pocket — and Tim’s road pin sits squarely in it (~+1.2°), so the “too far” criticism of the earlier sample was right: at ~0.7 km the mound *does* silhouette broadside. Adam’s Lockeridge pin is even stronger (~+5.4°), confirming the northern chalk approach as a genuine length-on-skyline catchment, not only the Pewsey Vale south. Contours (not corridor %) are the right primary product: they show **where** the effect concentrates inside the perp zone.

---

## How to re-run

```bash
.venv/bin/python scripts/skyline_perp_contours.py
```

Does **not** write `data/long_barrows.json`. Does **not** git push.

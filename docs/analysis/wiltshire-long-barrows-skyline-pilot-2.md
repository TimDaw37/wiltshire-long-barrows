# Wiltshire long barrows — Tim perp-zone skyline contours (pilot 2)

**Date:** 9 Sep 2026  
**Script:** [`scripts/skyline_perp_contours.py`](../../scripts/skyline_perp_contours.py) `--batch pilot2`  
**Outputs:** [`analysis/skyline_pilot_2/`](../../analysis/skyline_pilot_2/)  
**Site selection:** Archivist / Tim-flagged prominent & good-survival set (WS1, Whitebarrow, Giants Grave, Cold Kitchen Hill, Tinhead Hill, South Street, Horton Down, Lanhill, King Barrow, Amesbury 42 optional). Dropped Giant's Cave, Kings Play Hill, Tilshead Down, Tow. **Cold Kitchen Hill = ST83NW101** — not Kitchen SU06SE101.  
**Does not overwrite** `analysis/skyline_pilot_v2/` (original four).  
**Do not mutate** `data/long_barrows.json`. **Never touch** `SU14SW10W`.

---

## Tim’s method (authoritative)

1. Display long-axis θ undirected (0–180°, from `azimuth_display_deg`).
2. Perp wedges: viewing azimuth within **±32.5° of θ±90°**.
3. Observers 0.3–2.5 km in wedges; denser near (~125 m).
4. County DTM 20 m; crest Z from 1 m chip +2 m; eye 1.7 m.
5. Contour skyline clearance / hit field; draw axis + wedges.
6. Null contour-band secondary OK.

## Display axes (re-read from gazetteer)

| Site | id | Axis θ | E | N |
|------|----|-------:|--:|--:|
| Winterbourne Stoke Crossroads | SU14SW125 | 35.0° | 410014.5 | 141521.5 |
| Whitebarrow | SU04NW100 | 91.7° | 403300.5 | 146843.5 |
| Giants Grave | SU12SE100 | 9.0° | 416107.5 | 123018.5 |
| Cold Kitchen Hill | ST83NW101 | 148.5° | 384695.5 | 138354.5 |
| Tinhead Hill | ST95SW102 | 64.3° | 393910.5 | 152402.5 |
| South Street | SU06NE105 | 68.9° | 409010.5 | 169261.5 |
| Horton Down | SU06NE115 | 97.7° | 407673.5 | 165806.5 |
| Lanhill | ST87SE101 | 90.5° | 387741.5 | 174718.5 |
| King Barrow | ST84SE100 | 161.5° | 389762.5 | 144460.5 |
| Amesbury 42 | SU14SW102 | 5.0° | 413742.5 | 143161.5 |

## Results (chip Z + 2 m, perp wedges only)

| Site | n obs | % visible | % skyline | median clr | null sky % | ratio vs null |
|------|------:|----------:|----------:|-----------:|-----------:|--------------:|
| **Winterbourne Stoke Crossroads** | 222 | 66.22 | **66.22** | 0.531 | 25.26 | 2.621 |
| **Whitebarrow** | 222 | 44.59 | **14.41** | -0.142 | 7.39 | 1.951 |
| **Giants Grave** | 226 | 46.46 | **42.04** | 0.254 | 18.76 | 2.241 |
| **Cold Kitchen Hill** | 232 | 29.74 | **29.74** | 1.21 | 15.46 | 1.923 |
| **Tinhead Hill** | 224 | 31.7 | **31.7** | 1.05 | 22.89 | 1.385 |
| **South Street** | 226 | 55.31 | **0.44** | -0.526 | 1.87 | 0.237 |
| **Horton Down** | 222 | 48.65 | **23.42** | -0.135 | 6.05 | 3.873 |
| **Lanhill** | 222 | 51.35 | **0.0** | -0.293 | 24.4 | 0.0 |
| **King Barrow** | 222 | 69.82 | **19.82** | -0.505 | 5.51 | 3.599 |
| **Amesbury 42** | 224 | 50.45 | **42.41** | 0.244 | 21.95 | 1.932 |

### Adam’s / Kitchen-class markers

v2 benchmarks: **Adam’s Grave** ≈ 87% skyline / ~6× null (strong positive clearance); **Kitchen (SU06SE101)** ≈ 32% / ~4× null. Judge this batch on **% skyline**, **median clearance**, and **ratio vs contour-band null** (high nulls on open ridges compress the ratio even when the mound is a genuine silhouette).

| Class | Sites | Why |
|-------|-------|-----|
| **Adam’s-class (closest)** | **Winterbourne Stoke Crossroads (WS1)** | **66.2%** skyline (all visible cells also skyline); median clr **+0.53°**. Ratio only 2.6× because ridge nulls are high (25%) — still the standout length-on-skyline catchment; matches Tim’s “great mound at Longbarrow Crossroads”. |
| **Kitchen-class (skyline % + positive clr)** | **Giants Grave** (42%, +0.25°), **Amesbury 42** (42%, +0.24°), **Cold Kitchen Hill** (30%, **+1.21°**), **Tinhead Hill** (32%, **+1.05°**) | Skyline fractions in the Kitchen band; Cold Kitchen / Tinhead have the strongest positive clearance cores. |
| **Ratio-elevated (moderate sky%)** | **Horton Down** (23%, **3.87×**), **King Barrow** (20%, **3.60×**) | Above-null pockets but weaker absolute skyline cover than Kitchen. |
| **Not markers in this frame** | **Whitebarrow** (14%), **South Street** (0.4%), **Lanhill** (0%) | Visible often, but crest sits against rising far ground in the perp wedges (Lanhill especially). |

**Cold Kitchen Hill (ST83NW101)** is a separate monument from **Kitchen (SU06SE101)** in pilot_v2; it lands in the Kitchen-class skyline band here with stronger median clearance than Kitchen’s v2 +0.59°.

### Interpretation

WS1 is the clear pilot-2 headline: broadside wedges at 0.3–2.5 km light up green across most of the sample — consistent with a large, surviving mound on a local skyline. Giants Grave and Amesbury 42 form a second tier (~42% skyline). Cold Kitchen Hill and Tinhead Hill show Kitchen-like coverage with the best angular clearance. Horton Down / King Barrow beat their local nulls but are not Adam’s-scale. South Street and Lanhill fail the skyline test in this method despite good visibility / survival reputation — length-shows from the sides, but not as a crest-against-sky silhouette over the county DTM.

### Maps

- [Winterbourne Stoke Crossroads](../../analysis/skyline_pilot_2/skyline_SU14SW125.png)
- [Whitebarrow](../../analysis/skyline_pilot_2/skyline_SU04NW100.png)
- [Giants Grave](../../analysis/skyline_pilot_2/skyline_SU12SE100.png)
- [Cold Kitchen Hill](../../analysis/skyline_pilot_2/skyline_ST83NW101.png)
- [Tinhead Hill](../../analysis/skyline_pilot_2/skyline_ST95SW102.png)
- [South Street](../../analysis/skyline_pilot_2/skyline_SU06NE105.png)
- [Horton Down](../../analysis/skyline_pilot_2/skyline_SU06NE115.png)
- [Lanhill](../../analysis/skyline_pilot_2/skyline_ST87SE101.png)
- [King Barrow](../../analysis/skyline_pilot_2/skyline_ST84SE100.png)
- [Amesbury 42](../../analysis/skyline_pilot_2/skyline_SU14SW102.png)
- [Multipanel](../../analysis/skyline_pilot_2/skyline_multipanel.png)
- Summary CSV: [`skyline_summary.csv`](../../analysis/skyline_pilot_2/skyline_summary.csv)

Runtime ≈ 9 s.

## How to re-run

```bash
.venv/bin/python scripts/skyline_perp_contours.py --batch pilot2
```

Does **not** write `data/long_barrows.json`. Does **not** git push. Does **not** touch `SU14SW10W`.

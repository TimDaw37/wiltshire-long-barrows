# Wiltshire long barrows — skyline-from-below pilot

**Date:** 9 Sep 2026  
**Sites:** West Kennet (SU16NW100), East Kennet (SU16NW101), Kitchen (SU06SE101), Adam’s Grave (SU16SW102)  
**Question:** From *defined* vale / valley approaches (not cherry-picked viewpoints), does the mound sit **on the skyline** — silhouetted against sky — as a landscape marker / display?

This is **not** a ridge-axis test, **not** a Tilley-style phenomenological walk, and **not** the Bulford solstitial horizon-altitude protocol. It sits in the GIS skyline / display-catchment family associated with Field, McOmish, Wheatley, Bourgeois and related work: sample approaches systematically, ask whether the monument is the local horizon peak, and compare against null models.

Reproducible parameters: [`analysis/skyline_pilot/skyline_params.json`](../../analysis/skyline_pilot/skyline_params.json)  
Summary table: [`analysis/skyline_pilot/skyline_summary.csv`](../../analysis/skyline_pilot/skyline_summary.csv)  
Script: [`scripts/skyline_pilot.py`](../../scripts/skyline_pilot.py)

---

## Qualitative ground truth (photos)

Two photographs show the phenomenon the model is trying to score:

| Photo | What it shows |
|-------|----------------|
| ![Kitchen Barrow on the distant skyline, Sep 2026](assets/kitchen-barrow-skyline-2026-09-09.jpg) | **Kitchen Barrow** from a lower southern-ish vale approach — the mound is a clear bump **on** the distant ridge skyline (silhouette). |
| ![West Kennet from the north, Oct 2021](assets/west-kennet-skyline-north-2021-10-22.jpg) | **West Kennet** from the **north** — mound silhouetted on the ridge skyline. Shared album: [photos.app.goo.gl/CTFFnN9gZJKQZBWU6](https://photos.app.goo.gl/CTFFnN9gZJKQZBWU6). |

The pilot asks whether those catches are *typical* of the defined approach corridors, or rare sweet spots — and whether named barrows beat simple nulls.

---

## Method (short)

1. **Crest** — gazetteer E/N; Z refined to **1 m chip** max within 25 m (`lidar/chips/raw/`). Surviving height ≈ chip crest minus local Gaussian trend (WK ~2.9 m).
2. **Landscape LOS** — Wiltshire **county DTM** at **20 m** (`lidar/county/wiltshire_county_dtm.tif`, SCALEFACTOR mosaic). Eye height 1.7 m. Mild earth curvature + standard refraction (k=0.13).
3. **Observers** — regular **400 m** grid, **1–5 km** from crest, approach masks only:
   - **Adam’s Grave:** Pewsey Vale south / SE / SW of the scarp, elev ≪ crest.
   - **WK / EK:** Kennet corridor north **and** south of the ridge, elev below crest.
   - **Kitchen:** vale cells around the ridge (includes south — photo GT), elev below crest.
4. **Skyline hit** — LOS to crest clear **and** terrain **300 m–5 km beyond** the crest along the same azimuth does not rise above the LOS continuation (mound = local horizon peak / silhouette). Plain **visibility** (LOS only) reported separately. Brief’s 2–5 km window kept as a secondary column.
5. **Height offsets** — primary **chip Z + 2 m** (modest reconstruction). Also h=0; for WK, county+3.2 and county+5.2 (surviving / surviving+recon sensitivity).
6. **Nulls (required)**  
   - (a) random points on the same contour band (±8 m) within 2 km;  
   - (b) fake mound shifted ~200 m downslope.  
   Same observers; same stick-up. Named barrows should beat null if “designed skyline marker” holds.

Runtime tradeoff: 400 m spacing finished in ~5 s; a 200 m grid would be ~4× slower with little change to the rank order.

---

## Results (primary: chip Z + 2 m)

| Site | n obs | % visible | % skyline | null contour % skyline | fake downslope % | ratio vs null |
|------|------:|----------:|----------:|-------------------------:|-----------------:|--------------:|
| **Adam’s Grave** | 178 | 89.3 | **89.3** | 15.5 | 0.0 | **5.8×** |
| **Kitchen** | 390 | 41.8 | **36.7** | 10.3 | 0.0 | **3.6×** |
| East Kennet | 176 | 29.0 | 2.8 | 1.5 | 0.0 | 1.9× |
| West Kennet | 84 | 29.8 | 1.2 | 3.3 | 0.0 | 0.4× |

Maps (observers coloured skyline / visible-not-skyline / not-visible; hillshade backdrop):

- [Adam’s Grave](../../analysis/skyline_pilot/skyline_SU16SW102.png)
- [Kitchen](../../analysis/skyline_pilot/skyline_SU06SE101.png)
- [West Kennet](../../analysis/skyline_pilot/skyline_SU16NW100.png)
- [East Kennet](../../analysis/skyline_pilot/skyline_SU16NW101.png)
- [Multipanel](../../analysis/skyline_pilot/skyline_multipanel.png)

---

## Reading the four

**Adam’s Grave** is the clearest “skyline marker from the vale” in this set. From Pewsey Vale approaches the scarp-edge mound is almost always on the skyline when it is visible at all (89% / 89%). Contour-band nulls average ~16%; a fake crest shoved 200 m downslope collapses to 0%. That is what a designed (or at least highly effective) scarp silhouette looks like in these scores.

**Kitchen** also **beats null** (~37% skyline vs ~10% contour null; fake downslope 0%). The map shows a coherent southern / vale catchment — consistent with the Sep 2026 photo of the barrow as a distant skyline bump. Not as dominant as Adam’s Grave, but the named site outperforms random same-height ground and a downslope sham.

**East Kennet** is weak: a few percent skyline, only modestly above null. Often visible against backdrop rather than as the horizon peak.

**West Kennet** is the awkward one relative to the north skyline photo. Corridor sampling gives ~30% plain visibility but only ~1% true skyline — **below** the contour null mean. Geometry says why: from much of the northern Kennet valley the ray through WK continues onto higher chalk (East Kennet ridge and related ground), so the mound is often seen *against* terrain, not against sky. The Oct 2021 north photo is real qualitative ground truth — the model does find sparse northern cells where silhouette works — but those are **narrow sweet spots**, not the typical corridor cell at 400 m. Raising the target (chip+2, county+5.2) barely moves skyline %. So: WK *can* silhouette from the north; as a *fraction of defined approaches* it does not currently beat null as a skyline marker the way Kitchen and Adam’s Grave do.

---

## Caveats (please keep these next to the maps)

- **Trees / vegetation** — DTM is bare-earth. Real woodland on approaches or crests would shrink catchments. Treat percentages as an **upper bound**.
- **Chronology** — Neolithic land cover, mound height when built, and chalk brightness are not modelled. A fresh chalk mound would have been a much louder visual signal than a green DTM bump.
- **20 m county DTM** — fine for vale→ridge LOS; crest detail comes from 1 m chips. Coarse cells near the crest can smear local ridge texture; beyond-window starts at 300 m partly for that reason.
- **False positives without null** — raw skyline % on chalk scarps can look impressive for *any* high point. The contour-band and downslope-fake nulls are doing the real work. Adam’s Grave and Kitchen clear them; WK corridor scores do not.
- **Approach definition** — results are conditional on the masks (vale south for Adam’s; N/S Kennet corridor; Kitchen vale ring). A different sampling frame would change the percentages; the photo GTs remain valid for their specific viewpoints.
- **Bulford protocol** is a different question (solstitial horizon altitude). Do not mix the two.

---

## Bottom line

From defined vale approaches, **Adam’s Grave** and **Kitchen** behave like skyline display markers and beat nulls; **Kitchen’s map matches the southern silhouette photo**. **West Kennet** and **East Kennet** are often visible from the valley but rarely the true skyline peak in this 20 m / 400 m pilot — WK’s north skyline photo records a real but uncommon catch relative to the corridor sample. Next steps if worth pushing: denser observers near photo azimuths, DSM/vegetation sensitivity, and a larger Wiltshire batch with the same null discipline.

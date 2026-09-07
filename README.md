# Wiltshire long barrows

Leaflet / dark-theme gazetteer of Wiltshire Neolithic long barrows — HER seed,
NHLE footprints, Cotswold–Severn vs earthen type, first-pass long-axis orientation,
county EA terrain hillshade.

Author: **Tim Daw / [sarsen.org](https://www.sarsen.org/)** · **CC BY-SA 4.0**

Modelled on the Fremington Clay and A303 corridor maps (scientific honesty over folklore).

## v1 contents

- Gazetteer from open Wiltshire HER extracts (Zenodo) + NHLE scheduled polygons (OGL)
- Circle markers with rim arrows for undirected long-axis azimuth (NHLE footprint PCA)
- Search / filter (certain vs possible; has azimuth; Cotswold–Severn vs earthen); detail panel above catalogue (scrolls into view on select)
- County-wide EA Composite DTM hillshade (always on; map uses mobile JPEG `lidar/web/county-hillshade.jpg`)
- Desktop-only 1 m LiDAR hillshade chips around each barrow (zoom ≥ 14; `lidar/chips/web/`)
- Cotswold–Severn (stone-chambered) vs earthen filter (seven peer-cited Cotswold sites)

## Build

```bash
# use a venv with pyproj, rasterio, numpy, matplotlib, pillow (see ../fremington/.venv)
python ingest.py
python generate.py

# county terrain hillshade (default map base; ~20 m EA DTM)
python download_ea_county_dtm.py
python make_county_hillshade.py

# optional offline Stonehenge-cluster detail assets (not wired into the map)
python download_ea_dtm.py
python make_ea1m_hillshade.py

# per-barrow 1 m EA DTM hillshade chips (desktop map ≥ zoom 14)
python build_barrow_lidar_chips.py   # or make_barrow_chips.py

python generate.py
```

Do **not** commit `lidar/**/*.tif` (gitignored); **do** commit `lidar/chips/web/*.jpg` + `index.json`.
No `git push` from this box — laptop later.

## Mobile hillshade

The full `county-hillshade.png` is ~4.7 MB / 1739×2345 and can fail to paint as a Leaflet
`imageOverlay` on mobile Safari. The map loads `county-hillshade.jpg` instead (long side
1600, quality ~78, flattened onto the dark map background; ~0.26 MB / 1187×1600). Rebuild
with `scripts/_make_web_hillshade.py` after regenerating the PNG. County OSGB bbox
(outline + ~2 km) is E372000–438000 N114000–203000; see `lidar/web/county-bounds.json`.

## Desktop 1 m barrow chips

At desktop widths (≥901 px) and map zoom ≥ **14**, the map overlays small (~380 m OSGB)
EA Composite DTM **1 m** hillshade JPEGs centred on each long barrow (`lidar/chips/web/`).
Mobile and low zoom skip them (county coarse hillshade only). Rebuild with
`build_barrow_lidar_chips.py` (sequential WCS; resumes cached `lidar/chips/raw/*.tif`).
Chips © Environment Agency / **OGL**. Raw GeoTIFFs stay gitignored.

## Orientation note

“Faces the rising sun” is ambiguous: long-axis vs façade/forecourt; midwinter vs midsummer
vs equinox; true solar vs topographic horizon. v1 does **not** assert solar intent.
See `NOTES.md` and the on-page analysis.

## Licence

Compilation © Tim Daw / sarsen.org · CC BY-SA 4.0  
NHLE © Historic England / OGL · EA LiDAR © Environment Agency / OGL  
Zenodo Wheatley recreation 10.5281/zenodo.11005373 CC BY 4.0 (underlying Wiltshire HER)  
Zenodo Kutty 2024 10.5281/zenodo.10989406 CC BY 4.0 (HER via Heritage Gateway)  
Research gazetteer; not official HER; no land access implied.

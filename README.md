# Wiltshire long barrows

Leaflet / dark-theme gazetteer of Wiltshire Neolithic long barrows — HER seed,
NHLE footprints, Cotswold–Severn vs earthen type, first-pass long-axis orientation,
county EA terrain hillshade + Stonehenge detail overlay.

Author: **Tim Daw / [sarsen.org](https://www.sarsen.org/)** · **CC BY-SA 4.0**

Modelled on the Fremington Clay and A303 corridor maps (scientific honesty over folklore).

## v1 contents

- Gazetteer from open Wiltshire HER extracts (Zenodo) + NHLE scheduled polygons (OGL)
- Orientation ticks where NHLE footprint PCA yields an undirected long-axis azimuth
- Search / filter (certain vs possible; has azimuth)
- Optional sunrise-ray overlay (midsummer / equinox / midwinter ≈51.2°N) — illustrative only
- County-wide coarse EA Composite DTM hillshade + Stonehenge-cluster detail overlay
- Cotswold–Severn (stone-chambered) vs earthen filter (seven peer-cited Cotswold sites)

## Build

```bash
# use a venv with pyproj, rasterio, numpy, matplotlib, pillow (see ../fremington/.venv)
python ingest.py
python generate.py

# county terrain hillshade (default map base; ~20 m EA DTM)
python download_ea_county_dtm.py
python make_county_hillshade.py

# optional Stonehenge-cluster detail (override WILTS_LB_BBOX=e0,e1,n0,n1)
python download_ea_dtm.py
python make_ea1m_hillshade.py

python generate.py
```

Do **not** commit `lidar/**/*.tif` (gitignored). No `git push` from this box — laptop later.

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

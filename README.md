# Wiltshire long barrows

Leaflet / dark-theme gazetteer of Wiltshire Neolithic long barrows — HER seed,
NHLE footprints, Cotswold–Severn vs earthen type, first-pass long-axis orientation,
county EA terrain hillshade.

Author: **Tim Daw / [sarsen.org](https://www.sarsen.org/)** · **CC BY-SA 4.0**

Modelled on the Fremington Clay and A303 corridor maps (scientific honesty over folklore).

## v1 contents

- Gazetteer from open Wiltshire HER extracts (Zenodo) + NHLE scheduled polygons (OGL)
- Circle markers with rim arrows for undirected long-axis azimuth (NHLE footprint PCA)
- Search / filter (certain vs possible; has azimuth; Cotswold–Severn vs earthen)
- Optional sunrise-ref overlay (midsummer / equinox / midwinter ≈51.2°N) — illustrative only, not site alignments
- County-wide coarse EA Composite DTM hillshade
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

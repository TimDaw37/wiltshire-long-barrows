# Wiltshire long barrows

Live: https://timdaw37.github.io/wiltshire-long-barrows/

Leaflet / dark-theme gazetteer of Wiltshire Neolithic long barrows â€” HER seed,
NHLE footprints, first-pass long-axis orientation, EA LiDAR hillshade (when built).

Author: **Tim Daw / [sarsen.org](https://www.sarsen.org/)** Â· **CC BY-SA 4.0**

Modelled on the Fremington Clay and A303 corridor maps (scientific honesty over folklore).

## v1 contents

- Gazetteer from open Wiltshire HER extracts (Zenodo) + NHLE scheduled polygons (OGL)
- Orientation ticks where NHLE footprint PCA yields an undirected long-axis azimuth
- Search / filter (certain vs possible; has azimuth)
- Optional sunrise-ray overlay (midsummer / equinox / midwinter â‰ˆ51.2Â°N) â€” illustrative only
- EA Composite DTM hillshade for a first Stonehenge-cluster bbox (after download)

## Build

```bash
# use a venv with pyproj, rasterio, numpy, matplotlib, pillow (see ../fremington/.venv)
python ingest.py
python generate.py

# optional LiDAR (Stonehenge cluster by default; override WILTS_LB_BBOX=e0,e1,n0,n1)
python download_ea_dtm.py
python make_ea1m_hillshade.py
python generate.py
```

Do **not** commit `lidar/**/*.tif` (gitignored). No `git push` from this box â€” laptop later.

## Orientation note

â€œFaces the rising sunâ€ is ambiguous: long-axis vs faÃ§ade/forecourt; midwinter vs midsummer
vs equinox; true solar vs topographic horizon. v1 does **not** assert solar intent.
See `NOTES.md` and the on-page analysis.

## Licence

Compilation Â© Tim Daw / sarsen.org Â· CC BY-SA 4.0  
NHLE Â© Historic England / OGL Â· HER Â© Wiltshire Council Â· EA LiDAR Â© Environment Agency / OGL  
Research gazetteer only; no public land access implied.


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

## Orientation conventions (v1)

- `azimuth_deg`: undirected long-axis bearing, **degrees from north**, range **0–180**.  
  Computed as `atan2(ΔE, ΔN)` of the NHLE polygon PCA major axis, folded to 0–180.
- `front_end`: **null** (not asserted). Literature often places the wider/higher/forecourt end
  toward the east, but that is site-specific.
- `azimuth_method`: `nhle_polygon_pca` | null
- Flat-horizon sunrise ≈51.2°N (true solar, no refraction): midsummer ~50°, equinox ~90°, midwinter ~129°.

Peer consensus for Wiltshire chalk: **no clear common astronomical alignment**; topography matters
(Ruggles; Roberts et al. IA 47; Darvill). Treat solar claims as hypotheses to test against LiDAR-derived axes.

## Cotswold–Severn vs earthen

Important Wiltshire split: **Cotswold–Severn** (stone-chambered; “Cotteswold” tradition)
vs **earthen** long barrows (Wessex chalk). Field `barrow_type`:
`cotswold_severn` | `earthen` | `uncertain`.

v1 marks **seven** peer-attested Cotswold–Severn sites only (do not invent membership):

| Site | HE / id | Citation basis |
|------|---------|----------------|
| West Kennet | 1010628 | Darvill 2004; Piggott & Atkinson 1955–56 |
| East Kennet | 1012323 | Barker inventory; HE sarsens / probable chambers |
| Adam's Grave | 1013032 | HE (Thurnam sarsen chamber); Severn–Cotswold type |
| Millbarrow | SU07SE105 | Whittle excavation; Cotswold–Severn type (destroyed) |
| Lanhill | 1010908 | Corcoran 1969; Darvill 2004 |
| Lugbury | 1010397 | Corcoran 1969; Darvill 2004 (Littleton Drew) |
| Giant's Cave (Luckington) | 1010394 | Crawford 1925; Darvill 2004; HE “chambered” — added from NHLE (absent from Wheatley seed) |

All other rows default to `earthen`. Fringe Wikipedia lists (e.g. Kitchen Barrow, Horton Down,
South Street as “Cotswold–Severn”) are **not** auto-promoted without chambered peer evidence;
South Street / Longstones are excavated **earthen** monuments.

## LiDAR

- County: `python download_ea_county_dtm.py` then `python make_county_hillshade.py`
- Detail (Stonehenge): `WILTS_LB_BBOX=… python download_ea_dtm.py` then `make_ea1m_hillshade.py`
- Next: refine orientations from mound crest / ditch lines on hillshade rather than NHLE polygons alone.

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


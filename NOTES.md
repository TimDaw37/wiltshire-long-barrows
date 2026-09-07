# Notes — Wiltshire long barrows gazetteer

## Sources ranked (v1)

1. **Wiltshire HER certain/possible points** — Zenodo 10.5281/zenodo.11005373  
   (data for Wheatley 1996 viewshed recreation). Gives BNG coords + certainty + some names.  
   *Caveat:* CSV columns labelled Latitude/Longitude are actually easting/northing.  
   Licence: check Zenodo record; derived from Wiltshire HER (not a substitute for HER licence terms).

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

5. **EA LiDAR Composite DTM 1 m** — OGL  
   WCS: `https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs`  
   Coverage ID same pattern as Fremington / A303 corridor projects.

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

## LiDAR next step

Default download bbox = Stonehenge / Salisbury Plain cluster from gazetteer + margin, capped
~9×8 km. Expand with `WILTS_LB_BBOX` for Avebury / Pewsey belt. Then refine orientations from
mound crest / ditch lines on hillshade rather than NHLE polygons alone.

## Gaps

- Incomplete naming; many HER-only IDs
- Possible HER rows include oval barrows / uncertain cropmarks — keep `status`
- Two seed rows dropped for impossible OSGB (outside chalk envelope)
- Cranborne Chase fringe sites may sit on county borders
- No git push from box

## LiDAR status (this run)

Downloaded EA Composite DTM (SCALEFACTOR 0.5 → 2 m) for Stonehenge WHS first bbox
`E408500–416500 N139500–146500`. Hillshade: `lidar/web/ea1m-hillshade.png` (placeholder=false).
Next: expand to Avebury / Pewsey with `WILTS_LB_BBOX`.

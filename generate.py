#!/usr/bin/env python3
"""Build Wiltshire long-barrows gazetteer index.html (Leaflet dark theme)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

STATUS_COLOUR = {
    "certain": "#c9a227",
    "possible": "#7a8a9a",
    "modern": "#5ec8c0",
}
STATUS_LABEL = {
    "certain": "HER certain",
    "possible": "HER possible",
    "modern": "Modern (not Neolithic HER)",
}

# Flat-horizon sunrise azimuths ≈51.2°N (true solar; no refraction / altitude)
SUNRISE_AZ = {
    "midsummer": 50.2,
    "equinox": 89.7,
    "midwinter": 129.0,
}


def load_rows() -> list[dict]:
    return json.loads((DATA / "long_barrows.json").read_text(encoding="utf-8"))


def load_bounds(name: str) -> dict | None:
    p = ROOT / "lidar" / "web" / f"{name}-bounds.json"
    web = ROOT / "lidar" / "web"
    asset = None
    for ext in (".jpg", ".jpeg", ".png"):
        cand = web / f"{name}-hillshade{ext}"
        if cand.is_file():
            asset = cand
            break
    if p.is_file() and asset is not None:
        meta = json.loads(p.read_text(encoding="utf-8"))
        meta["_asset"] = asset.name
        return meta
    return None




def load_county_geojson() -> dict | None:
    p = DATA / "wiltshire-county.geojson"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def geojson_leaflet_bounds(gj: dict) -> list[list[float]] | None:
    """Return [[south, west], [north, east]] from FeatureCollection coords."""
    lons: list[float] = []
    lats: list[float] = []

    def walk(coords):
        if not coords:
            return
        if isinstance(coords[0], (int, float)):
            lons.append(float(coords[0]))
            lats.append(float(coords[1]))
            return
        for c in coords:
            walk(c)

    for f in gj.get("features") or []:
        geom = f.get("geometry") or {}
        walk(geom.get("coordinates"))
    if not lons:
        return None
    return [[min(lats), min(lons)], [max(lats), max(lons)]]

def html_page(
    rows: list[dict],
    county_bounds: dict | None,
    county_outline_bounds: list | None = None,
) -> str:
    n = len(rows)
    n_cert = sum(1 for r in rows if r.get("status") == "certain")
    n_az = sum(1 for r in rows if r.get("azimuth_display_deg") is not None)
    n_nhle_az = sum(1 for r in rows if r.get("azimuth_deg") is not None)
    n_sched = sum(1 for r in rows if r.get("scheduled"))
    clusters = Counter(r.get("cluster") or "—" for r in rows)
    has_county = county_bounds is not None
    has_outline = county_outline_bounds is not None

    holes_json = json.dumps(rows, ensure_ascii=False)
    colour_json = json.dumps(STATUS_COLOUR)
    label_json = json.dumps(STATUS_LABEL)
    county_bounds_json = json.dumps((county_bounds or {}).get("wgs84_leaflet"))
    county_outline_bounds_json = json.dumps(county_outline_bounds)
    county_asset = (county_bounds or {}).get("_asset") or "county-hillshade.png"
    county_asset_json = json.dumps(county_asset)
    cluster_bits = ", ".join(f"{k}: {v}" for k, v in sorted(clusters.items()))
    if has_county:
        lidar_legend = (
            "<br><b>LiDAR:</b> County backdrop: EA Composite DTM ~20&nbsp;m (all devices). "
            "Per-barrow 1&nbsp;m chips: desktop map zoom ≳14, and in the detail strip when a barrow is selected."
        )
    else:
        lidar_legend = (
            "LiDAR hillshade: placeholder — run download_ea_county_dtm.py / "
            "make_county_hillshade.py."
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>The Wiltshire Long Barrow Gazetteer</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  :root {{
    --bg: #141210;
    --panel: #1c1914;
    --ink: #e8e0d4;
    --muted: #9a9080;
    --line: #3a3428;
    --gold: #c9a227;
    --accent: #6d9e6b;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font: 15px/1.45 system-ui, -apple-system, sans-serif;
    overflow-x: hidden;
  }}
  a {{ color: var(--gold); }}
  header {{ padding: 1.25rem 1.5rem .5rem; max-width: 1400px; margin: 0 auto; }}
  header h1 {{ margin: 0 0 .35rem; font-size: 1.55rem; font-weight: 650; color: var(--gold); }}
  .layout {{
    display: flex; flex-direction: column; gap: 0;
    max-width: 1400px; margin: 0 auto; border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    width: 100%; overflow-x: hidden;
  }}
  #map {{
    width: 100%; height: 62vh; min-height: 420px; background: #0d0c0a;
    position: relative; z-index: 0; overflow: hidden; touch-action: pan-x pan-y;
    -webkit-transform: translateZ(0);
  }}
  .detail {{
    width: 100%; max-width: 100%; margin: 0; padding: 1rem 1.25rem 1.15rem;
    background: #18160f; border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    overflow-x: hidden; box-sizing: border-box;
  }}
  .detail-inner {{
    display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 420px);
    gap: 1.1rem 1.5rem; align-items: start;
    max-width: 100%; overflow-x: hidden; box-sizing: border-box;
  }}
  .detail h2 {{ margin: 0 0 .35rem; color: var(--gold); font-size: 1.35rem; }}
  .detail .meta {{ color: var(--muted); font-size: .88rem; }}
  .detail .placeholder {{ color: var(--muted); font-size: .95rem; margin: .35rem 0; }}
  .detail dl {{
    display: grid; grid-template-columns: minmax(0, 8rem) minmax(0, 1fr); gap: .25rem .65rem;
    margin: .65rem 0 0; font-size: .9rem;
  }}
  .detail dt {{ color: var(--muted); }}
  .detail dd {{ margin: 0; overflow-wrap: anywhere; }}
  .detail .chip-figure {{
    margin: 0; justify-self: end; width: 100%; max-width: 100%;
    overflow-x: hidden; box-sizing: border-box;
  }}
  .detail .chip-figure img {{
    display: block; width: 100%; max-width: 100%; height: auto; max-height: 420px; object-fit: contain;
    border-radius: 6px; border: 1px solid var(--line); background: #0d0c0a;
  }}
  .detail .chip-figure figcaption {{
    color: var(--muted); font-size: .75rem; margin-top: .35rem;
  }}
  .detail .chip-missing {{
    color: var(--muted); font-size: .85rem; margin: 0;
    padding: 1rem; border: 1px dashed var(--line); border-radius: 6px;
    background: #12100e; min-height: 8rem; display: flex; align-items: center;
  }}
  .gazetteer {{
    width: 100%; background: var(--panel);
    display: flex; flex-direction: column; min-height: 0;
  }}
  .gazetteer-head {{
    padding: .75rem 1.25rem .35rem; display: flex; flex-wrap: wrap;
    gap: .55rem .85rem; align-items: baseline;
  }}
  .gazetteer-head h2 {{
    margin: 0; color: var(--gold); font-size: 1.05rem; font-weight: 650;
  }}
  .filters {{ padding: .35rem 1.25rem .35rem; max-width: 42rem; }}
  .filters input {{
    width: 100%; background: #12100e; color: var(--ink); border: 1px solid var(--line);
    border-radius: 4px; padding: .5rem .65rem; font: inherit;
  }}
  .chip-row {{ padding: 0 1.25rem .55rem; display: flex; flex-wrap: wrap; gap: .35rem; }}
  .chip {{
    border: 1px solid var(--line); background: #12100e; color: var(--muted);
    border-radius: 999px; padding: .2rem .55rem; font-size: .72rem; cursor: pointer;
  }}
  .chip.on {{ border-color: var(--gold); color: var(--gold); }}
  .list {{
    overflow: auto; max-height: 48vh; min-height: 12rem;
    padding: 0 1rem .85rem;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: .25rem .45rem; align-content: start;
  }}
  .item {{
    padding: .5rem .55rem; border-radius: 4px; cursor: pointer;
    border: 1px solid transparent; margin: 0;
  }}
  .item:hover, .item.active {{ background: #242018; border-color: var(--line); }}
  .item .nm {{ font-weight: 600; font-size: .9rem; }}
  .item .meta {{ color: var(--muted); font-size: .72rem; margin-top: .1rem; }}
  .dot {{
    display: inline-block; width: .55rem; height: .55rem; border-radius: 50%;
    margin-right: .35rem; vertical-align: middle;
  }}
  section.about {{
    max-width: 1400px; margin: 0 auto; padding: .85rem 1.5rem 1.5rem;
    border-top: 1px solid var(--line);
  }}
  section.about > h2.about-heading {{
    color: var(--gold); font-size: 1.05rem; font-weight: 650;
    margin: 0; padding: .35rem 0;
  }}
  section.about .lead {{ margin: .7rem 0 0; max-width: 70rem; color: var(--ink); }}
  section.about .stats {{
    margin: .75rem 0 0; padding: 0;
    display: flex; flex-wrap: wrap; gap: .5rem .9rem; font-size: .85rem; color: var(--muted);
  }}
  section.about .stats b {{ color: var(--ink); }}
  section.about .legend {{
    margin: .65rem 0 0; padding: 0;
    color: var(--muted); font-size: .82rem;
  }}
  .notes {{
    max-width: none; margin: 0; padding: .6rem 0 0;
  }}
  .notes h2 {{ color: var(--gold); font-size: 1.05rem; margin: 1.2rem 0 .4rem; }}
  .notes p, .notes li {{ color: var(--ink); font-size: .9rem; }}
  .notes ul {{ padding-left: 1.2rem; }}

  .orientation-findings {{
    margin: 1.25rem 0 0;
    padding: 1rem 0 0;
    border-top: 1px solid var(--line);
    max-width: 70rem;
    display: grid;
    grid-template-columns: minmax(0, 16rem) minmax(0, 1fr);
    gap: 1rem 1.25rem;
    align-items: center;
  }}
  .orientation-findings img {{
    width: 100%;
    max-width: 16rem;
    height: auto;
    border-radius: 6px;
    background: #0b0a09;
    border: 1px solid var(--line);
  }}
  .orientation-findings h2 {{
    margin: 0 0 .45rem;
    font-size: 1.05rem;
  }}
  .orientation-findings p {{
    margin: 0 0 .55rem;
    color: var(--ink);
    line-height: 1.45;
  }}
  .orientation-findings .more {{
    margin: 0;
    font-size: .92rem;
  }}
  @media (max-width: 700px) {{
    .orientation-findings {{
      grid-template-columns: 1fr;
    }}
    .orientation-findings img {{ max-width: 14rem; }}
  }}

  footer {{
    max-width: 1400px; margin: 0 auto; padding: 0 1.5rem 2rem;
    color: var(--muted); font-size: .8rem;
  }}
  .lb-icon {{
    background: transparent; border: none;
  }}
  .lb-icon svg {{
    display: block; overflow: visible;
    filter: drop-shadow(0 0 1px #0d0c0a);
  }}
  .lb-icon.selected svg .lb-ring {{
    stroke: #e8e0d4;
    stroke-width: 3.2;
  }}
  .lb-icon.selected svg .lb-shaft,
  .lb-icon.selected svg .lb-head {{
    stroke: #e8e0d4;
  }}
  @media (max-width: 900px) {{
    body, .layout {{ overflow-x: hidden; }}
    #map {{
      height: 48vh; min-height: 260px; max-height: none;
      width: 100%; overflow: hidden;
    }}
    .detail {{ padding: .85rem 1rem; max-width: 100%; overflow-x: hidden; }}
    .detail-inner {{
      grid-template-columns: 1fr;
      max-width: 100%; overflow-x: hidden;
    }}
    .detail h2 {{ font-size: 1.15rem; }}
    .detail dl {{ grid-template-columns: minmax(0, 6.5rem) minmax(0, 1fr); }}
    .detail .chip-figure {{
      justify-self: stretch; max-width: 100%; overflow-x: hidden;
    }}
    .detail .chip-figure img {{
      width: 100%; max-width: 100%; height: auto; max-height: none;
    }}
    .list {{
      max-height: 42vh; grid-template-columns: 1fr;
      padding: 0 .75rem .75rem;
    }}
    .filters, .chip-row, .gazetteer-head {{ padding-left: 1rem; padding-right: 1rem; }}
    section.about {{ padding: .75rem 1rem 1.25rem; }}
  }}
</style>
</head>
<body>
<header>
  <h1>The Wiltshire Long Barrow Gazetteer</h1>
</header>

<div class="layout">
  <div id="map"></div>
  <section class="detail" id="detail" aria-live="polite">
    <div class="detail-inner">
      <div class="detail-copy">
        <p class="placeholder">Select a long barrow on the map or in the gazetteer to see its description and 1&nbsp;m LiDAR hillshade.</p>
      </div>
      <div class="chip-missing">Select a barrow for its ~380&nbsp;m <b>1&nbsp;m</b> EA hillshade chip here. The map backdrop behind the pins stays ~20&nbsp;m on every device.</div>
    </div>
  </section>
  <div class="gazetteer">
    <div class="gazetteer-head"><h2>Gazetteer</h2></div>
    <div class="filters">
      <input id="q" type="search" placeholder="Search name, HER, NHLE, parish, notes…"/>
    </div>
    <div class="chip-row" id="chips"></div>
    <div class="list" id="list"></div>
  </div>
</div>

<section class="about" id="about">
  <h2 class="about-heading">About this map</h2>
  <p class="lead">
    Interactive gazetteer of Wiltshire Neolithic long barrows from open HER extracts and
    Historic England scheduling polygons, plus Tim Daw’s modern All Cannings long barrow.
    Terrain is a county-wide EA Composite DTM hillshade at ~20&nbsp;m; desktop zoom shows 1&nbsp;m chips.
  </p>
  <div class="stats" id="stats">
    <span><b>{n}</b> barrows</span>
    <span><b>{n_cert}</b> HER certain · <b>{n - n_cert}</b> possible</span>
    <span><b>{n_sched}</b> NHLE-matched</span>
    <span><b>{n_az}</b> with long-axis bearing shown</span>
    <span>{cluster_bits}</span>
  </div>
  <p class="legend">
    Gold = HER certain · grey = possible.
    Circle markers: gold = HER certain, grey = possible, teal = modern.
    Rim arrows mark undirected long-axis bearings from north (0–180°), human-checked where shown.
    Gold outline = ceremonial Wiltshire (UA + Swindon).
    {lidar_legend}
  </p>

  <div class="orientation-findings" id="orientation">
    <img src="docs/analysis/fig-01-rose-display.png" width="512" height="512"
         alt="Rose diagram of 86 Wiltshire long-barrow long axes, drawn both ways, with flat-horizon sunrise lines for midsummer, equinox and midwinter">
    <div>
      <h2>Do they face the sun?</h2>
      <p>
        <strong>No</strong> — not as a shared design, and not as folklore likes.
        They do not all run along the ridges either. The eighty-six axes we could
        trust mostly <strong>spread</strong>, with only a gentle east–west smear
        and no spike at midsummer or midwinter.
      </p>
      <p class="more">
        <a href="docs/analysis/wiltshire-long-barrows-facing-the-land.html" target="_blank" rel="noopener noreferrer">Short note on the bearings</a>
        · dashed lines on the rose are sunrise on a flat horizon (drawn for scale, not a finding)
      </p>
    </div>
  </div>

  <section class="notes">
    <h2>Long axis</h2>
    <p>
      Map arrows are undirected long-axis bearings from north (0–180°),
      human-checked where shown. They are not solar alignments or façade directions.
    </p>

    <h2>Typology</h2>
    <p>
      Chambered, earthen, and hybrid traits form a spectrum — this map does not force a binary
      Cotswold–Severn vs earthen class on markers or filters. See each site’s Notes for plain-language typology.
      <b>All Cannings</b> is a modern (2014–) long barrow, not a Neolithic HER site.
    </p>

    <h2>Sources (v1 seed)</h2>
    <ul>
      <li>Wiltshire HER certain/possible points — Zenodo <a href="https://doi.org/10.5281/zenodo.11005373">10.5281/zenodo.11005373</a> (Wheatley recreation; underlying Wiltshire HER).</li>
      <li>Named Avebury / Stonehenge HER list — Kutty 2024 Zenodo <a href="https://doi.org/10.5281/zenodo.10989406">10.5281/zenodo.10989406</a> (compiled from HER via Heritage Gateway).</li>
      <li>Historic England NHLE Scheduled Monuments (OGL) — footprint + List Entry via ArcGIS FeatureServer.</li>
      <li>Cotswold–Severn typology: Corcoran 1969; Darvill 2004 <i>Long Barrows of the Cotswolds</i>; Crawford 1925; site reports (Piggott &amp; Atkinson; Whittle; Thurnam).</li>
      <li>Catalogue literature: Ashbee; Field 2006; Kinnes 1992; Roberts et al. IA 47; McOmish et al. 2002 (SPTA).</li>
      <li>EA LiDAR Composite DTM — OGL; county backdrop ~20 m (all devices); per-barrow 1 m hillshade chips (~380 m) on desktop zoom ≥14 and in the detail strip.</li>
    </ul>

    <h2>Known limits</h2>
    <ul>
      <li>Many HER rows lack published names; display falls back to HER / parish number.</li>
      <li>Long-axis bearings are human-checked where shown; sites without a clear axis appear as plain circles.</li>
      <li>Length/width from scheduling polygons are approximate (often oversize vs mound).</li>
      <li>Not a complete county inventory of every ploughed / cropmark candidate.</li>
    </ul>

    <h2>Licence / sources</h2>
    <p>
      Compilation © Tim Daw / <a href="https://www.sarsen.org/">sarsen.org</a> ·
      <a rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>.
      NHLE © Historic England / OGL.
      EA LiDAR © Environment Agency / OGL.
      Ceremonial county boundary © Office for National Statistics / OGL.
      Zenodo Wheatley recreation <a href="https://doi.org/10.5281/zenodo.11005373">10.5281/zenodo.11005373</a> CC BY 4.0 (underlying Wiltshire HER).
      Zenodo Kutty 2024 <a href="https://doi.org/10.5281/zenodo.10989406">10.5281/zenodo.10989406</a> CC BY 4.0 (compiled from HER via Heritage Gateway).
      Research gazetteer; not official HER; no land access implied.
    </p>
  </section>
</section>

<footer>
  <p>© Tim Daw / sarsen.org · CC BY-SA 4.0</p>
</footer>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="county-outline.js?v=8"></script>
<script src="barrow-chips.js"></script>
<script>
const ROWS = {holes_json};
const COLOUR = {colour_json};
const STATUS_LABEL = {label_json};
const COUNTY_BOUNDS = {county_bounds_json};
const COUNTY_ASSET = {county_asset_json};
const HAS_COUNTY = {json.dumps(has_county)};
const HAS_OUTLINE = {json.dumps(has_outline)};
const COUNTY_OUTLINE_BOUNDS = {county_outline_bounds_json};

const map = L.map('map', {{ zoomControl: true }});
const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}}).addTo(map);

let countyLayer = null;
if (!map.getPane('terrain')) {{
  map.createPane('terrain');
  map.getPane('terrain').style.zIndex = 350;
  map.getPane('terrain').style.pointerEvents = 'none';
}}
if (HAS_COUNTY) {{
  countyLayer = L.imageOverlay('lidar/web/' + COUNTY_ASSET + '?v=8', COUNTY_BOUNDS, {{
    opacity: 0.72,
    interactive: false,
    pane: 'terrain',
    attribution: 'EA LiDAR Composite DTM (county coarse) © Environment Agency / OGL'
  }}).addTo(map);
}}

if (!map.getPane('county')) {{
  map.createPane('county');
  map.getPane('county').style.zIndex = 450;
  map.getPane('county').style.pointerEvents = 'none';
}}
if (!map.getPane('barrows')) {{ map.createPane('barrows'); map.getPane('barrows').style.zIndex = 650; }}
function esc(s) {{
  return String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
}}
/** Human-reviewed preferred axis for map icons / filters / tooltips / primary detail. No NHLE fallback. */
function displayAz(h) {{
  return h.azimuth_display_deg != null ? h.azimuth_display_deg : null;
}}
function axisSourcePlain(src) {{
  if (src === 'eye') return 'eye reading';
  if (src === 'lidar') return 'LiDAR';
  if (src === 'nhle') return 'Historic England outline';
  return src ? String(src) : 'not set';
}}

/** SVG DivIcon: filled circle; with azimuth, bidirectional arrows from the rim. */
function makeIconHtml(h, selected) {{
  const col = COLOUR[h.status] || '#888';
  const az = displayAz(h);
  const hasAz = az != null;
  const size = hasAz ? 36 : 18;
  const cx = size / 2, cy = size / 2;
  const r = hasAz ? 7 : 5.5;
  const ringW = selected ? 3.2 : 1.4;
  const ringCol = selected ? '#e8e0d4' : '#1a1814';
  let inner = '<circle class="lb-ring" cx="' + cx + '" cy="' + cy + '" r="' + r +
    '" fill="' + col + '" stroke="' + ringCol + '" stroke-width="' + ringW + '"/>';
  if (hasAz) {{
    // Shaft from rim to near arrowhead tip both ways; arrowheads outside circumference.
    // ViewBox y-up after CSS rotate? We draw along +x then rotate whole SVG by az.
    // Azimuth from north toward east ≡ CSS rotate(az deg) with shaft along +y (up = north).
    const tip = size / 2 - 1;
    const rim = r + 0.5;
    const head = 4.5;
    const shaftCol = selected ? '#e8e0d4' : '#f2ebe0';
    // Draw shaft along vertical (north–south in unrotated coords), rotate by az.
    inner =
      '<g transform="rotate(' + az + ' ' + cx + ' ' + cy + ')">' +
      '<line class="lb-shaft" x1="' + cx + '" y1="' + (cy - tip) + '" x2="' + cx + '" y2="' + (cy - rim) +
        '" stroke="' + shaftCol + '" stroke-width="2.2" stroke-linecap="round"/>' +
      '<line class="lb-shaft" x1="' + cx + '" y1="' + (cy + rim) + '" x2="' + cx + '" y2="' + (cy + tip) +
        '" stroke="' + shaftCol + '" stroke-width="2.2" stroke-linecap="round"/>' +
      '<polygon class="lb-head" points="' +
        cx + ',' + (cy - tip) + ' ' +
        (cx - head * 0.55) + ',' + (cy - tip + head) + ' ' +
        (cx + head * 0.55) + ',' + (cy - tip + head) +
        '" fill="' + shaftCol + '"/>' +
      '<polygon class="lb-head" points="' +
        cx + ',' + (cy + tip) + ' ' +
        (cx - head * 0.55) + ',' + (cy + tip - head) + ' ' +
        (cx + head * 0.55) + ',' + (cy + tip - head) +
        '" fill="' + shaftCol + '"/>' +
      '<circle class="lb-ring" cx="' + cx + '" cy="' + cy + '" r="' + r +
        '" fill="' + col + '" stroke="' + ringCol + '" stroke-width="' + ringW + '"/>' +
      '</g>';
  }}
  return '<svg xmlns="http://www.w3.org/2000/svg" width="' + size + '" height="' + size +
    '" viewBox="0 0 ' + size + ' ' + size + '">' + inner + '</svg>';
}}

function makeIcon(h, selected) {{
  const hasAz = displayAz(h) != null;
  const size = hasAz ? 36 : 18;
  return L.divIcon({{
    className: 'lb-icon' + (selected ? ' selected' : ''),
    html: makeIconHtml(h, !!selected),
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2]
  }});
}}

function rowKey(h) {{
  // Stable unique key so duplicate gazetteer ids cannot clobber markers/rowById
  return [h.id, h.her_ref || '', h.easting, h.northing].join('|');
}}

const markers = {{}};
const rowById = {{}};
ROWS.forEach(h => {{ rowById[rowKey(h)] = h; }});
const layer = L.layerGroup().addTo(map);
let selectedKey = null;

ROWS.forEach(h => {{
  const key = rowKey(h);
  const m = L.marker([h.lat, h.lon], {{
    icon: makeIcon(h, false),
    pane: 'barrows',
    riseOnHover: true
  }}).bindTooltip((h.display_name || h.id) + (displayAz(h) != null ? ' · az ' + displayAz(h) + '°' : ''));
  m.on('click', () => select(key, true));
  markers[key] = m;
  m.addTo(layer);
}});

const group = L.featureGroup(Object.values(markers));
// Simple fit — same pattern as last-known-good 8de4907 (whenReady/maxZoom/setMaxBounds blanked the map).
if (HAS_OUTLINE && COUNTY_OUTLINE_BOUNDS) {{
  map.fitBounds(COUNTY_OUTLINE_BOUNDS, {{ padding: [12, 12] }});
}} else if (HAS_COUNTY && COUNTY_BOUNDS) {{
  map.fitBounds(COUNTY_BOUNDS, {{ padding: [12, 12] }});
}} else {{
  map.fitBounds(group.getBounds().pad(0.08));
}}

// OSM + terrain + outline + barrows always on (no layer control).
if (typeof initWiltshireCountyOutline === 'function') initWiltshireCountyOutline(map);
const barrowChips = (typeof initBarrowLidarChips === 'function')
  ? initBarrowLidarChips(map, {{ minZoom: 14 }})
  : null;

let filterStatus = 'all';
let filterAz = 'all';

function matches(h, q) {{
  if (filterStatus !== 'all' && h.status !== filterStatus) return false;
  if (filterAz === 'with' && displayAz(h) == null) return false;
  if (filterAz === 'without' && displayAz(h) != null) return false;
  if (!q) return true;
  const blob = [h.display_name, h.name, h.id, h.her_ref, h.her_alt_ref, h.he_list_entry, h.ngr, h.cluster, h.notes, h.parish].join(' ').toLowerCase();
  return blob.includes(q);
}}

function renderList() {{
  const q = (document.getElementById('q').value || '').trim().toLowerCase();
  const el = document.getElementById('list');
  const frag = document.createDocumentFragment();
  let n = 0;
  ROWS.forEach(h => {{
    const key = rowKey(h);
    const show = matches(h, q);
    if (markers[key]) {{
      if (show) {{ markers[key].addTo(layer); }}
      else {{ layer.removeLayer(markers[key]); }}
    }}
    if (!show) return;
    n++;
    const div = document.createElement('div');
    div.className = 'item' + (key === selectedKey ? ' active' : '');
    div.dataset.key = key;
    const col = COLOUR[h.status] || '#888';
    div.innerHTML = '<div class="nm"><span class="dot" style="background:' + col + '"></span>' + esc(h.display_name || h.id) + '</div>'
      + '<div class="meta">' + esc(STATUS_LABEL[h.status] || h.status)
      + (displayAz(h) != null ? ' · az ' + displayAz(h) + '°' : ' · az —')
      + (h.scheduled ? ' · scheduled' : '')
      + (h.cluster ? ' · ' + esc(h.cluster) : '') + '</div>';
    div.onclick = () => select(key, true);
    frag.appendChild(div);
  }});
  el.innerHTML = '';
  el.appendChild(frag);
}}

function sourceLinkLabel(u) {{
  const her = (u.match(/ViewHERItem\\?HER=(MWI\\d+)/i) || [])[1];
  if (her) return 'Wiltshire HER ' + her.toUpperCase();
  if (/HistoryEnvRecord\\/Home\\/Index/i.test(u)) return null;
  if (/zenodo\\.org/i.test(u)) return 'Zenodo dataset';
  if (/historicengland\\.org\\.uk\\/listing/i.test(u)) {{
    const le = (u.match(/list-entry\\/(\\d+)/i) || [])[1];
    return le ? ('NHLE ' + le) : 'Historic England';
  }}
  try {{
    const host = u.replace(/^https?:\\/\\//i, '').split('/')[0];
    return host || u;
  }} catch (e) {{
    return u;
  }}
}}

function select(key, pan) {{
  const h = rowById[key] || ROWS.find(r => rowKey(r) === key);
  if (!h) return;
  selectedKey = key;
  document.querySelectorAll('.item').forEach(n => n.classList.toggle('active', n.dataset.key === key));
  // Rebuild DivIcons for selection highlight (no setStyle on DivIcon markers)
  Object.keys(markers).forEach(mid => {{
    const row = rowById[mid];
    if (!row) return;
    markers[mid].setIcon(makeIcon(row, mid === key));
  }});
  if (pan && markers[key]) map.panTo(markers[key].getLatLng());
  const det = document.getElementById('detail');
  const links = [];
  if (h.he_url) links.push('<a href="' + esc(h.he_url) + '" target="_blank" rel="noopener noreferrer">NHLE ' + esc(h.he_list_entry) + '</a>');
  const herView = h.her_ref && String(h.her_ref).indexOf('MWI') === 0
    ? ('https://services.wiltshire.gov.uk/HistoryEnvRecord/Home/ViewHERItem?HER=' + h.her_ref)
    : null;
  if (herView) {{
    links.push('<a href="' + esc(herView) + '" target="_blank" rel="noopener noreferrer">Wiltshire HER ' + esc(h.her_ref) + '</a>');
  }}
  (h.source_urls || []).forEach(u => {{
    if (!u) return;
    if (h.he_url && u === h.he_url) return;
    if (herView && u === herView) return;
    if (/HistoryEnvRecord\\/Home\\/Index/i.test(u)) return;
    const lab = sourceLinkLabel(u);
    if (!lab) return;
    links.push('<a href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">' + esc(lab) + '</a>');
  }});
  const cp = barrowChips && barrowChips.getChipPath ? barrowChips.getChipPath(h.id) : null;
  const chipHtml = cp
    ? ('<figure class="chip-figure"><img src="' + esc(cp)
      + '" alt="EA 1 m DTM hillshade (~380 m around ' + esc(h.display_name || h.id) + ')"/>'
      + '<figcaption>EA Composite DTM 1&nbsp;m hillshade · ~380&nbsp;m square · OGL</figcaption></figure>')
    : '<p class="chip-missing">No 1&nbsp;m LiDAR chip for this barrow yet.</p>';
  det.innerHTML = '<div class="detail-inner">'
    + '<div class="detail-copy">'
    + '<h2>' + esc(h.display_name || h.id) + '</h2>'
    + '<p class="meta">' + esc(STATUS_LABEL[h.status] || h.status)
    + (h.status === 'modern' ? ' · contemporary (not scheduled Neolithic)' : (h.scheduled ? ' · scheduled monument' : ' · not matched to NHLE in v1'))
    + (h.cluster ? ' · ' + esc(h.cluster) : '') + '</p>'
    + '<dl>'
    + '<dt>NGR</dt><dd>' + esc(h.ngr || '—') + '</dd>'
    + '<dt>OSGB</dt><dd>E' + h.easting + ' N' + h.northing + '</dd>'
    + '<dt>Long axis</dt><dd>' + (displayAz(h) != null
      ? (displayAz(h) + '° from north · ' + axisSourcePlain(h.azimuth_display_source))
      : '—')
    + '</dd>'
    + '<dt>Length × width</dt><dd>' + (h.length_m != null ? (h.length_m + ' × ' + (h.width_m ?? '—') + ' m (approx.)') : '—') + '</dd>'
    + '<dt>Refs</dt><dd>' + (links.join(' · ') || '—') + '</dd>'
    + '<dt>Notes</dt><dd>' + esc(h.notes || '') + '</dd>'
    + '</dl>'
    + '</div>'
    + chipHtml
    + '</div>';
  try {{
    det.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
  }} catch (e) {{
    det.scrollIntoView(true);
  }}
}}

const chips = document.getElementById('chips');
const statusChips = [];
[['all','All'],['certain','Certain'],['possible','Possible'],['modern','Modern']].forEach(([k,lab]) => {{
  const b = document.createElement('button');
  b.className = 'chip' + (k === 'all' ? ' on' : '');
  b.textContent = lab;
  b.onclick = () => {{ filterStatus = k; statusChips.forEach((c,i) => c.classList.toggle('on', ['all','certain','possible','modern'][i]===k)); renderList(); }};
  statusChips.push(b);
  chips.appendChild(b);
}});
const azChips = [];
[['all','Any az'],['with','Has az'],['without','No az']].forEach(([k,lab]) => {{
  const b = document.createElement('button');
  b.className = 'chip' + (k === 'all' ? ' on' : '');
  b.textContent = lab;
  b.onclick = () => {{
    filterAz = k;
    azChips.forEach((c,i) => c.classList.toggle('on', ['all','with','without'][i]===k));
    renderList();
  }};
  azChips.push(b);
  chips.appendChild(b);
}});
document.getElementById('q').addEventListener('input', renderList);
renderList();
</script>
</body>
</html>
"""


def main() -> None:
    rows = load_rows()
    county_bounds = load_bounds("county")
    county_gj = load_county_geojson()
    outline_bounds = geojson_leaflet_bounds(county_gj) if county_gj else None
    # ea1m cluster mosaic unused; per-barrow 1 m chips via barrow-chips.js + lidar/chips/web/
    out = ROOT / "index.html"
    out.write_text(html_page(rows, county_bounds, outline_bounds), encoding="utf-8")
    n_az = sum(1 for r in rows if r.get("azimuth_display_deg") is not None)
    n_nhle_az = sum(1 for r in rows if r.get("azimuth_deg") is not None)
    print(
        f"wrote {out} ({len(rows)} barrows, {n_az} with display azimuth, "
        f"{n_nhle_az} NHLE PCA; county_lidar={county_bounds is not None})"
    )


if __name__ == "__main__":
    main()

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
}
STATUS_LABEL = {
    "certain": "HER certain",
    "possible": "HER possible",
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
    n_az = sum(1 for r in rows if r.get("azimuth_deg") is not None)
    n_sched = sum(1 for r in rows if r.get("scheduled"))
    n_cots = sum(1 for r in rows if r.get("barrow_type") == "cotswold_severn")
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
        lidar_legend = "County terrain hillshade always on (EA Composite DTM; mobile JPEG)."
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
<title>Wiltshire long barrows — gazetteer</title>
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
  }}
  a {{ color: var(--gold); }}
  header {{ padding: 1.25rem 1.5rem .5rem; max-width: 1400px; margin: 0 auto; }}
  header h1 {{ margin: 0 0 .35rem; font-size: 1.55rem; font-weight: 650; color: var(--gold); }}
  header .sub {{ margin: 0; color: var(--muted); font-size: .92rem; }}
  header .lead {{ margin: .7rem 0 0; max-width: 70rem; color: var(--ink); }}
  .stats {{
    max-width: 1400px; margin: 0 auto; padding: .4rem 1.5rem .6rem;
    display: flex; flex-wrap: wrap; gap: .5rem .9rem; font-size: .85rem; color: var(--muted);
  }}
  .stats b {{ color: var(--ink); }}
  .legend {{
    max-width: 1400px; margin: 0 auto; padding: 0 1.5rem .6rem;
    color: var(--muted); font-size: .82rem;
  }}
  .layout {{
    display: grid; grid-template-columns: 1fr 340px; gap: 0;
    max-width: 1400px; margin: 0 auto; border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
  }}
  #map {{
    height: 68vh; min-height: 420px; background: #0d0c0a;
    position: relative; z-index: 0; overflow: hidden; touch-action: pan-x pan-y;
    -webkit-transform: translateZ(0);
  }}
  .side {{
    background: var(--panel); border-left: 1px solid var(--line);
    display: flex; flex-direction: column; max-height: 68vh; min-height: 420px;
  }}
  .filters {{ padding: .65rem .75rem .35rem; }}
  .filters input {{
    width: 100%; background: #12100e; color: var(--ink); border: 1px solid var(--line);
    border-radius: 4px; padding: .45rem .55rem; font: inherit;
  }}
  .chip-row {{ padding: 0 .75rem .45rem; display: flex; flex-wrap: wrap; gap: .35rem; }}
  .chip {{
    border: 1px solid var(--line); background: #12100e; color: var(--muted);
    border-radius: 999px; padding: .2rem .55rem; font-size: .72rem; cursor: pointer;
  }}
  .chip.on {{ border-color: var(--gold); color: var(--gold); }}
  .list {{ overflow: auto; flex: 1; min-height: 0; padding: 0 .4rem .6rem; }}
  .item {{
    padding: .45rem .5rem; border-radius: 4px; cursor: pointer;
    border: 1px solid transparent; margin-bottom: .2rem;
  }}
  .item:hover, .item.active {{ background: #242018; border-color: var(--line); }}
  .item .nm {{ font-weight: 600; font-size: .88rem; }}
  .item .meta {{ color: var(--muted); font-size: .72rem; margin-top: .1rem; }}
  .dot {{
    display: inline-block; width: .55rem; height: .55rem; border-radius: 50%;
    margin-right: .35rem; vertical-align: middle;
  }}
  .detail {{
    flex: 0 0 auto; max-height: 42%; overflow: auto;
    margin: 0; padding: .65rem .75rem .75rem;
    background: #18160f; border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
  }}
  .detail h2 {{ margin: 0 0 .35rem; color: var(--gold); font-size: 1.05rem; }}
  .detail .meta {{ color: var(--muted); font-size: .8rem; }}
  .detail .placeholder {{ color: var(--muted); font-size: .85rem; margin: 0; }}
  .detail dl {{
    display: grid; grid-template-columns: 7.5rem 1fr; gap: .2rem .55rem;
    margin: .55rem 0 0; font-size: .82rem;
  }}
  .detail dt {{ color: var(--muted); }}
  .detail dd {{ margin: 0; }}
  .notes {{
    max-width: 1400px; margin: 0 auto; padding: 1.2rem 1.5rem 2rem;
  }}
  .notes h2 {{ color: var(--gold); font-size: 1.05rem; margin: 1.2rem 0 .4rem; }}
  .notes p, .notes li {{ color: var(--ink); font-size: .9rem; }}
  .notes ul {{ padding-left: 1.2rem; }}
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
    .layout {{ grid-template-columns: 1fr; }}
    #map {{
      height: 48vh; min-height: 260px; max-height: none;
      width: 100%; overflow: hidden;
    }}
    .side {{
      max-height: none; border-left: 0; border-top: 1px solid var(--line);
    }}
    .detail {{ max-height: none; }}
    .list {{ max-height: 42vh; }}
  }}
</style>
</head>
<body>
<header>
  <h1>Wiltshire long barrows</h1>
  <p class="sub">Neolithic long mounds · HER gazetteer · NHLE footprints · orientation first pass</p>
  <p class="lead">
    Interactive gazetteer of Wiltshire Neolithic long barrows seeded from open Wiltshire HER
    extracts and Historic England scheduling polygons. Orientation is treated carefully:
    <b>long-axis azimuth</b> (undirected, degrees from north) is derived from NHLE footprints
    where matched — <b>not</b> claimed as a measured façade → sunrise alignment.
    County-wide terrain hillshade from EA Composite DTM (coarse; mobile JPEG). Cotswold–Severn
    (stone-chambered) vs earthen long barrows are filterable — membership cited, not invented.
  </p>
</header>

<div class="stats" id="stats">
  <span><b>{n}</b> barrows</span>
  <span><b>{n_cert}</b> HER certain · <b>{n - n_cert}</b> possible</span>
  <span><b>{n_cots}</b> Cotswold–Severn · <b>{n - n_cots}</b> earthen/other</span>
  <span><b>{n_sched}</b> NHLE-matched</span>
  <span><b>{n_az}</b> with long-axis azimuth</span>
  <span>{cluster_bits}</span>
</div>
<p class="legend">
  Gold = HER certain · grey = possible.
  Circle markers with rim arrows show undirected long-axis from NHLE polygon PCA (where available);
  plain circles have no derived azimuth.
  Gold county outline = ceremonial Wiltshire (UA + Swindon); county terrain hillshade always on where available.
  {lidar_legend}
</p>

<div class="layout">
  <div id="map"></div>
  <div class="side">
    <div class="filters">
      <input id="q" type="search" placeholder="Search name, HER, NHLE, parish, notes…"/>
    </div>
    <div class="chip-row" id="chips"></div>
    <section class="detail" id="detail">
      <p class="placeholder">Select a long barrow.</p>
    </section>
    <div class="list" id="list"></div>
  </div>
</div>

<section class="notes">
  <h2>Orientation — what “faces the rising sun?” means</h2>
  <p>
    British earthen long barrows are often described as “east–west”, with ritual focus at the
    higher / wider / forecourt end (commonly east — Field 2006; Ashbee; Kinnes). That is
    <b>not</b> the same as a precise solstitial sightline. For Wiltshire latitude ≈51.2°N,
    flat-horizon true-solar sunrise azimuths are approximately:
  </p>
  <ul>
    <li>midsummer sunrise ≈ <b>{SUNRISE_AZ['midsummer']:.0f}°</b> from north</li>
    <li>equinox sunrise ≈ <b>{SUNRISE_AZ['equinox']:.0f}°</b></li>
    <li>midwinter sunrise ≈ <b>{SUNRISE_AZ['midwinter']:.0f}°</b></li>
  </ul>
  <p>
    v1 stores an <b>undirected</b> long-axis azimuth (0–180°) from NHLE scheduling polygons
    (<code>azimuth_method=nhle_polygon_pca</code>). The scheduling outline includes ditches and
    margins — it is a first pass, not a crest survey. <b>Front / façade end is null</b> until
    a peer source or LiDAR-derived morphology justifies it. Ruggles (1999) and Roberts et al.
    (Internet Archaeology 47) find <b>no clear common astronomical alignment</b> among Salisbury
    Plain / Stonehenge WHS long barrows; local topography often dominates. Burl’s lunar-arc
    reading of Salisbury Plain orientations remains contested (see Ruggles 1997 PBA).
  </p>

  <h2>Cotswold–Severn vs earthen</h2>
  <p>
    The important Wiltshire split is <b>Cotswold–Severn</b> (stone-chambered; classic
    “Cotteswold” tradition) versus <b>earthen</b> long barrows (Wessex chalk mounds,
    usually timber chambers if any). About seven Cotswold–Severn sites fall in the
    county; v1 marks only peer-attested membership (Darvill 2004; Corcoran 1969;
    Crawford 1925; site excavations / HE chamber notes) — see <code>NOTES.md</code>.
    All other gazetteer rows default to <code>earthen</code>.
  </p>

  <h2>Sources (v1 seed)</h2>
  <ul>
    <li>Wiltshire HER certain/possible points — Zenodo <a href="https://doi.org/10.5281/zenodo.11005373">10.5281/zenodo.11005373</a> (Wheatley recreation; underlying Wiltshire HER).</li>
    <li>Named Avebury / Stonehenge HER list — Kutty 2024 Zenodo <a href="https://doi.org/10.5281/zenodo.10989406">10.5281/zenodo.10989406</a> (compiled from HER via Heritage Gateway).</li>
    <li>Historic England NHLE Scheduled Monuments (OGL) — footprint + List Entry via ArcGIS FeatureServer.</li>
    <li>Cotswold–Severn typology: Corcoran 1969; Darvill 2004 <i>Long Barrows of the Cotswolds</i>; Crawford 1925; site reports (Piggott &amp; Atkinson; Whittle; Thurnam).</li>
    <li>Catalogue / orientation literature: Ashbee; Field 2006; Kinnes 1992; Ruggles 1997/1999; Roberts et al. IA 47; McOmish et al. 2002 (SPTA).</li>
    <li>EA LiDAR Composite DTM — OGL; county coarse hillshade (~20 m WCS).</li>
  </ul>

  <h2>Honesty gaps</h2>
  <ul>
    <li>Many HER rows lack published names; display falls back to HER / parish number.</li>
    <li>Orientation not in HER export — derived only where NHLE polygon matched.</li>
    <li>Length/width from scheduling polygons are approximate (often oversize vs mound).</li>
    <li>Not a complete county inventory of every ploughed / cropmark candidate.</li>
    <li>Cotswold–Severn membership is curated from peer sources; fringe / dubious chamber claims stay earthen unless cited.</li>
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

<footer>
  <p>© Tim Daw / sarsen.org · CC BY-SA 4.0 · scientific honesty over folklore</p>
</footer>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="county-outline.js"></script>
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
  countyLayer = L.imageOverlay('lidar/web/' + COUNTY_ASSET, COUNTY_BOUNDS, {{
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

/** SVG DivIcon: filled circle; with azimuth, bidirectional arrows from the rim. */
function makeIconHtml(h, selected) {{
  const col = COLOUR[h.status] || '#888';
  const hasAz = h.azimuth_deg != null;
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
      '<g transform="rotate(' + h.azimuth_deg + ' ' + cx + ' ' + cy + ')">' +
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
  const hasAz = h.azimuth_deg != null;
  const size = hasAz ? 36 : 18;
  return L.divIcon({{
    className: 'lb-icon' + (selected ? ' selected' : ''),
    html: makeIconHtml(h, !!selected),
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2]
  }});
}}

const markers = {{}};
const rowById = {{}};
ROWS.forEach(h => {{ rowById[h.id] = h; }});
const layer = L.layerGroup().addTo(map);
let selectedId = null;

ROWS.forEach(h => {{
  const m = L.marker([h.lat, h.lon], {{
    icon: makeIcon(h, false),
    pane: 'barrows',
    riseOnHover: true
  }}).bindTooltip((h.display_name || h.id) + (h.azimuth_deg != null ? ' · az ' + h.azimuth_deg + '°' : ''));
  m.on('click', () => select(h.id, true));
  markers[h.id] = m;
  m.addTo(layer);
}});

const group = L.featureGroup(Object.values(markers));
if (HAS_OUTLINE && COUNTY_OUTLINE_BOUNDS) {{
  map.fitBounds(COUNTY_OUTLINE_BOUNDS, {{ padding: [4, 4] }});
}} else if (HAS_COUNTY && COUNTY_BOUNDS) {{
  map.fitBounds(COUNTY_BOUNDS, {{ padding: [4, 4] }});
}} else {{
  map.fitBounds(group.getBounds().pad(0.08));
}}

// OSM + terrain + outline + barrows always on (no layer control).
if (typeof initWiltshireCountyOutline === 'function') initWiltshireCountyOutline(map);

let filterStatus = 'all';
let filterAz = 'all';
let filterType = 'all';

function matches(h, q) {{
  if (filterStatus !== 'all' && h.status !== filterStatus) return false;
  if (filterAz === 'with' && h.azimuth_deg == null) return false;
  if (filterAz === 'without' && h.azimuth_deg != null) return false;
  if (filterType !== 'all' && (h.barrow_type || 'earthen') !== filterType) return false;
  if (!q) return true;
  const blob = [h.display_name, h.name, h.id, h.her_ref, h.her_alt_ref, h.he_list_entry, h.ngr, h.cluster, h.notes, h.parish, h.barrow_type].join(' ').toLowerCase();
  return blob.includes(q);
}}

function renderList() {{
  const q = (document.getElementById('q').value || '').trim().toLowerCase();
  const el = document.getElementById('list');
  const frag = document.createDocumentFragment();
  let n = 0;
  ROWS.forEach(h => {{
    const show = matches(h, q);
    if (markers[h.id]) {{
      if (show) {{ markers[h.id].addTo(layer); }}
      else {{ layer.removeLayer(markers[h.id]); }}
    }}
    if (!show) return;
    n++;
    const div = document.createElement('div');
    div.className = 'item' + (h.id === selectedId ? ' active' : '');
    div.dataset.id = h.id;
    const col = COLOUR[h.status] || '#888';
    div.innerHTML = '<div class="nm"><span class="dot" style="background:' + col + '"></span>' + esc(h.display_name || h.id) + '</div>'
      + '<div class="meta">' + esc(STATUS_LABEL[h.status] || h.status)
      + (h.azimuth_deg != null ? ' · az ' + h.azimuth_deg + '°' : ' · az —')
      + (h.barrow_type === 'cotswold_severn' ? ' · Cotswold–Severn' : '')
      + (h.scheduled ? ' · scheduled' : '')
      + (h.cluster ? ' · ' + esc(h.cluster) : '') + '</div>';
    div.onclick = () => select(h.id, true);
    frag.appendChild(div);
  }});
  el.innerHTML = '';
  el.appendChild(frag);
}}

function select(id, pan) {{
  const h = ROWS.find(r => r.id === id);
  if (!h) return;
  selectedId = id;
  document.querySelectorAll('.item').forEach(n => n.classList.toggle('active', n.dataset.id === id));
  // Rebuild DivIcons for selection highlight (no setStyle on DivIcon markers)
  Object.keys(markers).forEach(mid => {{
    const row = rowById[mid];
    if (!row) return;
    markers[mid].setIcon(makeIcon(row, mid === id));
  }});
  if (pan && markers[id]) map.panTo(markers[id].getLatLng());
  const det = document.getElementById('detail');
  const links = [];
  if (h.he_url) links.push('<a href="' + esc(h.he_url) + '" target="_blank" rel="noopener">NHLE ' + esc(h.he_list_entry) + '</a>');
  if (h.her_ref) links.push('HER ' + esc(h.her_ref));
  (h.source_urls || []).slice(0, 4).forEach(u => {{
    if (h.he_url && u === h.he_url) return;
    links.push('<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(u.replace(/^https?:\\/\\//,'').slice(0,48)) + '</a>');
  }});
  det.innerHTML = '<h2>' + esc(h.display_name || h.id) + '</h2>'
    + '<p class="meta">' + esc(STATUS_LABEL[h.status] || h.status)
    + (h.scheduled ? ' · scheduled monument' : ' · not matched to NHLE in v1')
    + (h.cluster ? ' · ' + esc(h.cluster) : '') + '</p>'
    + '<dl>'
    + '<dt>Barrow type</dt><dd>' + (h.barrow_type === 'cotswold_severn'
      ? 'Cotswold–Severn (stone-chambered)'
      : (h.barrow_type === 'uncertain' ? 'Uncertain' : 'Earthen (Wessex tradition default)')) + '</dd>'
    + '<dt>NGR</dt><dd>' + esc(h.ngr || '—') + '</dd>'
    + '<dt>OSGB</dt><dd>E' + h.easting + ' N' + h.northing + '</dd>'
    + '<dt>Long axis</dt><dd>' + (h.azimuth_deg != null ? (h.azimuth_deg + '° from N (undirected)') : '—')
    + (h.azimuth_method ? ' · <code>' + esc(h.azimuth_method) + '</code>' : '') + '</dd>'
    + '<dt>Front / façade</dt><dd>' + esc(h.front_end || 'unknown (not asserted in v1)') + '</dd>'
    + '<dt>Length × width</dt><dd>' + (h.length_m != null ? (h.length_m + ' × ' + (h.width_m ?? '—') + ' m (approx.)') : '—') + '</dd>'
    + '<dt>Refs</dt><dd>' + (links.join(' · ') || '—') + '</dd>'
    + '<dt>Notes</dt><dd>' + esc(h.notes || '') + '</dd>'
    + '</dl>';
  try {{
    det.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
  }} catch (e) {{
    det.scrollIntoView(true);
  }}
}}

const chips = document.getElementById('chips');
const statusChips = [];
[['all','All'],['certain','Certain'],['possible','Possible']].forEach(([k,lab]) => {{
  const b = document.createElement('button');
  b.className = 'chip' + (k === 'all' ? ' on' : '');
  b.textContent = lab;
  b.onclick = () => {{ filterStatus = k; statusChips.forEach((c,i) => c.classList.toggle('on', ['all','certain','possible'][i]===k)); renderList(); }};
  statusChips.push(b);
  chips.appendChild(b);
}});
const typeChips = [];
[['all','Any type'],['cotswold_severn','Cotswold–Severn'],['earthen','Earthen']].forEach(([k,lab]) => {{
  const b = document.createElement('button');
  b.className = 'chip' + (k === 'all' ? ' on' : '');
  b.textContent = lab;
  b.onclick = () => {{ filterType = k; typeChips.forEach((c,i) => c.classList.toggle('on', ['all','cotswold_severn','earthen'][i]===k)); renderList(); }};
  typeChips.push(b);
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
    # ea1m detail intentionally unused on the map (optional offline scripts remain)
    out = ROOT / "index.html"
    out.write_text(html_page(rows, county_bounds, outline_bounds), encoding="utf-8")
    n_az = sum(1 for r in rows if r.get("azimuth_deg") is not None)
    n_cots = sum(1 for r in rows if r.get("barrow_type") == "cotswold_severn")
    print(
        f"wrote {out} ({len(rows)} barrows, {n_az} with azimuth, "
        f"{n_cots} Cotswold–Severn; county_lidar={county_bounds is not None})"
    )


if __name__ == "__main__":
    main()

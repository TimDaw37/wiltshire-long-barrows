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


def load_bounds() -> dict:
    p = ROOT / "lidar" / "web" / "ea1m-bounds.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "wgs84_leaflet": [[51.05, -2.15], [51.45, -1.55]],
        "placeholder": True,
    }


def html_page(rows: list[dict], bounds: dict) -> str:
    n = len(rows)
    n_cert = sum(1 for r in rows if r.get("status") == "certain")
    n_az = sum(1 for r in rows if r.get("azimuth_deg") is not None)
    n_sched = sum(1 for r in rows if r.get("scheduled"))
    clusters = Counter(r.get("cluster") or "—" for r in rows)
    has_png = (ROOT / "lidar" / "web" / "ea1m-hillshade.png").is_file()
    placeholder = bool(bounds.get("placeholder")) or not has_png

    holes_json = json.dumps(rows, ensure_ascii=False)
    colour_json = json.dumps(STATUS_COLOUR)
    label_json = json.dumps(STATUS_LABEL)
    bounds_json = json.dumps(bounds.get("wgs84_leaflet"))
    sunrise_json = json.dumps(SUNRISE_AZ)
    cluster_bits = ", ".join(f"{k}: {v}" for k, v in sorted(clusters.items()))

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
  #map {{ height: 68vh; min-height: 420px; background: #0d0c0a; }}
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
  .list {{ overflow: auto; flex: 1; padding: 0 .4rem .6rem; }}
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
    max-width: 1400px; margin: 0 auto; padding: 1rem 1.5rem;
    background: var(--panel); border-bottom: 1px solid var(--line);
  }}
  .detail h2 {{ margin: 0 0 .4rem; color: var(--gold); font-size: 1.15rem; }}
  .detail .meta {{ color: var(--muted); font-size: .85rem; }}
  .detail dl {{
    display: grid; grid-template-columns: 9rem 1fr; gap: .25rem .75rem;
    margin: .7rem 0 0; font-size: .88rem;
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
  .orient-tick {{
    background: transparent; border: none;
  }}
  @media (max-width: 900px) {{
    .layout {{ grid-template-columns: 1fr; }}
    #map {{ height: 52vh; min-height: 52vh; }}
    .side {{ max-height: 40vh; border-left: 0; border-top: 1px solid var(--line); }}
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
    LiDAR hillshade uses EA Composite DTM (OGL) when built.
  </p>
</header>

<div class="stats" id="stats">
  <span><b>{n}</b> barrows</span>
  <span><b>{n_cert}</b> HER certain · <b>{n - n_cert}</b> possible</span>
  <span><b>{n_sched}</b> NHLE-matched</span>
  <span><b>{n_az}</b> with long-axis azimuth</span>
  <span>{cluster_bits}</span>
</div>
<p class="legend">
  Gold = HER certain · grey = possible.
  Short ticks show undirected long-axis from NHLE polygon PCA (where available).
  {"LiDAR hillshade: placeholder — run download_ea_dtm.py / make_ea1m_hillshade.py." if placeholder else "EA LiDAR Composite DTM hillshade overlay (toggle)."}
</p>

<div class="layout">
  <div id="map"></div>
  <div class="side">
    <div class="filters">
      <input id="q" type="search" placeholder="Search name, HER, NHLE, parish, notes…"/>
    </div>
    <div class="chip-row" id="chips"></div>
    <div class="list" id="list"></div>
  </div>
</div>

<section class="detail" id="detail">
  <p class="meta">Select a long barrow.</p>
</section>

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

  <h2>Sources (v1 seed)</h2>
  <ul>
    <li>Wiltshire HER certain/possible points — Zenodo <a href="https://doi.org/10.5281/zenodo.11005373">10.5281/zenodo.11005373</a> (Wheatley 1996 viewshed recreation dataset).</li>
    <li>Named Avebury / Stonehenge HER list — Kutty 2024 Zenodo <a href="https://doi.org/10.5281/zenodo.10989406">10.5281/zenodo.10989406</a>.</li>
    <li>Historic England NHLE Scheduled Monuments (OGL) — footprint + List Entry via ArcGIS FeatureServer.</li>
    <li>Catalogue / orientation literature: Ashbee; Darvill; Field 2006; Kinnes 1992; Ruggles 1997/1999; Roberts et al. IA 47; McOmish et al. 2002 (SPTA).</li>
    <li>EA LiDAR Composite DTM 1 m — OGL; WCS same pattern as Fremington / A303 corridor.</li>
  </ul>

  <h2>Honesty gaps</h2>
  <ul>
    <li>Many HER rows lack published names; display falls back to HER / parish number.</li>
    <li>Orientation not in HER export — derived only where NHLE polygon matched.</li>
    <li>Length/width from scheduling polygons are approximate (often oversize vs mound).</li>
    <li>Not a complete county inventory of every ploughed / cropmark candidate.</li>
  </ul>

  <h2>Licence</h2>
  <p>
    Compilation © Tim Daw / <a href="https://www.sarsen.org/">sarsen.org</a> ·
    <a rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>.
    NHLE © Historic England / OGL. HER underlying records © Wiltshire Council.
    EA LiDAR © Environment Agency / OGL. Research gazetteer only; no public land access implied.
  </p>
</section>

<footer>
  <p>© Tim Daw / sarsen.org · CC BY-SA 4.0 · scientific honesty over folklore</p>
</footer>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const ROWS = {holes_json};
const COLOUR = {colour_json};
const STATUS_LABEL = {label_json};
const EA_BOUNDS = {bounds_json};
const SUNRISE = {sunrise_json};
const HAS_LIDAR = {json.dumps(not placeholder)};

const map = L.map('map', {{ zoomControl: true }});
const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}}).addTo(map);

let eaLayer = null;
if (HAS_LIDAR) {{
  eaLayer = L.imageOverlay('lidar/web/ea1m-hillshade.png', EA_BOUNDS, {{
    opacity: 0.72,
    interactive: false,
    attribution: 'EA LiDAR Composite DTM © Environment Agency / OGL'
  }}).addTo(map);
}}

if (!map.getPane('barrows')) {{ map.createPane('barrows'); map.getPane('barrows').style.zIndex = 650; }}
if (!map.getPane('ticks')) {{ map.createPane('ticks'); map.getPane('ticks').style.zIndex = 660; }}

function esc(s) {{
  return String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
}}

function tickLatLngs(h, halfLenM) {{
  // undirected axis: draw both ways from centre; halfLen in metres ≈ degrees
  const az = h.azimuth_deg;
  if (az == null) return null;
  const rad = az * Math.PI / 180;
  // metres to deg approx at lat
  const mLat = 1 / 111320;
  const mLon = 1 / (111320 * Math.cos(h.lat * Math.PI / 180));
  // az from N toward E: dN = cos, dE = sin
  const dLat = Math.cos(rad) * halfLenM * mLat;
  const dLon = Math.sin(rad) * halfLenM * mLon;
  return [[h.lat - dLat, h.lon - dLon], [h.lat + dLat, h.lon + dLon]];
}}

const markers = {{}};
const tickLayers = {{}};
const layer = L.layerGroup().addTo(map);
const ticks = L.layerGroup().addTo(map);

ROWS.forEach(h => {{
  const col = COLOUR[h.status] || '#888';
  const m = L.circleMarker([h.lat, h.lon], {{
    radius: h.scheduled ? 7 : 5.5,
    color: '#1a1814',
    weight: 1.2,
    fillColor: col,
    fillOpacity: 0.92,
    pane: 'barrows'
  }}).bindTooltip((h.display_name || h.id) + (h.azimuth_deg != null ? ' · az ' + h.azimuth_deg + '°' : ''));
  m.on('click', () => select(h.id, true));
  markers[h.id] = m;
  m.addTo(layer);

  const ll = tickLatLngs(h, Math.max(28, Math.min(70, (h.length_m || 50) * 0.45)));
  if (ll) {{
    const t = L.polyline(ll, {{
      color: '#e8e0d4', weight: 2, opacity: 0.75, pane: 'ticks', interactive: false
    }});
    tickLayers[h.id] = t;
    t.addTo(ticks);
  }}
}});

const group = L.featureGroup(Object.values(markers));
map.fitBounds(group.getBounds().pad(0.08));

const overlays = {{ 'Long barrows': layer, 'Orientation ticks': ticks }};
if (eaLayer) overlays['EA LiDAR hillshade'] = eaLayer;
L.control.layers({{ 'OSM': osm }}, overlays, {{ collapsed: true }}).addTo(map);

// sunrise reference rays (centre of map, decorative — not a claim)
const sunLayer = L.layerGroup();
function drawSunRays() {{
  sunLayer.clearLayers();
  const c = map.getCenter();
  const lenM = 1800;
  Object.entries(SUNRISE).forEach(([k, az]) => {{
    const rad = az * Math.PI / 180;
    const mLat = 1 / 111320;
    const mLon = 1 / (111320 * Math.cos(c.lat * Math.PI / 180));
    const dLat = Math.cos(rad) * lenM * mLat;
    const dLon = Math.sin(rad) * lenM * mLon;
    L.polyline([[c.lat, c.lon], [c.lat + dLat, c.lon + dLon]], {{
      color: k === 'equinox' ? '#c9a227' : '#6d9e6b',
      weight: 1, opacity: 0.35, dashArray: '4 6', interactive: false
    }}).bindTooltip('sunrise ' + k + ' ≈ ' + az + '°').addTo(sunLayer);
  }});
}}
let filterStatus = 'all';
let filterAz = 'all';

function matches(h, q) {{
  if (filterStatus !== 'all' && h.status !== filterStatus) return false;
  if (filterAz === 'with' && h.azimuth_deg == null) return false;
  if (filterAz === 'without' && h.azimuth_deg != null) return false;
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
    const show = matches(h, q);
    if (markers[h.id]) {{
      if (show) {{ markers[h.id].addTo(layer); if (tickLayers[h.id]) tickLayers[h.id].addTo(ticks); }}
      else {{ layer.removeLayer(markers[h.id]); if (tickLayers[h.id]) ticks.removeLayer(tickLayers[h.id]); }}
    }}
    if (!show) return;
    n++;
    const div = document.createElement('div');
    div.className = 'item';
    div.dataset.id = h.id;
    const col = COLOUR[h.status] || '#888';
    div.innerHTML = '<div class="nm"><span class="dot" style="background:' + col + '"></span>' + esc(h.display_name || h.id) + '</div>'
      + '<div class="meta">' + esc(STATUS_LABEL[h.status] || h.status)
      + (h.azimuth_deg != null ? ' · az ' + h.azimuth_deg + '°' : ' · az —')
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
  document.querySelectorAll('.item').forEach(n => n.classList.toggle('active', n.dataset.id === id));
  Object.values(markers).forEach(m => m.setStyle({{ weight: 1.2 }}));
  if (markers[id]) markers[id].setStyle({{ weight: 3 }});
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
    + '<dt>NGR</dt><dd>' + esc(h.ngr || '—') + '</dd>'
    + '<dt>OSGB</dt><dd>E' + h.easting + ' N' + h.northing + '</dd>'
    + '<dt>Long axis</dt><dd>' + (h.azimuth_deg != null ? (h.azimuth_deg + '° from N (undirected)') : '—')
    + (h.azimuth_method ? ' · <code>' + esc(h.azimuth_method) + '</code>' : '') + '</dd>'
    + '<dt>Front / façade</dt><dd>' + esc(h.front_end || 'unknown (not asserted in v1)') + '</dd>'
    + '<dt>Length × width</dt><dd>' + (h.length_m != null ? (h.length_m + ' × ' + (h.width_m ?? '—') + ' m (approx.)') : '—') + '</dd>'
    + '<dt>Refs</dt><dd>' + (links.join(' · ') || '—') + '</dd>'
    + '<dt>Notes</dt><dd>' + esc(h.notes || '') + '</dd>'
    + '</dl>';
}}

const chips = document.getElementById('chips');
[['all','All'],['certain','Certain'],['possible','Possible']].forEach(([k,lab]) => {{
  const b = document.createElement('button');
  b.className = 'chip' + (k === 'all' ? ' on' : '');
  b.textContent = lab;
  b.onclick = () => {{ filterStatus = k; [...chips.querySelectorAll('.chip')].slice(0,3).forEach((c,i) => c.classList.toggle('on', ['all','certain','possible'][i]===k)); renderList(); }};
  chips.appendChild(b);
}});
[['all','Any az'],['with','Has az'],['without','No az']].forEach(([k,lab]) => {{
  const b = document.createElement('button');
  b.className = 'chip' + (k === 'all' ? ' on' : '');
  b.textContent = lab;
  b.onclick = () => {{
    filterAz = k;
    [...chips.querySelectorAll('.chip')].slice(3).forEach((c,i) => c.classList.toggle('on', ['all','with','without'][i]===k));
    renderList();
  }};
  chips.appendChild(b);
}});
const sunBtn = document.createElement('button');
sunBtn.className = 'chip';
sunBtn.textContent = 'Sunrise rays';
sunBtn.onclick = () => {{
  if (map.hasLayer(sunLayer)) {{ map.removeLayer(sunLayer); sunBtn.classList.remove('on'); }}
  else {{ drawSunRays(); sunLayer.addTo(map); sunBtn.classList.add('on'); }}
}};
chips.appendChild(sunBtn);

document.getElementById('q').addEventListener('input', renderList);
renderList();
</script>
</body>
</html>
"""


def main() -> None:
    rows = load_rows()
    bounds = load_bounds()
    out = ROOT / "index.html"
    out.write_text(html_page(rows, bounds), encoding="utf-8")
    n_az = sum(1 for r in rows if r.get("azimuth_deg") is not None)
    print(f"wrote {out} ({len(rows)} barrows, {n_az} with azimuth)")


if __name__ == "__main__":
    main()

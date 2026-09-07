/* Wiltshire ceremonial county outline (always on, non-interactive).
   Outside mask uses a local bbox + hole (not a world polygon) — world-hole
   masks often fill the whole map black on mobile Safari. */
function initWiltshireCountyOutline(map) {
  if (!map || !window.L) return;
  var paneName = "county";
  if (!map.getPane(paneName)) {
    map.createPane(paneName);
    map.getPane(paneName).style.zIndex = 450;
  }
  map.getPane(paneName).style.pointerEvents = "none";
  var countyBoundary = L.layerGroup({ interactive: false }).addTo(map);

  function buildOutsideMask(exteriors) {
    // Local padded bbox around the county — safer than [[90,-180],...] world ring
    var bounds = L.latLngBounds(exteriors[0]);
    for (var i = 1; i < exteriors.length; i++) bounds.extend(L.latLngBounds(exteriors[i]));
    var sw = bounds.getSouthWest();
    var ne = bounds.getNorthEast();
    var pad = 0.35; // degrees ~25–40 km
    var outer = [
      [sw.lat - pad, sw.lng - pad],
      [sw.lat - pad, ne.lng + pad],
      [ne.lat + pad, ne.lng + pad],
      [ne.lat + pad, sw.lng - pad]
    ];
    // Skip heavy mask on narrow screens — outline alone is enough
    if (window.matchMedia && window.matchMedia("(max-width: 900px)").matches) {
      return null;
    }
    return L.polygon([outer].concat(exteriors), {
      stroke: false,
      fillColor: "#0d0c0a",
      fillOpacity: 0.4,
      pane: paneName,
      interactive: false
    });
  }

  fetch("data/wiltshire-county.geojson")
    .then(function(r) {
      if (!r.ok) throw new Error("county geojson " + r.status);
      return r.json();
    })
    .then(function(gj) {
      var exteriors = [];
      (gj.features || []).forEach(function(f) {
        var g = f.geometry;
        if (!g) return;
        if (g.type === "Polygon") {
          exteriors.push(g.coordinates[0].map(function(c) { return [c[1], c[0]]; }));
        } else if (g.type === "MultiPolygon") {
          g.coordinates.forEach(function(poly) {
            exteriors.push(poly[0].map(function(c) { return [c[1], c[0]]; }));
          });
        }
      });
      if (!exteriors.length) return;
      var mask = buildOutsideMask(exteriors);
      if (mask) mask.addTo(countyBoundary);
      L.polygon(exteriors, {
        color: "#e8d48b",
        weight: 3,
        opacity: 1,
        fill: false,
        pane: paneName,
        interactive: false
      }).addTo(countyBoundary);
    })
    .catch(function(err) { console.warn("Wiltshire outline:", err); });
}

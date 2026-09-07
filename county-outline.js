/* Wiltshire ceremonial county outline only (always on, non-interactive).
   No outside-fill mask — hole polygons blanked the map black on Safari/desktop. */
function initWiltshireCountyOutline(map) {
  if (!map || !window.L) return;
  var paneName = "county";
  if (!map.getPane(paneName)) {
    map.createPane(paneName);
    map.getPane(paneName).style.zIndex = 450;
  }
  map.getPane(paneName).style.pointerEvents = "none";
  var countyBoundary = L.layerGroup({ interactive: false }).addTo(map);

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

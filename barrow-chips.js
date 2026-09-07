/* Desktop-only 1 m EA LiDAR hillshade chips around long barrows.
 * Loaded by index.html; expects BARROW_CHIPS_INDEX (from generate.py) or fetches
 * lidar/chips/web/index.json. Shows L.imageOverlay at zoom >= CHIP_MIN_ZOOM
 * when matchMedia('(min-width: 901px)') matches. No layer-control UI.
 */
(function () {
  'use strict';

  var CHIP_MIN_ZOOM = 14;
  var CHIP_OPACITY = 0.85;
  var DESKTOP_MQ = '(min-width: 901px)';

  function isDesktop() {
    try {
      return window.matchMedia && window.matchMedia(DESKTOP_MQ).matches;
    } catch (e) {
      return window.innerWidth >= 901;
    }
  }

  function initBarrowLidarChips(map, opts) {
    opts = opts || {};
    var index = opts.index || null;
    var minZoom = opts.minZoom != null ? opts.minZoom : CHIP_MIN_ZOOM;
    var overlays = {};
    var group = null;
    var ready = false;

    if (!map.getPane('barrowChips')) {
      map.createPane('barrowChips');
      // Above county terrain (350), below county outline (450) / markers (650)
      map.getPane('barrowChips').style.zIndex = 400;
      map.getPane('barrowChips').style.pointerEvents = 'none';
    }
    group = L.layerGroup();

    function chipsDict(payload) {
      if (!payload) return {};
      if (payload.chips) return payload.chips;
      return payload;
    }

    function ensureOverlays() {
      var chips = chipsDict(index);
      Object.keys(chips).forEach(function (id) {
        if (overlays[id]) return;
        var meta = chips[id];
        if (!meta || !meta.bounds || !meta.path) return;
        var layer = L.imageOverlay(meta.path, meta.bounds, {
          opacity: CHIP_OPACITY,
          interactive: false,
          pane: 'barrowChips',
          attribution: 'EA LiDAR 1 m chips © Environment Agency / OGL'
        });
        overlays[id] = layer;
      });
      ready = true;
    }

    function sync() {
      if (!ready) return;
      var show = isDesktop() && map.getZoom() >= minZoom;
      if (!show) {
        if (map.hasLayer(group)) map.removeLayer(group);
        return;
      }
      if (!map.hasLayer(group)) group.addTo(map);
      var b = map.getBounds();
      Object.keys(overlays).forEach(function (id) {
        var layer = overlays[id];
        var lb = layer.getBounds();
        var vis = b.intersects(lb);
        if (vis) {
          if (!group.hasLayer(layer)) group.addLayer(layer);
        } else {
          if (group.hasLayer(layer)) group.removeLayer(layer);
        }
      });
    }

    function applyIndex(payload) {
      index = payload;
      ensureOverlays();
      sync();
    }

    map.on('zoomend moveend', sync);
    if (window.matchMedia) {
      try {
        window.matchMedia(DESKTOP_MQ).addEventListener('change', sync);
      } catch (e) {
        try {
          window.matchMedia(DESKTOP_MQ).addListener(sync);
        } catch (e2) {}
      }
    }

    if (index && (index.chips || Object.keys(index).length)) {
      applyIndex(index);
    } else {
      fetch('lidar/chips/web/index.json')
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .then(function (j) {
          if (j) applyIndex(j);
        })
        .catch(function () {});
    }

    return {
      getChipPath: function (id) {
        var chips = chipsDict(index);
        var m = chips && chips[id];
        return m && m.path ? m.path : null;
      },
      minZoom: minZoom,
      sync: sync
    };
  }

  window.initBarrowLidarChips = initBarrowLidarChips;
  window.BARROW_CHIP_MIN_ZOOM = CHIP_MIN_ZOOM;
})();

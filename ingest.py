#!/usr/bin/env python3
"""Build Wiltshire long-barrow gazetteer from open sources.

Primary seed: Zenodo 11005373 Wiltshire HER certain/possible points
  (Wheatley 1996 viewshed recreation dataset; columns mislabelled —
  Latitude = OSGB easting, Longitude = OSGB northing).

Enrichment:
  - Kutty 2024 Zenodo 10989406 HER-named Avebury/Stonehenge list (names + MWI URLs)
  - Historic England NHLE Scheduled Monuments polygons (OGL) for ListEntry,
    hyperlink, and first-pass long-axis azimuth from footprint PCA

Orientation: azimuth_deg is the undirected long-axis bearing in degrees from
north (0–180). Front / façade end is left null unless a peer source states it;
azimuth_method documents provenance. Do not invent monument names or fronts.
"""
from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

from pyproj import Transformer

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

TF_TO_WGS = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
TF_TO_OSGB = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)

HER_MATCH_M = 200.0
NHLE_MATCH_M = 250.0
KUTTY_MATCH_M = 120.0


def ngr_from_en(e: float, n: float) -> str:
    """Compact OSGB NGR to 1 m (12-figure) for display."""
    # simplified: use numeric only fallback if letters awkward; prefer HE NGR when present
    return f"E{int(round(e))} N{int(round(n))}"


def osgb_to_ngr(e: float, n: float) -> str:
    """Standard two-letter NGR (1 m precision)."""
    e100k = int(e) // 100000
    n100k = int(n) // 100000
    # OSGB grid letters
    # false origin south-west of SV
    # letters for 500km squares then 100km
    first = "STNOHJ"  # rough — use proper table
    # Proper OSGB grid letter lookup
    grid = [
        ["SV", "SW", "SX", "SY", "SZ", "TV"],
        ["SQ", "SR", "SS", "ST", "SU", "TQ"],
        ["SL", "SM", "SN", "SO", "SP", "TL"],
        ["SF", "SG", "SH", "SJ", "SK", "TF"],
        ["SA", "SB", "SC", "SD", "SE", "TA"],
    ]
    # e,n relative to false origin: origin of SV is (0,0) in letter space at 0,0
    # Actually OSGB false origin is SW of SV: e=0 is west of SV, n=0 south of SV
    # 100km indices:
    ei = e100k
    ni = n100k
    # Mapping: SV=(0,0), SW=(1,0), ... SU=(4,1), etc.
    # Use known formula via letters A–Z omitting I
    def letters(easting, northing):
        e100 = int(easting) // 100000
        n100 = int(northing) // 100000
        # 500 km square
        first_e = e100 // 5
        first_n = n100 // 5
        # alphabet without I
        alphabet = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
        # false origin offset: SV is index 0 for both after shifting by +10 / +10? 
        # Classic: 
        #   major = alphabet[(4 - first_n)*5 + first_e] wait
        # Simpler known approach:
        sq500 = {
            (0, 0): "S", (1, 0): "T",
            (0, 1): "N", (1, 1): "O",
            (0, 2): "H", (1, 2): "J",
        }
        # e100 0-6, n100 0-12 roughly for GB
        major_e = e100 // 5
        major_n = n100 // 5
        # S covers e0-4,n0-4; T e5-9,n0-4; N e0-4,n5-9; O e5-9,n5-9
        if major_e == 0 and major_n == 0:
            c500 = "S"
        elif major_e == 1 and major_n == 0:
            c500 = "T"
        elif major_e == 0 and major_n == 1:
            c500 = "N"
        elif major_e == 1 and major_n == 1:
            c500 = "O"
        elif major_e == 0 and major_n == 2:
            c500 = "H"
        elif major_e == 1 and major_n == 2:
            c500 = "J"
        else:
            return None
        # 100 km within 500
        e_i = e100 % 5
        n_i = n100 % 5
        # 5x5 letters A-Z no I, row from north
        # for S: A B C D E (n=4); F G H J K (n=3); ... V W X Y Z (n=0)
        idx = (4 - n_i) * 5 + e_i
        if idx < 0 or idx >= 25:
            return None
        c100 = alphabet[idx]
        return c500 + c100

    pair = letters(e, n)
    if not pair:
        return ngr_from_en(e, n)
    e_rem = int(round(e)) % 100000
    n_rem = int(round(n)) % 100000
    return f"{pair}{e_rem:05d}{n_rem:05d}"


def her_mwid(ref: str) -> str | None:
    m = re.search(r"(MWI\d+)", ref or "", re.I)
    return m.group(1).upper() if m else None


def load_wheatley() -> list[dict]:
    path = DATA / "wiltshire_long_barrows_dataset.csv"
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            # mislabelled columns: Latitude=easting, Longitude=northing
            e = float(r["Latitude"])
            n = float(r["Longitude"])
            lon, lat = TF_TO_WGS.transform(e, n)
            certainty = (r.get("Certainty") or "").strip() or "Unknown"
            name = (r.get("Name") or "").strip() or None
            ref = (r.get("Ref_no") or "").strip()
            status = "certain" if certainty.lower() == "certain" else (
                "possible" if certainty.lower() == "possible" else certainty.lower()
            )
            rows.append(
                {
                    "id": ref or f"E{int(e)}N{int(n)}",
                    "name": name,
                    "easting": round(e, 1),
                    "northing": round(n, 1),
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "ngr": osgb_to_ngr(e, n),
                    "length_m": None,
                    "width_m": None,
                    "azimuth_deg": None,
                    "azimuth_method": None,
                    "front_end": None,
                    "parish": None,
                    "her_ref": her_mwid(ref) or (ref if ref.startswith("MWI") else None),
                    "her_alt_ref": ref if not ref.startswith("MWI") else None,
                    "he_list_entry": None,
                    "he_url": None,
                    "status": status,  # certain|possible from HER dataset
                    "scheduled": False,
                    "notes": (
                        "Seeded from Wiltshire HER extract in Zenodo 11005373 "
                        f"(certainty={certainty})."
                    ),
                    "source_urls": [
                        "https://doi.org/10.5281/zenodo.11005373",
                    ],
                    "cluster": None,
                }
            )
            her = rows[-1]["her_ref"]
            if her and str(her).startswith("MWI"):
                rows[-1]["source_urls"].append(
                    "https://services.wiltshire.gov.uk/HistoryEnvRecord/Home/ViewHERItem"
                    f"?HER={her}"
                )
    return rows


def load_kutty() -> list[dict]:
    path = DATA / "CSV_longbarrows_data.csv"
    out = []
    with path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            e, n = float(r["x"]), float(r["y"])
            url = (r.get("Source") or "").strip()
            m = re.search(r"HER=(MWI\d+)", url, re.I)
            her = m.group(1).upper() if m else None
            out.append(
                {
                    "name": (r.get("Name") or "").strip(),
                    "easting": e,
                    "northing": n,
                    "region": (r.get("Region") or "").strip(),
                    "her_ref": her,
                    "url": url,
                }
            )
    return out


def polygon_centroid_wgs(geom: dict) -> tuple[float, float] | None:
    if geom["type"] == "Polygon":
        ring = geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        ring = geom["coordinates"][0][0]
    else:
        return None
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def long_axis_azimuth_osgb(geom: dict) -> tuple[float | None, float | None, float | None]:
    """Return (azimuth_0_180_from_N, length_m_approx, width_m_approx) from footprint PCA."""
    if geom["type"] == "Polygon":
        rings = [geom["coordinates"][0]]
    elif geom["type"] == "MultiPolygon":
        rings = [p[0] for p in geom["coordinates"]]
    else:
        return None, None, None
    pts = []
    for ring in rings:
        for lon, lat in ring[:-1]:
            e, n = TF_TO_OSGB.transform(lon, lat)
            pts.append((e, n))
    if len(pts) < 3:
        return None, None, None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    # covariance
    sxx = sum((p[0] - mx) ** 2 for p in pts) / len(pts)
    syy = sum((p[1] - my) ** 2 for p in pts) / len(pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts) / len(pts)
    # principal eigenvector of [[sxx,sxy],[sxy,syy]]
    # angle of major axis: atan2(2sxy, sxx-syy)/2 but for direction of eigenvector:
    trace = sxx + syy
    det = sxx * syy - sxy * sxy
    # eigenvalue major
    disc = max(0.0, trace * trace / 4 - det)
    l1 = trace / 2 + math.sqrt(disc)
    # eigenvector
    if abs(sxy) > 1e-9:
        vx, vy = l1 - syy, sxy  # (vx,vy) in (e,n) = (x,y)
        # wait: matrix acts on [x,y]=[e,n]; (sxx-l)x + sxy y = 0
        # sxy * e + (syy - l1) * n = 0 → n direction
        ve = sxy
        vn = l1 - sxx
        if abs(ve) < 1e-12 and abs(vn) < 1e-12:
            ve, vn = 1.0, 0.0
    else:
        if sxx >= syy:
            ve, vn = 1.0, 0.0
        else:
            ve, vn = 0.0, 1.0
    # azimuth from north toward east (clockwise): atan2(east, north)
    az = math.degrees(math.atan2(ve, vn)) % 180.0  # undirected 0–180
    # approximate length/width from projected extents along axes
    # unit vectors
    norm = math.hypot(ve, vn) or 1.0
    ue, un = ve / norm, vn / norm
    # minor axis perpendicular
    pe, pn = -un, ue
    proj_maj = [(p[0] - mx) * ue + (p[1] - my) * un for p in pts]
    proj_min = [(p[0] - mx) * pe + (p[1] - my) * pn for p in pts]
    length = max(proj_maj) - min(proj_maj)
    width = max(proj_min) - min(proj_min)
    # scheduling polygons often include ditch margin — treat as approx only
    return round(az, 1), round(length, 1), round(width, 1)


def load_nhle() -> list[dict]:
    path = DATA / "nhle_long_barrows_raw.geojson"
    fc = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for f in fc.get("features") or []:
        props = f.get("properties") or {}
        geom = f.get("geometry")
        if not geom:
            continue
        c = polygon_centroid_wgs(geom)
        if not c:
            continue
        lon, lat = c
        e, n = TF_TO_OSGB.transform(lon, lat)
        az, length, width = long_axis_azimuth_osgb(geom)
        out.append(
            {
                "list_entry": props.get("ListEntry"),
                "name": props.get("Name"),
                "ngr": props.get("NGR"),
                "url": props.get("hyperlink"),
                "easting": e,
                "northing": n,
                "lat": lat,
                "lon": lon,
                "azimuth_deg": az,
                "length_m": length,
                "width_m": width,
                "geometry": geom,
            }
        )
    return out


def nearest(rows_en: list[tuple[float, float, int]], e: float, n: float, limit: float):
    best_i, best_d = None, None
    for i, (ee, nn, _) in enumerate(rows_en):
        # rows_en stores (e,n,idx) — fix below
        pass
    return None, None


# Peer-attested Cotswold–Severn (stone-chambered) sites in Wiltshire (~7).
# Membership only where chambered Cotswold–Severn architecture is cited —
# do not invent. Keys: HE List Entry (int) and/or gazetteer id (str).
COTSWOLD_SEVERN_BY_HE = {
    1010628: {  # West Kennet
        "cite": "Darvill 2004; Piggott & Atkinson 1955–56 (transepted chambers)",
        "label": "West Kennet",
    },
    1012323: {  # East Kennet
        "cite": "Barker Avebury chambered-tomb inventory; HE notes protruding sarsens / probable chambers",
        "label": "East Kennet",
    },
    1013032: {  # Adam's Grave
        "cite": "HE scheduling (sarsen chamber, Thurnam 1860); commonly classed Severn–Cotswold / Cotswold–Severn",
        "label": "Adam's Grave",
    },
    1010908: {  # Lanhill
        "cite": "Corcoran 1969; Darvill 2004 (Cotswold–Severn chambered)",
        "label": "Lanhill",
    },
    1010397: {  # Lugbury / Littleton Drew
        "cite": "Corcoran 1969; Darvill 2004 (Cotswold–Severn; aka Littleton Drew)",
        "label": "Lugbury",
    },
    1010394: {  # Giant's Cave, Luckington
        "cite": "Crawford 1925 Long Barrows of the Cotswolds; Darvill 2004; HE 'chambered long barrow'",
        "label": "Giant's Cave (Luckington)",
    },
}
COTSWOLD_SEVERN_BY_ID = {
    "SU07SE105": {  # Millbarrow (largely destroyed; Whittle excavation)
        "cite": "Whittle et al. Millbarrow excavation; Cotswold–Severn type chambered long barrow (destroyed)",
        "label": "Millbarrow",
    },
}

# NHLE List Entries to ensure present even if absent from Wheatley HER seed
ENSURE_NHLE_COTSWOLD = {1010394}


def assign_barrow_type(rows: list[dict]) -> None:
    """Set barrow_type: cotswold_severn | earthen | uncertain (cited membership only)."""
    for r in rows:
        he = r.get("he_list_entry")
        info = None
        if he is not None and int(he) in COTSWOLD_SEVERN_BY_HE:
            info = COTSWOLD_SEVERN_BY_HE[int(he)]
        elif r.get("id") in COTSWOLD_SEVERN_BY_ID:
            info = COTSWOLD_SEVERN_BY_ID[r["id"]]
        if info:
            r["barrow_type"] = "cotswold_severn"
            note = f" barrow_type=cotswold_severn ({info['label']}; {info['cite']})."
            if note.strip() not in (r.get("notes") or ""):
                r["notes"] = (r.get("notes") or "") + note
        else:
            # Default Wiltshire chalk long mounds are earthen (Wessex) tradition
            r["barrow_type"] = "earthen"


def add_missing_cotswold_from_nhle(rows: list[dict], nhle: list[dict]) -> list[dict]:
    """Add peer Cotswold–Severn NHLE sites missing from the HER seed (e.g. Giant's Cave)."""
    have = {int(r["he_list_entry"]) for r in rows if r.get("he_list_entry") is not None}
    by_le = {int(h["list_entry"]): h for h in nhle if h.get("list_entry") is not None}
    for le in ENSURE_NHLE_COTSWOLD:
        if le in have:
            continue
        h = by_le.get(le)
        if not h:
            print(f"WARN: Cotswold NHLE {le} not in nhle_long_barrows_raw.geojson")
            continue
        e, n = h["easting"], h["northing"]
        info = COTSWOLD_SEVERN_BY_HE[le]
        row = {
            "id": f"NHLE{le}",
            "name": h.get("name"),
            "easting": round(e, 1),
            "northing": round(n, 1),
            "lat": round(h["lat"], 6),
            "lon": round(h["lon"], 6),
            "ngr": h.get("ngr") or osgb_to_ngr(e, n),
            "length_m": h.get("length_m"),
            "width_m": h.get("width_m"),
            "azimuth_deg": h.get("azimuth_deg"),
            "azimuth_method": "nhle_polygon_pca" if h.get("azimuth_deg") is not None else None,
            "front_end": None,
            "parish": None,
            "her_ref": None,
            "her_alt_ref": None,
            "he_list_entry": le,
            "he_url": h.get("url"),
            "status": "certain",
            "scheduled": True,
            "notes": (
                f"Added from NHLE (not in Wheatley HER seed). "
                f"Cotswold–Severn chambered long barrow: {info['cite']}."
                + (
                    " Long-axis azimuth from PCA of NHLE scheduling polygon "
                    "(undirected 0–180° from N; scheduling outline ≠ mound crest)."
                    if h.get("azimuth_deg") is not None
                    else ""
                )
                + (
                    " Length/width approx. from NHLE polygon extents."
                    if h.get("length_m") is not None
                    else ""
                )
            ),
            "source_urls": [
                "https://doi.org/10.5281/zenodo.11005373",
                h["url"],
            ] if h.get("url") else ["https://doi.org/10.5281/zenodo.11005373"],
            "cluster": assign_cluster(e, n),
            "barrow_type": "cotswold_severn",
        }
        rows.append(row)
        print(f"added missing Cotswold–Severn from NHLE: {le} {h.get('name')}")
    return rows


def assign_cluster(e: float, n: float) -> str:
    # rough chalk clusters from seed extent
    if 160000 <= n <= 180000 and 398000 <= e <= 420000:
        return "Avebury / Pewsey"
    if 130000 <= n <= 155000 and 398000 <= e <= 422000:
        return "Stonehenge / Salisbury Plain"
    if n >= 155000:
        return "North Wiltshire chalk"
    if n < 130000:
        return "South Wiltshire / Chase fringe"
    return "Wiltshire chalk"


def enrich(rows: list[dict], kutty: list[dict], nhle: list[dict]) -> list[dict]:
    # One NHLE polygon → at most one gazetteer row (nearest unused within limit)
    nhle_used: set[int] = set()
    # Pre-sort candidate pairs by distance
    pairs = []
    for i, r in enumerate(rows):
        e, n = r["easting"], r["northing"]
        for h in nhle:
            d = math.hypot(e - h["easting"], n - h["northing"])
            if d <= NHLE_MATCH_M:
                pairs.append((d, i, h))
    pairs.sort()
    nhle_for_row: dict[int, dict] = {}
    for d, i, h in pairs:
        le = h["list_entry"]
        if i in nhle_for_row or le in nhle_used:
            continue
        nhle_for_row[i] = h
        nhle_used.add(le)

    for i, r in enumerate(rows):
        e, n = r["easting"], r["northing"]
        r["cluster"] = assign_cluster(e, n)
        # Kutty by HER
        matched_k = None
        if r.get("her_ref"):
            for k in kutty:
                if k["her_ref"] and k["her_ref"] == r["her_ref"]:
                    matched_k = k
                    break
        if matched_k is None:
            best, bd = None, 1e9
            for k in kutty:
                d = math.hypot(e - k["easting"], n - k["northing"])
                if d < bd:
                    best, bd = k, d
            if best is not None and bd <= KUTTY_MATCH_M:
                matched_k = best
        if matched_k:
            if not r["name"] and matched_k["name"]:
                r["name"] = matched_k["name"]
            if matched_k["her_ref"] and not r.get("her_ref"):
                r["her_ref"] = matched_k["her_ref"]
            if matched_k["url"] and matched_k["url"] not in r["source_urls"]:
                r["source_urls"].append(matched_k["url"])
            if matched_k["region"]:
                r["notes"] += f" Kutty region tag: {matched_k['region']}."
                if matched_k["region"].startswith("Avebury"):
                    r["cluster"] = "Avebury / Pewsey"
                elif matched_k["region"].startswith("Stonehenge"):
                    r["cluster"] = "Stonehenge / Salisbury Plain"

        # NHLE (unique assignment)
        best = nhle_for_row.get(i)
        if best is not None:
            r["scheduled"] = True
            r["he_list_entry"] = best["list_entry"]
            r["he_url"] = best["url"]
            if best["url"] and best["url"] not in r["source_urls"]:
                r["source_urls"].append(best["url"])
            if best.get("ngr"):
                r["ngr"] = best["ngr"]
            if not r["name"] and best.get("name"):
                r["name"] = best["name"]
            if best["azimuth_deg"] is not None:
                r["azimuth_deg"] = best["azimuth_deg"]
                r["azimuth_method"] = "nhle_polygon_pca"
                r["notes"] += (
                    " Long-axis azimuth from PCA of NHLE scheduling polygon "
                    "(undirected 0–180° from N; scheduling outline ≠ mound crest)."
                )
            if best["length_m"] is not None and r["length_m"] is None:
                r["length_m"] = best["length_m"]
                r["width_m"] = best["width_m"]
                r["notes"] += " Length/width approx. from NHLE polygon extents."
        else:
            r["azimuth_method"] = None
    return rows


def display_name(r: dict) -> str:
    if r.get("name"):
        return r["name"]
    if r.get("her_ref"):
        return r["her_ref"]
    return r["id"]


def to_geojson(rows: list[dict]) -> dict:
    feats = []
    for r in rows:
        props = {k: v for k, v in r.items() if k not in ("lat", "lon")}
        props["display_name"] = display_name(r)
        feats.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                "properties": props,
            }
        )
    return {"type": "FeatureCollection", "features": feats}



HER_INDEX_URL = "https://services.wiltshire.gov.uk/HistoryEnvRecord/Home/Index"
HER_VIEW_TMPL = (
    "https://services.wiltshire.gov.uk/HistoryEnvRecord/Home/ViewHERItem?HER={her}"
)


def scrub_source_urls(rows: list[dict]) -> None:
    """Drop useless HER Index URLs; ensure ViewHERItem for every MWI her_ref."""
    for r in rows:
        her = r.get("her_ref")
        cleaned: list[str] = []
        seen: set[str] = set()
        for u in r.get("source_urls") or []:
            if not u:
                continue
            if "HistoryEnvRecord/Home/Index" in u:
                continue
            if u in seen:
                continue
            seen.add(u)
            cleaned.append(u)
        if her and str(her).startswith("MWI"):
            view = HER_VIEW_TMPL.format(her=her)
            if view not in seen:
                cleaned.insert(0, view)
                seen.add(view)
            else:
                # Prefer her_ref ViewHER first
                cleaned = [view] + [u for u in cleaned if u != view]
        r["source_urls"] = cleaned


def resolve_duplicate_ref_nos(rows: list[dict]) -> list[dict]:
    """Fix known Wheatley duplicate Ref_no SU16NW133 (two sites, one id).

    Keep Avebury White Hill (E414364 N167444) as SU16NW133.
    Rogue Stonehenge-area point (~537 m from MWI13689) is a wrong-sheet
    duplicate — re-id provisionally rather than silent drop (>200 m apart).
    """
    from collections import defaultdict

    by_id: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_id[r["id"]].append(r)

    out: list[dict] = []
    for rid, group in by_id.items():
        if len(group) == 1 or rid != "SU16NW133":
            if len(group) > 1:
                print(f"WARN: duplicate id {rid} x{len(group)} — leaving as-is")
            out.extend(group)
            continue
        keep, reids = [], []
        for r in group:
            # Avebury / White Hill seed coords
            if abs(r["easting"] - 414364.0) < 80 and abs(r["northing"] - 167444.0) < 80:
                keep.append(r)
            else:
                reids.append(r)
        if not keep and reids:
            # Fallback: keep northernmost as SU16NW133 (sheet-correct)
            reids.sort(key=lambda r: r["northing"], reverse=True)
            keep = [reids.pop(0)]
        if len(keep) > 1:
            print(f"WARN: multiple Avebury candidates for {rid}; keeping first")
            reids.extend(keep[1:])
            keep = keep[:1]
        out.extend(keep)
        for r in reids:
            old = r["id"]
            new_id = "SU15SE152198"
            d_mwi = math.hypot(r["easting"] - 419884.0, r["northing"] - 151661.0)
            r["id"] = new_id
            if not r.get("her_alt_ref"):
                r["her_alt_ref"] = old
            r["notes"] = (
                (r.get("notes") or "").rstrip()
                + f" Wheatley Zenodo duplicate Ref_no {old} at wrong sheet; "
                f"re-id {new_id} (unverified; ~{d_mwi:.0f} m from MWI13689/"
                "SU15SE100). No independent HER matched."
            )
            print(
                f"re-id Wheatley duplicate {old} E{r['easting']:.0f} "
                f"N{r['northing']:.0f} → {new_id} (dist MWI13689 {d_mwi:.0f} m)"
            )
            out.append(r)
    return out


def main() -> None:
    rows = load_wheatley()
    # Drop clear coordinate errors / far outliers (Wiltshire chalk envelope)
    kept, dropped = [], []
    for r in rows:
        e, n = r["easting"], r["northing"]
        if 360000 <= e <= 430000 and 118000 <= n <= 190000:
            kept.append(r)
        else:
            dropped.append(r)
    if dropped:
        print(f"dropped {len(dropped)} rows outside Wiltshire chalk envelope:")
        for r in dropped:
            print(f"  {r['id']} E{r['easting']:.0f} N{r['northing']:.0f}")
    rows = kept
    rows = resolve_duplicate_ref_nos(rows)
    kutty = load_kutty()
    nhle = load_nhle()
    rows = enrich(rows, kutty, nhle)
    rows = add_missing_cotswold_from_nhle(rows, nhle)
    assign_barrow_type(rows)
    scrub_source_urls(rows)
    # stable sort
    rows.sort(key=lambda r: (0 if r["status"] == "certain" else 1, r["northing"], r["easting"], r["id"]))
    for r in rows:
        r["display_name"] = display_name(r)

    (DATA / "long_barrows.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    (DATA / "long_barrows.geojson").write_text(
        json.dumps(to_geojson(rows), indent=2) + "\n", encoding="utf-8"
    )

    # NHLE footprints matched only (for later orientation refinement)
    matched_ids = {r["he_list_entry"] for r in rows if r.get("he_list_entry")}
    nhle_fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": h["geometry"],
                "properties": {
                    "ListEntry": h["list_entry"],
                    "Name": h["name"],
                    "NGR": h["ngr"],
                    "hyperlink": h["url"],
                    "azimuth_deg": h["azimuth_deg"],
                    "length_m": h["length_m"],
                    "width_m": h["width_m"],
                },
            }
            for h in nhle
            if h["list_entry"] in matched_ids
        ],
    }
    (DATA / "nhle_matched_polygons.geojson").write_text(
        json.dumps(nhle_fc) + "\n", encoding="utf-8"
    )

    n = len(rows)
    n_cert = sum(1 for r in rows if r["status"] == "certain")
    n_sched = sum(1 for r in rows if r["scheduled"])
    n_az = sum(1 for r in rows if r.get("azimuth_deg") is not None)
    n_named = sum(1 for r in rows if r.get("name"))
    es = [r["easting"] for r in rows]
    ns = [r["northing"] for r in rows]
    print(f"wrote {n} barrows → data/long_barrows.json")
    print(f"  certain={n_cert} possible={n-n_cert} named={n_named} scheduled_NHLE={n_sched} with_azimuth={n_az}")
    print(f"  OSGB bbox E {min(es):.0f}–{max(es):.0f} N {min(ns):.0f}–{max(ns):.0f}")
    print(f"  NHLE polygons matched: {len(nhle_fc['features'])}")
    from collections import Counter
    print(f"  barrow_type: {dict(Counter(r.get('barrow_type') for r in rows))}")


if __name__ == "__main__":
    main()

import json, math, sys
from pathlib import Path
sys.path.insert(0, "/workspace/wiltshire-long-barrows")
from build_barrow_lidar_chips import DATA, RAW, WEB, HALF_M, fetch_chip, process_tif, tif_ok
bid = "MODERN_ALL_CANNINGS"
rows = json.loads((DATA / "long_barrows.json").read_text())
r = next(x for x in rows if x["id"] == bid)
e, n = float(r["easting"]), float(r["northing"])
e0, e1 = int(math.floor(e - HALF_M)), int(math.ceil(e + HALF_M))
n0, n1 = int(math.floor(n - HALF_M)), int(math.ceil(n + HALF_M))
tif, jpg = RAW / f"{bid}.tif", WEB / f"{bid}.jpg"
print(bid, e0, e1, n0, n1)
print("fetch" if not tif_ok(tif) else "reuse")
fetch_chip(e0, e1, n0, n1, tif) if not tif_ok(tif) else None
meta = process_tif(tif, jpg)
print(meta)
idx = WEB / "index.json"
payload = json.loads(idx.read_text())
payload["chips"][bid] = meta
payload["n"] = len(payload["chips"])
idx.write_text(json.dumps(payload, indent=2) + chr(10))
print("n", payload["n"])

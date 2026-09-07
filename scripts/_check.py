import json
rows=json.load(open("data/long_barrows.json"))
out=[r for r in rows if not (350000<=r["easting"]<=430000 and 120000<=r["northing"]<=190000)]
print("outliers",len(out))
for r in sorted(out, key=lambda x: x["easting"]):
 print(r["id"], r.get("name"), r["easting"], r["northing"], r["status"])
print("west of 360k:")
for r in rows:
  if r["easting"]<360000: print(r["id"], r.get("name"), r["easting"], r["northing"], r["status"])
c=0
for r in rows:
  if r.get("azimuth_deg") is not None and r.get("name"):
    print(r["display_name"][:48], "az=", r["azimuth_deg"], "L=", r.get("length_m")); c+=1
    if c>=12: break

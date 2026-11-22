"""Analyse an Apify instagram-scraper probe export.

Usage: python analyse_probe.py <export.json> <out_dir>
Writes probe_posts.csv (no captions, no image URLs), probe_summary.csv, probe_cost.csv.
"""
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PRICE_PER_1000 = 2.70
KEEP = ["inputUrl", "ownerUsername", "shortCode", "url", "type", "timestamp", "isPinned", "error"]

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
items = json.load(open(src, encoding="utf-8"))


def handle_of(item):
    u = item.get("inputUrl")
    if u and "/p/" not in u:
        return u.rstrip("/").split("/")[-1].lower()
    if item.get("ownerUsername"):
        return item["ownerUsername"].lower()
    return (item.get("username") or "").lower()


errors = {}
posts = defaultdict(list)
rows = []
for it in items:
    h = handle_of(it)
    if it.get("error") and not it.get("timestamp"):
        errors[h] = f"{it['error']}: {it.get('errorDescription', '')}"
        continue
    rows.append({k: it.get(k, "") for k in KEEP} | {"handle": h})
    posts[h].append(it)

with open(out / "probe_posts.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["handle"] + KEEP)
    w.writeheader()
    w.writerows(rows)

summary = []
for h in sorted(set(posts) | set(errors)):
    ps = posts.get(h, [])
    owners = sorted({(p.get("ownerUsername") or "").lower() for p in ps})
    restricted = sum(1 for p in ps if p.get("error") == "restricted_page")
    unpinned = [p for p in ps if not p.get("isPinned")]
    ts = sorted(datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")) for p in unpinned)
    span = (ts[-1] - ts[0]).days if len(ts) > 1 else 0
    n_img = sum(1 for p in unpinned if p.get("type") in ("Image", "Sidecar"))
    ppy = (len(ts) - 1) / span * 365 if span > 0 else None
    share_img = n_img / len(unpinned) if unpinned else None
    flag = []
    if h in errors:
        flag.append(errors[h])
    if owners and owners != [h]:
        flag.append(f"owner mismatch {owners}")
    if restricted:
        flag.append(f"{restricted} restricted_page items")
    if 0 < len(ps) < 20:
        flag.append(f"only {len(ps)} posts")
    summary.append({
        "handle": h, "n_posts": len(ps), "n_pinned": len(ps) - len(unpinned),
        "oldest": ts[0].date().isoformat() if ts else "", "newest": ts[-1].date().isoformat() if ts else "",
        "span_days": span, "posts_per_year": round(ppy, 1) if ppy else "",
        "image_share": round(share_img, 2) if share_img is not None else "",
        "image_posts_per_year": round(ppy * share_img, 1) if ppy and share_img is not None else "",
        "flag": "; ".join(flag),
    })

with open(out / "probe_summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(summary[0]))
    w.writeheader()
    w.writerows(summary)

ok = [s for s in summary if s["posts_per_year"] != ""]
total_ppy = sum(s["posts_per_year"] for s in ok)
cost = []
for years in (1, 1.5, 2):
    n = total_ppy * years
    cost.append({"years": years, "brands_with_rate": len(ok), "posts": round(n), "usd": round(n / 1000 * PRICE_PER_1000, 2)})
with open(out / "probe_cost.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(cost[0]))
    w.writeheader()
    w.writerows(cost)

for s in sorted(summary, key=lambda s: -(s["posts_per_year"] or 0)):
    print(s)
print()
for c in cost:
    print(c)
print("total results in export:", len(items))

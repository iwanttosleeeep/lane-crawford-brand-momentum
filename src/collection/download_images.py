"""Download Instagram images from Apify instagram-scraper exports.

Usage:
  python download_images.py --exports a.json b.json ... --out "$LC_IMAGES_ROOT/final" \
      --since 2024-11-01 --per-month 15 [--dry-run]

- Keeps Image and Sidecar posts only (videos/reels are skipped). For a Sidecar,
  every image slide is downloaded (video slides are skipped); --max-per-post caps it.
- Samples at most --per-month posts per account per calendar month. The sample for
  each account-month uses its own fixed seed, so it does not depend on which other
  exports are passed in.
- Resizes each image so its longer side is at most --max-side px (default 1024;
  needs Pillow). Enough for YOLO (640) and CLIP (224) and keeps the folder small.
- Skips items that carry an Apify "error" field (e.g. restricted_page).
- Never writes captions. Writes manifest_<first export name>.csv in --out, so several
  people can write into the same shared folder.
- Image URLs from Apify expire after a few days: run this soon after export.
"""
import argparse
import csv
import hashlib
import json
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

FIELDS = ["handle", "shortCode", "slide", "post_url", "timestamp", "month", "type",
          "is_collab", "file", "sha256", "status"]


def handle_of(it):
    u = it.get("inputUrl") or ""
    if u and "/p/" not in u:
        return u.rstrip("/").split("/")[-1].lower()
    return (it.get("ownerUsername") or "").lower()


def load(paths, since):
    seen, posts = set(), []
    for p in paths:
        for it in json.load(open(p, encoding="utf-8")):
            if it.get("error"):  # restricted or missing pages: partial data only
                continue
            if it.get("type") not in ("Image", "Sidecar") or not it.get("displayUrl"):
                continue
            ts = it.get("timestamp") or ""
            if ts[:10] < since or it.get("shortCode") in seen:
                continue
            seen.add(it["shortCode"])
            h = handle_of(it)
            if it["type"] == "Sidecar" and it.get("childPosts"):
                urls = [c["displayUrl"] for c in it["childPosts"]
                        if c.get("type") == "Image" and c.get("displayUrl")]
            else:
                urls = [it["displayUrl"]]
            if not urls:
                continue
            posts.append({
                "handle": h, "shortCode": it["shortCode"], "post_url": it.get("url", ""),
                "timestamp": ts, "month": ts[:7], "type": it["type"],
                "is_collab": (it.get("ownerUsername") or "").lower() != h,
                "urls": urls,
            })
    return posts


def sample(posts, per_month, max_per_post, seed=6207):
    groups = defaultdict(list)
    for p in posts:
        groups[(p["handle"], p["month"])].append(p)
    jobs = []
    for (h, m) in sorted(groups):
        g = sorted(groups[(h, m)], key=lambda p: p["shortCode"])
        if len(g) > per_month:
            g = random.Random(f"{seed}-{h}-{m}").sample(g, per_month)
        for p in g:
            urls = p["urls"][:max_per_post] if max_per_post else p["urls"]
            for i, u in enumerate(urls):
                jobs.append(p | {"slide": i, "displayUrl": u})
    return jobs


def shrink(data, max_side):
    """Resize so the longer side is at most max_side px (needs Pillow)."""
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(data)).convert("RGB")
    if max(im.size) <= max_side:
        return data
    im.thumbnail((max_side, max_side))
    buf = BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def fetch(p, out_dir, delay, max_side=0):
    f = out_dir / p["handle"] / f"{p['shortCode']}_{p['slide']}.jpg"
    row = {k: p[k] for k in FIELDS if k in p} | {"file": f"{p['handle']}/{f.name}"}
    if f.exists():
        row |= {"sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "status": "exists"}
        return row
    for attempt in range(2):
        try:
            req = Request(p["displayUrl"], headers={"User-Agent": "Mozilla/5.0"})
            data = urlopen(req, timeout=30).read()
            if max_side:
                data = shrink(data, max_side)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            row |= {"sha256": hashlib.sha256(data).hexdigest(), "status": "ok"}
            break
        except Exception as e:  # expired URL returns 403
            row |= {"sha256": "", "status": f"error: {e}"}
            time.sleep(2)
    time.sleep(delay)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exports", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--since", default="2024-11-01")
    ap.add_argument("--per-month", type=int, default=15)
    ap.add_argument("--max-per-post", type=int, default=0, help="0 = all image slides")
    ap.add_argument("--max-side", type=int, default=1024, help="resize longer side; 0 = keep original")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    posts = load(a.exports, a.since)
    chosen = sample(posts, a.per_month, a.max_per_post)
    per_handle = defaultdict(int)
    for p in chosen:
        per_handle[p["handle"]] += 1
    n_posts = len({p["shortCode"] for p in chosen})
    print(f"image posts after filter: {len(posts)}; sampled posts: {n_posts}; images: {len(chosen)}")
    for h in sorted(per_handle):
        print(f"  {h}: {per_handle[h]}")
    if a.dry_run:
        return
    if a.max_side:
        import PIL  # noqa: F401  (fail early: pip install pillow)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(lambda p: fetch(p, out, a.delay, a.max_side), chosen))
    errors = [r for r in rows if r["status"].startswith("error")]
    with open(out / f"manifest_{Path(a.exports[0]).stem}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"downloaded/existing: {len(rows) - len(errors)}; errors: {len(errors)}")
    if errors:
        print("first error:", errors[0]["status"])
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Freeze the shared C/D post-level image sample. Requires Pillow only."""

import argparse
import csv
import hashlib
import io
import json
import platform
import random
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import PIL
from PIL import Image


FIELDS = ["image_id", "file", "handle", "slug", "shortCode", "slide", "timestamp", "month"]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def months_between(first, last):
    year, month = map(int, first.split("-"))
    while f"{year:04d}-{month:02d}" <= last:
        yield f"{year:04d}-{month:02d}"
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def check_file(root, row):
    relative = PurePosixPath(row["file"])
    if relative.is_absolute() or ".." in relative.parts or "\\" in row["file"]:
        return "unsafe_file_path"
    if len(relative.parts) != 2 or relative.parts[0] != row["handle"]:
        return "file_handle_mismatch"
    path = root.joinpath(*relative.parts)
    if not path.is_file():
        return "missing_file"
    try:
        if row["sha256"] and sha256(path) != row["sha256"]:
            return "sha256_mismatch"
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.convert("RGB").load()
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        return f"unreadable_image:{type(error).__name__}"
    return ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--brands", type=Path, default=Path("brands.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/images"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--per-month", type=int, default=10)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.per_month < 1 or args.workers < 1:
        parser.error("per-month and workers must be positive")
    root = args.images_root.resolve()
    brands = read_csv(args.brands)
    handles = {brand["instagram_handle"]: brand["slug"] for brand in brands}
    if len(handles) != len(brands) or len({b["slug"] for b in brands}) != len(brands):
        raise ValueError("Brand slugs and Instagram handles must map one-to-one")
    source = read_csv(args.manifest)
    accepted, excluded, seen = [], [], {}
    raw_counts = Counter()
    post_times = {}
    for row in source:
        reason = ""
        handle = row["handle"]
        if handle not in handles:
            raise ValueError(f"Unknown manifest handle: {handle}")
        timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError(f"Timestamp lacks timezone: {row['file']}")
        month = timestamp.astimezone(timezone.utc).strftime("%Y-%m")
        if row["month"] != month:
            raise ValueError(f"UTC month mismatch: {row['file']}")
        slide = int(row["slide"])
        if slide < 0 or not row["shortCode"]:
            raise ValueError(f"Invalid post/slide: {row['file']}")
        row = dict(row, slug=handles[handle], month=month, slide=slide)
        raw_counts[row["slug"], month] += 1
        post_key = (row["slug"], row["shortCode"])
        prior_time = post_times.setdefault(post_key, timestamp)
        if prior_time != timestamp:
            raise ValueError(f"Conflicting publication timestamps: {post_key}")
        if row["file"] in seen:
            if row != seen[row["file"]]:
                raise ValueError(f"Conflicting duplicate image row: {row['file']}")
            reason = "duplicate_manifest_row"
        else:
            seen[row["file"]] = row
            if row["status"] not in {"ok", "exists"}:
                reason = "download_failed"
        if reason:
            excluded.append(dict(file=row["file"], reason=reason))
        else:
            accepted.append(row)
    valid = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        reasons = executor.map(lambda row: check_file(root, row), accepted)
        for row, reason in zip(accepted, reasons):
            if reason:
                excluded.append(dict(file=row["file"], reason=reason))
            else:
                valid.append(row)
    print(f"Checked {len(accepted)} files; valid {len(valid)}; exclusions {len(excluded)}", flush=True)
    posts = defaultdict(list)
    for row in valid:
        posts[row["slug"], row["month"], row["shortCode"]].append(row)
    groups = defaultdict(list)
    for (slug, month, _), slides in sorted(posts.items()):
        first = min(slides, key=lambda row: (row["slide"], row["file"]))
        groups[slug, month].append(first)
    selected = []
    for (slug, month), rows in sorted(groups.items()):
        rows.sort(key=lambda row: (row["shortCode"], row["file"]))
        if len(rows) > args.per_month:
            rows = random.Random(f"{args.seed}|{slug}|{month}").sample(rows, args.per_month)
        selected.extend(rows)
    selected.sort(key=lambda row: (row["slug"], row["month"], row["shortCode"], row["file"]))
    sample = [{key: row["file"] if key == "image_id" else row[key] for key in FIELDS} for row in selected]
    if len({row["image_id"] for row in sample}) != len(sample):
        raise ValueError("Sample image IDs are not unique")
    sampled_counts = Counter((row["slug"], row["month"]) for row in sample)
    valid_counts = Counter((row["slug"], row["month"]) for row in valid)
    first_month = min("2024-11", min(row["month"] for row in source))
    last_month = max(row["month"] for row in source)
    coverage = []
    for slug in sorted(handles.values()):
        for month in months_between(first_month, last_month):
            key = (slug, month)
            coverage.append(dict(slug=slug, month=month, manifest_rows=raw_counts[key],
                                 valid_images=valid_counts[key], eligible_posts=len(groups[key]),
                                 selected_images=sampled_counts[key],
                                 missing_month=int(not groups[key])))
    disk_files = {file.relative_to(root).as_posix() for file in root.rglob("*")
                  if file.is_file() and file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}}
    unlisted = sorted(disk_files - seen.keys())
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / "sample_manifest.csv"
    serialized = io.StringIO(newline="")
    writer = csv.DictWriter(serialized, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(sample)
    if target.exists() and target.read_bytes() != serialized.getvalue().encode("utf-8"):
        raise ValueError("Frozen sample differs. Coordinate any revision with D before replacing it.")
    write_csv(target, FIELDS, sample)
    write_csv(args.output / "sample_coverage.csv", list(coverage[0]), coverage)
    write_csv(args.output / "sample_exclusions.csv", ["file", "reason"], sorted(excluded, key=lambda row: (row["file"], row["reason"])))
    report = dict(seed=args.seed, per_month=args.per_month,
                  input_manifest=args.manifest.name, input_manifest_sha256=sha256(args.manifest),
                  brands_sha256=sha256(args.brands), sample_sha256=sha256(target),
                  source_rows=len(source), unique_manifest_files=len(seen),
                  disk_image_files=len(disk_files), unlisted_image_files=len(unlisted),
                  unlisted_files=unlisted, valid_images=len(valid), distinct_posts=len(posts),
                  excluded_rows=len(excluded), exclusion_reasons=dict(Counter(row["reason"] for row in excluded)),
                  selected_images=len(sample), sampled_brands=len({row["slug"] for row in sample}),
                  coverage_month_start=first_month, coverage_month_end=last_month,
                  brand_months=len(coverage), missing_brand_months=sum(row["missing_month"] for row in coverage),
                  selected_by_brand=dict(sorted(Counter(row["slug"] for row in sample).items())),
                  python=platform.python_version(), pillow=PIL.__version__)
    (args.output / "sample_checks.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

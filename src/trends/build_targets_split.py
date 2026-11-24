#!/usr/bin/env python3
"""Step 2 (Member B): construct the Trends target and the locked chronological split.

Run from the repository root:

    python src/trends/build_targets_split.py

Environment: Python 3.11+, standard library only.

Input:  outputs/trends/trends_monthly.csv (from Step 1)
        outputs/trends/trends_monthly_flags.csv (incomplete-month flag)
Output: outputs/trends/targets_and_split.csv  (slug, origin_month, target_growth, split)
        outputs/trends/targets_exclusions.csv (excluded brand-origin rows + reasons)
        outputs/trends/targets_step2_report.md (actual counts and checks)

No model, hyperparameter search or random split is performed here.
"""

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

TRENDS_CSV = ROOT / "outputs" / "trends" / "trends_monthly.csv"
FLAGS_CSV = ROOT / "outputs" / "trends" / "trends_monthly_flags.csv"
BRANDS_CSV = ROOT / "brands.csv"

OUT_CSV = ROOT / "outputs" / "trends" / "targets_and_split.csv"
EXCLUSIONS_CSV = ROOT / "outputs" / "trends" / "targets_exclusions.csv"
REPORT_MD = ROOT / "outputs" / "trends" / "targets_step2_report.md"

FIRST_ORIGIN = "2025-01"
LAST_ORIGIN = "2026-07"
TRAIN_RANGE = ("2025-01", "2026-02")
PURGE_RANGE = ("2026-03", "2026-04")
TEST_RANGE = ("2026-05", "2026-07")
FALLBACK_INCOMPLETE_MONTHS = {"2026-11"}


# ---------------------------------------------------------------------------
# calendar helpers (zero-based month index avoids December carry errors)
# ---------------------------------------------------------------------------
def month_index(month: str) -> int:
    year, mon = (int(part) for part in month.split("-"))
    return year * 12 + (mon - 1)


def index_month(idx: int) -> str:
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def month_range(first: str, last: str) -> list[str]:
    return [index_month(i) for i in range(month_index(first), month_index(last) + 1)]


def shift_month(month: str, delta: int) -> str:
    return index_month(month_index(month) + delta)


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------
def read_brand_order() -> list[str]:
    if BRANDS_CSV.exists():
        with BRANDS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
            return [row["slug"] for row in csv.DictReader(handle)]
    return []


def read_incomplete_months() -> set[str]:
    months = set(FALLBACK_INCOMPLETE_MONTHS)
    if FLAGS_CSV.exists():
        with FLAGS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if {"month", "flag"}.issubset(reader.fieldnames or []):
                for row in reader:
                    if row["flag"].strip().lower() == "incomplete":
                        months.add(row["month"].strip())
    return months


def read_trends(incomplete: set[str]) -> tuple[dict[tuple[str, str], float], dict[str, Any]]:
    values: dict[tuple[str, str], float] = {}
    meta: dict[str, Any] = {"duplicates": [], "bad_values": [], "incomplete_rows_dropped": 0}
    slugs: list[str] = []

    with TRENDS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"slug", "month", "trend_value", "valid_from"}
        absent = required.difference(reader.fieldnames or [])
        if absent:
            raise ValueError(f"trends_monthly.csv missing columns: {sorted(absent)}")

        for line_no, raw in enumerate(reader, start=2):
            slug = raw["slug"].strip()
            month = raw["month"].strip()
            if slug not in slugs:
                slugs.append(slug)

            if month in incomplete:
                meta["incomplete_rows_dropped"] += 1
                continue

            text = (raw["trend_value"] or "").strip()
            try:
                value = float(text)
            except ValueError:
                meta["bad_values"].append(f"line {line_no}: {slug} {month} value={text!r}")
                continue

            key = (slug, month)
            if key in values:
                meta["duplicates"].append(f"{slug}:{month}")
                continue
            values[key] = value

    ordered = read_brand_order()
    if ordered:
        slugs = [s for s in ordered if s in slugs] + sorted(set(slugs).difference(ordered))
    else:
        slugs = sorted(slugs)
    return values, {**meta, "slugs": slugs}


# ---------------------------------------------------------------------------
# target construction
# ---------------------------------------------------------------------------
def split_for(origin: str) -> str:
    if TRAIN_RANGE[0] <= origin <= TRAIN_RANGE[1]:
        return "train"
    if PURGE_RANGE[0] <= origin <= PURGE_RANGE[1]:
        return "purge"
    if TEST_RANGE[0] <= origin <= TEST_RANGE[1]:
        return "test"
    raise ValueError(f"origin {origin} is outside the locked split ranges")


def build(
    values: dict[tuple[str, str], float], slugs: list[str], incomplete: set[str]
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    origins = month_range(FIRST_ORIGIN, LAST_ORIGIN)
    rows: list[dict[str, str]] = []
    exclusions: list[dict[str, str]] = []
    max_future_by_split: dict[str, str] = {}

    for slug in slugs:
        for origin in origins:
            past = [shift_month(origin, d) for d in (-2, -1, 0)]
            future = [shift_month(origin, d) for d in (1, 2, 3)]
            required = past + future

            missing = []
            for month in required:
                if (slug, month) not in values:
                    if month in incomplete:
                        missing.append(f"{month}=incomplete_2026_11")
                    else:
                        missing.append(f"{month}=missing")
            if missing:
                exclusions.append(
                    {
                        "slug": slug,
                        "origin_month": origin,
                        "reason": "required month unavailable: " + "; ".join(missing),
                    }
                )
                continue

            past_mean = sum(values[(slug, m)] for m in past) / 3.0
            future_mean = sum(values[(slug, m)] for m in future) / 3.0
            target = math.log1p(future_mean) - math.log1p(past_mean)
            split = split_for(origin)

            latest_future = max(future)
            max_future_by_split[split] = max(max_future_by_split.get(split, ""), latest_future)

            rows.append(
                {
                    "slug": slug,
                    "origin_month": origin,
                    "target_growth": f"{target:.10f}",
                    "split": split,
                }
            )

    counts = {s: sum(1 for r in rows if r["split"] == s) for s in ("train", "purge", "test")}
    meta = {
        "origins": origins,
        "candidate_rows": len(slugs) * len(origins),
        "counts": counts,
        "max_future_by_split": max_future_by_split,
        "slug_count": len(slugs),
    }
    return rows, exclusions, meta


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------
def write_outputs(
    rows: list[dict[str, str]],
    exclusions: list[dict[str, str]],
    meta: dict[str, Any],
    input_meta: dict[str, Any],
    incomplete: set[str],
) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["slug", "origin_month", "target_growth", "split"])
        writer.writeheader()
        writer.writerows(rows)

    with EXCLUSIONS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["slug", "origin_month", "reason"])
        writer.writeheader()
        writer.writerows(exclusions)

    counts = meta["counts"]
    lines = [
        "# Trends Step 2 — target and locked split report",
        "",
        "Generated by `python src/trends/build_targets_split.py`.",
        "",
        "## Target definition",
        "",
        "`y(b,t) = log(1 + mean Trend t+1..t+3) - log(1 + mean Trend t-2..t)`. "
        "A row is kept only when all six months are observed. Forecast origin `t` means "
        "the prediction is made at the end of month `t`.",
        "",
        "## Row counts",
        "",
        f"- Brands: **{meta['slug_count']}**",
        f"- Candidate brand–origin rows ({FIRST_ORIGIN}..{LAST_ORIGIN}, {len(meta['origins'])} origins): **{meta['candidate_rows']}**",
        f"- Valid rows written to `targets_and_split.csv`: **{len(rows)}**",
        f"- Excluded brand–origin rows: **{len(exclusions)}**",
        "",
        "| Split | Origins | Valid rows | Max future month used |",
        "|---|---|---:|---|",
        f"| train | {TRAIN_RANGE[0]}..{TRAIN_RANGE[1]} | **{counts['train']}** | {meta['max_future_by_split'].get('train', 'n/a')} |",
        f"| purge (never used for fitting/tuning/evaluation) | {PURGE_RANGE[0]}..{PURGE_RANGE[1]} | **{counts['purge']}** | {meta['max_future_by_split'].get('purge', 'n/a')} |",
        f"| test (locked holdout) | {TEST_RANGE[0]}..{TEST_RANGE[1]} | **{counts['test']}** | {meta['max_future_by_split'].get('test', 'n/a')} |",
        "",
        "## Checks",
        "",
        f"- Incomplete months removed from the observed pool: {sorted(incomplete)} "
        f"({input_meta['incomplete_rows_dropped']} rows dropped from the input table)",
        "- Assignment is deterministic by `origin_month`; no shuffling or row-wise K-fold was used.",
        f"- Latest future month used by any **train** label: **{meta['max_future_by_split'].get('train', 'n/a')}** "
        "(must not be after 2026-05).",
        f"- Latest future month used by any **test** label: **{meta['max_future_by_split'].get('test', 'n/a')}** "
        "(consistent with the locked holdout).",
        f"- Duplicate `(slug, month)` in input: {input_meta['duplicates'] or 'none'}",
        f"- Non-numeric input values: {input_meta['bad_values'] or 'none'}",
        "",
        "## Excluded brand–origin rows",
        "",
    ]
    if exclusions:
        for exc in exclusions:
            lines.append(f"- `{exc['slug']}` {exc['origin_month']}: {exc['reason']}")
    else:
        lines.append("- None. Every candidate brand–origin row had all six required months observed.")
    lines += [
        "",
        "## Outputs",
        "",
        f"- `{OUT_CSV.relative_to(ROOT).as_posix()}` — `{','.join(['slug', 'origin_month', 'target_growth', 'split'])}`",
        f"- `{EXCLUSIONS_CSV.relative_to(ROOT).as_posix()}` — exclusion reasons",
        f"- `{REPORT_MD.relative_to(ROOT).as_posix()}` — this report",
        "",
        "No target values were altered for convenience and no split was changed after construction.",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    incomplete = read_incomplete_months()
    values, input_meta = read_trends(incomplete)
    rows, exclusions, meta = build(values, input_meta["slugs"], incomplete)
    write_outputs(rows, exclusions, meta, input_meta, incomplete)

    print(f"brands: {meta['slug_count']}")
    print(f"candidate brand-origin rows: {meta['candidate_rows']}")
    print(f"valid rows written: {len(rows)}")
    print(f"excluded rows: {len(exclusions)}")
    for split in ("train", "purge", "test"):
        print(f"  {split}: {meta['counts'][split]} rows, max future {meta['max_future_by_split'].get(split, 'n/a')}")
    print(f"incomplete months excluded from observed pool: {sorted(incomplete)}")
    print(f"report: {REPORT_MD.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()

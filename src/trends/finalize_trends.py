#!/usr/bin/env python3
"""Finalize the legacy final-project Google Trends dataset.

This script:
1. Replaces SHANG XIA with FRETTE in ``final_project_brands.csv``.
2. Selects one final trends variant per selected brand.
3. Copies the chosen series to ``data/trends/final/<slug>.csv``
   and adds a ``valid_from`` column equal to the first nonzero month.
4. Adds ``trends_variant`` and ``trends_file`` columns to the brand CSV.
5. Prints the final 30-brand table.

The variant choices are explicit for the brands that were rechecked; all
other selected brands keep the series already stored in ``raw/``.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BRANDS_CSV = REPO_ROOT / "data" / "legacy_final_project_brands.csv"
TRENDS_DIR = REPO_ROOT / "data" / "trends"
RAW_DIR = TRENDS_DIR / "raw"
RECHECK_DIR = TRENDS_DIR / "recheck"
FINAL_DIR = TRENDS_DIR / "final"
MAIN_SUMMARY_CSV = TRENDS_DIR / "trends_summary.csv"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_google_trends as base  # noqa: E402


OVERRIDES = {
    "JELLYCAT": {
        "source": RECHECK_DIR / "jellycat__g-113lj412p.csv",
        "variant": "topic /g/113lj412p",
    },
    "STANLEY": {
        "source": RECHECK_DIR / "stanley__stanley-tumbler.csv",
        "variant": "query Stanley tumbler",
    },
    "ANYA HINDMARCH": {
        "source": RECHECK_DIR / "anya-hindmarch__anya-hindmarch.csv",
        "variant": "query Anya Hindmarch",
    },
    "ASTIER DE VILLATTE": {
        "source": RECHECK_DIR / "astier-de-villatte__g-11dxd4gnx5.csv",
        "variant": "topic /g/11dxd4gnx5",
    },
    "FRETTE": {
        "source": RECHECK_DIR / "frette__g-11bc59742y.csv",
        "variant": "topic /g/11bc59742y",
    },
    "TEENAGE ENGINEERING": {
        "source": RECHECK_DIR / "teenage-engineering__teenage-engineering.csv",
        "variant": "query Teenage Engineering",
    },
    "NOTHING": {
        "source": RAW_DIR / "nothing.csv",
        "variant": "query Nothing phone",
    },
}


def read_brands() -> tuple[list[dict[str, str]], list[str]]:
    with BRANDS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]
    return rows, fieldnames


def read_main_summary() -> dict[str, dict[str, str]]:
    with MAIN_SUMMARY_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["brand_name"]: row
            for row in csv.DictReader(handle)
            if row.get("brand_name")
        }


def read_series(path: Path) -> tuple[list[tuple[str, str, float]], str, float]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        points: list[tuple[str, str, float]] = []
        for row in reader:
            date = (row.get("date") or "").strip()
            value_text = (row.get("value") or "").strip()
            if not date or not value_text:
                continue
            points.append((date, value_text, float(value_text)))
    if not points:
        raise SystemExit("Empty series: {}".format(path))
    nonzero = [point for point in points if point[2] > 0]
    valid_from = nonzero[0][0] if nonzero else ""
    n_months = len(points)
    n_zero = sum(1 for point in points if point[2] == 0)
    pct_zero = round(100.0 * n_zero / n_months, 2) if n_months else 0.0
    return points, valid_from, pct_zero


def write_final_series(
    destination: Path,
    points: list[tuple[str, str, float]],
    valid_from: str,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "value", "valid_from"])
        for date, value_text, _ in points:
            writer.writerow([date, value_text, valid_from])


def choose_source_and_variant(
    row: dict[str, str],
    main_summary: dict[str, dict[str, str]],
) -> tuple[Path, str]:
    brand_name = row["brand_name"]
    if brand_name in OVERRIDES:
        override = OVERRIDES[brand_name]
        return override["source"], override["variant"]

    summary = main_summary.get(brand_name)
    if summary is None:
        raise SystemExit(
            "No main trends summary row for {}".format(brand_name)
        )
    source = RAW_DIR / "{}.csv".format(base.slugify(brand_name))
    if summary.get("trends_source") == "topic":
        variant = "topic {}".format(summary.get("topic_mid", ""))
    else:
        query = row.get("trends_query") or brand_name
        variant = "query {}".format(query)
    return source, variant


def write_brands(rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with BRANDS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_table(
    selected: list[dict[str, str]],
    computed: dict[str, dict[str, object]],
) -> None:
    print("\nFinal selected brands ({})".format(len(selected)))
    header = "{:<24} {:<22} {:<30} {:>8} {:<12} {:<22}".format(
        "brand_name",
        "category",
        "trends_variant",
        "pct_zero",
        "valid_from",
        "instagram_handle",
    )
    print(header)
    print("-" * len(header))
    for row in selected:
        info = computed[row["brand_name"]]
        print(
            "{:<24} {:<22} {:<30} {:>8.2f} {:<12} {:<22}".format(
                row["brand_name"],
                row["category"],
                row["trends_variant"],
                float(info["pct_zero"]),
                str(info["valid_from"]),
                row["instagram_handle"],
            )
        )


def main() -> int:
    rows, fieldnames = read_brands()
    by_name = {row["brand_name"]: row for row in rows}

    if "SHANG XIA" not in by_name or "FRETTE" not in by_name:
        raise SystemExit("SHANG XIA and FRETTE rows are required")

    shang_xia = by_name["SHANG XIA"]
    shang_xia["status"] = "skipped"
    shang_xia["reason"] = (
        "replaced by FRETTE: brand topic SHANG XIA /g/11b639pm8s is "
        "95% zero months; other series are ambiguous with unrelated meanings"
    )

    frette = by_name["FRETTE"]
    frette["category"] = "home textiles"
    frette["status"] = "selected"
    frette["instagram_handle"] = "fretteofficial"
    frette["handle_source_url"] = "https://www.frette.com/"
    frette["trends_query"] = "Frette"
    frette["reason"] = (
        "final selected; category=home textiles; on_sale=Yes; "
        "Instagram handle verified from archived 2024 official homepage footer"
    )

    anya = by_name.get("ANYA HINDMARCH")
    if anya is not None:
        anya["trends_query"] = "Anya Hindmarch"

    for row in rows:
        row["trends_variant"] = ""
        row["trends_file"] = ""

    selected = [row for row in rows if row["status"] == "selected"]
    if len(selected) != 30:
        raise SystemExit(
            "Expected 30 selected brands after replacement, found {}".format(
                len(selected)
            )
        )

    main_summary = read_main_summary()
    computed: dict[str, dict[str, object]] = {}

    for row in selected:
        source, variant = choose_source_and_variant(row, main_summary)
        if not source.is_file():
            raise SystemExit("Missing source series: {}".format(source))
        points, valid_from, pct_zero = read_series(source)
        destination = FINAL_DIR / "{}.csv".format(base.slugify(row["brand_name"]))
        write_final_series(destination, points, valid_from)
        row["trends_variant"] = variant
        row["trends_file"] = str(destination.relative_to(REPO_ROOT))
        computed[row["brand_name"]] = {
            "valid_from": valid_from,
            "pct_zero": pct_zero,
        }

    write_brands(rows, fieldnames + ["trends_variant", "trends_file"])
    print_table(selected, computed)

    nothing = computed.get("NOTHING", {})
    print(
        "\nWrote {} final series to {}".format(
            len(computed), FINAL_DIR.relative_to(REPO_ROOT)
        )
    )
    print("NOTHING valid_from: {}".format(nothing.get("valid_from", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

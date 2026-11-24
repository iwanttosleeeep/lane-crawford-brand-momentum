#!/usr/bin/env python3
"""Step 1 (Member B): clean and merge the 30 Google Trends monthly series.

Run from the repository root:

    python src/trends/clean_trends.py

Environment: Python 3.11+, standard library only.

Outputs
-------
outputs/trends/trends_monthly.csv       slug, month, trend_value, valid_from
outputs/trends/trends_monthly_flags.csv machine-readable incomplete-month flag
outputs/trends/trends_step1_report.md   actual counts, checks and Artemide finding

The ZIP is extracted into the repository root as ``Google Trends/<slug>.csv``,
matching the relative ``trends_file`` paths in brands.csv. Archive junk
(``__MACOSX/`` and ``.DS_Store``) is ignored. No modelling is performed here.
"""

from __future__ import annotations

import csv
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BRANDS_CSV = ROOT / "brands.csv"
TRENDS_ZIP = ROOT / "Google Trends.zip"
OUT_DIR = ROOT / "outputs" / "trends"

MAIN_OUT = OUT_DIR / "trends_monthly.csv"
FLAGS_OUT = OUT_DIR / "trends_monthly_flags.csv"
REPORT_OUT = OUT_DIR / "trends_step1_report.md"

INCOMPLETE_MONTH = "2026-11"  # retained in the table, flagged, not used as a measured target
ARTEMIDE_MONTHS = [f"2025-{m:02d}" for m in range(8, 13)] + [f"2026-{m:02d}" for m in range(1, 3)]
CONTEXT_SLUGS = ["frette", "artemide", "flos", "louis-poulsen", "tom-dixon"]


def read_brands() -> list[dict[str, str]]:
    with BRANDS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"brand_name", "slug", "trends_file", "trends_valid_from"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"brands.csv missing required columns: {sorted(missing)}")
        return [dict(row) for row in reader]


def extract_trends_zip() -> list[str]:
    """Extract only real CSV members; ignore macOS archive junk."""
    if not TRENDS_ZIP.exists():
        raise FileNotFoundError(TRENDS_ZIP)

    extracted: list[str] = []
    with zipfile.ZipFile(TRENDS_ZIP) as archive:
        for member in archive.infolist():
            name = member.filename
            if member.is_dir() or "__MACOSX" in name or Path(name).name == ".DS_Store":
                continue
            if Path(name).name.startswith("."):
                continue
            if not name.lower().endswith(".csv"):
                continue
            archive.extract(member, ROOT)
            extracted.append(name)
    return sorted(extracted)


def parse_month(value: str) -> str:
    text = value.strip()
    if len(text) == 7:  # YYYY-MM
        text += "-01"
    return datetime.strptime(text, "%Y-%m-%d").strftime("%Y-%m")


def month_index(month: str) -> int:
    year, mon = (int(part) for part in month.split("-"))
    return year * 12 + (mon - 1)


def month_range(first: str, last: str) -> list[str]:
    out = []
    for idx in range(month_index(first), month_index(last) + 1):
        out.append(f"{idx // 12:04d}-{idx % 12 + 1:02d}")
    return out


def build(brands: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows: list[dict[str, str]] = []
    report: dict[str, Any] = {
        "brand_count": len(brands),
        "missing_files": [],
        "bad_schemas": [],
        "valid_from_mismatches": [],
        "nonnumeric": [],
        "source_duplicates": [],
        "merged_duplicates": [],
        "gaps": {},
        "excluded_prevalidity": {},
        "source_months": {},
        "included_months": {},
        "source_rows": {},
        "included_rows": {},
    }

    for brand in brands:
        slug = brand["slug"]
        rel_path = brand["trends_file"]
        path = ROOT / rel_path
        if not path.exists():
            report["missing_files"].append(f"{slug}: {rel_path}")
            continue

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            needed = {"date", "value", "valid_from"}
            absent = needed.difference(reader.fieldnames or [])
            if absent:
                report["bad_schemas"].append(f"{slug}: missing {sorted(absent)}")
                continue
            source = list(reader)

        brand_valid_month = parse_month(brand["trends_valid_from"])
        seen_months: set[str] = set()
        source_months: list[str] = []
        included = 0
        excluded = 0

        for line_no, raw in enumerate(source, start=2):
            try:
                month = parse_month(raw["date"])
            except (ValueError, TypeError):
                report["nonnumeric"].append(f"{slug}:{line_no}: bad date {raw['date']!r}")
                continue

            source_months.append(month)
            if month in seen_months:
                report["source_duplicates"].append(f"{slug}:{month}")
                continue
            seen_months.add(month)

            value_text = (raw["value"] or "").strip()
            if not value_text:
                report["nonnumeric"].append(f"{slug}:{month}: empty value")
                continue
            try:
                float(value_text)
            except ValueError:
                report["nonnumeric"].append(f"{slug}:{month}: non-numeric {value_text!r}")
                continue

            csv_valid_month = parse_month(raw["valid_from"])
            if csv_valid_month != brand_valid_month:
                report["valid_from_mismatches"].append(
                    f"{slug}: brands.csv={brand_valid_month}, csv={csv_valid_month}"
                )

            if month_index(month) < month_index(brand_valid_month):
                excluded += 1
                continue

            rows.append(
                {
                    "slug": slug,
                    "month": month,
                    "trend_value": value_text,
                    "valid_from": brand["trends_valid_from"],
                }
            )
            included += 1

        report["source_rows"][slug] = len(source)
        report["included_rows"][slug] = included
        report["excluded_prevalidity"][slug] = excluded

        if source_months:
            first, last = min(source_months), max(source_months)
            report["source_months"][slug] = (first, last)
            expected = set(month_range(first, last))
            missing_months = sorted(expected.difference(seen_months))
            if missing_months:
                report["gaps"][slug] = missing_months
            inc_months = sorted({r["month"] for r in rows if r["slug"] == slug})
            if inc_months:
                report["included_months"][slug] = (inc_months[0], inc_months[-1])
                inc_expected = set(month_range(inc_months[0], inc_months[-1]))
                inc_gaps = sorted(inc_expected.difference(inc_months))
                if inc_gaps:
                    report["gaps"][slug + " (post-validity)"] = inc_gaps

    seen_pairs: set[tuple[str, str]] = set()
    for row in rows:
        pair = (row["slug"], row["month"])
        if pair in seen_pairs:
            report["merged_duplicates"].append(f"{pair[0]}:{pair[1]}")
        seen_pairs.add(pair)

    report["total_rows"] = len(rows)
    report["total_excluded_prevalidity"] = sum(report["excluded_prevalidity"].values())
    report["incomplete_rows"] = [r for r in rows if r["month"] == INCOMPLETE_MONTH]
    return rows, report


def artemide_context(rows: list[dict[str, str]], brands: list[dict[str, str]]) -> list[list[str]]:
    by_key = {(r["slug"], r["month"]): float(r["trend_value"]) for r in rows}
    names = {b["slug"]: b["brand_name"] for b in brands}
    table = [["brand"] + ARTEMIDE_MONTHS]
    for slug in CONTEXT_SLUGS:
        table.append([f"{names.get(slug, slug)} ({slug})"] + [f"{by_key.get((slug, m), float('nan')):.4f}" for m in ARTEMIDE_MONTHS])
    return table


def write_outputs(rows: list[dict[str, str]], report: dict[str, Any], brands: list[dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with MAIN_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["slug", "month", "trend_value", "valid_from"])
        writer.writeheader()
        writer.writerows(rows)

    with FLAGS_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["slug", "month", "flag", "reason"])
        writer.writeheader()
        for row in report["incomplete_rows"]:
            writer.writerow(
                {
                    "slug": row["slug"],
                    "month": row["month"],
                    "flag": "incomplete",
                    "reason": "2026-11 is incomplete; retained for traceability, exclude from measured targets",
                }
            )

    art_table = artemide_context(rows, brands)
    lines = [
        "# Trends Step 1 — Cleaning and merge report",
        "",
        f"Generated by `python src/trends/clean_trends.py` from `brands.csv` and `Google Trends.zip`.",
        "",
        "## Row counts",
        "",
        f"- Brands in `brands.csv`: **{report['brand_count']}**",
        f"- Merged rows written to `trends_monthly.csv`: **{report['total_rows']}**",
        f"- Pre-validity rows excluded as UNAVAILABLE: **{report['total_excluded_prevalidity']}**",
        f"- `{INCOMPLETE_MONTH}` rows retained and flagged incomplete: **{len(report['incomplete_rows'])}**",
        "",
        "## Verification",
        "",
        f"- Missing Trend CSVs: {report['missing_files'] or 'none'}",
        f"- Bad schemas: {report['bad_schemas'] or 'none'}",
        f"- Non-numeric / empty values: {report['nonnumeric'] or 'none'}",
        f"- Duplicate source months: {report['source_duplicates'] or 'none'}",
        f"- Duplicate merged (slug, month) keys: {report['merged_duplicates'] or 'none'}",
        f"- `valid_from` mismatches (brands.csv vs CSV): {report['valid_from_mismatches'] or 'none'}",
        f"- Month gaps: {report['gaps'] or 'none'}",
        "",
        "### Pre-validity exclusions by brand",
        "",
    ]
    for slug in sorted(report["excluded_prevalidity"]):
        count = report["excluded_prevalidity"][slug]
        if count:
            span = report["source_months"].get(slug, ("?", "?"))
            lines.append(f"- `{slug}`: {count} row(s) before valid_from; source span {span[0]}–{span[1]}")
    if not any(report["excluded_prevalidity"].values()):
        lines.append("- none")

    lines += [
        "",
        "## Incomplete month flag",
        "",
        f"`{INCOMPLETE_MONTH}` remains in `trends_monthly.csv` with its observed value. "
        f"It is flagged in `trends_monthly_flags.csv` and must not be used as a measured "
        "monthly target in later steps.",
        "",
        "## Artemide 2025-11 investigation",
        "",
        "Values (0–100 within each independently scaled series):",
        "",
        "| " + " | ".join(art_table[0]) + " |",
        "|" + "---|" * len(art_table[0]),
    ]
    for row in art_table[1:]:
        lines.append("| " + " | ".join(row) + " |")

    # art_table[0] is the header; [1] is Frette (adjacent brand), [2] is Artemide.
    art_by_month = {m: art_table[2][i + 1] for i, m in enumerate(ARTEMIDE_MONTHS)}
    conclusion = (
        "Artemide rises from {octv} in 2025-10 to {novv} in 2025-11 and then falls to "
        "{decv} in 2025-12. The other lighting brands in this snapshot (Flos, Louis "
        "Poulsen, Tom Dixon) do not show a comparable jump: Flos and Louis Poulsen change "
        "only modestly and Tom Dixon falls. Frette, the adjacent non-lighting brand, also "
        "rises in 2025-11, so the spike is not unique in the whole table, but it is unusual "
        "within the lighting peer group. The supplied files contain no event, definition "
        "or extraction notes that explain it, so its cause cannot be determined from these "
        "data. The value is retained unchanged; no capping, removal or silent correction "
        "was applied."
    ).format(octv=art_by_month["2025-10"], novv=art_by_month["2025-11"], decv=art_by_month["2025-12"])
    lines += ["", "Factual conclusion: " + conclusion, ""]

    lines += [
        "## Outputs",
        "",
        f"- `{MAIN_OUT.relative_to(ROOT).as_posix()}` — exact requested schema",
        f"- `{FLAGS_OUT.relative_to(ROOT).as_posix()}` — incomplete-month flag",
        f"- `{REPORT_OUT.relative_to(ROOT).as_posix()}` — this report",
        "",
        "No target construction, split assignment, hyperparameter tuning or model fitting "
        "was performed in this step.",
        "",
    ]
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    brands = read_brands()
    extracted = extract_trends_zip()
    print(f"Extracted {len(extracted)} CSV members from {TRENDS_ZIP.name} (macOS junk ignored).")
    rows, report = build(brands)
    write_outputs(rows, report, brands)

    print(f"brands.csv brands: {report['brand_count']}")
    print(f"merged rows written: {report['total_rows']}")
    print(f"pre-validity rows excluded: {report['total_excluded_prevalidity']}")
    print(f"{INCOMPLETE_MONTH} rows retained/flagged: {len(report['incomplete_rows'])}")
    for key in (
        "missing_files",
        "bad_schemas",
        "nonnumeric",
        "source_duplicates",
        "merged_duplicates",
        "valid_from_mismatches",
        "gaps",
    ):
        print(f"{key}: {report[key] or 'none'}")
    print("\nArtemide context (2025-08 to 2026-02):")
    for row in artemide_context(rows, brands):
        print("  " + " | ".join(row))
    print(f"\nReport: {REPORT_OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()

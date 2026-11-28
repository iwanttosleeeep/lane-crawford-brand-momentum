#!/usr/bin/env python3
"""Re-check Google Trends variants for legacy final-project brands.

This script is separate from ``fetch_google_trends.py`` and does not modify
``final_project_brands.csv``.  For each requested brand it:

1. Fetches and prints every suggestion (mid, title, type).
2. Fetches a series for every suggestion whose title is exactly the brand
   name, plus each explicitly listed query variant.
3. Saves each series to ``data/trends/recheck/<slug>__<variant>.csv``.
4. Writes ``recheck_summary.csv`` with the requested diagnostics.

It also computes the same summary columns for NOTHING and TEENAGE ENGINEERING
from their existing raw files without making new requests.

Usage:
    python3 src/trends/recheck_google_trends.py
    python3 src/trends/recheck_google_trends.py --resume --delay 15
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import pandas as pd
    from pytrends.request import TrendReq
except ImportError as exc:  # pragma: no cover - dependency guard
    sys.exit(
        "Missing dependency: {}. Install with "
        "`pip install pytrends pandas requests`.".format(exc)
    )

import fetch_google_trends as base


REPO_ROOT = Path(__file__).resolve().parents[2]
TRENDS_DIR = REPO_ROOT / "data" / "trends"
RECHECK_DIR = TRENDS_DIR / "recheck"
SUGGESTIONS_DIR = RECHECK_DIR / "suggestions"
SUMMARY_CSV = RECHECK_DIR / "recheck_summary.csv"
LOG_PATH = RECHECK_DIR / "fetch_log.txt"
MAIN_RAW_DIR = TRENDS_DIR / "raw"
MAIN_SUMMARY_CSV = TRENDS_DIR / "trends_summary.csv"
BRANDS_CSV = REPO_ROOT / "data" / "legacy_final_project_brands.csv"

SUMMARY_FIELDS = [
    "brand_name",
    "variant",
    "topic_type",
    "n_months",
    "n_zero_months",
    "pct_zero",
    "first_nonzero_month",
    "pct_zero_after_first_nonzero",
    "last_12m_mean",
]

RECHECK_BRANDS = [
    {
        "brand_name": "JELLYCAT",
        "queries": ["Jellycat"],
    },
    {
        "brand_name": "STANLEY",
        "queries": ["Stanley tumbler", "Stanley 1913"],
    },
    {
        "brand_name": "ANYA HINDMARCH",
        "queries": ["Anya Hindmarch"],
    },
    {
        "brand_name": "SHANG XIA",
        "queries": ["Shang Xia"],
    },
    {
        "brand_name": "ASTIER DE VILLATTE",
        "queries": ["Astier de Villatte"],
    },
    {
        "brand_name": "FRETTE",
        "queries": ["Frette"],
    },
    {
        "brand_name": "ARTEMIDE",
        "queries": ["Artemide"],
    },
]

EXISTING_BRANDS = ["NOTHING", "TEENAGE ENGINEERING"]


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = "[{}] {}".format(stamp, message)
    print(line)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def title_is_brand(title: str, brand_name: str) -> bool:
    """Exact normalized title match, e.g. STANLEY == Stanley, not Marshalls."""
    return base.normalize_tokens(title) == base.normalize_tokens(brand_name)


def variant_token(variant: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", variant.lower()).strip("-")
    return token or "variant"


def load_suggestions(
    brand_name: str,
    cache_path: Path,
    client: TrendReq,
    suggestion_delay: float,
) -> list[dict]:
    if cache_path.is_file():
        with cache_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        suggestions = payload.get("suggestions")
        if isinstance(suggestions, list):
            return suggestions
    log("Suggestions request: {}".format(brand_name))
    suggestions = client.suggestions(brand_name)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "brand_name": brand_name,
        "query": brand_name,
        "suggestions": suggestions,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    cache_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    time.sleep(suggestion_delay + random.uniform(0, 1))
    return suggestions


def build_variants(
    brand_name: str, suggestions: list[dict], queries: list[str]
) -> list[dict]:
    variants: list[dict] = []
    seen_mids: set[str] = set()
    for suggestion in suggestions:
        mid = (suggestion.get("mid") or "").strip()
        title = (suggestion.get("title") or "").strip()
        suggestion_type = (suggestion.get("type") or "").strip()
        if not mid or mid in seen_mids:
            continue
        if not title_is_brand(title, brand_name):
            continue
        variants.append(
            {
                "kind": "topic",
                "variant": mid,
                "topic_type": suggestion_type,
                "title": title,
            }
        )
        seen_mids.add(mid)
    seen_queries: set[str] = set()
    for query in queries:
        query = query.strip()
        if not query or query in seen_queries:
            continue
        variants.append(
            {
                "kind": "query",
                "variant": query,
                "topic_type": "",
                "title": query,
            }
        )
        seen_queries.add(query)
    return variants


def summarize_series(
    brand_name: str,
    variant: str,
    topic_type: str,
    monthly: pd.Series,
) -> dict:
    n_months = int(monthly.size)
    n_zero_months = int((monthly == 0).sum())
    pct_zero = (
        round(100.0 * n_zero_months / n_months, 2) if n_months else 0.0
    )
    nonzero = monthly[monthly > 0]
    if nonzero.empty:
        first_nonzero_month = ""
        pct_zero_after = 100.0 if n_months else 0.0
    else:
        first_date = nonzero.index[0]
        first_nonzero_month = first_date.strftime("%Y-%m-%d")
        after = monthly.loc[first_date:]
        pct_zero_after = round(
            100.0 * int((after == 0).sum()) / len(after), 2
        )
    last_12m_mean = (
        round(float(monthly.tail(12).mean()), 4) if n_months else 0.0
    )
    return {
        "brand_name": brand_name,
        "variant": variant,
        "topic_type": topic_type,
        "n_months": n_months,
        "n_zero_months": n_zero_months,
        "pct_zero": pct_zero,
        "first_nonzero_month": first_nonzero_month,
        "pct_zero_after_first_nonzero": pct_zero_after,
        "last_12m_mean": last_12m_mean,
    }


def read_monthly_csv(path: Path) -> pd.Series:
    frame = pd.read_csv(path, parse_dates=["date"])
    return frame.set_index("date")["value"].astype(float).sort_index()


def read_trends_queries() -> dict[str, str]:
    if not BRANDS_CSV.is_file():
        return {}
    with BRANDS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["brand_name"]: (row.get("trends_query") or "").strip()
            for row in csv.DictReader(handle)
            if row.get("brand_name")
        }


def read_summary() -> dict[tuple[str, str], dict]:
    if not SUMMARY_CSV.is_file():
        return {}
    with SUMMARY_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return {
            (row["brand_name"], row["variant"]): row
            for row in csv.DictReader(handle)
            if row.get("brand_name") and row.get("variant")
        }


def write_summary(
    rows_by_key: dict[tuple[str, str], dict],
    variant_order: dict[tuple[str, str], int],
) -> None:
    brand_order = [item["brand_name"] for item in RECHECK_BRANDS] + EXISTING_BRANDS
    brand_index = {name: index for index, name in enumerate(brand_order)}
    ordered = sorted(
        rows_by_key.values(),
        key=lambda row: (
            brand_index.get(row["brand_name"], len(brand_index)),
            variant_order.get(
                (row["brand_name"], row["variant"]), 10_000
            ),
            row["variant"],
        ),
    )
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(ordered)


def print_suggestions(brand_name: str, suggestions: list[dict]) -> None:
    print("\n=== {} suggestions ===".format(brand_name))
    for suggestion in suggestions:
        print(
            "  {} | {} | {}".format(
                suggestion.get("mid", ""),
                suggestion.get("title", ""),
                suggestion.get("type", ""),
            )
        )


def print_grouped_summary(
    rows_by_key: dict[tuple[str, str], dict],
    variant_order: dict[tuple[str, str], int],
) -> None:
    brand_order = [item["brand_name"] for item in RECHECK_BRANDS] + EXISTING_BRANDS
    print("\n\nRecheck summary grouped by brand")
    for brand_name in brand_order:
        brand_rows = [
            row
            for (name, _), row in rows_by_key.items()
            if name == brand_name
        ]
        if not brand_rows:
            continue
        brand_rows.sort(
            key=lambda row: (
                variant_order.get(
                    (row["brand_name"], row["variant"]), 10_000
                ),
                row["variant"],
            )
        )
        print("\n{}".format(brand_name))
        print(
            "  {:<34} {:<38} {:>3} {:>5} {:>8} {:>12} {:>10} {:>9}".format(
                "variant",
                "topic_type",
                "n",
                "zero",
                "pct_zero",
                "first_nonzero",
                "pct_after",
                "last12m",
            )
        )
        print("  " + "-" * 128)
        for row in brand_rows:
            print(
                "  {:<34} {:<38} {:>3} {:>5} {:>8.2f} {:>12} {:>10.2f} {:>9.2f}".format(
                    row["variant"][:34],
                    row["topic_type"][:38],
                    int(row["n_months"]),
                    int(row["n_zero_months"]),
                    float(row["pct_zero"]),
                    row["first_nonzero_month"] or "-",
                    float(row["pct_zero_after_first_nonzero"]),
                    float(row["last_12m_mean"]),
                )
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delay",
        type=float,
        default=15.0,
        help="Seconds between series requests (default: 15).",
    )
    parser.add_argument(
        "--suggestion-delay",
        type=float,
        default=2.0,
        help="Seconds between uncached suggestions requests (default: 2).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries after an HTTP 429 (default: 3).",
    )
    parser.add_argument(
        "--backoff",
        type=float,
        default=90.0,
        help="Base backoff in seconds for HTTP 429 (default: 90).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse existing series files and summary rows where possible.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    RECHECK_DIR.mkdir(parents=True, exist_ok=True)
    SUGGESTIONS_DIR.mkdir(parents=True, exist_ok=True)

    rows_by_key: dict[tuple[str, str], dict] = (
        read_summary() if args.resume else {}
    )
    variant_order: dict[tuple[str, str], int] = {}
    failures: list[tuple[str, str]] = []
    client = TrendReq(hl="en-US", tz=0, timeout=(10, 30))
    # The autocomplete endpoint works without the session cookie; clearing it
    # avoids stale-cookie 429s seen on shared egress IPs.
    client.cookies = {}

    log(
        "Starting recheck for {} brands (timeframe={}, delay={}s)".format(
            len(RECHECK_BRANDS), base.TIMEFRAME, args.delay
        )
    )

    for brand in RECHECK_BRANDS:
        brand_name = brand["brand_name"]
        slug = base.slugify(brand_name)
        cache_path = SUGGESTIONS_DIR / "{}.json".format(slug)
        try:
            suggestions = load_suggestions(
                brand_name, cache_path, client, args.suggestion_delay
            )
        except Exception as exc:
            message = "{}: {}".format(type(exc).__name__, exc)
            log("{} suggestions failed: {}".format(brand_name, message))
            failures.append((brand_name, "suggestions: " + message))
            continue

        print_suggestions(brand_name, suggestions)
        variants = build_variants(brand_name, suggestions, brand["queries"])
        print(
            "  -> fetching {} variant(s): {}".format(
                len(variants), ", ".join(item["variant"] for item in variants)
            )
        )

        for order, item in enumerate(variants):
            variant = item["variant"]
            key = (brand_name, variant)
            variant_order[key] = order
            token = variant_token(variant)
            raw_path = RECHECK_DIR / "{}__{}.csv".format(slug, token)

            if raw_path.is_file() and args.resume:
                if key in rows_by_key:
                    log(
                        "{} / {}: cached, skipping".format(
                            brand_name, variant
                        )
                    )
                    continue
                monthly = read_monthly_csv(raw_path)
                rows_by_key[key] = summarize_series(
                    brand_name, variant, item["topic_type"], monthly
                )
                write_summary(rows_by_key, variant_order)
                log(
                    "{} / {}: rebuilt summary from existing CSV".format(
                        brand_name, variant
                    )
                )
                continue

            keyword = (
                {"mid": variant, "name": item["title"], "type": "Topic"}
                if item["kind"] == "topic"
                else variant
            )
            try:
                frame = base.fetch_interest(
                    keyword,
                    max_retries=args.max_retries,
                    backoff_seconds=args.backoff,
                )
            except Exception as exc:
                if base.is_429(exc):
                    message = "HTTP 429 persisted after {} retries".format(
                        args.max_retries
                    )
                    log(
                        "{} / {}: {}; stopping".format(
                            brand_name, variant, message
                        )
                    )
                    failures.append((brand_name, message))
                    write_summary(rows_by_key, variant_order)
                    print_grouped_summary(rows_by_key, variant_order)
                    print(
                        "\nSTOPPED: Google returned HTTP 429 after retries. "
                        "Re-run with --resume after switching egress IP.",
                        file=sys.stderr,
                    )
                    return 2
                message = "{}: {}".format(type(exc).__name__, exc)
                log(
                    "{} / {}: fetch failed: {}".format(
                        brand_name, variant, message
                    )
                )
                failures.append((brand_name, variant + ": " + message))
                continue

            monthly = base.monthly_series(frame)
            if monthly.empty:
                message = "monthly series is empty"
                log("{} / {}: {}".format(brand_name, variant, message))
                failures.append((brand_name, variant + ": " + message))
                continue

            base.write_raw(raw_path, monthly)
            rows_by_key[key] = summarize_series(
                brand_name, variant, item["topic_type"], monthly
            )
            write_summary(rows_by_key, variant_order)
            log(
                "{} / {}: saved {} months, zeros={}, pct_zero={:.2f}".format(
                    brand_name,
                    variant,
                    rows_by_key[key]["n_months"],
                    rows_by_key[key]["n_zero_months"],
                    rows_by_key[key]["pct_zero"],
                )
            )
            time.sleep(args.delay + random.uniform(0, 3))

    # Existing brands: recompute from the already-fetched raw files only.
    main_summary: dict[str, dict] = {}
    if MAIN_SUMMARY_CSV.is_file():
        with MAIN_SUMMARY_CSV.open(encoding="utf-8-sig", newline="") as handle:
            main_summary = {
                row["brand_name"]: row for row in csv.DictReader(handle)
            }
    trends_queries = read_trends_queries()

    for brand_name in EXISTING_BRANDS:
        slug = base.slugify(brand_name)
        raw_path = MAIN_RAW_DIR / "{}.csv".format(slug)
        if not raw_path.is_file():
            log("{}: missing existing raw file {}".format(brand_name, raw_path))
            failures.append((brand_name, "missing existing raw file"))
            continue
        source_row = main_summary.get(brand_name, {})
        if source_row.get("trends_source") == "topic":
            variant = source_row.get("topic_mid", "")
            topic_type = source_row.get("topic_type", "")
        else:
            variant = trends_queries.get(brand_name, "") or brand_name
            topic_type = ""
        if not variant:
            variant = source_row.get("topic_mid", "") or brand_name
        monthly = read_monthly_csv(raw_path)
        key = (brand_name, variant)
        variant_order[key] = 0
        rows_by_key[key] = summarize_series(
            brand_name, variant, topic_type, monthly
        )
        log(
            "{}: computed from existing raw file (variant={})".format(
                brand_name, variant
            )
        )

    write_summary(rows_by_key, variant_order)
    print_grouped_summary(rows_by_key, variant_order)

    if failures:
        print("\nFailures:", file=sys.stderr)
        for brand_name, message in failures:
            print("  - {}: {}".format(brand_name, message), file=sys.stderr)
        return 1

    log("Recheck complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

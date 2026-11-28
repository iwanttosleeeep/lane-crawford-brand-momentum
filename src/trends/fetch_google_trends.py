#!/usr/bin/env python3
"""Fetch Google Trends interest for the legacy final-project brands.

Workflow
--------
1. Read the 30 ``status=selected`` rows from
   ``data/legacy_final_project_brands.csv``.
2. For each brand, query the Google Trends suggestions endpoint with the
   brand name.  Keep the suggestion whose type describes a company/brand
   (e.g. "Company", "Toy company", "Ceramic manufacturer") and whose title
   matches the brand name.  Save its ``mid`` and type.  If no such
   suggestion exists, use the brand's ``trends_query`` string instead and
   mark the source as ``query``.
3. Fetch worldwide interest over time for ``today 5-y`` with one keyword per
   request.  Google returns weekly points for this window, so the points are
   aggregated to calendar-month means before saving.  Boundary months are
   kept because they contain real observations returned by Google.
4. Write ``raw/<slug>.csv`` with columns ``date,value`` and
   ``trends_summary.csv`` with the requested summary fields (plus a
   ``sparse`` flag).

Rate limiting
-------------
If Google returns HTTP 429, wait with exponential backoff and retry at most
three times.  If the third retry still returns 429, stop the run, keep the
partial summary, and report the failure.

Usage
-----
    python3 src/trends/fetch_google_trends.py
    python3 src/trends/fetch_google_trends.py --resume

The script requires ``pytrends``, ``pandas`` and ``requests``.  A local
virtual environment is sufficient, e.g.::

    python3 -m venv .venv-trends
    .venv-trends/bin/pip install pytrends pandas requests
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
from difflib import SequenceMatcher
from pathlib import Path

try:
    import pandas as pd
    from pytrends import exceptions
    from pytrends.request import TrendReq
except ImportError as exc:  # pragma: no cover - dependency guard
    sys.exit(
        "Missing dependency: {}. Install with "
        "`pip install pytrends pandas requests`.".format(exc)
    )


REPO_ROOT = Path(__file__).resolve().parents[2]
BRANDS_CSV = REPO_ROOT / "data" / "legacy_final_project_brands.csv"
TRENDS_DIR = REPO_ROOT / "data" / "trends"
RAW_DIR = TRENDS_DIR / "raw"
SUGGESTIONS_DIR = TRENDS_DIR / "suggestions"
SUMMARY_CSV = TRENDS_DIR / "trends_summary.csv"
LOG_PATH = TRENDS_DIR / "fetch_log.txt"

TIMEFRAME = "today 5-y"
SUMMARY_FIELDS = [
    "brand_name",
    "slug",
    "trends_source",
    "topic_mid",
    "topic_type",
    "n_months",
    "n_zero_months",
    "pct_zero",
    "mean_value",
    "last_12m_mean",
    "sparse",
]

# Types that describe a company/brand rather than a film, food, person, etc.
# The substring check deliberately accepts descriptions such as
# "Consumer electronics company" and "Ceramic manufacturer in Paris, France".
BRAND_TYPE_TERMS = [
    "company",
    "corporation",
    "brand",
    "manufacturer",
    "manufacturing",
    "retailer",
    "retail company",
    "business",
    "enterprise",
    "fashion house",
    "design house",
    "conglomerate",
    "holding company",
    "subsidiary",
    "maker",
    "label",
]


class TopicTrendReq(TrendReq):
    """TrendReq with support for topic-entity payloads.

    pytrends 4.9.2 only builds payloads from plain search strings.  Google
    Trends represents a topic as ``{"keyword": <mid>, "name": ..., "type":
    "Topic"}`` in the token request, so ``build_payload`` is extended to
    accept a dict instead of a string.
    """

    def build_payload(
        self,
        kw_list,
        cat=0,
        timeframe="today 5-y",
        geo="",
        gprop="",
    ):
        if gprop not in ["", "images", "news", "youtube", "froogle"]:
            raise ValueError("Invalid gprop value: {}".format(gprop))
        self.kw_list = kw_list
        self.geo = geo or self.geo
        self.token_payload = {
            "hl": self.hl,
            "tz": self.tz,
            "req": {
                "comparisonItem": [],
                "category": cat,
                "property": gprop,
            },
        }
        for keyword in self.kw_list:
            if isinstance(keyword, dict):
                item = {
                    "keyword": keyword["mid"],
                    "name": keyword.get("name", ""),
                    "type": keyword.get("type", "Topic"),
                    "time": timeframe,
                    "geo": self.geo,
                }
            else:
                item = {
                    "keyword": keyword,
                    "time": timeframe,
                    "geo": self.geo,
                }
            self.token_payload["req"]["comparisonItem"].append(item)
        self.token_payload["req"] = json.dumps(self.token_payload["req"])
        self._tokens()


def slugify(name: str) -> str:
    """Project slug convention: drop ampersands, hyphenate other separators."""
    value = name.lower().replace("&", " ")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def normalize_tokens(text: str) -> list[str]:
    value = text.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return [token for token in value.split() if token]


def title_matches_brand(title: str, brand_name: str) -> bool:
    """True when every token of the brand name appears in the suggestion title.

    This rejects suggestions for different entities such as "Marshalls" when
    the brand is "MARSHALL", or "MillerKnoll" when the brand is
    "HERMAN MILLER", while still accepting "The Lego Group" for "LEGO".
    """
    brand_tokens = normalize_tokens(brand_name)
    if not brand_tokens:
        return False
    title_tokens = set(normalize_tokens(title))
    return all(token in title_tokens for token in brand_tokens)


def is_brand_type(suggestion_type: str) -> bool:
    value = suggestion_type.lower()
    return any(term in value for term in BRAND_TYPE_TERMS)


def choose_topic(brand_name: str, suggestions: list[dict]) -> dict | None:
    candidates = []
    brand_text = " ".join(normalize_tokens(brand_name))
    for index, suggestion in enumerate(suggestions):
        title = (suggestion.get("title") or "").strip()
        suggestion_type = (suggestion.get("type") or "").strip()
        mid = (suggestion.get("mid") or "").strip()
        if not mid or not suggestion_type:
            continue
        if not is_brand_type(suggestion_type):
            continue
        if not title_matches_brand(title, brand_name):
            continue
        title_text = " ".join(normalize_tokens(title))
        score = SequenceMatcher(None, brand_text, title_text).ratio()
        candidates.append((score, -index, suggestion))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = "[{}] {}".format(stamp, message)
    print(line)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def read_selected_brands() -> list[dict[str, str]]:
    with BRANDS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = [
        {key: (value or "").strip() for key, value in row.items()}
        for row in rows
        if (row.get("status") or "").strip() == "selected"
    ]
    if not selected:
        raise SystemExit("No selected brands found in {}".format(BRANDS_CSV))
    return selected


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


def is_429(exc: Exception) -> bool:
    if isinstance(exc, exceptions.TooManyRequestsError):
        return True
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) == 429


def fetch_interest(
    keyword: dict | str,
    max_retries: int,
    backoff_seconds: float,
) -> pd.DataFrame:
    retries = 0
    while True:
        try:
            client = TopicTrendReq(hl="en-US", tz=0, timeout=(10, 30))
            client.build_payload([keyword], timeframe=TIMEFRAME, geo="")
            # The payload already contains the entity; use a simple column name.
            client.kw_list = ["value"]
            frame = client.interest_over_time()
            if frame is None or frame.empty:
                raise RuntimeError("Google Trends returned an empty series")
            return frame
        except Exception as exc:
            if not is_429(exc):
                raise
            if retries >= max_retries:
                raise
            wait = backoff_seconds * (2**retries) + random.uniform(0, 10)
            log(
                "HTTP 429; retry {}/{} in {:.0f}s".format(
                    retries + 1, max_retries, wait
                )
            )
            time.sleep(wait)
            retries += 1


def monthly_series(frame: pd.DataFrame) -> pd.Series:
    values = frame["value"].astype(float)
    monthly = values.resample("MS").mean().dropna()
    return monthly


def summarize(brand_name: str, slug: str, monthly: pd.Series) -> dict:
    n_months = int(monthly.size)
    n_zero_months = int((monthly == 0).sum())
    pct_zero = round(100.0 * n_zero_months / n_months, 2) if n_months else 0.0
    mean_value = round(float(monthly.mean()), 4) if n_months else 0.0
    last_12m_mean = (
        round(float(monthly.tail(12).mean()), 4) if n_months else 0.0
    )
    return {
        "brand_name": brand_name,
        "slug": slug,
        "n_months": n_months,
        "n_zero_months": n_zero_months,
        "pct_zero": pct_zero,
        "mean_value": mean_value,
        "last_12m_mean": last_12m_mean,
        "sparse": "Yes" if (pct_zero > 20.0 or mean_value < 5.0) else "No",
    }


def write_raw(path: Path, monthly: pd.Series) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "value"])
        for date, value in monthly.items():
            writer.writerow([date.strftime("%Y-%m-%d"), "{:.4f}".format(value)])


def read_summary() -> dict[str, dict]:
    if not SUMMARY_CSV.is_file():
        return {}
    with SUMMARY_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["brand_name"]: row
            for row in csv.DictReader(handle)
            if row.get("brand_name")
        }


def write_summary(rows: list[dict]) -> None:
    ordered = sorted(
        rows,
        key=lambda row: (
            -float(row["pct_zero"]),
            float(row["mean_value"]),
            row["brand_name"],
        ),
    )
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(ordered)


def print_summary(rows: list[dict]) -> None:
    ordered = sorted(
        rows,
        key=lambda row: (
            -float(row["pct_zero"]),
            float(row["mean_value"]),
            row["brand_name"],
        ),
    )
    print("\nGoogle Trends summary (sorted by pct_zero, descending)")
    print(
        "{:<24} {:<6} {:>3} {:>5} {:>9} {:>8} {:>9} {:<6}".format(
            "brand_name",
            "source",
            "n",
            "zero",
            "pct_zero",
            "mean",
            "last_12m",
            "sparse",
        )
    )
    print("-" * 80)
    for row in ordered:
        print(
            "{:<24} {:<6} {:>3} {:>5} {:>9.2f} {:>8.2f} {:>9.2f} {:<6}".format(
                row["brand_name"],
                row["trends_source"],
                int(row["n_months"]),
                int(row["n_zero_months"]),
                float(row["pct_zero"]),
                float(row["mean_value"]),
                float(row["last_12m_mean"]),
                row["sparse"],
            )
        )
    sparse = [row for row in ordered if row["sparse"] == "Yes"]
    print("\nSparse brands (pct_zero > 20% or mean_value < 5): {}".format(
        len(sparse)
    ))
    if sparse:
        for row in sparse:
            print(
                "  - {} (pct_zero={:.2f}%, mean={:.2f})".format(
                    row["brand_name"], float(row["pct_zero"]),
                    float(row["mean_value"])
                )
            )
    else:
        print("  (none)")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delay",
        type=float,
        default=10.0,
        help="Seconds between interest-over-time requests (default: 10).",
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
        default=60.0,
        help="Base backoff in seconds for HTTP 429 (default: 60).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip brands that already have a raw file and summary row.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    TRENDS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SUGGESTIONS_DIR.mkdir(parents=True, exist_ok=True)

    brands = read_selected_brands()
    existing = read_summary() if args.resume else {}
    rows: list[dict] = list(existing.values())
    completed = {row["brand_name"] for row in rows}
    failures: list[tuple[str, str]] = []

    log(
        "Starting Google Trends fetch for {} selected brands (timeframe={}, "
        "delay={}s)".format(len(brands), TIMEFRAME, args.delay)
    )
    client = TrendReq(hl="en-US", tz=0, timeout=(10, 30))

    for index, brand in enumerate(brands, start=1):
        brand_name = brand["brand_name"]
        slug = slugify(brand_name)
        raw_path = RAW_DIR / "{}.csv".format(slug)

        if args.resume and brand_name in completed and raw_path.is_file():
            log(
                "[{}/{}] {}: already complete, skipping".format(
                    index, len(brands), brand_name
                )
            )
            continue

        cache_path = SUGGESTIONS_DIR / "{}.json".format(slug)
        try:
            suggestions = load_suggestions(
                brand_name, cache_path, client, args.suggestion_delay
            )
        except Exception as exc:
            message = "{}: {}".format(type(exc).__name__, exc)
            log("[{}/{}] {} suggestions failed: {}".format(
                index, len(brands), brand_name, message
            ))
            failures.append((brand_name, "suggestions: " + message))
            continue

        topic = choose_topic(brand_name, suggestions)
        if topic is not None:
            keyword = {
                "mid": topic["mid"],
                "name": topic.get("title", brand_name),
                "type": "Topic",
            }
            trends_source = "topic"
            topic_mid = topic["mid"]
            topic_type = (topic.get("type") or "").strip()
            log(
                "[{}/{}] {}: topic {} ({})".format(
                    index, len(brands), brand_name, topic_mid, topic_type
                )
            )
        else:
            keyword = brand["trends_query"] or brand_name
            trends_source = "query"
            topic_mid = ""
            topic_type = ""
            log(
                "[{}/{}] {}: no company/brand suggestion, query={!r}".format(
                    index, len(brands), brand_name, keyword
                )
            )

        try:
            frame = fetch_interest(
                keyword,
                max_retries=args.max_retries,
                backoff_seconds=args.backoff,
            )
        except Exception as exc:
            if is_429(exc):
                message = "HTTP 429 persisted after {} retries".format(
                    args.max_retries
                )
                log("[{}/{}] {}: {}; stopping".format(
                    index, len(brands), brand_name, message
                ))
                failures.append((brand_name, message))
                write_summary(rows)
                print_summary(rows)
                print(
                    "\nSTOPPED: Google returned HTTP 429 after retries. "
                    "Re-run with --resume after waiting.",
                    file=sys.stderr,
                )
                return 2
            message = "{}: {}".format(type(exc).__name__, exc)
            log("[{}/{}] {} interest failed: {}".format(
                index, len(brands), brand_name, message
            ))
            failures.append((brand_name, "interest: " + message))
            continue

        monthly = monthly_series(frame)
        if monthly.empty:
            message = "monthly series is empty"
            log("[{}/{}] {}: {}".format(
                index, len(brands), brand_name, message
            ))
            failures.append((brand_name, message))
            continue

        write_raw(raw_path, monthly)
        row = summarize(brand_name, slug, monthly)
        row.update(
            {
                "trends_source": trends_source,
                "topic_mid": topic_mid,
                "topic_type": topic_type,
            }
        )
        rows = [item for item in rows if item["brand_name"] != brand_name]
        rows.append(row)
        completed.add(brand_name)
        write_summary(rows)
        log(
            "[{}/{}] {}: saved {} months, zeros={}, mean={:.2f}, sparse={}".format(
                index,
                len(brands),
                brand_name,
                row["n_months"],
                row["n_zero_months"],
                row["mean_value"],
                row["sparse"],
            )
        )
        time.sleep(args.delay + random.uniform(0, 3))

    write_summary(rows)
    print_summary(rows)

    if failures:
        print("\nFailures:", file=sys.stderr)
        for brand_name, message in failures:
            print("  - {}: {}".format(brand_name, message), file=sys.stderr)
        return 1

    log("Completed all {} brands".format(len(brands)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

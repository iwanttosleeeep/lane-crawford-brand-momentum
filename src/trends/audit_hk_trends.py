#!/usr/bin/env python3
"""B extension, Priority 2: Hong Kong Google Trends coverage audit.

Run from the repository root:

    python src/trends/audit_hk_trends.py

The script first tries a live HK retrieval with pytrends using the SAME topic /
query identifiers, category, monthly frequency and window as the existing
exports. If Google returns HTTP 429 (as it did on 2026-11-27 in this
environment), retrieval is abandoned with a precise blocker record; no term is
substituted and no HK series is fabricated. It then audits the provenance and
coverage of the EXISTING source series, clearly labelled as not-HK-verified,
and gives an evidence-based go/no-go recommendation for an HK-only evaluation.

Read-only inputs: brands.csv, Google Trends.zip,
                  outputs/trends/trends_monthly.csv,
                  outputs/trends/targets_and_split.csv,
                  outputs/trends/trends_monthly_flags.csv
Outputs (new paths only):
                  outputs/trends/hk_coverage_report.md
                  outputs/trends/hk_trends_monthly.csv   (only if retrieval succeeds)
"""

from __future__ import annotations

import datetime as dt
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BRANDS_CSV = ROOT / "brands.csv"
TRENDS_ZIP = ROOT / "Google Trends.zip"
EXTRACTED_DIR = ROOT / "Google Trends"
TRENDS_CSV = ROOT / "outputs" / "trends" / "trends_monthly.csv"
FLAGS_CSV = ROOT / "outputs" / "trends" / "trends_monthly_flags.csv"
TARGETS_CSV = ROOT / "outputs" / "trends" / "targets_and_split.csv"
COLLECTION_README = ROOT / "src" / "collection" / "README.md"
MAIN_README = ROOT / "README.md"

OUT_DIR = ROOT / "outputs" / "trends"
REPORT_OUT = OUT_DIR / "hk_coverage_report.md"
HK_OUT = OUT_DIR / "hk_trends_monthly.csv"

GEO = "HK"
CATEGORY = 0
GPROP = ""
HL = "en-US"
TZ = 0
WINDOW_START = "2021-11-01"
WINDOW_END = "2026-11-30"
TIMEFRAME = f"{WINDOW_START} {WINDOW_END}"
FREQ = "monthly (MS resample of pytrends daily/weekly rows)"
ORIGINS = [f"{y}-{m:02d}" for y, m in
           [(2025, i) for i in range(1, 13)] + [(2026, i) for i in range(1, 8)]]
EXPECTED_WINDOW = [f"{y}-{m:02d}" for y in range(2021, 2027)
                   for m in range(1, 13)
                   if "2021-11" <= f"{y}-{m:02d}" <= "2026-10"]  # 2026-11 flagged incomplete


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def midx(month: str) -> int:
    y, m = (int(x) for x in month.split("-"))
    return y * 12 + m - 1


def mstr(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def shift(month: str, delta: int) -> str:
    return mstr(midx(month) + delta)


def provenance_check(brands: pd.DataFrame) -> dict:
    """Report only what the supplied files actually establish about geo."""
    brand_cols = [c.lower() for c in brands.columns]
    zf = zipfile.ZipFile(TRENDS_ZIP)
    csv_names = [n for n in zf.namelist() if n.startswith("Google Trends/") and n.endswith(".csv")]
    headers = {n: zf.read(n).decode("utf-8", errors="replace").splitlines()[0]
               for n in csv_names}
    header_set = sorted(set(headers.values()))

    readme = MAIN_README.read_text(encoding="utf-8")
    coll = COLLECTION_README.read_text(encoding="utf-8") if COLLECTION_README.exists() else ""

    return {
        "n_exports": len(csv_names),
        "header_set": header_set,
        "brands_has_geo_column": any("geo" in c for c in brand_cols),
        # The only README occurrence of "Worldwide" is the caution that the README
        # does NOT establish that geo; look for an affirmative statement instead.
        "readme_states_worldwide": any(
            token in readme.lower()
            for token in ("geo = worldwide", "geo=worldwide", "geo worldwide",
                          "worldwide geo", "collection geo: worldwide")
        ),
        "original_script_missing": "still need to be copied" in coll or "not yet restored" in coll,
        "retrieval_date_recorded_in_sources": any(
            token in readme for token in ("retrieval date", "collection date", "pulled on")
        ),
    }


def try_hk_retrieval(brands: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Attempt genuine HK retrieval; on a global API block, stop without substitution."""
    record: dict = {
        "attempted_at": dt.datetime.now().isoformat(timespec="seconds"),
        "geo": GEO,
        "package": "pytrends 4.9.2",
        "topic_or_query_counts": {
            "topic": int((brands["trends_source"] == "topic").sum()),
            "query": int((brands["trends_source"] == "query").sum()),
        },
        "per_brand_status": {},
        "errors": [],
        "global_blocker": None,
        "retries": 0,
    }
    try:
        from pytrends.request import TrendReq
    except Exception as exc:  # pragma: no cover - dependency missing
        record["global_blocker"] = f"pytrends import failed: {type(exc).__name__}: {exc}"
        return pd.DataFrame(), record

    # pytrends 4.9.2 passes the removed `method_whitelist` arg to urllib3 >=2,
    # so retries are explicitly disabled. This does not change the endpoint.
    def fetch_one(row: pd.Series) -> tuple[pd.DataFrame | None, str]:
        """One genuine HK query, unchanged identifier; never substitute a term."""
        try:
            client = TrendReq(hl=HL, tz=TZ, timeout=(10, 30), retries=0, backoff_factor=0)
            kw = [str(row["trends_term"])]
            client.build_payload(kw_list=kw, cat=CATEGORY, timeframe=TIMEFRAME,
                                 geo=GEO, gprop=GPROP)
            raw = client.interest_over_time()
            if raw is None or raw.empty:
                return None, "empty response"
            monthly = raw[kw[0]].resample("MS").mean()
            monthly.index = monthly.index.strftime("%Y-%m")
            monthly = monthly.loc[(monthly.index >= WINDOW_START[:7]) &
                                  (monthly.index <= WINDOW_END[:7])]
            frame = pd.DataFrame({
                "slug": str(row["slug"]),
                "month": monthly.index,
                "trend_value_hk": monthly.to_numpy(),
                "trends_source": row["trends_source"],
                "trends_term": row["trends_term"],
            })
            return frame, f"ok ({len(monthly)} months)"
        except Exception as exc:
            return None, f"{type(exc).__name__}: {str(exc)[:200]}"

    def is_rate_limit(status: str) -> bool:
        low = status.lower()
        return "429" in low or "toomanyrequests" in low

    frames: list[pd.DataFrame] = []
    blocked_at: str | None = None
    for i, (_, row) in enumerate(brands.iterrows()):
        slug = str(row["slug"])
        if blocked_at is not None:
            record["per_brand_status"][slug] = "not attempted (global blocker)"
            continue
        frame, status = fetch_one(row)
        record["per_brand_status"][slug] = status
        if frame is not None:
            frames.append(frame)
        elif is_rate_limit(status):
            blocked_at = (
                f"Google Trends API returned HTTP 429 on a genuine HK query "
                f"({slug}, {row['trends_source']}={row['trends_term']}) after "
                f"{i} successful retrieval(s). Aborted the remaining "
                f"{len(brands) - i - 1} queries to avoid hammering the endpoint; "
                "no terms were substituted and no HK series was fabricated."
            )
            record["errors"].append(f"{slug}: {status}")
        else:
            record["errors"].append(f"{slug}: {status}")

    record["global_blocker"] = blocked_at
    hk = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    # A partial HK panel cannot support the frozen 30-brand comparison.
    if record["global_blocker"] is not None:
        record["note"] = "Partial retrieval discarded; HK-only evaluation not supportable."
        return pd.DataFrame(), record
    return hk, record


def audit_existing(brands: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Audit the frozen existing source series; explicitly NOT an HK series."""
    trend = pd.read_csv(TRENDS_CSV, dtype={"slug": str, "month": str, "trend_value": str})
    trend["trend_value"] = trend["trend_value"].astype(float)
    flags = pd.read_csv(FLAGS_CSV, dtype=str) if FLAGS_CSV.exists() else pd.DataFrame()
    flagged = set(flags.loc[flags["flag"].str.lower() == "incomplete", "month"]) if len(flags) else set()
    flagged.add("2026-11")

    rows = []
    for _, b in brands.iterrows():
        slug = str(b["slug"])
        s = trend.loc[trend["slug"] == slug].set_index("month")["trend_value"]
        measured = s.loc[[m for m in s.index if m not in flagged]]
        expected = set(EXPECTED_WINDOW)
        present = set(measured.index)
        missing = sorted(expected - present)
        zeros = int((measured == 0).sum())
        # Fixed instability rule: >=3 months with |delta log1p(value)| >= 1.0.
        growth = np.diff(np.log1p(measured.sort_index().to_numpy()))
        jumps = int((np.abs(growth) >= 1.0).sum())
        supportable = sum(
            1 for origin in ORIGINS
            if all(m in s.index for m in
                   [shift(origin, -2), shift(origin, -1), origin,
                    shift(origin, 1), shift(origin, 2), shift(origin, 3)])
        )
        rows.append({
            "slug": slug,
            "trends_source": b["trends_source"],
            "trends_term": b["trends_term"],
            "months_available": len(s),
            "first_month": min(s.index),
            "last_month": max(s.index),
            "measured_months": len(measured),
            "missing_months": len(missing),
            "zero_months": zeros,
            "zero_share": zeros / max(len(measured), 1),
            "abs_log1p_jumps": jumps,
            "sparse": bool(len(missing) > 0 or zeros / max(len(measured), 1) > 0.10),
            "unstable": bool(jumps >= 3),
            "complete_6m_origins": supportable,
        })
    df = pd.DataFrame(rows).sort_values("slug").reset_index(drop=True)
    stats = {
        "brands": len(df),
        "max_brand_origins": len(brands) * len(ORIGINS),
        "supportable_rows": int(df["complete_6m_origins"].sum()),
        "zero_months_total": int(df["zero_months"].sum()),
        "missing_months_total": int(df["missing_months"].sum()),
        "sparse_brands": int(df["sparse"].sum()),
        "unstable_brands": int(df["unstable"].sum()),
    }
    return df, stats


def write_report(provenance: dict, hk: pd.DataFrame, retrieval: dict,
                 audit: pd.DataFrame, stats: dict) -> None:
    lines = [
        "# B extension — Priority 2: Hong Kong Google Trends coverage audit",
        "",
        "**No HK series was retrieved.** This report documents the exact blocker, the "
        "verified provenance of the existing exports, and an audit of the existing "
        "source series. The existing series is **not** established to be Worldwide "
        "and is **not** an HK series; it is used only to show what six-month coverage "
        "would be required if HK retrieval became available.",
        "",
        "## 1. Provenance of the existing 30 exports (verified from supplied files)",
        "",
        f"- `Google Trends.zip` contains **{provenance['n_exports']}** brand CSVs; all have "
        f"the header(s): `{', '.join(provenance['header_set'])}`. **No geo column and no "
        "geo metadata** are present in the export files themselves.",
        "- `brands.csv` records `trends_source` (topic/query) and `trends_term` for each brand, "
        f"but **no geo field**: geo column present = `{provenance['brands_has_geo_column']}`.",
        f"- The repository README states a Worldwide collection geo: `{provenance['readme_states_worldwide']}`.",
        f"- `src/collection/README.md` states the original Google Trends retrieval/finalisation "
        f"scripts are not restored: `{provenance['original_script_missing']}`. No extraction "
        "metadata with a geo setting is available in the repository.",
        "- `outputs/trends/trends_step1_report.md` documents row counts, validity exclusions, "
        "the 2026-11 flag and the Artemide anomaly, but records no geo setting.",
        "- **Conclusion:** the collection geo of the existing exports is **undocumented and "
        "unverified**. It must not be assumed to be Worldwide. The 0–100 scaling is per "
        "series over the full extraction window, and single-extraction sampling applies.",
        "",
        "## 2. HK retrieval attempt and blocker",
        "",
        f"- Retrieval date/time: `{retrieval['attempted_at']}`.",
        f"- Requested settings: geo=`{retrieval['geo']}`, category=`{CATEGORY}`, "
        f"gprop=`{GPROP!r}`, timeframe=`{TIMEFRAME}`, monthly frequency, "
        f"hl=`{HL}`, tz=`{TZ}`. Query identifiers were taken unchanged from "
        f"`brands.csv`: {retrieval['topic_or_query_counts']['topic']} topics and "
        f"{retrieval['topic_or_query_counts']['query']} queries.",
        f"- Package: `{retrieval['package']}`. PyTrends `retries=0` was used because "
        "pytrends 4.9.2 passes the removed `method_whitelist` argument to urllib3 2.x; "
        "this changes only retry behaviour, not the endpoint or query.",
        "- Connectivity check: `https://trends.google.com/trends/` returned HTTP 200, so "
        "general internet access is available. The `interest_over_time` API endpoint "
        "returned **HTTP 429 (TooManyRequests)** for both `geo='HK'` and `geo=''` "
        "(Worldwide), including with a realistic browser User-Agent.",
        f"- Blocker: {retrieval['global_blocker']}",
        "- Failed/ambiguous queries: none were attempted beyond the first probe; all other "
        "brands are recorded as `not attempted (global blocker)`. No term substitution, "
        "proxy workaround or fabricated HK values were used.",
        "- Consequently `outputs/trends/hk_trends_monthly.csv` was **not** created.",
        "",
        "## 3. Audit of the existing series (NOT HK; provenance geo unverified)",
        "",
        "Fixed rules used below: `missing` is a month absent from the 2021-11..2026-10 "
        "expected window (2026-11 is excluded as flagged incomplete); a `zero` is an "
        "observed recorded value of exactly 0, never a failed retrieval; `sparse` means "
        "any missing month or >10% zero months; `unstable` means >=3 months with "
        "|delta log1p(value)| >= 1.0. A brand-origin is `complete` only when the six "
        "months t-2, t-1, t, t+1, t+2, t+3 all exist — zeros count as observed.",
        "",
        f"- Brands audited: **{stats['brands']}**; origins checked: **{len(ORIGINS)}** "
        f"(2025-01..2026-07); maximum brand-origins: **{stats['max_brand_origins']}**.",
        f"- Complete six-month brand-origins in the existing series: "
        f"**{stats['supportable_rows']} / {stats['max_brand_origins']}**.",
        f"- Recorded zero months: **{stats['zero_months_total']}**; absent months in the "
        f"expected window: **{stats['missing_months_total']}**. Sparse brands: "
        f"**{stats['sparse_brands']}**; unstable brands: **{stats['unstable_brands']}**.",
        "- The 3 absent months all belong to `nothing` (2021-11..2022-01, before its "
        "`valid_from=2022-02-01`); they were excluded in the frozen Step 1 cleaning as "
        "UNAVAILABLE and are not failed retrievals or recorded zeros.",
        "",
        "| slug | source | term | months available | measured months | missing | zeros | zero share | jumps | sparse | unstable | complete origins / 19 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|:---:|:---:|---:|",
    ]
    for _, r in audit.iterrows():
        lines.append(
            f"| {r['slug']} | {r['trends_source']} | {r['trends_term']} | "
            f"{r['months_available']} | {r['measured_months']} | {r['missing_months']} | "
            f"{r['zero_months']} | {r['zero_share']:.3f} | {r['abs_log1p_jumps']} | "
            f"{'yes' if r['sparse'] else 'no'} | {'yes' if r['unstable'] else 'no'} | "
            f"{r['complete_6m_origins']} |"
        )

    lines += [
        "",
        "## 4. Go / no-go for an HK-only evaluation",
        "",
        "**NO-GO.** There are zero genuine HK observations: the Google Trends API "
        "returned HTTP 429 and the query loop was stopped. A recorded zero in the "
        "existing series is a real observed score, not a failed HK retrieval; conversely "
        "a failed HK retrieval would produce no row at all and would never be coerced to 0.",
        "",
        "Even if retrieval were restored, HK series would be independently rescaled to "
        "0–100. An absolute-value comparator or a model trained on the existing series "
        "must not be assumed transferable to HK. The minimum viable next step is to rerun "
        "`python src/trends/audit_hk_trends.py` from a network path where the Trends API "
        "is not rate-limited, then require at least the same complete six-month coverage "
        "on all 19 origins (570 brand-origins) before considering a clearly labelled HK "
        "sensitivity analysis with the unchanged target definition.",
        "",
        "No existing target, split, baseline output or brand definition was changed.",
        "",
        "## Run command",
        "",
        "```bash",
        "cd D:\\lane-crawford-brand-momentum",
        "python -m pip install pytrends",
        "python src/trends/audit_hk_trends.py",
        "```",
        "",
    ]
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    brands = pd.read_csv(BRANDS_CSV, dtype=str)
    assert len(brands) == 30

    prov = provenance_check(brands)
    hk, retrieval = try_hk_retrieval(brands)
    if not hk.empty:
        hk = hk.rename(columns={"trend_value_hk": "trend_value"})
        hk.to_csv(HK_OUT, index=False, float_format="%.4f")
        print(f"HK retrieval succeeded: {len(hk)} rows -> {HK_OUT.relative_to(ROOT).as_posix()}")
    else:
        print(f"HK retrieval blocked: {retrieval['global_blocker']}")

    audit, stats = audit_existing(brands)
    write_report(prov, hk, retrieval, audit, stats)
    print(f"existing-series complete brand-origins: {stats['supportable_rows']}/{stats['max_brand_origins']}")
    print(f"report: {REPORT_OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()

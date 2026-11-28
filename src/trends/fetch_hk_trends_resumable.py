#!/usr/bin/env python3
"""Resumable, manual-stop Google Trends HK collection for STAT6207.

Based on the user's original fetch_google_trends.py (TopicTrendReq payload and
weekly-to-monthly averaging), with the exact FINAL topic/query identifiers read
from brands.csv. No suggestions/reselection, automatic retry or proxy rotation.

Install:  python -m pip install "pytrends==4.9.2" pandas requests
Preview:  python src/trends/fetch_hk_trends_resumable.py --dry-run
Collect:  python src/trends/fetch_hk_trends_resumable.py
Resume:   python src/trends/fetch_hk_trends_resumable.py
Test one: python src/trends/fetch_hk_trends_resumable.py --max-brands 1

Default per-brand checkpoints:
  outputs/trends/hk_collection/raw/<slug>.csv       (Google's weekly values)
  outputs/trends/hk_collection/monthly/<slug>.csv   (monthly mean values)
  outputs/trends/hk_collection/metadata/<slug>.json (query and file checksums)
  outputs/trends/hk_collection/collection_report.md

Only after ALL brands complete:
  outputs/trends/hk_trends_monthly.csv

The main Trends and frozen model files are NEVER read-modified or overwritten.
All values are independently normalised Google Trends indices, not comparable
absolute search volumes; changing geo also changes the normalisation base.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

GEO = "HK"
TIMEFRAME = "2021-11-01 2026-10-31"  # complete months only; freeze across resumptions
HL = "en-US"
TZ = 0
CAT = 0
GPROP = ""
SCHEMA_VERSION = 1
EXPECTED_MONTHS = [f"{y:04d}-{m:02d}" for y in range(2021, 2027)
                   for m in range(1, 13)
                   if "2021-11" <= f"{y:04d}-{m:02d}" <= "2026-10"]


def repo_root() -> Path:
    """Works either from src/trends/ in the repo or a standalone copied file."""
    script = Path(__file__).resolve()
    for candidate in (script.parent, *script.parents, Path.cwd()):
        if (candidate / "brands.csv").exists():
            return candidate
    return Path.cwd()


def resolved_path(text: str, root: Path) -> Path:
    p = Path(text).expanduser()
    return p if p.is_absolute() else root / p


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_csv(df, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            df.to_csv(f, index=False, float_format="%.6f")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_write_text(content: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_brands(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = [{k: (v or "").strip() for k, v in row.items()}
                for row in csv.DictReader(f)]
    needed = {"slug", "brand_name", "trends_source", "trends_term", "trends_valid_from"}
    if not rows or not needed.issubset(rows[0]):
        raise ValueError(f"Brands file must have columns: {sorted(needed)}")
    if len(set(r["slug"] for r in rows)) != len(rows):
        raise ValueError("Duplicate brand slug(s) in brands file")
    for row in rows:
        src, term = row["trends_source"], row["trends_term"]
        if src not in {"topic", "query"} or not term:
            raise ValueError(f"Invalid trends_source/term for {row['slug']}: {src!r}/{term!r}")
        if src == "topic" and not term.startswith(("/m/", "/g/")):
            raise ValueError(f"Expected topic MID (not plain search): {row['slug']} {term}")
        if src == "query" and term.startswith(("/m/", "/g/")):
            raise ValueError(f"Query unexpectedly looks like a MID: {row['slug']} {term}")
    return rows


def is_429(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    text = str(exc).lower()
    return (code == 429 or "429" in text or "toomanyrequests" in text)


def fetch_monthly(row: dict[str, str]):
    """One request without automatic retries; original custom Topic payload."""
    import pandas as pd
    from pytrends.request import TrendReq

    class TopicTrendReq(TrendReq):
        # Adapted from the supplied original fetch_google_trends.py.
        # Native pytrends treats MID strings as ordinary keyword strings;
        # pass a proper Topic entity object in the comparisonItem payload.
        def build_payload(self, kw_list, cat=0, timeframe=TIMEFRAME, geo=GEO, gprop=""):
            if gprop not in ("", "images", "news", "youtube", "froogle"):
                raise ValueError("Unsupported gprop")
            self.kw_list = kw_list
            self.geo = geo
            self.token_payload = {
                "hl": self.hl, "tz": self.tz,
                "req": {"comparisonItem": [], "category": cat, "property": gprop},
            }
            for keyword in kw_list:
                if isinstance(keyword, dict):
                    item = {"keyword": keyword["mid"],
                            "name": keyword.get("name", ""),
                            "type": "Topic", "time": timeframe, "geo": geo}
                else:
                    item = {"keyword": keyword, "time": timeframe, "geo": geo}
                self.token_payload["req"]["comparisonItem"].append(item)
            self.token_payload["req"] = json.dumps(self.token_payload["req"])
            self._tokens()

    # retries=0 avoids deprecated urllib3 method_whitelist in pytrends 4.9.2
    # when urllib3 >=2 is installed. It also ensures the first 429 stops us.
    client = TopicTrendReq(hl=HL, tz=TZ, timeout=(10, 30), retries=0,
                           backoff_factor=0)
    term = row["trends_term"]
    if row["trends_source"] == "topic":
        keyword = {"mid": term, "name": row["brand_name"], "type": "Topic"}
    else:
        keyword = term
    client.build_payload([keyword], cat=CAT, timeframe=TIMEFRAME, geo=GEO, gprop=GPROP)
    # Exactly mirrors the original TopicTrendReq collector's column handling.
    client.kw_list = ["value"]
    df = client.interest_over_time()
    if df is None or df.empty or "value" not in df.columns:
        raise ValueError(f"Empty/invalid Trends response for {row['slug']}")
    weekly = df.reset_index().rename(columns={df.index.name or "date": "date"})
    if "date" not in weekly:
        weekly = weekly.rename(columns={weekly.columns[0]: "date"})
    weekly = weekly[["date", "value"] + (["isPartial"] if "isPartial" in weekly else [])].copy()
    weekly["date"] = pd.to_datetime(weekly["date"], errors="raise")
    weekly["value"] = pd.to_numeric(weekly["value"], errors="raise")
    if weekly["value"].isna().any() or not weekly["value"].between(0, 100).all():
        raise ValueError(f"Nonfinite/out-of-range GT values for {row['slug']}")
    if weekly["date"].duplicated().any():
        raise ValueError(f"Duplicate GT time points for {row['slug']}")
    monthly = (weekly.set_index("date")["value"].sort_index()
               .resample("MS").mean().dropna())
    monthly = monthly[(monthly.index >= pd.Timestamp("2021-11-01")) &
                      (monthly.index <= pd.Timestamp("2026-10-01"))]
    if monthly.empty:
        raise ValueError(f"No usable months for {row['slug']}")
    out = pd.DataFrame({"slug": row["slug"],
                        "month": monthly.index.strftime("%Y-%m"),
                        "trend_value": monthly.to_numpy(),
                        "valid_from": row["trends_valid_from"],
                        "trends_source": row["trends_source"],
                        "trends_term": term,
                        "geo": GEO})
    return weekly, out


def checkpoint_paths(outdir: Path, slug: str) -> tuple[Path, Path, Path]:
    return (outdir / "raw" / f"{slug}.csv",
            outdir / "monthly" / f"{slug}.csv",
            outdir / "metadata" / f"{slug}.json")


def load_checkpoint(outdir: Path, row: dict[str, str]):
    """Return checked monthly DataFrame or None. Never silently accept mismatches."""
    import pandas as pd
    raw, monthly, meta = checkpoint_paths(outdir, row["slug"])
    if not meta.exists():
        # If the process was interrupted before metadata was written, redo this
        # brand; partial weekly/monthly CSVs are not trusted as completed.
        return None
    try:
        m = json.loads(meta.read_text(encoding="utf-8"))
        expect = {"schema_version": SCHEMA_VERSION, "geo": GEO,
                  "timeframe": TIMEFRAME, "slug": row["slug"],
                  "trends_source": row["trends_source"],
                  "trends_term": row["trends_term"],
                  "valid_from": row["trends_valid_from"]}
        for key, val in expect.items():
            if m.get(key) != val:
                raise ValueError(f"{key} changed: saved={m.get(key)!r}, expected={val!r}")
        for path, key in ((raw, "raw_sha256"), (monthly, "monthly_sha256")):
            if not path.is_file() or sha256(path) != m[key]:
                raise ValueError(f"missing or altered {path} (SHA mismatch)")
        df = pd.read_csv(monthly, dtype={"slug": str, "month": str})
        if df.empty or df.duplicated(["slug", "month"]).any():
            raise ValueError("empty/duplicate brand-month rows")
        if set(df["slug"]) != {row["slug"]} or set(df["geo"]) != {GEO}:
            raise ValueError("slug/geo mismatch")
        if not df["trend_value"].between(0, 100).all() or df["trend_value"].isna().any():
            raise ValueError("invalid trend values")
        return df
    except Exception as exc:
        raise RuntimeError(f"Invalid checkpoint for {row['slug']}: {exc}. "
                           "Repair this brand's files or use a NEW --output-dir; "
                           "do not merge incompatible extraction settings.") from exc


def store_checkpoint(outdir: Path, row: dict[str, str], weekly, monthly) -> None:
    raw, mon, meta = checkpoint_paths(outdir, row["slug"])
    atomic_write_csv(weekly, raw)
    atomic_write_csv(monthly, mon)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "slug": row["slug"], "geo": GEO, "timeframe": TIMEFRAME,
        "trends_source": row["trends_source"], "trends_term": row["trends_term"],
        "valid_from": row["trends_valid_from"], "retrieved_at_utc": utc_now(),
        "n_raw_observations": len(weekly), "n_months": len(monthly),
        "raw_sha256": sha256(raw), "monthly_sha256": sha256(mon),
    }
    atomic_write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", meta)


def write_report(outdir: Path, rows: list[dict[str, str]],
                 completed: dict[str, object], status: str) -> None:
    import pandas as pd
    lines = ["# Google Trends Hong Kong — manual resumable collection", "",
             f"Status: **{status}**", "",
             f"Collected: **{len(completed)} / {len(rows)}** official brands", "",
             f"Region: `{GEO}`; exact timeframe: `{TIMEFRAME}`; geo and query terms fixed.",
             "Method: one request per brand; original topic MID payload; weekly→monthly mean.",
             "No automatic 429 retries, proxy rotation or post-hoc term substitution.",
             "Each brand's raw response, monthly means and SHA-256 metadata are saved.",
             "The overall final CSV is written only on full completion.", "",
             "| slug | source | months | zeros | missing months in fixed window |",
             "|---|---|---:|---:|---:|"]
    for row in rows:
        df = completed.get(row["slug"])
        if df is None:
            lines.append(f"| {row['slug']} | {row['trends_source']} | pending | — | — |")
        else:
            months = set(df["month"])
            missing = len(set(EXPECTED_MONTHS) - months)
            zeros = int((pd.to_numeric(df["trend_value"]) == 0).sum())
            lines.append(f"| {row['slug']} | {row['trends_source']} | {len(df)} | {zeros} | {missing} |")
    lines += ["", "## Interpretation", "",
              "- These are HK-specific Google Trends indices independently normalised to 0–100.",
              "- Their scale differs from the original Worldwide series. Do not substitute HK data into the frozen main target, splits, or model predictions.",
              "- Recorded zero is an observation, not an absent month; missing months must remain missing.",
              "- The data request uses complete calendar months through October 2026; endpoint sampling or partial weekly points can still create boundary effects.",
              "- Temporal look-ahead from whole-window Google normalisation remains; report it in any sensitivity analysis.", ""]
    atomic_write_text("\n".join(lines), outdir / "collection_report.md")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brands", default="brands.csv", help="Relative to repository root")
    p.add_argument("--output-dir", default="outputs/trends/hk_collection")
    p.add_argument("--final-output", default="outputs/trends/hk_trends_monthly.csv")
    p.add_argument("--delay", type=float, default=20.0,
                   help="Seconds between successful requests (default 20)")
    p.add_argument("--max-brands", type=int, default=0,
                   help="Collect at most N NEW brands this run (0 = all)")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview fixed geo/query choices without network access")
    args = p.parse_args(argv)
    if args.delay < 0 or args.max_brands < 0:
        p.error("--delay and --max-brands must be nonnegative")

    root = repo_root()
    brands_file = resolved_path(args.brands, root)
    outdir = resolved_path(args.output_dir, root)
    final = resolved_path(args.final_output, root)
    rows = load_brands(brands_file)
    if outdir == root or final == brands_file:
        p.error("Unsafe output paths")
    if args.dry_run:
        print(f"Geo={GEO}, timeframe={TIMEFRAME}, brands={len(rows)}, output={outdir}")
        for i, row in enumerate(rows, 1):
            print(f"{i:2}. {row['slug']:24} {row['trends_source']:5} {row['trends_term']}")
        return 0

    try:
        import pandas as pd
        import pytrends  # noqa: F401
    except ImportError:
        print('Missing package. Run: python -m pip install "pytrends==4.9.2" pandas requests',
              file=sys.stderr)
        return 1

    outdir.mkdir(parents=True, exist_ok=True)
    # Config lock also prevents stale checkpoints from another brands list or
    # output directory being mixed into a different dataset.
    lock = outdir / "collection_config.json"
    config = {"schema_version": SCHEMA_VERSION, "geo": GEO,
              "timeframe": TIMEFRAME, "brand_rows": [
                  {k: row[k] for k in ("slug", "brand_name", "trends_source",
                                          "trends_term", "trends_valid_from")}
                  for row in rows]}
    if lock.exists():
        if json.loads(lock.read_text(encoding="utf-8")) != config:
            print("STOP: brand list/query/timeframe changed since checkpoint. "
                  "Use a new --output-dir and --final-output, or restore the original brands file.",
                  file=sys.stderr)
            return 1
    else:
        atomic_write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", lock)

    completed = {}
    try:
        for row in rows:
            old = load_checkpoint(outdir, row)
            if old is not None:
                completed[row["slug"]] = old
    except RuntimeError as exc:
        print("STOP: " + str(exc), file=sys.stderr)
        return 1

    pending = [r for r in rows if r["slug"] not in completed]
    print(f"HK Trends: {len(completed)}/{len(rows)} saved; {len(pending)} pending. "
          "Exit/re-run this same command to resume.", flush=True)
    attempted = 0
    for row in pending:
        if args.max_brands and attempted >= args.max_brands:
            break
        slug = row["slug"]
        print(f"Fetching [{len(completed)+1}/{len(rows)}] {slug} "
              f"({row['trends_source']}: {row['trends_term']})", flush=True)
        try:
            weekly, monthly = fetch_monthly(row)
            store_checkpoint(outdir, row, weekly, monthly)
            completed[slug] = monthly
            attempted += 1
            print(f"  SAVED {slug}: {len(monthly)} months, {len(weekly)} source points", flush=True)
            write_report(outdir, rows, completed, "IN PROGRESS")
        except Exception as exc:
            label = "HTTP 429 (rate limited)" if is_429(exc) else f"{type(exc).__name__}: {exc}"
            print(f"\nSTOP at {slug}: {label}\nCompleted: {len(completed)}/{len(rows)}. "
                  "No automatic retries. After resolving the issue, rerun the same command.",
                  file=sys.stderr, flush=True)
            write_report(outdir, rows, completed, f"STOPPED at {slug}: {label}")
            return 2 if is_429(exc) else 1
        if len(completed) < len(rows) and args.delay > 0:
            time.sleep(args.delay)

    if len(completed) != len(rows):
        write_report(outdir, rows, completed, "PAUSED (resume to finish)")
        print(f"Paused: {len(completed)}/{len(rows)} brands. Final file not written.")
        return 0

    result = pd.concat([completed[row["slug"]] for row in rows], ignore_index=True)
    result = result.sort_values(["slug", "month"]).reset_index(drop=True)
    if result.duplicated(["slug", "month"]).any():
        print("STOP: duplicate brand/month in combined HK result", file=sys.stderr)
        return 1
    # Do not quietly overwrite an unrelated or existing final output file.
    if final.exists():
        existing = pd.read_csv(final, dtype={"slug": str, "month": str})
        keys = ["slug", "month", "trend_value", "valid_from", "trends_source", "trends_term", "geo"]
        if not all(k in existing.columns for k in keys):
            same = False
        else:
            categorical = [k for k in keys if k != "trend_value"]
            same = (len(existing) == len(result)
                    and existing[categorical].astype(str).reset_index(drop=True).equals(
                        result[categorical].astype(str).reset_index(drop=True))
                    and (existing["trend_value"].to_numpy()
                         - result["trend_value"].to_numpy()).__abs__().max() <= 0.00000051)
        if not same:
            print(f"STOP: {final} already exists and differs. Refusing overwrite. "
                  "Choose a new --final-output.", file=sys.stderr)
            return 1
    else:
        atomic_write_csv(result, final)
    write_report(outdir, rows, completed, "COMPLETE")
    print(f"COMPLETE: {len(rows)} brands, {len(result)} brand-month rows, file: {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

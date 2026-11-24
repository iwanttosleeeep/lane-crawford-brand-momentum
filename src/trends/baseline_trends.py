#!/usr/bin/env python3
"""Step 3 (Member B): Trends-only baselines on the locked chronological split.

Run from the repository root:

    python src/trends/baseline_trends.py

Environment: Python 3.11+, pandas, numpy, scipy, scikit-learn.

Inputs
------
outputs/trends/trends_monthly.csv   slug, month, trend_value, valid_from
outputs/trends/targets_and_split.csv slug, origin_month, target_growth, split

Outputs
-------
outputs/trends/baseline_predictions.csv
outputs/trends/baseline_metrics.csv
outputs/trends/README.md

No random K-fold and no row-wise TimeSeriesSplit are used. Hyperparameters are
chosen with purged, calendar-origin-month-grouped expanding-window CV.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
TRENDS_CSV = ROOT / "outputs" / "trends" / "trends_monthly.csv"
FLAGS_CSV = ROOT / "outputs" / "trends" / "trends_monthly_flags.csv"
TARGETS_CSV = ROOT / "outputs" / "trends" / "targets_and_split.csv"
OUT_DIR = ROOT / "outputs" / "trends"

PRED_OUT = OUT_DIR / "baseline_predictions.csv"
METRICS_OUT = OUT_DIR / "baseline_metrics.csv"
README_OUT = OUT_DIR / "README.md"

FEATURES = [
    "lag_0",
    "lag_1",
    "lag_2",
    "roll3",
    "roll6",
    "growth_1",
    "growth_2",
    "growth_3",
]
ALPHA_GRID = [0.01, 0.1, 1.0, 10.0, 100.0]
VAL_MONTHS = ["2025-10", "2025-12", "2026-02"]
MATCHED_TRAIN = ("2025-01", "2026-02")
PURGE = ("2026-03", "2026-04")
TEST = ("2026-05", "2026-07")
LAST_SAFE_ORIGIN = "2026-02"  # origin + 3 <= 2026-05 label-availability cutoff
LAST_ORIGIN = "2026-07"
EARLIEST_EXTENDED_SEARCH = "2022-01"


# ---------------------------------------------------------------------------
# calendar helpers
# ---------------------------------------------------------------------------
def midx(month: str) -> int:
    year, mon = (int(p) for p in month.split("-"))
    return year * 12 + (mon - 1)


def mstr(idx: int) -> str:
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def shift(month: str, delta: int) -> str:
    return mstr(midx(month) + delta)


def month_span(first: str, last: str) -> list[str]:
    return [mstr(i) for i in range(midx(first), midx(last) + 1)]


def incomplete_months() -> set[str]:
    months = {"2026-11"}
    if FLAGS_CSV.exists():
        flags = pd.read_csv(FLAGS_CSV, dtype=str)
        if {"month", "flag"}.issubset(flags.columns):
            months.update(flags.loc[flags["flag"].str.lower() == "incomplete", "month"].tolist())
    return months


def make_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=alpha, random_state=None)),
        ]
    )


def mean_abs_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))


# ---------------------------------------------------------------------------
# input loading / consistency
# ---------------------------------------------------------------------------
def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    excl = incomplete_months()
    trend = pd.read_csv(
        TRENDS_CSV,
        dtype={"slug": str, "month": str, "trend_value": str, "valid_from": str},
    )
    trend["trend_value"] = trend["trend_value"].astype(float)
    n_input_rows = len(trend)
    n_excluded_rows = int(trend["month"].isin(excl).sum())
    trend = trend.loc[~trend["month"].isin(excl)].copy()
    n_duplicate_keys = int(trend.duplicated(["slug", "month"]).sum())
    trend = trend.drop_duplicates(["slug", "month"], keep="first")

    targets = pd.read_csv(
        TARGETS_CSV,
        dtype={"slug": str, "origin_month": str, "target_growth": str, "split": str},
    )
    targets["target_growth"] = targets["target_growth"].astype(float)

    meta = {
        "incomplete_months": sorted(excl),
        "n_input_rows": n_input_rows,
        "n_excluded_rows": n_excluded_rows,
        "n_observed_rows": len(trend),
        "n_duplicate_keys": n_duplicate_keys,
        "n_locked_rows": len(targets),
        "n_slugs": int(trend["slug"].nunique()),
    }
    return trend, targets, meta


# ---------------------------------------------------------------------------
# feature / extended-target panel
# ---------------------------------------------------------------------------
def build_panel(trend: pd.DataFrame, targets: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    series_by_slug: dict[str, dict[str, float]] = {
        slug: dict(zip(group["month"], group["trend_value"]))
        for slug, group in trend.groupby("slug", sort=False)
    }
    valid_from_month = {
        slug: str(group["valid_from"].iloc[0])[:7]
        for slug, group in trend.groupby("slug", sort=False)
    }

    locked = targets.set_index(["slug", "origin_month"])
    records: list[dict] = []
    first_origin_by_slug: dict[str, str] = {}

    for slug in sorted(series_by_slug):
        series = series_by_slug[slug]
        vmonth = valid_from_month[slug]
        # Need six observed history months (t-5..t), so first usable origin is vmonth + 5.
        search_start = max(EARLIEST_EXTENDED_SEARCH, mstr(midx(vmonth) + 5))
        first_origin_by_slug[slug] = search_start

        for origin in month_span(search_start, LAST_ORIGIN):
            hist = [shift(origin, d) for d in range(-5, 1)]
            if not all(m in series for m in hist):
                continue
            vals = [series[m] for m in hist]  # t-5 ... t
            future = [series.get(shift(origin, d), np.nan) for d in (1, 2, 3)]
            if not np.all(np.isfinite(future)):
                continue

            past_mean = float(np.mean(vals[-3:]))
            future_mean = float(np.mean(future))
            recomputed_target = math.log1p(future_mean) - math.log1p(past_mean)

            key = (slug, origin)
            if key in locked.index:
                row = locked.loc[key]
                y_true = float(row["target_growth"])
                split = str(row["split"])
            else:
                y_true = recomputed_target
                split = "extended_prefix"

            records.append(
                {
                    "slug": slug,
                    "origin_month": origin,
                    "split": split,
                    "y_true": y_true,
                    "recomputed_target": recomputed_target,
                    "lag_0": vals[-1],
                    "lag_1": vals[-2],
                    "lag_2": vals[-3],
                    "roll3": float(np.mean(vals[-3:])),
                    "roll6": float(np.mean(vals)),
                    "growth_1": math.log1p(vals[-1]) - math.log1p(vals[-2]),
                    "growth_2": math.log1p(vals[-2]) - math.log1p(vals[-3]),
                    "growth_3": math.log1p(vals[-3]) - math.log1p(vals[-4]),
                }
            )

    panel = pd.DataFrame.from_records(records)
    locked_key = set(zip(targets["slug"], targets["origin_month"]))
    panel_key = set(zip(panel["slug"], panel["origin_month"]))
    missing_locked = sorted(locked_key - panel_key)
    target_diff = float(np.max(np.abs(panel["y_true"] - panel["recomputed_target"])))

    # Restrict extended training to before the locked train period and label cutoff.
    ext = panel.loc[
        (panel["split"] == "extended_prefix") & (panel["origin_month"] <= LAST_SAFE_ORIGIN)
    ].copy()
    matched = panel.loc[panel["split"] == "train"].copy()
    purge = panel.loc[panel["split"] == "purge"].copy()
    test = panel.loc[panel["split"] == "test"].copy().sort_values(["origin_month", "slug"]).reset_index(drop=True)
    extended_train = pd.concat([ext, matched], ignore_index=True)

    stats = {
        "panel_rows": len(panel),
        "extended_prefix_rows": len(ext),
        "matched_train_rows": len(matched),
        "purge_rows": len(purge),
        "test_rows": len(test),
        "extended_train_rows": len(extended_train),
        "missing_locked_rows": missing_locked,
        "max_target_discrepancy": target_diff,
        "first_origin_by_slug": first_origin_by_slug,
        "extended_origin_min": ext["origin_month"].min() if len(ext) else "n/a",
        "extended_origin_max": ext["origin_month"].max() if len(ext) else "n/a",
        "max_train_future_month": mstr(midx(max(matched["origin_month"])) + 3) if len(matched) else "n/a",
    }
    return panel, stats


# ---------------------------------------------------------------------------
# CV and final fit
# ---------------------------------------------------------------------------
def cv_results(train_df: pd.DataFrame) -> list[dict]:
    results: list[dict] = []
    for alpha in ALPHA_GRID:
        for val_month in VAL_MONTHS:
            cut = mstr(midx(val_month) - 3)
            tr = train_df.loc[train_df["origin_month"] <= cut]
            va = train_df.loc[train_df["origin_month"] == val_month]
            if len(tr) == 0 or len(va) == 0:
                raise RuntimeError(f"empty CV fold: alpha={alpha}, val={val_month}")
            pipe = make_pipeline(alpha)
            pipe.fit(tr[FEATURES], tr["y_true"])
            pred = pipe.predict(va[FEATURES])
            results.append(
                {
                    "alpha": alpha,
                    "val_month": val_month,
                    "latest_train_origin": cut,
                    "n_train_rows": len(tr),
                    "n_val_rows": len(va),
                    "val_mae": mean_abs_error(va["y_true"].to_numpy(), pred),
                }
            )
    return results


def choose_alpha(cv: list[dict]) -> tuple[float, pd.DataFrame]:
    df = pd.DataFrame(cv)
    summary = (
        df.groupby("alpha", as_index=False)
        .agg(mean_val_mae=("val_mae", "mean"))
        .sort_values(["mean_val_mae", "alpha"], kind="stable")
    )
    chosen = float(summary.iloc[0]["alpha"])
    return chosen, summary


def fit_predict(train_df: pd.DataFrame, test_df: pd.DataFrame, alpha: float) -> np.ndarray:
    pipe = make_pipeline(alpha)
    pipe.fit(train_df[FEATURES], train_df["y_true"])
    return pipe.predict(test_df[FEATURES])


def monthly_spearman(test: pd.DataFrame, pred: np.ndarray) -> dict[str, float]:
    out: dict[str, float] = {}
    for month in sorted(test["origin_month"].unique()):
        mask = test["origin_month"].to_numpy() == month
        y_true = test.loc[mask, "y_true"].to_numpy()
        y_pred = np.asarray(pred)[mask]
        if np.allclose(y_pred, y_pred[0]):
            out[month] = float("nan")
        else:
            out[month] = float(spearmanr(y_true, y_pred).statistic)
    return out


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------
def write_outputs(
    test: pd.DataFrame,
    preds: dict[tuple[str, str], np.ndarray],
    metrics_rows: list[dict],
    cv_all: dict[str, list[dict]],
    chosen: dict[str, float],
    alpha_summary: dict[str, pd.DataFrame],
    panel_stats: dict,
    input_meta: dict,
    artemide: dict[str, float],
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pred_frames = []
    for (model, window), values in preds.items():
        frame = test[["slug", "origin_month", "y_true"]].copy()
        frame["y_pred"] = values
        frame["model"] = model
        frame["training_window"] = window
        pred_frames.append(frame)
    pred_df = pd.concat(pred_frames, ignore_index=True)
    pred_df = pred_df[["slug", "origin_month", "y_true", "y_pred", "model", "training_window"]]
    pred_df.to_csv(PRED_OUT, index=False, float_format="%.10f")

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(METRICS_OUT, index=False, na_rep="nan", float_format="%.10f")

    lines = [
        "# Member B — Trends-only baselines",
        "",
        "## Run",
        "",
        "```bash",
        "cd D:\\lane-crawford-brand-momentum",
        "python src/trends/clean_trends.py",
        "python src/trends/build_targets_split.py",
        "python src/trends/baseline_trends.py",
        "```",
        "",
        "Environment: Python 3.11 with pandas, numpy, scipy and scikit-learn. "
        "This script uses only the two named CSV inputs and writes the three outputs below.",
        "",
        "## Data coverage",
        "",
        f"- Input `trends_monthly.csv` rows: **{input_meta['n_input_rows']}**; "
        f"removed incomplete `{', '.join(input_meta['incomplete_months'])}`: **{input_meta['n_excluded_rows']}**; "
        f"observed rows used: **{input_meta['n_observed_rows']}**.",
        f"- Brands: **{input_meta['n_slugs']}**. Duplicate `(slug, month)` keys in input: "
        f"**{input_meta['n_duplicate_keys']}**.",
        f"- Locked rows in `targets_and_split.csv`: **{input_meta['n_locked_rows']}** "
        "(420 train / 60 purge / 90 test in Step 2).",
        f"- Constructed feature/target panel rows: **{panel_stats['panel_rows']}** "
        f"(extended pre-2025 prefix **{panel_stats['extended_prefix_rows']}**, "
        f"matched train **{panel_stats['matched_train_rows']}**, "
        f"purge **{panel_stats['purge_rows']}**, test **{panel_stats['test_rows']}**).",
        f"- Extended-prefix origins: **{panel_stats['extended_origin_min']} … {panel_stats['extended_origin_max']}**; "
        f"extended training rows in total: **{panel_stats['extended_train_rows']}**.",
        f"- Max target discrepancy between supplied `target_growth` and recomputation from "
        f"`trends_monthly.csv`: **{panel_stats['max_target_discrepancy']:.3e}**.",
        f"- Locked rows missing from the feature panel: {panel_stats['missing_locked_rows'] or 'none'}.",
        f"- Latest future month used by any training label: **{panel_stats['max_train_future_month']}** "
        "(no training label uses months after 2026-05).",
        f"- Purge origins {PURGE[0]}–{PURGE[1]} were excluded from fitting, tuning and evaluation.",
        "",
        "### Features (origin t, all past-only)",
        "",
        "- `lag_0`, `lag_1`, `lag_2`: Trends values at t, t-1, t-2.",
        "- `roll3`: mean over t-2..t; `roll6`: mean over t-5..t.",
        "- `growth_1`, `growth_2`, `growth_3`: `log1p(v_month) - log1p(v_prev_month)` "
        "for consecutive pairs (t vs t-1, t-1 vs t-2, t-2 vs t-3). The +1 smoothing "
        "keeps zero-valued Trends months finite.",
        "",
        "## Artemide 2025-11 conclusion (unchanged from Step 1)",
        "",
        f"Artemide moves from **{artemide['2025-10']:.4f}** in 2025-10 to "
        f"**{artemide['2025-11']:.4f}** in 2025-11 and then **{artemide['2025-12']:.4f}** "
        "in 2025-12. Lighting peers (Flos, Louis Poulsen, Tom Dixon) do not show a comparable "
        "jump. The supplied files contain no event or definition note explaining the spike, so "
        "its cause is unknown. The observation was retained unchanged; no capping or removal was applied.",
        "",
        "## Hyperparameter tuning",
        "",
        f"Candidate alpha grid: `{ALPHA_GRID}`. Folds are formed by calendar `origin_month` "
        "and applied to all eligible brands; no shuffled K-fold and no row-wise "
        "`TimeSeriesSplit(gap=2)` were used. For validation origin v, a training origin u "
        "is included only when `u + 3 calendar months <= v`.",
        "",
    ]

    for variant in ("matched_history", "extended_history"):
        cv = cv_all[variant]
        summary = alpha_summary[variant]
        lines += [
            f"### {variant}",
            "",
            f"Chosen alpha: **{chosen[variant]:g}** (lowest mean validation MAE).",
            "",
            "| alpha | " + " | ".join(VAL_MONTHS) + " | mean val MAE |",
            "|---:|" + "---:|" * (len(VAL_MONTHS) + 1),
        ]
        for _, row in summary.iterrows():
            a = float(row["alpha"])
            cell = []
            for v in VAL_MONTHS:
                val = next(r["val_mae"] for r in cv if r["alpha"] == a and r["val_month"] == v)
                cell.append(f"{val:.6f}")
            lines.append(f"| {a:g} | " + " | ".join(cell) + f" | {row['mean_val_mae']:.6f} |")

        lines += [
            "",
            "Chosen-alpha fold details:",
            "",
            "| validation origin | latest train origin | train rows | val rows | val MAE |",
            "|---|---|---:|---:|---:|",
        ]
        for r in cv:
            if r["alpha"] == chosen[variant]:
                lines.append(
                    f"| {r['val_month']} | {r['latest_train_origin']} | "
                    f"{r['n_train_rows']} | {r['n_val_rows']} | {r['val_mae']:.6f} |"
                )
        lines.append("")

    lines += [
        "## Test-set results (identical 90 rows for every model)",
        "",
        "Persistence predicts y=0 and has no fitted training window; the schema label "
        "`matched_history` is used to denote the shared matched evaluation set.",
        "",
        "| model | training_window | MAE | Spearman 2026-05 | Spearman 2026-06 | Spearman 2026-07 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        sp = []
        for month in ("2026-05", "2026-06", "2026-07"):
            value = row[f"spearman_{month}"]
            sp.append("undefined" if value is None or (isinstance(value, float) and math.isnan(value)) else f"{value:.6f}")
        lines.append(
            f"| {row['model']} | {row['training_window']} | {row['MAE']:.6f} | "
            f"{sp[0]} | {sp[1]} | {sp[2]} |"
        )

    lines += [
        "## Limitations",
        "",
        "- Each Google Trends series is rescaled to 0–100 over its own five-year window; "
        "raw values and derived cross-brand ranks are not absolute search volumes.",
        "- Google Trends was extracted once per series; rerunning a query can produce "
        "different values. No repeat-extraction reliability study was performed.",
        "- The full-window 0–100 normalisation can reflect later peaks, so historical "
        "backtesting has a look-ahead-in-the-source limitation.",
        "- The `log(1+x)` transform is not exactly scale-invariant, especially near zero; "
        "the +1 offset does not fully remove scaling dependence.",
        "- Spearman for persistence is undefined because its predictions are constant.",
        "",
        "## Outputs",
        "",
        f"- `{PRED_OUT.relative_to(ROOT).as_posix()}`",
        f"- `{METRICS_OUT.relative_to(ROOT).as_posix()}`",
        f"- `{README_OUT.relative_to(ROOT).as_posix()}`",
        "",
    ]
    README_OUT.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    trend, targets, input_meta = load_inputs()
    panel, panel_stats = build_panel(trend, targets)

    matched_train = panel.loc[panel["split"] == "train"]
    extended_train = panel.loc[
        (panel["split"].isin(["extended_prefix", "train"])) & (panel["origin_month"] <= LAST_SAFE_ORIGIN)
    ]
    test = panel.loc[panel["split"] == "test"].sort_values(["origin_month", "slug"]).reset_index(drop=True)

    cv_all: dict[str, list[dict]] = {}
    chosen: dict[str, float] = {}
    alpha_summary: dict[str, pd.DataFrame] = {}
    preds: dict[tuple[str, str], np.ndarray] = {}

    for name, train_df in (("matched_history", matched_train), ("extended_history", extended_train)):
        cv = cv_results(train_df)
        alpha, summary = choose_alpha(cv)
        cv_all[name] = cv
        chosen[name] = alpha
        alpha_summary[name] = summary
        preds[("ridge", name)] = fit_predict(train_df, test, alpha)

    preds[("persistence", "matched_history")] = np.zeros(len(test), dtype=float)

    metrics_rows: list[dict] = []
    for (model, window), values in preds.items():
        spear = monthly_spearman(test, values)
        metrics_rows.append(
            {
                "model": model,
                "training_window": window,
                "MAE": mean_abs_error(test["y_true"].to_numpy(), values),
                "spearman_2026-05": spear["2026-05"],
                "spearman_2026-06": spear["2026-06"],
                "spearman_2026-07": spear["2026-07"],
            }
        )

    art_series = trend.loc[trend["slug"] == "artemide"].set_index("month")["trend_value"]
    artemide = {m: float(art_series[m]) for m in ("2025-10", "2025-11", "2025-12")}

    write_outputs(
        test,
        preds,
        metrics_rows,
        cv_all,
        chosen,
        alpha_summary,
        panel_stats,
        input_meta,
        artemide,
    )

    print(f"observed trend rows: {input_meta['n_observed_rows']} (excluded {input_meta['n_excluded_rows']})")
    print(f"panel rows: {panel_stats['panel_rows']}")
    print(f"matched train rows: {panel_stats['matched_train_rows']}")
    print(f"extended train rows: {panel_stats['extended_train_rows']}")
    print(f"test rows: {panel_stats['test_rows']}")
    print(f"max target discrepancy: {panel_stats['max_target_discrepancy']:.3e}")
    for name in ("matched_history", "extended_history"):
        print(f"{name}: chosen alpha={chosen[name]:g}")
        for r in cv_all[name]:
            if r["alpha"] == chosen[name]:
                print(f"  val {r['val_month']}: train={r['n_train_rows']} val={r['n_val_rows']} MAE={r['val_mae']:.6f}")
    for row in metrics_rows:
        print(f"TEST {row['model']}/{row['training_window']}: MAE={row['MAE']:.6f}")
    print(f"predictions: {PRED_OUT.relative_to(ROOT).as_posix()}")
    print(f"metrics: {METRICS_OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()

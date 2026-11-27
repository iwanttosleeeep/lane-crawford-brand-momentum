#!/usr/bin/env python3
"""Follow-up supplement A: expanded Ridge alpha search, matched history only.

Run from the repository root:

    python src/trends/ridge_expanded_alpha.py

This reuses the frozen Step 3 pipeline by importing `baseline_trends` and
changing ONLY the candidate alpha grid. The purged, origin-month-grouped
expanding-window CV, validation months, training period, features, target and
frozen 90-row test set are unchanged. Alpha is selected on validation MAE
alone; test rows are not used for selection.

If the selected alpha is still 100, no refit is performed: the existing frozen
Ridge matched-history rows are copied (read-only) into the new output files and
the report states "alpha remains 100, results unchanged".

Outputs (new paths only):
    outputs/trends/ridge_expanded_alpha_predictions.csv
    outputs/trends/ridge_expanded_alpha_metrics.csv
    outputs/trends/ridge_expanded_alpha_report.md
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import baseline_trends as bt

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "trends"
PRED_OUT = OUT_DIR / "ridge_expanded_alpha_predictions.csv"
METRICS_OUT = OUT_DIR / "ridge_expanded_alpha_metrics.csv"
REPORT_OUT = OUT_DIR / "ridge_expanded_alpha_report.md"

ORIGINAL_GRID = list(bt.ALPHA_GRID)
EXPANDED_GRID = ORIGINAL_GRID + [1000.0, 10000.0]
PREVIOUS_ALPHA = 100.0


def fmt(value: float) -> str:
    return "undefined" if not math.isfinite(value) else f"{value:.10f}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trend, targets, meta = bt.load_inputs()
    panel, stats = bt.build_panel(trend, targets)
    matched_train = panel.loc[panel["split"] == "train"].copy()

    # Selection uses only validation CV inside Jan 2025 - Feb 2026.
    bt.ALPHA_GRID = EXPANDED_GRID
    cv = bt.cv_results(matched_train)
    chosen_alpha, summary = bt.choose_alpha(cv)
    bt.ALPHA_GRID = ORIGINAL_GRID  # restore; no other script should be affected

    cv_df = pd.DataFrame(cv)
    changed = not math.isclose(chosen_alpha, PREVIOUS_ALPHA)

    test = (
        panel.loc[panel["split"] == "test"]
        .sort_values(["origin_month", "slug"])
        .reset_index(drop=True)
    )
    assert len(test) == 90

    if changed:
        y_pred = bt.fit_predict(matched_train, test, chosen_alpha)
        source = "refit on the full matched training window with the selected alpha"
    else:
        frozen = pd.read_csv(
            OUT_DIR / "baseline_predictions.csv",
            dtype={"slug": str, "origin_month": str, "model": str, "training_window": str},
        )
        ridge = frozen.loc[
            (frozen["model"] == "ridge") & (frozen["training_window"] == "matched_history")
        ].copy()
        ridge = ridge.sort_values(["origin_month", "slug"]).reset_index(drop=True)
        assert ridge[["slug", "origin_month"]].equals(test[["slug", "origin_month"]])
        y_pred = ridge["y_pred"].to_numpy(dtype=float)
        source = "copied from frozen baseline_predictions.csv (no refit)"

    y_true = test["y_true"].to_numpy(dtype=float)
    mae = bt.mean_abs_error(y_true, y_pred)
    spear = bt.monthly_spearman(test, y_pred)

    pred_df = test[["slug", "origin_month", "y_true"]].copy()
    pred_df["y_pred"] = y_pred
    pred_df["model"] = "ridge"
    pred_df["training_window"] = "matched_history"
    pred_df = pred_df[
        ["slug", "origin_month", "y_true", "y_pred", "model", "training_window"]
    ]
    pred_df.to_csv(PRED_OUT, index=False, float_format="%.10f")

    metrics_df = pd.DataFrame(
        [{
            "model": "ridge",
            "training_window": "matched_history",
            "MAE": mae,
            "spearman_2026-05": spear["2026-05"],
            "spearman_2026-06": spear["2026-06"],
            "spearman_2026-07": spear["2026-07"],
        }]
    )
    metrics_df.to_csv(METRICS_OUT, index=False, na_rep="nan", float_format="%.10f")

    per_alpha = (
        cv_df.groupby("alpha", as_index=False)["val_mae"]
        .mean()
        .rename(columns={"val_mae": "mean_val_mae"})
    )
    lines = [
        "# Follow-up supplement A — expanded Ridge alpha search (matched history)",
        "",
        "Only the candidate alpha grid changed. The purged, origin-month-grouped "
        "expanding-window CV, validation origins, Jan 2025–Feb 2026 training period, "
        "features, target and frozen 90-row test set are identical to "
        "`baseline_trends.py`. Alpha was chosen on **validation MAE only**; no test "
        "value or test-derived statistic was used for selection.",
        "",
        "## Alpha grid and validation results",
        "",
        f"- Original grid: `{ORIGINAL_GRID}`",
        f"- Expanded grid: `{EXPANDED_GRID}`",
        f"- Validation origins: `{bt.VAL_MONTHS}`; folds use only training origins "
        "whose `origin + 3 <= validation month`.",
        f"- Matched training rows: **{len(matched_train)}**.",
        "",
        "| alpha | " + " | ".join(bt.VAL_MONTHS) + " | mean val MAE |",
        "|---:|" + "---:|" * (len(bt.VAL_MONTHS) + 1),
    ]
    for _, row in summary.iterrows():
        a = float(row["alpha"])
        cells = [
            f"{r['val_mae']:.10f}"
            for r in cv
            if r["alpha"] == a and r["val_month"] in bt.VAL_MONTHS
        ]
        lines.append(f"| {a:g} | " + " | ".join(cells) + f" | {row['mean_val_mae']:.10f} |")

    lines += [
        "",
        f"**Selected alpha: {chosen_alpha:g}** (lowest mean validation MAE; "
        f"previous selection was {PREVIOUS_ALPHA:g}).",
        "",
    ]
    if not changed:
        lines += [
            "**alpha remains 100, results unchanged.** No refit was performed; the "
            "frozen Ridge matched-history predictions and metrics were copied "
            "read-only into the new output files.",
            "",
        ]
    else:
        lines += [
            "The selected alpha changed, so the model was refit on the full matched "
            "training window and re-evaluated on the frozen 90 test rows.",
            "",
        ]

    lines += [
        "## Test metrics (identical frozen 90 rows)",
        "",
        f"- Source of predictions: {source}.",
        f"- MAE: **{mae:.10f}**",
        f"- Spearman 2026-05: **{fmt(spear['2026-05'])}**",
        f"- Spearman 2026-06: **{fmt(spear['2026-06'])}**",
        f"- Spearman 2026-07: **{fmt(spear['2026-07'])}**",
        "- No exclusions: all 90 brand-origin rows were evaluated.",
        "",
        "## Run command",
        "",
        "```bash",
        "cd D:\\lane-crawford-brand-momentum",
        "python src/trends/ridge_expanded_alpha.py",
        "```",
        "",
        "## Outputs",
        "",
        f"- `{PRED_OUT.relative_to(ROOT).as_posix()}`",
        f"- `{METRICS_OUT.relative_to(ROOT).as_posix()}`",
        f"- `{REPORT_OUT.relative_to(ROOT).as_posix()}`",
        "",
        "No frozen file was modified.",
        "",
    ]
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"expanded grid: {EXPANDED_GRID}")
    print(f"selected alpha: {chosen_alpha:g} (previous {PREVIOUS_ALPHA:g})")
    print(f"changed: {changed}")
    print(f"test MAE: {mae:.10f}")
    print(f"predictions: {PRED_OUT.relative_to(ROOT).as_posix()}")
    print(f"metrics: {METRICS_OUT.relative_to(ROOT).as_posix()}")
    print(f"report: {REPORT_OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Follow-up supplement B: training-free growth-continuation baseline.

Run from the repository root:

    python src/trends/growth_continuation_baseline.py

For each frozen test origin t this baseline uses ONLY the six observed past
Google Trends months t-5..t-3 and t-2..t:

    predicted_growth = log1p(mean(GT[t-2..t])) - log1p(mean(GT[t-5..t-3]))

Arithmetic means are taken before log1p, matching the project target scale.
There is no fitted model, no training and no tuning. Persistence is untouched.

Outputs (new paths only):
    outputs/trends/baseline_predictions_extension.csv
    outputs/trends/baseline_extension_report.md
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import baseline_trends as bt

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "trends"
PRED_OUT = OUT_DIR / "baseline_predictions_extension.csv"
REPORT_OUT = OUT_DIR / "baseline_extension_report.md"


def fmt(value: float) -> str:
    return "undefined" if not math.isfinite(value) else f"{value:.10f}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trend, targets, meta = bt.load_inputs()
    series = {
        str(slug): dict(zip(group["month"], group["trend_value"]))
        for slug, group in trend.groupby("slug", sort=False)
    }
    test = (
        targets.loc[targets["split"] == "test"]
        .sort_values(["origin_month", "slug"])
        .reset_index(drop=True)
    )
    assert len(test) == 90

    rows = []
    unavailable: list[dict] = []
    for r in test.itertuples(index=False):
        slug, origin = str(r.slug), str(r.origin_month)
        need = [bt.shift(origin, d) for d in (-5, -4, -3, -2, -1, 0)]
        s = series.get(slug, {})
        if not all(m in s for m in need):
            unavailable.append({"slug": slug, "origin_month": origin, "missing": need})
            continue
        recent = [s[bt.shift(origin, d)] for d in (-2, -1, 0)]
        earlier = [s[bt.shift(origin, d)] for d in (-5, -4, -3)]
        y_pred = math.log1p(float(np.mean(recent))) - math.log1p(float(np.mean(earlier)))
        rows.append({
            "slug": slug,
            "origin_month": origin,
            "y_true": float(r.target_growth),
            "y_pred": y_pred,
            "model": "growth_continuation",
        })

    usable = pd.DataFrame(rows)
    assert len(usable) + len(unavailable) == 90
    y_true = usable["y_true"].to_numpy(dtype=float)
    y_pred = usable["y_pred"].to_numpy(dtype=float)
    mae = bt.mean_abs_error(y_true, y_pred)
    spear = bt.monthly_spearman(usable, y_pred)

    pred_df = usable[["slug", "origin_month", "y_true", "y_pred", "model"]]
    pred_df.to_csv(PRED_OUT, index=False, float_format="%.10f")

    if unavailable:
        subset_note = (
            f"**{len(unavailable)} rows could not be computed** and are excluded. "
            "All comparators must be restricted to the identical computable subset; "
            "see the table below."
        )
    else:
        subset_note = (
            "**All 90 rows were computable** (t-5..t present for every brand-origin), "
            "so this baseline is directly comparable with the frozen 90-row results "
            "of every other model. No subset restriction is needed."
        )

    lines = [
        "# Follow-up supplement B — growth-continuation baseline",
        "",
        "A training-free baseline added because per-month cross-brand Spearman is "
        "undefined for the constant-zero persistence predictions. Persistence itself "
        "is untouched.",
        "",
        "## Fixed rule (identical for every test row)",
        "",
        "```text",
        "predicted_growth = log1p(mean(GT[t-2..t])) - log1p(mean(GT[t-5..t-3]))",
        "```",
        "",
        "- Both means are arithmetic means taken **before** `log1p`, matching the "
        "project target definition.",
        "- Only observed months `t-5..t` are used. No future GT value, target column "
        "or test outcome is used as input.",
        "- No fitting, tuning or model selection is performed.",
        "",
        "## Data availability",
        "",
        f"- Test rows checked: **{len(test)}**; origins: "
        f"`{', '.join(sorted(test['origin_month'].unique()))}`.",
        "",
        subset_note,
    ]
    if unavailable:
        lines += [
            "",
            "| slug | origin_month | required months |",
            "|---|---|---|",
        ]
        for u in unavailable:
            lines.append(f"| {u['slug']} | {u['origin_month']} | {', '.join(u['missing'])} |")

    lines += [
        "",
        "## Test metrics",
        "",
        f"- Evaluated rows: **{len(usable)}**.",
        f"- MAE: **{mae:.10f}**",
        f"- Spearman 2026-05: **{fmt(spear['2026-05'])}**",
        f"- Spearman 2026-06: **{fmt(spear['2026-06'])}**",
        f"- Spearman 2026-07: **{fmt(spear['2026-07'])}**",
        "",
        "## Run command",
        "",
        "```bash",
        "cd D:\\lane-crawford-brand-momentum",
        "python src/trends/growth_continuation_baseline.py",
        "```",
        "",
        "## Outputs",
        "",
        f"- `{PRED_OUT.relative_to(ROOT).as_posix()}`",
        f"- `{REPORT_OUT.relative_to(ROOT).as_posix()}`",
        "",
        "No frozen file was modified; persistence predictions remain unchanged.",
        "",
    ]
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"unavailable rows: {len(unavailable)}")
    print(f"test MAE: {mae:.10f}")
    for month in ("2026-05", "2026-06", "2026-07"):
        print(f"Spearman {month}: {fmt(spear[month])}")
    print(f"predictions: {PRED_OUT.relative_to(ROOT).as_posix()}")
    print(f"report: {REPORT_OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()

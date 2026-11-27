#!/usr/bin/env python3
"""B extension, Priority 3 (optional): descriptive momentum change-point notes.

Run from the repository root:

    python src/trends/momentum_shift_notes.py

This is a RETROSPECTIVE DESCRIPTIVE analysis, not an ex-ante forecast and not a
change to the frozen target, split or baseline outputs. A single CUSUM rule is
applied uniformly to all 30 brands.

Predeclared rule (fixed before examining any result)
----------------------------------------------------
1. Use cleaned monthly `trend_value` from `trends_monthly.csv`, excluding the
   flagged incomplete `2026-11` month. Values are in each series' own 0-100 scale.
2. Growth observation g_t = log1p(v_t) - log1p(v_(t-1)) for consecutive months.
3. Standardised observation z_t = g_t / 0.25. The scale 0.25 is a fixed common
   constant for every brand; nothing is fitted per brand.
4. Two-sided CUSUM with zero reference/drift target:
       S+_t = max(0, S+_(t-1) + z_t - 0.5)
       S-_t = max(0, S-_(t-1) - z_t - 0.5)
   starting at S+ = S- = 0.
5. A change point is recorded at the first month where S+ or S- exceeds the
   fixed threshold h = 5.0. After a detection both accumulators reset to 0 and
   a 3-month cooldown is enforced before another detection may be recorded.
6. The same constants (0.25, 0.5, 5.0, cooldown 3) are used for all brands.

Outputs (new paths only):
    outputs/trends/momentum_shift_notes.md
    outputs/trends/figures/momentum_<slug>.png
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "trends"
FIG_DIR = OUT_DIR / "figures"
TRENDS_CSV = OUT_DIR / "trends_monthly.csv"
FLAGS_CSV = OUT_DIR / "trends_monthly_flags.csv"
NOTES_OUT = OUT_DIR / "momentum_shift_notes.md"

SCALE = 0.25
DRIFT = 0.5
THRESHOLD = 5.0
COOLDOWN = 3
ILLUSTRATIVE = ("artemide", "louis-poulsen", "jo-malone-london")


def midx(month: str) -> int:
    y, m = (int(x) for x in month.split("-"))
    return y * 12 + m - 1


def incomplete_months() -> set[str]:
    months = {"2026-11"}
    if FLAGS_CSV.exists():
        flags = pd.read_csv(FLAGS_CSV, dtype=str)
        if {"month", "flag"}.issubset(flags.columns):
            months.update(flags.loc[flags["flag"].str.lower() == "incomplete", "month"].tolist())
    return months


def detect(months: list[str], values: np.ndarray) -> list[dict]:
    """Fixed two-sided CUSUM; returns (month, direction, accumulator, value)."""
    sp = sm = 0.0
    detections: list[dict] = []
    cooldown_left = 0
    for i in range(1, len(values)):
        g = math.log1p(values[i]) - math.log1p(values[i - 1])
        z = g / SCALE
        sp = max(0.0, sp + z - DRIFT)
        sm = max(0.0, sm - z - DRIFT)
        if cooldown_left > 0:
            cooldown_left -= 1
            continue
        if sp > THRESHOLD or sm > THRESHOLD:
            direction = "up" if sp > THRESHOLD else "down"
            acc = sp if direction == "up" else sm
            detections.append({
                "month": months[i],
                "direction": direction,
                "accumulator": acc,
                "value": float(values[i]),
            })
            sp = sm = 0.0
            cooldown_left = COOLDOWN
    return detections


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    excl = incomplete_months()
    trend = pd.read_csv(TRENDS_CSV, dtype={"slug": str, "month": str, "trend_value": str})
    trend["trend_value"] = trend["trend_value"].astype(float)
    trend = trend.loc[~trend["month"].isin(excl)].copy()

    all_detections: dict[str, list[dict]] = {}
    plotted_values: dict[str, tuple[list[str], np.ndarray]] = {}
    for slug, group in trend.groupby("slug", sort=True):
        group = group.sort_values("month")
        months = group["month"].tolist()
        values = group["trend_value"].to_numpy(dtype=float)
        all_detections[str(slug)] = detect(months, values)
        plotted_values[str(slug)] = (months, values)

    total = sum(len(v) for v in all_detections.values())
    lines = [
        "# B extension — Priority 3: descriptive momentum change-point notes",
        "",
        "**Optional supplementary analysis.** This is retrospective detection on the "
        "already-cleaned Google Trends series. It is **not an ex-ante forecast**, does "
        "not change the frozen 90-row holdout, and is not evidence of the cause of any "
        "observed spike.",
        "",
        "## Predeclared method (fixed before examining results)",
        "",
        "- Input: cleaned monthly `trend_value` from `trends_monthly.csv`, excluding the "
        "flagged incomplete `2026-11` month.",
        "- Growth: `g_t = log1p(v_t) - log1p(v_(t-1))`; standardised `z_t = g_t / 0.25` "
        "with a fixed common scale for all brands (no per-brand fitting).",
        "- Two-sided CUSUM with zero reference: `S+_t = max(0, S+_(t-1) + z_t - 0.5)`, "
        "`S-_t = max(0, S-_(t-1) - z_t - 0.5)`, starting at zero.",
        "- Detection when `S+` or `S-` exceeds `h = 5.0`; then both accumulators reset "
        "and a 3-month cooldown applies. Identical constants for all 30 brands.",
        "",
        "## Results across all 30 brands",
        "",
        f"- Total detected change points: **{total}**.",
        f"- Brands with at least one detection: **{sum(bool(v) for v in all_detections.values())}** "
        "of 30.",
        "",
        "| slug | detections | months and direction |",
        "|---|---:|---|",
    ]
    for slug in sorted(all_detections):
        det = all_detections[slug]
        desc = ", ".join(f"{d['month']} ({d['direction']})" for d in det) if det else "none"
        lines.append(f"| {slug} | {len(det)} | {desc} |")

    lines += [
        "",
        "## Illustrative examples",
        "",
        "The three brands below are illustrative charts of the same uniform rule; "
        "they are not selected as predictions and are not claimed to be representative "
        "of all brands.",
        "",
    ]
    for slug in ILLUSTRATIVE:
        months, values = plotted_values[slug]
        det = all_detections.get(slug, [])
        fig_path = FIG_DIR / f"momentum_{slug}.png"
        fig, ax = plt.subplots(figsize=(10, 4.2))
        ax.plot(months, values, marker="o", linewidth=1.4, markersize=3, color="#1f4e79")
        for d in det:
            if d["month"] in months:
                ax.axvline(d["month"], color="#c00000" if d["direction"] == "up" else "#7f6000",
                           linestyle="--", linewidth=1.2, alpha=0.8)
                ax.annotate(f"{d['month']}\n{d['value']:.1f}",
                            (d["month"], d["value"]), fontsize=7,
                            xytext=(0, 8), textcoords="offset points", ha="center")
        ax.set_title(f"{slug}: monthly Google Trends value with predeclared CUSUM detections")
        ax.set_ylabel("trend_value (series-specific 0-100)")
        ax.set_xlabel("month")
        ax.tick_params(axis="x", labelrotation=90, labelsize=7)
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(fig_path, dpi=130)
        plt.close(fig)

        detail = "none" if not det else "; ".join(
            f"{d['month']}: {d['direction']}, value {d['value']:.4f}, accumulator {d['accumulator']:.2f}"
            for d in det
        )
        lines += [
            f"### {slug}",
            "",
            f"Detections: {detail}.",
            "",
            f"![{slug} CUSUM chart](figures/momentum_{slug}.png)",
            "",
        ]

    lines += [
        "## Caveats",
        "",
        "- Each Google Trends series is independently rescaled to 0–100 over the full "
        "extraction window, so later peaks affect earlier values. A retrospective "
        "change point can partly reflect that source-side rescaling and one-off "
        "Google Trends sampling, not a real-world behavioural shift.",
        "- The fixed scale, drift, threshold and cooldown are descriptive choices, "
        "not fitted or optimised for forecast performance. A different threshold "
        "would produce different detections; the rule was not tuned on outcomes.",
        "- Seasonal peaks (e.g. holiday months) can trigger the rule. Detections are "
        "associations in observed data, not causes and not ex-ante signals.",
        "- The Artemide 2025-11 jump is visible in the source series, but the supplied "
        "files contain no event or definition information. **No cause is claimed**; "
        "the spike was retained unchanged in all frozen outputs.",
        "- HK data were not available (Google Trends API HTTP 429; see "
        "`hk_coverage_report.md`), so this analysis uses the existing provenance-"
        "unverified series only.",
        "",
        "## Run command",
        "",
        "```bash",
        "cd D:\\lane-crawford-brand-momentum",
        "python src/trends/momentum_shift_notes.py",
        "```",
        "",
        "The script writes only `outputs/trends/momentum_shift_notes.md` and new figures "
        "under `outputs/trends/figures/`; no frozen file is modified.",
        "",
    ]
    NOTES_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"detections: {total} across 30 brands")
    print(f"notes: {NOTES_OUT.relative_to(ROOT).as_posix()}")
    print(f"figures: {FIG_DIR.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()

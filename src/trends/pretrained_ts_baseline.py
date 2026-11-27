#!/usr/bin/env python3
"""B extension, Priority 1: zero-shot pretrained time-series benchmark.

Run from the repository root (after `pip install chronos-forecasting`):

    python src/trends/pretrained_ts_baseline.py

This script is INFERENCE ONLY. It loads genuine pretrained Amazon Chronos
weights (`amazon/chronos-t5-small`, revision pinned below), forecasts the three
months after each frozen test origin using only that brand's own past
`trend_value` observations, converts the forecasts to the project's
`target_growth` scale, and evaluates on the unchanged 90-row May-Jul 2026
holdout in `outputs/trends/targets_and_split.csv`.

No fitting, fine-tuning, prompt tuning or hyperparameter search is performed.
The model, decoding settings and negative-value rule below were FIXED BEFORE
any held-out metric was computed; they are not tuned on the test set.

Inputs (read-only)
------------------
outputs/trends/trends_monthly.csv
outputs/trends/trends_monthly_flags.csv
outputs/trends/targets_and_split.csv
outputs/trends/baseline_metrics.csv   (reference figures only)

Outputs (new paths only)
------------------------
outputs/trends/pretrained_ts_predictions.csv
outputs/trends/pretrained_ts_report.md

Environment used for the recorded run: Python 3.11.8, torch 2.14.1+cpu,
transformers 5.20.2, chronos-forecasting 2.3.2, device cpu.

------------------------------------------------------------------------------
PREDECLARED NEGATIVE-PREDICTION RULE (fixed before examining test metrics)
------------------------------------------------------------------------------
Google Trends values are defined on [0, 100]. Chronos emits unconstrained
real-valued forecasts, so a sample path may contain negative values or values
above 100. The fixed rule is:

    clip each predicted monthly GT value to the closed interval [0, 100]
    BEFORE taking the arithmetic mean of t+1, t+2, t+3.

No alternative clipping, flooring, rescaling or sample-selection rule was
tried. The denominator always uses the ACTUAL past Google Trends values at
t-2, t-1, t from the frozen source; it is never forecast or clipped.
------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
import math
import platform
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "trends"

TRENDS_CSV = OUT_DIR / "trends_monthly.csv"
FLAGS_CSV = OUT_DIR / "trends_monthly_flags.csv"
TARGETS_CSV = OUT_DIR / "targets_and_split.csv"
BASELINE_METRICS_CSV = OUT_DIR / "baseline_metrics.csv"

PRED_OUT = OUT_DIR / "pretrained_ts_predictions.csv"
REPORT_OUT = OUT_DIR / "pretrained_ts_report.md"

# ---------------------------------------------------------------------------
# Fixed model / inference configuration (pre-registered, not tuned)
# ---------------------------------------------------------------------------
CHECKPOINT = "amazon/chronos-t5-small"
CHECKPOINT_REVISION = "a971ba21945c4f1796b17a91fe69214b5f4ad472"
MODEL_LABEL = "chronos-t5-small"
DEVICE = "cpu"
TORCH_DTYPE = torch.float32
CONTEXT_LENGTH = 512  # from the pinned checkpoint's chronos_config
PREDICTION_LENGTH = 3
NUM_SAMPLES = 1
TEMPERATURE = 1.0  # inert under greedy top_k=1 decoding
TOP_K = 1          # greedy: selects the highest-probability token
TOP_P = 1.0
SEED = 42
CLIP_LOW, CLIP_HIGH = 0.0, 100.0
TEST_ORIGINS = ("2026-05", "2026-06", "2026-07")
EXPECTED_TEST_ROWS = 90


# ---------------------------------------------------------------------------
# calendar helpers (same month arithmetic as the frozen Step 2/3 scripts)
# ---------------------------------------------------------------------------
def midx(month: str) -> int:
    year, mon = (int(part) for part in month.split("-"))
    return year * 12 + (mon - 1)


def mstr(idx: int) -> str:
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def shift(month: str, delta: int) -> str:
    return mstr(midx(month) + delta)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def incomplete_months() -> set[str]:
    """Months excluded by the frozen Step 1 cleaning decision."""
    months = {"2026-11"}
    if FLAGS_CSV.exists():
        flags = pd.read_csv(FLAGS_CSV, dtype=str)
        if {"month", "flag"}.issubset(flags.columns):
            months.update(
                flags.loc[flags["flag"].str.lower() == "incomplete", "month"].tolist()
            )
    return set(months)


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------
def load_inputs() -> tuple[dict[str, dict[str, float]], pd.DataFrame, dict]:
    excl = incomplete_months()
    trend = pd.read_csv(
        TRENDS_CSV,
        dtype={"slug": str, "month": str, "trend_value": str, "valid_from": str},
    )
    trend["trend_value"] = trend["trend_value"].astype(float)
    n_input = len(trend)
    n_excluded = int(trend["month"].isin(excl).sum())
    trend = trend.loc[~trend["month"].isin(excl)].copy()
    n_duplicate_keys = int(trend.duplicated(["slug", "month"]).sum())
    trend = trend.drop_duplicates(["slug", "month"], keep="first")

    series: dict[str, dict[str, float]] = {
        slug: dict(zip(group["month"], group["trend_value"]))
        for slug, group in trend.groupby("slug", sort=False)
    }

    targets = pd.read_csv(
        TARGETS_CSV,
        dtype={"slug": str, "origin_month": str, "target_growth": str, "split": str},
    )
    targets["target_growth"] = targets["target_growth"].astype(float)
    test = targets.loc[targets["split"] == "test"].copy()
    test = test.sort_values(["origin_month", "slug"]).reset_index(drop=True)
    test["y_true"] = test["target_growth"].astype(float)

    assert len(test) == EXPECTED_TEST_ROWS, f"expected 90 test rows, got {len(test)}"
    assert tuple(sorted(test["origin_month"].unique())) == TEST_ORIGINS
    assert not test.duplicated(["slug", "origin_month"]).any()
    assert test["slug"].nunique() == 30
    assert np.isfinite(test["target_growth"]).all()

    meta = {
        "excluded_months": sorted(excl),
        "n_input_rows": n_input,
        "n_excluded_rows": n_excluded,
        "n_duplicate_keys": n_duplicate_keys,
        "n_observed_rows": len(trend),
        "n_slugs": len(series),
        "trends_sha256": sha256(TRENDS_CSV),
        "targets_sha256": sha256(TARGETS_CSV),
        "flags_sha256": sha256(FLAGS_CSV) if FLAGS_CSV.exists() else "n/a",
    }
    return series, test, meta


def build_contexts(
    series: dict[str, dict[str, float]], test: pd.DataFrame
) -> tuple[list[torch.Tensor], list[dict]]:
    """For each frozen test row, build a past-only context ending at origin t."""
    contexts: list[torch.Tensor] = []
    info: list[dict] = []
    for row in test.itertuples(index=False):
        slug, origin = str(row.slug), str(row.origin_month)
        s = series.get(slug, {})
        past_months = sorted(m for m in s if midx(m) <= midx(origin))
        past = [s[m] for m in past_months]
        if len(past) < 3:
            raise RuntimeError(f"{slug} {origin}: fewer than 3 past months available")
        # Denominator months t-2, t-1, t must be observed actual GT values.
        denom_months = [shift(origin, d) for d in (-2, -1, 0)]
        if not all(m in s for m in denom_months):
            raise RuntimeError(f"{slug} {origin}: missing denominator months {denom_months}")
        denom = [s[m] for m in denom_months]

        used_months = past_months[-CONTEXT_LENGTH:]
        used = past[-CONTEXT_LENGTH:]
        ctx = torch.tensor(used, dtype=torch.float32)  # 1-D; Chronos left-pads a list
        contexts.append(ctx)
        info.append(
            {
                "slug": slug,
                "origin_month": origin,
                "context_first": used_months[0],
                "context_last": used_months[-1],
                "context_len": len(used),
                "denom": denom,
            }
        )
    return contexts, info


def convert(
    raw: np.ndarray, denom: list[float]
) -> tuple[float, float, float]:
    """Predeclared clip to [0,100], then arithmetic-mean-before-log1p conversion."""
    clipped = np.clip(raw, CLIP_LOW, CLIP_HIGH)
    pred_mean = float(np.mean(clipped))
    past_mean = float(np.mean(denom))
    y_pred = math.log1p(pred_mean) - math.log1p(past_mean)
    return y_pred, pred_mean, past_mean


# ---------------------------------------------------------------------------
# metrics / report
# ---------------------------------------------------------------------------
def monthly_spearman(test: pd.DataFrame, y_pred: np.ndarray) -> dict[str, float]:
    out: dict[str, float] = {}
    for month in TEST_ORIGINS:
        mask = test["origin_month"].to_numpy() == month
        yt, yp = test.loc[mask, "y_true"].to_numpy(), np.asarray(y_pred)[mask]
        if len(yt) < 2 or np.allclose(yp, yp[0]):
            out[month] = float("nan")
        else:
            out[month] = float(spearmanr(yt, yp).statistic)
    return out


def fmt(value: float) -> str:
    return "undefined" if not math.isfinite(value) else f"{value:.6f}"


def write_report(
    test: pd.DataFrame,
    y_pred: np.ndarray,
    info: list[dict],
    stats: dict,
    meta: dict,
    raw_samples: np.ndarray,
    clipped_samples: np.ndarray,
) -> None:
    mae = float(np.mean(np.abs(test["y_true"].to_numpy() - y_pred)))
    spear = monthly_spearman(test, y_pred)

    refs = pd.read_csv(BASELINE_METRICS_CSV)
    ref_lines = []
    for _, r in refs.iterrows():
        ref_lines.append(
            f"| {r['model']} / {r['training_window']} | {float(r['MAE']):.6f} | "
            f"{fmt(float(r['spearman_2026-05']))} | {fmt(float(r['spearman_2026-06']))} | "
            f"{fmt(float(r['spearman_2026-07']))} |"
        )

    context_lens = [i["context_len"] for i in info]
    lines = [
        "# B extension — Priority 1: zero-shot pretrained time-series benchmark",
        "",
        "This is a **supplementary zero-shot pretrained benchmark**, not a change to the "
        "frozen Trends target, split or baseline outputs, and not a matched-training-data "
        "ablation for the effect of visual features.",
        "",
        "## Model and fixed settings (pre-registered before test evaluation)",
        "",
        f"- Model: **{CHECKPOINT}** (genuine pretrained T5-based Chronos weights), "
        f"revision `{CHECKPOINT_REVISION}`.",
        f"- Package: `chronos-forecasting=={_version('chronos')}`; "
        f"torch `{_version('torch')}`; transformers `{_version('transformers')}`; "
        f"Python `{platform.python_version()}`.",
        f"- Device: `{DEVICE}`, dtype `{TORCH_DTYPE}`. No GPU, no fine-tuning, inference only.",
        f"- Model context length: **{CONTEXT_LENGTH}** months; horizon **{PREDICTION_LENGTH}** months.",
        f"- Decoding: `num_samples={NUM_SAMPLES}`, `top_k={TOP_K}` (greedy), "
        f"`top_p={TOP_P}`, `temperature={TEMPERATURE}` (inert under greedy decoding).",
        f"- Random seed: `{SEED}` (set for `random`, `numpy` and `torch`; greedy decoding is deterministic).",
        "- At origin `t`, input is **only** that brand's own observed `trend_value` values at "
        "months `<= t`, in chronological order. No future Google Trends values, no `target_growth`, "
        "no test outcomes and no other brand's series are supplied to the model.",
        "- The incomplete `2026-11` observations (flagged in Step 1) are excluded. They are later "
        "than every test origin in any case.",
        "",
        "### Predeclared negative-value rule",
        "",
        "Google Trends is defined on `[0, 100]`, while Chronos outputs unconstrained real values. "
        "**Fixed rule, chosen before any test metric was computed:** each predicted monthly value "
        f"is clipped to `[{CLIP_LOW:.0f}, {CLIP_HIGH:.0f}]` before the arithmetic mean of "
        "`t+1, t+2, t+3` is taken. No alternative rule was tried or selected using the holdout.",
        "",
        "### Target conversion",
        "",
        "```text",
        "pred_GT_clipped[m] = clip(chronos_prediction[m], 0, 100)   for m in t+1, t+2, t+3",
        "y_pred = log1p(mean(pred_GT_clipped[t+1:t+3])) - log1p(mean(actual_GT[t-2:t]))",
        "```",
        "",
        "The arithmetic mean is taken **before** `log1p`; the denominator uses the actual past "
        "Google Trends values from the frozen source. `y_true` is the untouched `target_growth` "
        "from `targets_and_split.csv`.",
        "",
        "## Coverage",
        "",
        f"- Frozen input rows: `{meta['n_excluded_rows']}` excluded as incomplete; "
        f"`{meta['n_observed_rows']}` observed rows across `{meta['n_slugs']}` brands.",
        f"- Forecasts produced: **{len(test)} / {EXPECTED_TEST_ROWS}** frozen test rows; "
        f"exclusions: **{EXPECTED_TEST_ROWS - len(test)}**.",
        f"- All 30 brands and all three origins `{', '.join(TEST_ORIGINS)}` are covered; "
        "no subset comparators are needed because no row was dropped.",
        f"- Past context length per forecast: min `{min(context_lens)}`, max `{max(context_lens)}` "
        f"months (well below the model's {CONTEXT_LENGTH}-month limit).",
        f"- Raw (unclipped) prediction range: `[{raw_samples.min():.4f}, {raw_samples.max():.4f}]`; "
        f"after clipping: `[{clipped_samples.min():.4f}, {clipped_samples.max():.4f}]`.",
        "",
        "## Held-out results (identical frozen 90 rows)",
        "",
        "| model | MAE | Spearman 2026-05 | Spearman 2026-06 | Spearman 2026-07 |",
        "|---|---:|---:|---:|---:|",
        f"| {MODEL_LABEL} (zero-shot) | {mae:.6f} | {fmt(spear['2026-05'])} | "
        f"{fmt(spear['2026-06'])} | {fmt(spear['2026-07'])} |",
        "",
        "Existing reference figures (from frozen `baseline_metrics.csv`, not expected outcomes "
        "for this model):",
        "",
        "| model / window | MAE | Spearman 2026-05 | Spearman 2026-06 | Spearman 2026-07 |",
        "|---|---:|---:|---:|---:|",
        *ref_lines,
        "",
        "## Limitations",
        "",
        "- Chronos was **pretrained externally** on a large, unrelated time-series corpus. "
        "It is not a matched-data ablation: it cannot isolate the value of Instagram CLIP/YOLO/OCR "
        "visual features, and extra models are not automatically better.",
        "- Each Google Trends series was rescaled to 0–100 over its own full extraction window. "
        "Later peaks therefore affect earlier values: historical backtesting has a "
        "look-ahead-in-the-source limitation that this benchmark inherits.",
        "- Google Trends sampling and one-off extraction mean the series are not exactly "
        "reproducible; a repeat query may return different values.",
        "- The model sees only 0–100 search-interest values, with no brand identity, category, "
        "seasonality covariates or image features. `y_pred` is a within-brand search-interest "
        "change, not predicted sales or a composite Brand Momentum Index.",
        "- Greedy decoding removes sampling randomness but does not make the model deterministic "
        "across package/hardware versions; the pinned checkpoint revision and package versions "
        "are recorded above.",
        "",
        "## Run command",
        "",
        "```bash",
        "cd D:\\lane-crawford-brand-momentum",
        "python -m pip install chronos-forecasting",
        "python src/trends/pretrained_ts_baseline.py",
        "```",
        "",
        "## Input provenance (SHA-256 of frozen files read by this script)",
        "",
        f"- `trends_monthly.csv`: `{meta['trends_sha256']}`",
        f"- `targets_and_split.csv`: `{meta['targets_sha256']}`",
        f"- `trends_monthly_flags.csv`: `{meta['flags_sha256']}`",
        "",
        "## Outputs",
        "",
        f"- `{PRED_OUT.relative_to(ROOT).as_posix()}`",
        f"- `{REPORT_OUT.relative_to(ROOT).as_posix()}`",
        "",
    ]
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    return mae


def _version(module_name: str) -> str:
    try:
        module = __import__(module_name)
        return getattr(module, "__version__", "unknown")
    except Exception:
        return "not installed"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(1)  # deterministic CPU execution

    from chronos import ChronosPipeline

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    series, test, meta = load_inputs()
    contexts, info = build_contexts(series, test)

    print(
        f"loading {CHECKPOINT}@{CHECKPOINT_REVISION[:8]} on {DEVICE} "
        f"(context={CONTEXT_LENGTH}, horizon={PREDICTION_LENGTH})"
    )
    pipeline = ChronosPipeline.from_pretrained(
        CHECKPOINT,
        revision=CHECKPOINT_REVISION,
        device_map=DEVICE,
        torch_dtype=TORCH_DTYPE,
    )
    cfg = pipeline.model.config
    assert cfg.context_length == CONTEXT_LENGTH
    assert cfg.prediction_length >= PREDICTION_LENGTH

    # One batched inference call for all 90 origins; Chronos left-pads contexts.
    samples = pipeline.predict(
        contexts,
        prediction_length=PREDICTION_LENGTH,
        num_samples=NUM_SAMPLES,
        temperature=TEMPERATURE,
        top_k=TOP_K,
        top_p=TOP_P,
    )
    raw = samples.numpy().reshape(len(test), NUM_SAMPLES, PREDICTION_LENGTH)
    raw = raw[:, 0, :]  # greedy => single path
    assert raw.shape == (len(test), PREDICTION_LENGTH)
    assert np.isfinite(raw).all(), "non-finite Chronos output"

    clipped = np.clip(raw, CLIP_LOW, CLIP_HIGH)
    y_pred = np.empty(len(test), dtype=float)
    for i, row_info in enumerate(info):
        value, _, _ = convert(raw[i], row_info["denom"])
        y_pred[i] = value

    pred_df = test[["slug", "origin_month", "y_true"]].copy()
    pred_df["y_pred"] = y_pred
    pred_df["model"] = MODEL_LABEL
    pred_df = pred_df[["slug", "origin_month", "y_true", "y_pred", "model"]]
    pred_df.to_csv(PRED_OUT, index=False, float_format="%.10f")

    mae = write_report(test, y_pred, info, {}, meta, raw, clipped)

    print(f"forecast rows: {len(pred_df)} / {EXPECTED_TEST_ROWS}")
    print(f"held-out MAE: {mae:.6f}")
    for month, value in monthly_spearman(test, y_pred).items():
        print(f"  Spearman {month}: {fmt(value)}")
    print(f"predictions: {PRED_OUT.relative_to(ROOT).as_posix()}")
    print(f"report: {REPORT_OUT.relative_to(ROOT).as_posix()}")
    print("frozen baseline files were not modified")


if __name__ == "__main__":
    main()

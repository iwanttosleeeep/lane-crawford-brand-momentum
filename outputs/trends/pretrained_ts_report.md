# B extension — Priority 1: zero-shot pretrained time-series benchmark

This is a **supplementary zero-shot pretrained benchmark**, not a change to the frozen Trends target, split or baseline outputs, and not a matched-training-data ablation for the effect of visual features.

## Model and fixed settings (pre-registered before test evaluation)

- Model: **amazon/chronos-t5-small** (genuine pretrained T5-based Chronos weights), revision `a971ba21945c4f1796b17a91fe69214b5f4ad472`.
- Package: `chronos-forecasting==2.3.2`; torch `2.14.1+cpu`; transformers `5.20.2`; Python `3.11.8`.
- Device: `cpu`, dtype `torch.float32`. No GPU, no fine-tuning, inference only.
- Model context length: **512** months; horizon **3** months.
- Decoding: `num_samples=1`, `top_k=1` (greedy), `top_p=1.0`, `temperature=1.0` (inert under greedy decoding).
- Random seed: `42` (set for `random`, `numpy` and `torch`; greedy decoding is deterministic).
- At origin `t`, input is **only** that brand's own observed `trend_value` values at months `<= t`, in chronological order. No future Google Trends values, no `target_growth`, no test outcomes and no other brand's series are supplied to the model.
- The incomplete `2026-11` observations (flagged in Step 1) are excluded. They are later than every test origin in any case.

### Predeclared negative-value rule

Google Trends is defined on `[0, 100]`, while Chronos outputs unconstrained real values. **Fixed rule, chosen before any test metric was computed:** each predicted monthly value is clipped to `[0, 100]` before the arithmetic mean of `t+1, t+2, t+3` is taken. No alternative rule was tried or selected using the holdout.

### Target conversion

```text
pred_GT_clipped[m] = clip(chronos_prediction[m], 0, 100)   for m in t+1, t+2, t+3
y_pred = log1p(mean(pred_GT_clipped[t+1:t+3])) - log1p(mean(actual_GT[t-2:t]))
```

The arithmetic mean is taken **before** `log1p`; the denominator uses the actual past Google Trends values from the frozen source. `y_true` is the untouched `target_growth` from `targets_and_split.csv`.

## Coverage

- Frozen input rows: `30` excluded as incomplete; `1797` observed rows across `30` brands.
- Forecasts produced: **90 / 90** frozen test rows; exclusions: **0**.
- All 30 brands and all three origins `2026-05, 2026-06, 2026-07` are covered; no subset comparators are needed because no row was dropped.
- Past context length per forecast: min `52`, max `57` months (well below the model's 512-month limit).
- Raw (unclipped) prediction range: `[5.9986, 125.8500]`; after clipping: `[5.9986, 100.0000]`.

## Held-out results (identical frozen 90 rows)

| model | MAE | Spearman 2026-05 | Spearman 2026-06 | Spearman 2026-07 |
|---|---:|---:|---:|---:|
| chronos-t5-small (zero-shot) | 0.191987 | 0.174638 | 0.418910 | 0.615573 |

Existing reference figures (from frozen `baseline_metrics.csv`, not expected outcomes for this model):

| model / window | MAE | Spearman 2026-05 | Spearman 2026-06 | Spearman 2026-07 |
|---|---:|---:|---:|---:|
| Ridge matched-history (expanded alpha=100) | 0.203914 | 0.218242 | 0.527475 | 0.573749 |
| ridge / extended_history | 0.189297 | 0.293437 | 0.544383 | 0.616463 |
| persistence / matched_history | 0.229590 | undefined | undefined | undefined |
| growth_continuation (no training) | 0.404265 | -0.527920 | -0.662291 | -0.147052 |

## Limitations

- Chronos was **pretrained externally** on a large, unrelated time-series corpus. It is not a matched-data ablation: it cannot isolate the value of Instagram CLIP/YOLO/OCR visual features, and extra models are not automatically better.
- Each Google Trends series was rescaled to 0–100 over its own full extraction window. Later peaks therefore affect earlier values: historical backtesting has a look-ahead-in-the-source limitation that this benchmark inherits.
- Google Trends sampling and one-off extraction mean the series are not exactly reproducible; a repeat query may return different values.
- The model sees only 0–100 search-interest values, with no brand identity, category, seasonality covariates or image features. `y_pred` is a within-brand search-interest change, not predicted sales or a composite Brand Momentum Index.
- Greedy decoding removes sampling randomness but does not make the model deterministic across package/hardware versions; the pinned checkpoint revision and package versions are recorded above.

## Run command

```bash
cd D:\lane-crawford-brand-momentum
python -m pip install chronos-forecasting
python src/trends/pretrained_ts_baseline.py
```

## Input provenance (SHA-256 of frozen files read by this script)

- `trends_monthly.csv`: `5a12dfb011d39a4acde546d8ef817b565bb4e65bc6da76adc294d593356d6324`
- `targets_and_split.csv`: `f123e2f644f21f9752033d0ca847187af4a9b3e09072846e362bbe47238747e5`
- `trends_monthly_flags.csv`: `52874ccd70e564c2ebac28f1c1073810f9a1986a5d50f4e9fc7bc89c73e6ddcf`

## Outputs

- `outputs/trends/pretrained_ts_predictions.csv`
- `outputs/trends/pretrained_ts_report.md`

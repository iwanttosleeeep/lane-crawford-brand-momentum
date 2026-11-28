# Member B — Trends-only baselines

## Run

```bash
python src/trends/clean_trends.py
python src/trends/build_targets_split.py
python src/trends/baseline_trends.py
```

Environment: Python 3.11 with pandas, numpy, scipy and scikit-learn. This script uses only the two named CSV inputs and writes the three outputs below.

## Data coverage

- Input `trends_monthly.csv` rows: **1827**; removed incomplete `2026-11`: **30**; observed rows used: **1797**.
- Brands: **30**. Duplicate `(slug, month)` keys in input: **0**.
- Locked rows in `targets_and_split.csv`: **570** (420 train / 60 purge / 90 test in Step 2).
- Constructed feature/target panel rows: **1557** (extended pre-2025 prefix **987**, matched train **420**, purge **60**, test **90**).
- Extended-prefix origins: **2022-04 … 2024-12**; extended training rows in total: **1407**.
- Max target discrepancy between supplied `target_growth` and recomputation from `trends_monthly.csv`: **4.974e-11**.
- Locked rows missing from the feature panel: none.
- Latest future month used by any training label: **2026-05** (no training label uses months after 2026-05).
- Purge origins 2026-03–2026-04 were excluded from fitting, tuning and evaluation.

### Features (origin t, all past-only)

- `lag_0`, `lag_1`, `lag_2`: Trends values at t, t-1, t-2.
- `roll3`: mean over t-2..t; `roll6`: mean over t-5..t.
- `growth_1`, `growth_2`, `growth_3`: `log1p(v_month) - log1p(v_prev_month)` for consecutive pairs (t vs t-1, t-1 vs t-2, t-2 vs t-3). The +1 smoothing keeps zero-valued Trends months finite.

## Artemide 2025-11 conclusion (unchanged from Step 1)

Artemide moves from **15.0000** in 2025-10 to **70.2000** in 2025-11 and then **44.7500** in 2025-12. Lighting peers (Flos, Louis Poulsen, Tom Dixon) do not show a comparable jump. The supplied files contain no event or definition note explaining the spike, so its cause is unknown. The observation was retained unchanged; no capping or removal was applied.

## Hyperparameter tuning

Candidate alpha grid: `[0.01, 0.1, 1.0, 10.0, 100.0]`. Folds are formed by calendar `origin_month` and applied to all eligible brands; no shuffled K-fold and no row-wise `TimeSeriesSplit(gap=2)` were used. For validation origin v, a training origin u is included only when `u + 3 calendar months <= v`.

### matched_history

Chosen alpha: **100** (lowest mean validation MAE).

| alpha | 2025-10 | 2025-12 | 2026-02 | mean val MAE |
|---:|---:|---:|---:|---:|
| 100 | 0.294890 | 0.217612 | 0.236356 | 0.249619 |
| 10 | 0.302653 | 0.216302 | 0.236479 | 0.251811 |
| 1 | 0.319435 | 0.201001 | 0.236461 | 0.252299 |
| 0.1 | 0.326259 | 0.197502 | 0.236369 | 0.253377 |
| 0.01 | 0.327233 | 0.197104 | 0.236357 | 0.253565 |

Chosen-alpha fold details:

| validation origin | latest train origin | train rows | val rows | val MAE |
|---|---|---:|---:|---:|
| 2025-10 | 2025-07 | 210 | 30 | 0.294890 |
| 2025-12 | 2025-09 | 270 | 30 | 0.217612 |
| 2026-02 | 2025-11 | 330 | 30 | 0.236356 |

### extended_history

Chosen alpha: **1** (lowest mean validation MAE).

| alpha | 2025-10 | 2025-12 | 2026-02 | mean val MAE |
|---:|---:|---:|---:|---:|
| 1 | 0.294874 | 0.180993 | 0.239774 | 0.238547 |
| 0.1 | 0.295357 | 0.180558 | 0.239792 | 0.238569 |
| 0.01 | 0.295407 | 0.180513 | 0.239794 | 0.238571 |
| 10 | 0.291450 | 0.184581 | 0.239767 | 0.238599 |
| 100 | 0.284986 | 0.194861 | 0.240263 | 0.240037 |

Chosen-alpha fold details:

| validation origin | latest train origin | train rows | val rows | val MAE |
|---|---|---:|---:|---:|
| 2025-10 | 2025-07 | 1197 | 30 | 0.294874 |
| 2025-12 | 2025-09 | 1257 | 30 | 0.180993 |
| 2026-02 | 2025-11 | 1317 | 30 | 0.239774 |

## Test-set results (identical 90 rows for every model)

Persistence predicts y=0 and has no fitted training window; the schema label `matched_history` is used to denote the shared matched evaluation set.

| model | training_window | MAE | Spearman 2026-05 | Spearman 2026-06 | Spearman 2026-07 |
|---|---|---:|---:|---:|---:|
| ridge | matched_history | 0.203914 | 0.218242 | 0.527475 | 0.573749 |
| ridge | extended_history | 0.189297 | 0.293437 | 0.544383 | 0.616463 |
| persistence | matched_history | 0.229590 | undefined | undefined | undefined |
## Limitations

- Each Google Trends series is rescaled to 0–100 over its own five-year window; raw values and derived cross-brand ranks are not absolute search volumes.
- Google Trends was extracted once per series; rerunning a query can produce different values. No repeat-extraction reliability study was performed.
- The full-window 0–100 normalisation can reflect later peaks, so historical backtesting has a look-ahead-in-the-source limitation.
- The `log(1+x)` transform is not exactly scale-invariant, especially near zero; the +1 offset does not fully remove scaling dependence.
- Spearman for persistence is undefined because its predictions are constant.

## Outputs

- `outputs/trends/baseline_predictions.csv`
- `outputs/trends/baseline_metrics.csv`
- `outputs/trends/README.md`

## B extension — 27 Nov 2026 (additional files only)

The frozen files and all sections above are unchanged. New supplementary files:

**Priority 1 — zero-shot pretrained time-series benchmark**

- [src/trends/pretrained_ts_baseline.py](../../src/trends/pretrained_ts_baseline.py)
- [outputs/trends/pretrained_ts_predictions.csv](pretrained_ts_predictions.csv)
- [outputs/trends/pretrained_ts_report.md](pretrained_ts_report.md)

**Priority 2 — Hong Kong Google Trends coverage audit**

- [src/trends/audit_hk_trends.py](../../src/trends/audit_hk_trends.py)
- [outputs/trends/hk_coverage_report.md](hk_coverage_report.md)

**Priority 3 — optional descriptive momentum change-point notes**

- [src/trends/momentum_shift_notes.py](../../src/trends/momentum_shift_notes.py)
- [outputs/trends/momentum_shift_notes.md](momentum_shift_notes.md)
- [Artemide chart](figures/momentum_artemide.png) · [Louis Poulsen chart](figures/momentum_louis-poulsen.png) · [Jo Malone London chart](figures/momentum_jo-malone-london.png)

## Baseline supplements — 28 Nov 2026 (additional files only)

**Expanded Ridge alpha search (matched history)**

- [src/trends/ridge_expanded_alpha.py](../../src/trends/ridge_expanded_alpha.py)
- [outputs/trends/ridge_expanded_alpha_predictions.csv](ridge_expanded_alpha_predictions.csv)
- [outputs/trends/ridge_expanded_alpha_metrics.csv](ridge_expanded_alpha_metrics.csv)
- [outputs/trends/ridge_expanded_alpha_report.md](ridge_expanded_alpha_report.md)

**Growth-continuation baseline (no training)**

- [src/trends/growth_continuation_baseline.py](../../src/trends/growth_continuation_baseline.py)
- [outputs/trends/baseline_predictions_extension.csv](baseline_predictions_extension.csv)
- [outputs/trends/baseline_extension_report.md](baseline_extension_report.md)

## A collection handoff — 28 Nov 2026

The four supplied collection scripts are restored under `src/trends/`; the first
three preserve the original **Worldwide `geo=""`** methodology as historical
provenance. The fourth is the separate **HK `geo="HK"`** resumable collector.
Monthly averaging is performed by the fetching/rechecking scripts.
`finalize_trends.py` selects and copies already aggregated monthly series and
adds `valid_from` metadata; it does not perform the averaging.
See [collection methodology](../../src/trends/README.md).

- [Completed HK CSV](hk_trends_monthly.csv): 1,800 rows, 30 brands x 60 months,
  2021-11 through 2026-10. [Source/checkpoint notes](hk_collection/README.md).
- [Baccarat exception](hk_collection/overrides/baccarat/README.md): the original
  query returned empty HK responses; topic `/g/1ymztwqsw` is explicitly recorded
  in the final CSV. The other 29 terms remain unchanged.
- HK sparsity: 1,084/1,800 recorded zeros (60.22%); 15 brands have at least
  54 zero months. Nothing's three pre-validity rows remain unavailable in analysis.
- `hk_coverage_report.md` is the earlier failed attempt, before this collection
  and restoration of the Worldwide code. `hk_collection/collection_report.md`
  preserves the intermediate 25/30 stop. Their historical statuses do not
  describe the completed CSV.

All original B results and documentation above are retained. No collection,
model, target construction or split was rerun or changed. HK is supplementary
and must not overwrite the frozen Worldwide inputs or baseline/model outputs.

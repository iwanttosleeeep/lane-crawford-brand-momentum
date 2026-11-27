# Follow-up supplement A — expanded Ridge alpha search (matched history)

Only the candidate alpha grid changed. The purged, origin-month-grouped expanding-window CV, validation origins, Jan 2025–Feb 2026 training period, features, target and frozen 90-row test set are identical to `baseline_trends.py`. Alpha was chosen on **validation MAE only**; no test value or test-derived statistic was used for selection.

## Alpha grid and validation results

- Original grid: `[0.01, 0.1, 1.0, 10.0, 100.0]`
- Expanded grid: `[0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0]`
- Validation origins: `['2025-10', '2025-12', '2026-02']`; folds use only training origins whose `origin + 3 <= validation month`.
- Matched training rows: **420**.

| alpha | 2025-10 | 2025-12 | 2026-02 | mean val MAE |
|---:|---:|---:|---:|---:|
| 100 | 0.2948899222 | 0.2176115122 | 0.2363561560 | 0.2496191968 |
| 10 | 0.3026529630 | 0.2163015624 | 0.2364789397 | 0.2518111550 |
| 1 | 0.3194345240 | 0.2010012626 | 0.2364609154 | 0.2522989007 |
| 1000 | 0.2948913892 | 0.2088414960 | 0.2558041887 | 0.2531790246 |
| 0.1 | 0.3262589331 | 0.1975021309 | 0.2363694412 | 0.2533768351 |
| 0.01 | 0.3272327073 | 0.1971043449 | 0.2363574251 | 0.2535648258 |
| 10000 | 0.2934564733 | 0.2272755805 | 0.2890187482 | 0.2699169340 |

**Selected alpha: 100** (lowest mean validation MAE; previous selection was 100).

**alpha remains 100, results unchanged.** No refit was performed; the frozen Ridge matched-history predictions and metrics were copied read-only into the new output files.

## Test metrics (identical frozen 90 rows)

- Source of predictions: copied from frozen baseline_predictions.csv (no refit).
- MAE: **0.2039143948**
- Spearman 2026-05: **0.2182424917**
- Spearman 2026-06: **0.5274749722**
- Spearman 2026-07: **0.5737486096**
- No exclusions: all 90 brand-origin rows were evaluated.

## Run command

```bash
cd D:\lane-crawford-brand-momentum
python src/trends/ridge_expanded_alpha.py
```

## Outputs

- `outputs/trends/ridge_expanded_alpha_predictions.csv`
- `outputs/trends/ridge_expanded_alpha_metrics.csv`
- `outputs/trends/ridge_expanded_alpha_report.md`

No frozen file was modified.

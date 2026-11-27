# Follow-up supplement B — growth-continuation baseline

A training-free baseline added because per-month cross-brand Spearman is undefined for the constant-zero persistence predictions. Persistence itself is untouched.

## Fixed rule (identical for every test row)

```text
predicted_growth = log1p(mean(GT[t-2..t])) - log1p(mean(GT[t-5..t-3]))
```

- Both means are arithmetic means taken **before** `log1p`, matching the project target definition.
- Only observed months `t-5..t` are used. No future GT value, target column or test outcome is used as input.
- No fitting, tuning or model selection is performed.

## Data availability

- Test rows checked: **90**; origins: `2026-05, 2026-06, 2026-07`.

**All 90 rows were computable** (t-5..t present for every brand-origin), so this baseline is directly comparable with the frozen 90-row results of every other model. No subset restriction is needed.

## Test metrics

- Evaluated rows: **90**.
- MAE: **0.4042649191**
- Spearman 2026-05: **-0.5279199110**
- Spearman 2026-06: **-0.6622914349**
- Spearman 2026-07: **-0.1470522803**

## Run command

```bash
cd D:\lane-crawford-brand-momentum
python src/trends/growth_continuation_baseline.py
```

## Outputs

- `outputs/trends/baseline_predictions_extension.csv`
- `outputs/trends/baseline_extension_report.md`

No frozen file was modified; persistence predictions remain unchanged.

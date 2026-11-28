# Baccarat override — documented substitution

## Why
The exact `brands.csv` query for baccarat (`query: "Baccarat crystal"`) repeatedly returned an
empty HK timeline (`ValueError: Empty/invalid Trends response`) across three attempts on two
VPN nodes. A diagnostic request for `lego` succeeded on the same node, so the failure was
specific to the baccarat query in Hong Kong, not rate limiting.

## What was used
- Brand: baccarat
- Override source: `topic`
- Override identifier: `/g/1ymztwqsw` (Google Trends topic "Baccarat")
- Geo: `HK`
- Timeframe: `2021-11-01` to `2026-10-31` (complete months)
- Valid from: `2021-11-01`
- Retrieved: 2026-11-28T03:37:45+00:00
- Diagnostic result: 261 weekly points, 60 monthly means, min 0.00, max 72.75,
  mean 15.89, 23 zero months.

## Scope and caveats
- The other 29 brands use the exact `brands.csv` terms unchanged.
- `brands.csv`, GitHub files, Worldwide Trends data, and model outputs were not modified.
- This override is **not** the exact query defined in `brands.csv`; baccarat is therefore
  not a like-for-like replication of the original query. Its scale/definition may differ.
- The final CSV records baccarat as `trends_source=topic` and `trends_term=/g/1ymztwqsw`
  so the substitution is visible per row.

## Files
- Override raw weekly: `outputs/trends/hk_collection/overrides/baccarat/raw/baccarat.csv`
- Override monthly: `outputs/trends/hk_collection/overrides/baccarat/monthly/baccarat.csv`
- Override metadata: `outputs/trends/hk_collection/overrides/baccarat/metadata/baccarat.json`
- Final combined CSV: `outputs/trends/hk_trends_monthly.csv`
- Final SHA-256: `7fd119ee15f6e003f473dd921422eb7e7b4b9cbf1625d01da01db3a3e43606b3`
- Final shape: 30 brands x 60 months = 1800 rows

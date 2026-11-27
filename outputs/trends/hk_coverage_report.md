# B extension — Priority 2: Hong Kong Google Trends coverage audit

**No HK series was retrieved.** This report documents the exact blocker, the verified provenance of the existing exports, and an audit of the existing source series. The existing series is **not** established to be Worldwide and is **not** an HK series; it is used only to show what six-month coverage would be required if HK retrieval became available.

## 1. Provenance of the existing 30 exports (verified from supplied files)

- `Google Trends.zip` contains **30** brand CSVs; all have the header(s): `date,value,valid_from`. **No geo column and no geo metadata** are present in the export files themselves.
- `brands.csv` records `trends_source` (topic/query) and `trends_term` for each brand, but **no geo field**: geo column present = `False`.
- The repository README states a Worldwide collection geo: `False`.
- `src/collection/README.md` states the original Google Trends retrieval/finalisation scripts are not restored: `True`. No extraction metadata with a geo setting is available in the repository.
- `outputs/trends/trends_step1_report.md` documents row counts, validity exclusions, the 2026-11 flag and the Artemide anomaly, but records no geo setting.
- **Conclusion:** the collection geo of the existing exports is **undocumented and unverified**. It must not be assumed to be Worldwide. The 0–100 scaling is per series over the full extraction window, and single-extraction sampling applies.

## 2. HK retrieval attempt and blocker

- Retrieval date/time: `2026-11-27T23:05:37`.
- Requested settings: geo=`HK`, category=`0`, gprop=`''`, timeframe=`2021-11-01 2026-11-30`, monthly frequency, hl=`en-US`, tz=`0`. Query identifiers were taken unchanged from `brands.csv`: 19 topics and 11 queries.
- Package: `pytrends 4.9.2`. PyTrends `retries=0` was used because pytrends 4.9.2 passes the removed `method_whitelist` argument to urllib3 2.x; this changes only retry behaviour, not the endpoint or query.
- Connectivity check: `https://trends.google.com/trends/` returned HTTP 200, so general internet access is available. The `interest_over_time` API endpoint returned **HTTP 429 (TooManyRequests)** for both `geo='HK'` and `geo=''` (Worldwide), including with a realistic browser User-Agent.
- Blocker: Google Trends API returned HTTP 429 on a genuine HK query (bang-olufsen, topic=/m/055q5t) after 0 successful retrieval(s). Aborted the remaining 29 queries to avoid hammering the endpoint; no terms were substituted and no HK series was fabricated.
- Failed/ambiguous queries: none were attempted beyond the first probe; all other brands are recorded as `not attempted (global blocker)`. No term substitution, proxy workaround or fabricated HK values were used.
- Consequently `outputs/trends/hk_trends_monthly.csv` was **not** created.

## 3. Audit of the existing series (NOT HK; provenance geo unverified)

Fixed rules used below: `missing` is a month absent from the 2021-11..2026-10 expected window (2026-11 is excluded as flagged incomplete); a `zero` is an observed recorded value of exactly 0, never a failed retrieval; `sparse` means any missing month or >10% zero months; `unstable` means >=3 months with |delta log1p(value)| >= 1.0. A brand-origin is `complete` only when the six months t-2, t-1, t, t+1, t+2, t+3 all exist — zeros count as observed.

- Brands audited: **30**; origins checked: **19** (2025-01..2026-07); maximum brand-origins: **570**.
- Complete six-month brand-origins in the existing series: **570 / 570**.
- Recorded zero months: **0**; absent months in the expected window: **3**. Sparse brands: **1**; unstable brands: **5**.
- The 3 absent months all belong to `nothing` (2021-11..2022-01, before its `valid_from=2022-02-01`); they were excluded in the frozen Step 1 cleaning as UNAVAILABLE and are not failed retrievals or recorded zeros.

| slug | source | term | months available | measured months | missing | zeros | zero share | jumps | sparse | unstable | complete origins / 19 |
|---|---|---|---:|---:|---:|---:|---:|---:|:---:|:---:|---:|
| aesop | topic | /m/0j_3lkw | 61 | 60 | 0 | 0 | 0.000 | 1 | no | no | 19 |
| anya-hindmarch | query | Anya Hindmarch | 61 | 60 | 0 | 0 | 0.000 | 2 | no | no | 19 |
| artemide | topic | /m/026p2z5 | 61 | 60 | 0 | 0 | 0.000 | 7 | no | yes | 19 |
| assouline | topic | /m/05t00qj | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| astier-de-villatte | topic | /g/11dxd4gnx5 | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| baccarat | query | Baccarat crystal | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| bang-olufsen | topic | /m/055q5t | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| buccellati | topic | /m/0105qz9b | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| christofle | topic | /m/0b_hbp | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| flos | query | Flos lighting | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| fortnum-mason | topic | /m/05t_x2 | 61 | 60 | 0 | 0 | 0.000 | 1 | no | no | 19 |
| frette | topic | /g/11bc59742y | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| herman-miller | query | Herman Miller chair | 61 | 60 | 0 | 0 | 0.000 | 3 | no | yes | 19 |
| jellycat | topic | /g/113lj412p | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| jo-malone-london | topic | /g/11b6s_y1x9 | 61 | 60 | 0 | 0 | 0.000 | 4 | no | yes | 19 |
| knoll | query | Knoll furniture | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| kodak | topic | /m/0ftdd | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| lego | topic | /m/06r6dr | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| louis-poulsen | topic | /m/0h_dd94 | 61 | 60 | 0 | 0 | 0.000 | 7 | no | yes | 19 |
| marshall | query | Marshall speakers | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| noritake | topic | /m/0489tk | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| nothing | query | Nothing phone | 58 | 57 | 3 | 0 | 0.000 | 2 | yes | no | 19 |
| oura | topic | /g/11jrs8n__7 | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| polaroid | topic | /m/017zf_ | 61 | 60 | 0 | 0 | 0.000 | 1 | no | no | 19 |
| sennheiser | topic | /m/01r_r5 | 61 | 60 | 0 | 0 | 0.000 | 2 | no | no | 19 |
| stanley | query | Stanley tumbler | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |
| teenage-engineering | query | Teenage Engineering | 61 | 60 | 0 | 0 | 0.000 | 1 | no | no | 19 |
| tom-dixon | query | Tom Dixon lighting | 61 | 60 | 0 | 0 | 0.000 | 3 | no | yes | 19 |
| trudon | topic | /m/03c_xjk | 61 | 60 | 0 | 0 | 0.000 | 1 | no | no | 19 |
| vitra | query | Vitra furniture | 61 | 60 | 0 | 0 | 0.000 | 0 | no | no | 19 |

## 4. Go / no-go for an HK-only evaluation

**NO-GO.** There are zero genuine HK observations: the Google Trends API returned HTTP 429 and the query loop was stopped. A recorded zero in the existing series is a real observed score, not a failed HK retrieval; conversely a failed HK retrieval would produce no row at all and would never be coerced to 0.

Even if retrieval were restored, HK series would be independently rescaled to 0–100. An absolute-value comparator or a model trained on the existing series must not be assumed transferable to HK. The minimum viable next step is to rerun `python src/trends/audit_hk_trends.py` from a network path where the Trends API is not rate-limited, then require at least the same complete six-month coverage on all 19 origins (570 brand-origins) before considering a clearly labelled HK sensitivity analysis with the unchanged target definition.

No existing target, split, baseline output or brand definition was changed.

## Run command

```bash
cd D:\lane-crawford-brand-momentum
python -m pip install pytrends
python src/trends/audit_hk_trends.py
```

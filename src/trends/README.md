# Google Trends collection provenance

## Original Worldwide collection (`geo=""`)

The original Worldwide workflow uses three scripts:

- `fetch_google_trends.py`: fetch one brand at a time using pytrends 4.9.2,
  `hl="en-US"`, `tz=0`, Web Search (`gprop=""`), all categories (`cat=0`),
  `timeframe="today 5-y"`, and **Worldwide `geo=""`**. Topic entities use the
  custom `TopicTrendReq` payload; historical selection uses suggestion-title/type
  checks and falls back to the recorded search query when appropriate. It
  averages returned observations by calendar month during fetching.
- `recheck_google_trends.py`: fetch diagnostic/recheck variants and perform the
  same monthly averaging, retaining those series separately.
- `finalize_trends.py`: select the documented variants and copy the **already
  aggregated monthly series** into the final files, adding `valid_from` metadata.
  It does **not** perform monthly averaging.

Monthly averaging therefore occurs during **fetching/rechecking, before
finalisation**. The scripts preserve the Worldwide collection provenance;
`Google Trends.zip` and B's existing cleaned table remain the frozen baseline inputs.

The scripts now make the configured Worldwide geography explicit. Older CSVs
themselves contain no geo column; the earlier HK audit recorded that lack of
repository provenance before these source files were restored. The retrospective
documentation does not constitute a new extraction or a repeat-sampling study.

## Hong Kong collection (`geo="HK"`)

`fetch_hk_trends_resumable.py` is the separate, resumable HK collector. It reads
the current root `brands.csv`, fixes **`geo="HK"`**, and requests the complete
window **2021-11-01 through 2026-10-31**, with `hl="en-US"`, `tz=0`, all
categories and Web Search. It requests one brand at a time, averages source
observations by calendar month, and stores raw responses, monthly files and
SHA-256 metadata. Its config/checkpoint checks prevent mixing query definitions
or silently overwriting a different final CSV. It stops on a request failure;
there is no automatic 429 retry or proxy rotation.

The existing completed handoff is
[`outputs/trends/hk_trends_monthly.csv`](../../outputs/trends/hk_trends_monthly.csv):
**30 brands x 60 months = 1,800 rows**, unique by `(slug, month)`, with per-row
`trends_source`, `trends_term`, `geo` and `valid_from`. November 2026 is excluded.
See the [completed collection notes](../../outputs/trends/hk_collection/README.md)
and the [Baccarat exception](../../outputs/trends/hk_collection/overrides/baccarat/README.md).

### Baccarat exception

The root `brands.csv` specifies query `Baccarat crystal`. The supplied collection
notes record repeated empty HK responses for that query; a same-node LEGO
diagnostic succeeded. A separately documented topic **`/g/1ymztwqsw` (Baccarat)**
was therefore collected and included in the completed handoff. The final CSV
explicitly records `trends_source=topic` and this topic MID for Baccarat. The
other 29 brands retain the exact root `brands.csv` terms. The override is not a
like-for-like replication of the original Baccarat query. The unmodified HK
script's default query loop does not silently perform this substitution; the
override has its own raw/monthly/metadata directory and explanation. Neither
`brands.csv` nor the Worldwide series was changed.

## Sparse HK observations and evaluation scope

The supplied HK file has **1,084 recorded zero values out of 1,800 rows (60.22%)**;
**15 brands have at least 54 zero months out of 60**. There are no absent
brand-month rows in this file, but full calendar coverage is not evidence of a
strong signal. A low-volume Trends zero is not a confirmed absence of searches,
sales, or brand activity. Keep recorded zeros distinct from missing observations.

Nothing's first three rows precede `valid_from=2022-02-01`. They are preserved
exactly as collected and must be treated as unavailable in downstream analysis,
not valid zero-interest history. Excluding those rows leaves 1,081 recorded zeros
among 1,797 validity-eligible rows.

HK and Worldwide indices are independently normalised 0-100. Their levels are
not comparable absolute search counts; sample variation, topic/query differences
and whole-window normalisation remain limitations. HK is a supplementary regional
dataset, not a replacement for the frozen main target. No collection or model
was rerun for this upload; no existing Trends values, baseline/model results,
training/test splits or model scripts were changed.

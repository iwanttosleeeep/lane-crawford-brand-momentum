# Completed Hong Kong Google Trends collection

The supplied `../hk_trends_monthly.csv` is **complete for 30 brands x 60 months
(2021-11 through 2026-10), 1,800 unique brand-month rows**. It uses `geo="HK"`.
The file SHA-256 is
`7fd119ee15f6e003f473dd921422eb7e7b4b9cbf1625d01da01db3a3e43606b3`.

## Source accounting

- `raw/`, `monthly/`, and `metadata/` contain the 29 exact-term brands.
- `overrides/baccarat/` contains the 30th brand and the
  [explicit topic-override explanation](overrides/baccarat/README.md).
- `collection_config.json` preserves the original exact-term config. The
  unmodified `collection_report.md` is the **historical stopped run at 25/30**,
  before the Baccarat override and later completion. It is not the status of
  the final combined CSV. The earlier repository `../hk_coverage_report.md` also
  predates this successful handoff and the restored Worldwide source files.
- Baccarat's original query `Baccarat crystal` returned empty HK responses;
  the final file instead explicitly records topic `/g/1ymztwqsw`. The other
  29 terms match `brands.csv`. The default resumable collector does not
  silently apply that exception.

## Offline checks performed for upload

All 30 raw and monthly checkpoint pairs match their recorded SHA-256 metadata.
Each brand's 60 monthly rows match the completed combined CSV exactly. All keys
are unique, all values are finite and between 0 and 100, and all rows record HK.
No script was executed and no request to Google Trends was made for these checks.

## Sparsity and interpretation

- 1,084 of 1,800 rows are recorded zeros (60.22%); 15 brands have at least
  54 zero months. No calendar rows are missing, but the HK signal is sparse.
- Nothing's three pre-validity months must remain unavailable in analysis;
  the original file is preserved, including those recorded zeros.
- Recorded zero, missing month and invalid-before-validity are different cases.
  Trends values are not absolute search volumes or sales.
- HK is independently normalised from Worldwide. Keep this regional handoff
  separate from the frozen Worldwide target, splits and baseline/model results.

Full methodology: [src/trends/README.md](../../../src/trends/README.md).

# Collection provenance and reproducibility

This folder preserves original, non-sensitive collection scripts and configurations for the 30-brand Lane Crawford dataset.

## Original materials restored

- [download_images.py](download_images.py) — the original downloader used for the final image ZIP. It reads exported Apify JSON datasets, filters Image/Sidecar posts, samples up to 15 posts per account/month (seed 6207), downloads all available image slides, resizes long edges to a maximum of 1024 px and writes a manifest. Source media and raw captions are not committed.
- [analyse_probe.py](analyse_probe.py) — the **original** first-run Apify probe analysis script (posts, account coverage, estimated posting rates and costs). Example invocation: `python src/collection/analyse_probe.py probe_export.json /path/to/probe_output`.
- [apify_inputs/](apify_inputs/) — the **four original JSON inputs actually used in Apify Console**, preserved verbatim from the provenance archive supplied by the team:
  1. `01_probe_latest20.json` — preliminary 30-account probe, latest 20 posts per account (NOT part of the final image dataset).
  2. `02_trudon_depth_test.json` — Trudon depth test; this export *was* used as the final Trudon data.
  3. `03_batch1_free.json` — eleven-account final collection batch.
  4. `04_batch2_starter.json` — eighteen-account final collection batch.
- [APIFY_RUNS.md](APIFY_RUNS.md) — the original run ledger recording settings, dates, returned counts, changes to verified handles and batch composition.

**Source accounting:** Final image data came from exports of runs **2, 3 and 4 only** (30 brand accounts, 12,167 export items in total). The downloader dry run chose 7,018 source posts and 22,882 images; 22,850 images were saved. The complete image ZIP and manifest are in the group Drive.

## Original scripts not yet restored

The files above document **Apify inputs, the probe analyser and the image downloader**. The supplied original Google Trends retrieval, recheck and finalisation scripts have now been restored byte-for-byte under `src/trends/`, alongside the separate resumable HK collector. See [Worldwide and HK collection provenance](../trends/README.md), including the Baccarat topic exception and sparse HK data. Historical local paths in the first three scripts are retained as provenance and may not run in this checkout.

The earlier Lane Crawford catalogue/brand-selection scripts are still not restored. The collection files do not reproduce every historical selection step. Do not invent replacement scripts and describe them as original collection code.

## Security and reproducibility

- Four original **actor configuration JSON files** can be committed because they list only official brand-account URLs and scraper settings. Do not commit exported Apify datasets: they may include captions, personal data and ephemeral image URLs.
- Image files stay in the privately shared Google Drive ZIP, not GitHub.
- The probe run contains two old handles (`aesopskincare`, `fretteofficial`) and `riedel_official`; the final account list was corrected as documented in APIFY_RUNS.md. Avoid rerunning the probe input as the final dataset configuration.
- Extracting a fresh dataset on a later date is not guaranteed to return the same posts, even with identical actor settings.
- C's modelling sample is **up to 10 distinct posts per brand-month, one first-available image per post**. This is a separate second-stage subsample and is not the same operation as the original downloader's up-to-15-posts-per-month selection.

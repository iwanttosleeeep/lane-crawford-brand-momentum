# Data collection provenance and reproducibility

This directory keeps source code and non-sensitive collection configuration for the Lane Crawford final project.

## Available in this repository

- `download_images.py`: **the original Python script used for this dataset**, recovered from the project conversation upload without functional changes. It reads Apify JSON list exports, filters Image/Sidecar posts, samples up to 15 posts per account-month (seed 6207), downloads each image slide, resizes to a maximum long edge of 1,024 px, and records a CSV manifest. It does not save captions. The original invocation used `--since 2024-11-01 --per-month 15 --max-per-post 0` and three export files. Actual downloaded data are in the shared Drive, not GitHub.
- `apify_official_accounts.json`: a **reconstructed non-sensitive account-list template** generated from the current 30 entries in `brands.csv`; it is not an archival copy of the exact original Apify run settings, which varied between export batches. Each URL is an official brand handle only.

## Original scripts still to restore (do not invent replacements and call them original)

- Lane Crawford catalogue retrieval, brand selection, matching and current-sale verification.
- Google Trends retrieval and finalisation. An earlier working directory reportedly contained `src/trends/finalize_trends.py`; that original file has **not** been copied into this new repository.
- Initial Apify probe analysis and related data-quality scripts, if available.

If a teammate has the actual original scripts in the earlier local repository/workspace, copy them here (or under `src/trends/` for Trends code), keeping the original file contents and a short note of how each script was run. Code that is newly recreated from a description should be labelled **reconstructed**, not a verified original.

## Privacy, access and replay notes

- Original Apify JSON exports are **not committed** because they may contain captions, user details or temporary URLs. Raw images are also **not committed**; use the group-shared Drive ZIP and its manifest.
- The Apify actor input file here only lists official Instagram URLs. Other options (date window, limits and pinned-post behavior) used in different collection batches should be documented from actual run records, not assumed from this template.
- Instagram media links from Apify can expire; reproducing an older download may require a new legal/public collection instead of replaying historical URLs.
- Preserve raw data outside Git and use the manifest to audit coverage. A new modelling sample (up to 10 **distinct posts** per brand-month, first available image only) is **different from** the original download script's source-post sample and must be recorded separately by C.

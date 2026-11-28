# Lane Crawford Brand Discovery — STAT6207 Final Project

CUHK STAT6207 Applied Deep Learning · Group 14 · Topic 2: Lane Crawford Brand Discovery

## 1. Project objective

**Research question:** Can features extracted from brands' Instagram images using pretrained deep learning models improve forecasts of future Google Trends interest, compared with a Trends-only baseline?

We study **30 existing Lane Crawford brands**. The core deliverable is an evaluated forecast and a **rising / declining brands watchlist**, supported by image-feature analysis and commercial interpretation. An optional new-brand case study may be added if required by the final scope and feasible within the data budget; do not delay the core evaluated forecast for it.

**Pipeline:** Instagram posts → pretrained CLIP / YOLO / OCR → brand-month image features; historical Google Trends → prediction targets and baseline; combine both → multimodal forecasting → quantitative evaluation → brand analysis.

**Primary prediction target (proposed):** For brand b at forecast origin month t,

y(b,t) = log(1 + mean Google Trends during t+1 to t+3) − log(1 + mean Google Trends during t−2 to t).

This predicts the change between the **next three months** and **previous three months** of average search interest. B and E must jointly confirm and freeze this exact definition before modelling; do not independently implement different targets.

**Evaluation:** follow the **fixed, purged chronological split in Section 4** and compare MAE and cross-brand Spearman on identical held-out months. The final protocol uses **14 training origins, 2 purged origins and 3 test origins**, giving an approximately **82/18** split of retained origins (close to the required 80/20). Report the actual number of valid brand-month rows.

## 2. Available data and access

| Resource | Location | Notes |
| --- | --- | --- |
| **brands.csv** | This repository root | 30 selected brands, brand slug, category, official Instagram handle, Google Trends query/topic, expected Trends filename and valid-from date |
| **Google Trends.zip** | This repository root | Extract the ZIP; its 30 CSVs are in `Google Trends/`, matching `brands.csv` |
| **images.zip** (~3.7 GB) | **Google Drive link shared privately in the group chat** | Instagram images organised by account, plus a download manifest. Not stored in GitHub |
| **src/collection/download_images.py** | This repository | Original image downloader and source-post sampling script |
| **src/collection/apify_inputs/** | This repository | All **four original Apify run inputs**, including the preliminary probe; do not confuse the probe with final data |
| **src/collection/analyse_probe.py** | This repository | Original first-probe evaluation script |
| **src/collection/APIFY_RUNS.md** | This repository | Recorded run settings, returned item counts and which three exports formed the final dataset |
| **Google Trends collection scripts** | [src/trends/README.md](src/trends/README.md) | Original Worldwide collection/recheck/finalisation provenance and the separate resumable HK collector |
| **HK Trends supplement** | [outputs/trends/hk_trends_monthly.csv](outputs/trends/hk_trends_monthly.csv) | 30 brands, 60 months; HK-specific sparse series with an explicit Baccarat topic exception |
| **New-brand CLIP/YOLO features** | [outputs/new_brands/images/README.md](outputs/new_brands/images/README.md) | A's 280-image handoff for four candidates; never used for training or tuning |
| **Other collection code** | See src/collection/README.md | Earlier Lane Crawford catalogue/brand-selection scripts remain to be restored |

**Instagram dataset:** 22,850 downloaded images across 30 brands. See the included manifest for image metadata.

Do not upload the full image ZIP, extracted images, large embeddings, raw Apify exports, or pretrained model weights to GitHub. Raw exports may include captions or personal information; only the original **Apify input settings** and privacy-safe collection scripts are versioned. Small tables, reproducible code, figures, and technical notes belong here.

### Trends collection provenance and HK supplement (28 Nov 2026)

The original Worldwide collection uses **`geo=""`**, one brand/topic or query at
a time, and `today 5-y`. Monthly averaging is performed during fetching and
rechecking by `fetch_google_trends.py` and `recheck_google_trends.py`.
`finalize_trends.py` selects and copies the already aggregated monthly series,
adding `valid_from` metadata; it does not perform the averaging.
See [the collection methodology](src/trends/README.md).

The separate **`geo="HK"`** handoff contains **1,800 rows (30 brands x 60 months,
2021-11 through 2026-10)**. Baccarat is the explicit exception: the HK query
`Baccarat crystal` returned empty responses, so topic `/g/1ymztwqsw` was supplied
instead; every Baccarat row records the changed source/term. The other 29 terms
are unchanged. See [the exception](outputs/trends/hk_collection/overrides/baccarat/README.md).

HK is sparse: **1,084/1,800 recorded zeros (60.22%)**, with at least 54 zero
months for 15 brands. Nothing's three pre-validity months remain unavailable for
analysis. HK and Worldwide are independently normalised indices, not comparable
absolute search volumes. [Completed HK notes](outputs/trends/hk_collection/README.md)
supersede the status of the preserved earlier blocked/stopped reports. This
supplement does not replace the frozen Worldwide data, baseline/model outputs
or training/test split. The new-brand feature handoff remains outside training
and tuning.

### Instagram post-level engagement metadata (added 27 Nov 2026)

The **numeric-only** post metadata extracts have now been checked and committed. These are **full scraped-post exports**, not C's curated image sample or a model-ready historical feature table:

| Dataset | Repository path | Scope | Valid posts | UTC post dates | Apify snapshot |
| --- | --- | --- | ---: | --- | --- |
| Existing portfolio | [`data/instagram/post_engagement.csv`](data/instagram/post_engagement.csv) | 30 official brand accounts from `brands.csv` | **12,164** | 2024-11-01 to 2026-11-22 | **2026-11-22** |
| Optional new-brand candidates | [`data/instagram/post_engagement_new_brands.csv`](data/instagram/post_engagement_new_brands.csv) | BAGGU, Dusen Dusen, Our Place, Owala | **1,732** | 2024-11-01 to 2026-11-24 | **2026-11-24** |

- The existing-brand file matches the documented final Apify runs: **12,167** retrieved items minus **three** `restricted_page` error items = **12,164** post rows; `trudon.json` contributes 286, `part1.json` 2,858, and `part2.json` 9,020. Both uploads have unique `shortCode` values, valid UTC timestamps/month keys, valid nonnegative integer fields and correct account sets. **No duplicate post keys** appeared within or across these two extracts. These are *structural checks* of the supplied CSVs, not a second independent rerun of the original JSON-to-CSV extraction.
- **CSV schema:** `handle, shortCode, timestamp, month, type, is_collab, likes, comments, video_views, video_plays, n_hashtags, n_mentions, caption_chars, source_export`. `type` is Image/Sidecar/Video; `is_collab` is the export-derived binary account/owner mismatch indicator, **not** verified evidence of a paid endorsement. `n_mentions` counts textual @-mentions **within the account's own post caption**, not consumer conversations or independent third-party brand mentions.
- **Observed missingness:** existing 30 brands have **459** missing `likes` entries; four candidates have **8**. `comments` is present in every row (including legitimate zero counts). `video_views` is **empty in every row of both files**; do not use it as a feature. `video_plays` is populated for **4,411 of 4,416** portfolio Video posts and **642 of 642** candidate Video posts. Leave unavailable values **NA, not zero**. Do not relabel plays as views or fabricate missing saves, shares, or follower history.
- **Coverage:** 2026-11 is an **incomplete month** in both extracts (snapshot dates above); exclude it from complete-month trend analyses. Known existing-brand zero-post months within 2024-11 to 2026-10 include early unavailable data for Bang & Olufsen, Marshall and Stanley, plus a December 2024 gap for Jo Malone London, May 2025 for Teenage Engineering, and March 2025 for Trudon. Do not interpret missing post history as confirmed no activity without independent coverage evidence. The snapshot/extraction does not guarantee exhaustive historic Instagram coverage.
- **Time validity / leakage:** `likes`, `comments` and `video_plays` are **cumulative counts measured in Nov 2026**, not verified historical point-in-time counts. **Using t−1 posts at a 2025 forecast origin does not fix this.** These variables may support **descriptive** engagement analysis, but should **not** enter E's locked historical prediction ablation unless genuinely historical snapshots/point-in-time evidence become available. Post publication dates and derived monthly post counts are different: they may be considered as historical activity *proxies*, subject to source completeness, unchanged time splits, and E's agreement.
- **Privacy and interpretation:** no raw caption text, @usernames, consumer identities, personal URLs or media links are included. `shortCode` identifies public posts; `source_export` contains source filenames only. Highly skewed engagement counts mean that a simple arithmetic mean may be driven by viral outliers; present counts/coverage and consider medians or transparent `log1p` summaries. The new-brand file is **not** part of the fixed 30-brand training/testing design and should not be pooled into its models.
- **Ownership:** A supplied these files; D may build a **separate** `slug × month` social-activity summary as described in the D supplement below. Preserve the original `outputs/images/monthly_image_features` and E's core evaluation unchanged. Additional data or a composite Momentum Index are not substitutes for validated out-of-sample forecasting.

 Ignore irrelevant Mac archive entries such as `.DS_Store` and `__MACOSX/` when reading the Trends ZIP; re-zipping is optional.

### Known coverage issues and data limitations (check before modelling)

- **Instagram availability (reported from the collection):** Bang & Olufsen and Marshall have posts starting **2025-03**; Stanley starts **2025-01**. Older posts appear unavailable/archived, but archival cause is not independently verified. **Jo Malone London has no posts for 2024-12**. C/D should confirm the observed coverage against the manifest and preserve missing brand-months instead of imputing them as zero image content.
- **Artemide Google Trends (unverified anomaly):** Search interest reportedly jumps substantially in **2025-11**. B should inspect the actual series, source term and adjacent months, investigate whether this reflects interest, a one-off event or measurement/definition change, and report the outcome. **Do not silently cap or remove the observation.**
- **Google Trends scaling:** Values are 0–100 within each retrieved series over the full five-year window; later peaks influence how earlier months are scaled, so historical backtesting has a **look-ahead-in-the-source** limitation. Use within-brand changes or lagged ratios where appropriate rather than treating raw levels as comparable across brands. The proposed `log(1+value)` growth target is **not exactly scale-invariant**, especially near zero. State this limitation in the report; avoid claiming that the +1 transform fully fixes scaling.
- **Sampling uncertainty:** Google Trends was pulled **once** per series; Google Trends values can vary when a query is rerun because of sampling. No repeat-extraction reliability study was conducted.

## 3. Team responsibilities

The owner labels are **A–E**; members B–E should claim their role in the group chat.

### A — Data collection and business analysis (already assigned)

**Already done:** Select the 30 brands; collect and download Instagram images; provide the brand list and Google Trends archive.

**Remaining work:**
- Share image ZIP and the data manifest with the group and confirm teammates can access them.
- Clarify brand/Instagram handle mappings and missing-file questions.
- After E produces validated forecasts, prepare a concise interpretation of rising/declining brands, visual themes, and Lane Crawford relevance.
- **Optional / scope-dependent extension:** by **2 Dec**, decide whether a small set of new brands not currently sold by Lane Crawford can be investigated. Confirm if the lecturer/TA requires it. New brands also need Instagram and Google Trends inputs and could incur **additional Apify charges**; if pursued, collect within the remaining paid-plan window and before the 5 Dec analysis deadline. Do not assume existing 30-brand data suffice to score new brands.

**Deliverable:** Data handoff plus a short, evidence-linked business recommendations section. A is **not** responsible for training the baseline or running image models.

#### 28 Nov additions — A

- **Brand Momentum Index:** Combine per brand-month signals (recent Trends growth, E's predicted growth, post-activity change, and CLIP visual change) using PCA **fitted on training origins only**; assign green/amber/red labels using fixed thresholds stated in advance.
- **New-brand case study:** Run C/D/E scripts on BAGGU, Dusen Dusen, Our Place, and Owala; report test-month errors as an unseen-brand check and their latest-origin forecasts.
- **Lightweight dashboard:** Present the watchlist and Brand Momentum Index.

### B — Google Trends, target construction, and baseline forecasting

**Inputs:** brands.csv; Google Trends.zip.

**Tasks:**
1. Extract the Trends ZIP and merge the 30 brand series by **slug and month**. Verify month continuity, validity dates, numeric fields and query/topic choices. Handle pre-validity entries for **Nothing** as unavailable, not observed zero. Check the reported **Artemide 2025-11 jump** and document any conclusion rather than automatically correcting it.
2. Exclude incomplete November 2026 from measured monthly targets. Document geographic scope, per-series 0–100 scaling, single-extraction sampling uncertainty, and historical-source look-ahead. Prefer lagged within-brand growth/ratios to unqualified raw Trends levels; the agreed target may still use log(1+value) but its scaling sensitivity must be disclosed.
3. Confirm with E the **fixed forecast origins and purged train/test split in Section 4 by 25 Nov**. Target labels require three complete future months. Do not randomly split rows, use purged origins for training, or let training labels extend into the test period.
4. Implement (a) persistence/no-change and (b) regularised Ridge using historical Trends lags, rolling means and within-brand growth. Produce **two Ridge training-window variants**: **matched-history** (the same Jan 2025–Feb 2026 training origins as E), and **extended-history** (use all eligible pre-test Trends-only history from approximately 2022 onward, respecting each brand's valid_from and the same purge/availability cut-off). The extended model is a **separate longer-history benchmark**, not a matched-data ablation against E; it may or may not perform better.
5. Tune hyperparameters using **purged expanding-window validation grouped by calendar origin month** within the training period (see Section 4), not random K-fold or row-wise gaps on brand-month rows. Report validation folds, selected settings, held-out MAE and per-month brand-rank Spearman when defined. Save test predictions **on exactly the same three test months and same brand rows as E** for both matched-history and extended-history variants. Report missing/insufficient historical rows.

**Required outputs:**
- outputs/trends/trends_monthly.csv — slug, month, trend_value, valid_from (plus documented source metadata).
- outputs/trends/targets_and_split.csv — slug, origin_month, target_growth, split (and any historical features).
- outputs/trends/baseline_predictions.csv — slug, origin_month, y_true, y_pred, model, training_window (matched_history or extended_history).
- outputs/trends/baseline_metrics.csv and outputs/trends/README.md — results for both training histories, coverage, anomaly checks, limitations and reproducible run instructions.

**Required handoff by 25 Nov:** Confirm the fixed target and split with E before either model is finalised. **Final deliverables: 29 Nov.** E independently reviews B's results by **1 Dec**.

#### B extension — 27 Nov 2026: pretrained time-series benchmark, HK coverage and momentum shifts

**Why this was added:** The Lane Crawford partner's original brief proposes (i) external social/search signals, (ii) momentum-shift detection, (iii) a composite Brand Momentum Index and (iv) trend-velocity forecasting. The lecturer/TA's later Q&A specifically asks students to use **different pretrained deep-learning models** and validate predictions with historical Google Trends. These are **supplementary B tasks**, not changes to the agreed core Google Trends target, split or handoff to E. The multi-signal index and business watchlist remain **A's downstream responsibility**, after evaluated forecasts are available; B should not invent index weights or alter the target.

**Already completed; DO NOT rerun or replace just to add the extension:** B's 30-brand Trends clean/merge, fixed targets/split, and persistence + Ridge baselines are recorded in \`outputs/trends/\`. The locked panel has 420 train, 60 purge and 90 test brand-origins; the Ridge baseline uses exactly the May–July 2026 holdout. Existing files, row keys, source scaling and split rules are frozen. Continue to honor the original 29 Nov handoff and 1 Dec independent review.

**Priority 1 — One zero-shot pretrained time-series model (Chronos OR TimesFM; supplementary benchmark).**

- Choose **one** accessible pretrained time-series foundation model (for example, Amazon Chronos or Google TimesFM), not both by default. Use its genuine pretrained weights, **inference only**; document the exact model identifier/checkpoint, package version, context length, inference settings, random seed if applicable and device. If setup/model download is blocked, document the blocker rather than delaying the core handoff.
- **Input:** each brand's historical monthly \`trend_value\` in \`outputs/trends/trends_monthly.csv\`, using only months up to and including the forecast-origin \`t\`. **Never** provide future GT values, the target column or test outcomes as input. At each origin \`t\`, predict the three monthly values for \`t+1, t+2, t+3\`. If necessary, choose and document a fixed nonnegative-value handling rule before examining test metrics (GT is defined on 0–100); do not tune the rule on holdout performance.
- Convert these 3 predicted months to the **same y scale** as B/E: \`y_pred = log1p(mean(pred_GT[t+1:t+3])) - log1p(mean(actual_GT[t-2:t]))\`. The arithmetic mean is taken **before** \`log1p\`. This is a forecast of *within-brand search-interest change*, not predicted sales, absolute search volume or a separately validated composite brand index.
- Run the model on the **same frozen 90 test rows** (\`slug, origin_month\`; May–July 2026) and calculate held-out **MAE** and **per-origin-month cross-brand Spearman** against \`target_growth\`. If some brands cannot produce a forecast, report exclusions and additionally evaluate any comparators on the identical subset; never silently change E's main 90-row comparison.
- Present results as a **supplementary zero-shot pretrained baseline**, next to Ridge matched-history (MAE 0.203914), Ridge extended-history (MAE 0.189297) and no-change persistence (MAE 0.229590). These Ridge values are **existing reference figures**, not the expected result of the new model. The pretrained model has external pretraining; it is **not** a matched-training-data ablation proving the impact of Instagram visual features. Model selection must be fixed before reading test results; disclose the source's full-window scaling/look-ahead limitation.
- **Additive deliverables:** \`src/trends/pretrained_ts_baseline.py\` (or a reproducible notebook), \`outputs/trends/pretrained_ts_predictions.csv\` with \`slug, origin_month, y_true, y_pred, model\`, and \`outputs/trends/pretrained_ts_report.md\` with checkpoint, conversion formula, settings, coverage, metrics, limitations and a run command. **Do not overwrite** \`baseline_predictions.csv\`, \`baseline_metrics.csv\` or \`targets_and_split.csv\`.

**Priority 2 — Hong Kong Google Trends coverage audit (geography robustness; feasibility first).**

- **First verify** the geo selection of the existing 30 original Google Trends exports from their original extraction metadata/process. The README does not itself establish that their collection geo is Worldwide; **report observed provenance rather than assuming** it.
- Query the same **30 slugs** with the **same brand query vs topic identifiers**, category settings, data frequency and, insofar as available, the same time window as the original series, but set **geo = HK**. Document exceptions, failed/ambiguous queries, retrieval date, and the effect of per-query 0–100 normalization and Google Trends sampling. Do not substitute new terms silently to improve coverage. Do not overwrite the main Trends source, which underpins the frozen model evaluation.
- Audit each HK series: available months; monthly zeros and missingness; unusually sparse or unstable brands; availability of the **six months required per target** around the **same 19 forecast origins (Jan 2025–Jul 2026)**; and how many brand-origin rows would support a meaningful HK-only evaluation. A recorded zero GT score is **not** the same as a failed or missing retrieval; distinguish both.
- Only **if coverage is adequate** consider a small, clearly labelled HK sensitivity analysis using the **same target definition** and chronological safeguards. HK Trends is independently rescaled, so a worldwide-trained model/absolute brand ranking must **not** be assumed transferable. If HK is too sparse, stop at the coverage audit and give the evidence-based reason it cannot replace the main series.
- **Additive deliverables:** \`outputs/trends/hk_coverage_report.md\` including a brand-by-brand coverage table, source settings, zero/missingness summary and go/no-go recommendation; optionally \`outputs/trends/hk_trends_monthly.csv\` and \`src/trends/audit_hk_trends.py\` if retrieval succeeds. No change to current targets, B/E handoff or test split.

**Priority 3 — Descriptive momentum change-point analysis (only if Priorities 1–2 and original duties are secure).**

- The partner's proposed **CUSUM change-point analysis** is a **suggested method**, not a requirement to replace the deep-learning approach. As an optional analysis, use the already cleaned monthly Trends data to identify and visualize notable **within-brand** shifts or turning points. Predeclare whether using CUSUM (with threshold/reference choice explained) or a simpler rolling-growth/shift rule, and use the same definition across brands when possible.
- Output 2–3 **illustrative brand examples**, with charted months and the corresponding observed values; note seasonal spikes, sampling/scaling issues and the fact that **retrospective detection is not an ex-ante forecast**. In particular, do not claim the cause of the Artemide Nov 2025 spike is established by the data.
- **Optional deliverable:** \`outputs/trends/momentum_shift_notes.md\` plus figures/code. A may reuse the verified examples in Data Analytics / Business Value; the composite Index is still A's task.

**Coordination and stop conditions**

- **Do not modify** the 30 brand definitions, target formula, January 2025–February 2026 train range, March–April 2026 purge, May–July 2026 holdout, or E's planned Trends+CLIP/YOLO/OCR ablation.
- **Required original work comes first.** B may deliver Priority 1 and/or Priority 2 independently; Priority 3 is optional. If only one is feasible, prioritize the reproducible pretrained time-series benchmark; otherwise explain the blocker and provide the HK coverage audit. Extra models are not automatically better or required to establish the value of visual features.
- Please alert A and E before changing any shared schema. Put extension files under their **new paths** and link them from \`outputs/trends/README.md\` when complete. Report actual results only after running the code; do not promise a specific runtime, accuracy gain or HK data coverage.

#### 28 Nov additions — B (small follow-ups to delivered work)

- Extend the Ridge alpha candidate grid with **1000** and **10000** (matched-history selected **100**, the previous upper boundary). Re-select using the existing validation procedure and report whether the chosen alpha changes.
- Add a **growth-continuation** baseline: `y_hat(t) = log1p(mean Trends[t-2..t]) - log1p(mean Trends[t-5..t-3])`. Evaluate on the **same 90 test rows**. Unlike persistence (`y_hat = 0`, undefined Spearman), this provides a rankable naive benchmark.

### C — CLIP and YOLO feature extraction

**Inputs:** images.zip; image manifest; brands.csv.

**Tasks:**
1. Check image files against the manifest and exclude failed/missing entries. Sample **up to 10 distinct posts per brand-month, selecting the first available image slide from each post** (smallest numeric slide index), with a fixed seed. Never treat different slides of the same post as different sampled posts. Freeze a single sample manifest by **25 Nov**; D must not resample independently. Preserve all months and report coverage.
2. Run **pretrained CLIP** on the sampled images for visual embeddings (e.g., CLIP ViT-B/32). **In addition, calculate the eight predefined zero-shot image–text similarity scores from Section 4**, using the same image embeddings and matching CLIP text encoder (no second image inference pass). Record checkpoint, image/text preprocessing, prompt strings and output dimensions; do not fit PCA using the full dataset.
3. Run **pretrained YOLO** (e.g., YOLO11n) on the **same sample** to extract interpretable object-class counts/presences. Record checkpoint, confidence threshold and classes; note that a generic object detector may not recognise specialised luxury-product categories.
4. Save **per-image** features (not only monthly summaries), identify missing/broken files, and perform a small visual spot-check of detections/semantic outputs.
5. Provide a simple reproducible run command or notebook. Reuse an available GPU when possible; do not require each member to process all 22,850 files.

**Required outputs:**
- outputs/images/sample_manifest.csv — **image_id, file, handle, slug, shortCode, slide, timestamp, month**; set image_id equal to the manifest-relative **file** path (e.g., handle/shortCode_slide.jpg), and ensure one unique row per image.
- outputs/images/clip_features.parquet (or CSV) — one row per sampled image, keyed by image_id; retain the original CLIP dimensions and add eight `clip_sem_*` similarity columns in this **same file** (no additional handoff).
- outputs/images/yolo_features.parquet (or CSV) — one row per sampled image, keyed by image_id.
- outputs/images/clip_yolo_notes.md — model versions, sample coverage, feature definitions, QC and reproducible commands.

**Required handoffs:** Send D the frozen **sample_manifest.csv** by **25 Nov** and both complete **per-image CLIP and YOLO feature files** by **28 Nov**, so D can integrate them. Final C documentation/QC is due **29 Nov**. B independently reviews C by **1 Dec**.

### D — OCR and monthly feature integration

**Inputs:** C's exact sample_manifest.csv; the corresponding image files; C's CLIP/YOLO outputs.

**Tasks:**
1. Run **pretrained OCR** (e.g., EasyOCR English) on **exactly the images listed in C's frozen sample_manifest.csv**. Derive compact numeric features such as has_text, number of detected text regions, total characters, or presence of the brand name. Record the OCR library/model and preprocessing.
2. Save per-image OCR features keyed by image_id. Avoid publishing unnecessary transcribed text or personal content.
3. Implement the merge/aggregation code independently while C processes CLIP/YOLO, then join the completed per-image files when C uploads them by **28 Nov**. Join using **image_id** (equal to file path), then aggregate into **one row per slug × month**. Preserve **n_images** and missingness and check that no images or months are accidentally duplicated.
4. Keep an explicit feature dictionary covering original CLIP dimensions and eight `clip_sem_*` features. Aggregate both, without performing PCA or other training-dependent fitted transforms. If PCA/scaling is used for prediction, **fit only on each training fold** inside E's modelling pipeline.
5. Validate every input image was published on or before its forecast origin (see Section 4). Missing brand-months, including known early-account gaps, must remain explicit missing observations, not zero-valued image features. Any rolling features must use past data only.

**Required outputs:**
- outputs/images/ocr_features.parquet (or CSV), keyed by image_id.
- outputs/images/monthly_image_features.parquet (or CSV) — slug, month, n_images plus numeric feature columns.
- outputs/images/feature_dictionary.md and outputs/images/integration_checks.md — schema and verification results.

**Due:** Complete OCR features and integrated monthly image features by **29 Nov**. Do not wait for C's final documentation to start OCR. C independently reviews D by **1 Dec**.

#### D supplement — 27 Nov 2026: optional Instagram post-activity / engagement data (NEW ONLY)

**Why:** The partner brief mentions social velocity and engagement depth as possible brand-momentum signals. A has extracted **numeric post metadata** from the original full Apify exports (not from the images or C's 10-post-per-brand-month sample). The 30-brand numeric CSV is **already verified and uploaded** at `data/instagram/post_engagement.csv` (four optional candidates have their own separate file). This is a separate optional data stream; everything in D's existing OCR + image aggregation contract above remains unchanged, and **E must receive the original `monthly_image_features` on time even if this extension is unfinished.**

**D can start now (without waiting for A):** Keep the mandatory image/OCR pipeline independent. If time permits, build a separate monthly aggregator using the existing `data/instagram/post_engagement.csv`. Its exact fields and limitations are documented above. Do not mix the four candidate brands into the fixed 30-brand scope.

**For the already uploaded CSV:**

1. **Post-level provenance and keys.** Use `brands.csv` to map official account/handle to **`slug`**. Derive **UTC `month`** from the original post publication timestamp, not the scrape date. Deduplicate by **`slug × shortCode`** (one post may have many image slides); flag conflicting timestamps or metadata, duplicate exports, wrong handles, error items and out-of-scope accounts. Use only the **30 selected brands** for the core analysis; the four optional candidate brands must remain separate. Never merge post counts onto the per-image sample by `image_id`.
2. **Create a separate monthly social table** at **one row per `slug × month`**: `n_posts_full` (unique posts in the retained full-post export), `n_posts_like_observed`, `n_posts_comment_observed`, and, when fields exist, `mean_likes_observed`, `mean_comments_observed`, `share_video_posts`. Optional reporting columns can include medians or `log1p`-transformed summaries, but document the exact order of aggregation/transformation. For missing/hidden likes/comments, preserve **NA (not zero)**; a recorded count of 0 is different from an unavailable count. Use denominator/coverage columns for each interaction metric. Do not infer follower growth, saves, shares or third-party brand mentions from official-account posts or from a `@mention` count in captions.
3. **Coverage/quality checks.** Compare monthly unique-post counts to what the complete original Apify exports support, **not** to C's capped `sample_manifest.csv` or its `n_images`. Document which months/accounts may be incomplete (account history limits, skips, missing months, videos, errors); `n_posts_full` is **observed export activity**, not guaranteed total Instagram activity. Distinguish a verified zero-post month from one with missing or unreliable coverage; do not silently fill absent months with zeros. State the actual extraction/snapshot date provided by A.
4. **Critical point-in-time constraint.** The `likesCount`/`commentsCount` observed in a Nov 2026 scrape are **cumulative as of collection**, not counts observable at historical forecasting origins (e.g. 2025). Lagging posts by one month **does not cure this look-ahead problem**. Keep engagement summaries **descriptive only**, and **do not attach them as historical predictor columns for E's locked backtest** unless A/E can document genuine archived point-in-time interaction snapshots or an explicitly justified time-valid alternative. Posting *dates/counts* can be considered separately as past activity features, subject to documented completeness and E's approval; do not change E's primary features or test rows without agreement.
5. **Separate outputs and handoff.** If undertaking this optional stream, save **`outputs/instagram/monthly_post_activity.csv`** (or Parquet) with a data dictionary and **`outputs/instagram/post_activity_checks.md`**. Keep **`outputs/images/monthly_image_features.parquet` unchanged** in schema and semantics; E can join the separate activity table later by **`slug × month`**, and decide whether a *separately labelled* activity-only sensitivity test is valid. No PCA, retraining, new CLIP scores, or historical engagement ablation is part of D's work.

**Priority:** Complete mandatory OCR and image-feature integration **by 29 Nov** first. This CSV is available now, but any optional activity aggregation must not block E or require re-running the image pipeline.

#### 28 Nov additions — D

- As required for C's pipeline, make the **OCR and monthly aggregation scripts accept input/output paths as arguments**, so A can rerun them on the new-brand sample. Document the **exact command**.

### E — Multimodal prediction, evaluation, and results

**Inputs:** B's targets/splits and baseline predictions; D's monthly_image_features; brands.csv.

**Tasks:**
1. **Coordinate with B by 25 Nov** to confirm the fixed time split in Section 4 and exact evaluation rows. Forecast input at t may use only Trends and images available by t. The matched-history baseline and every multimodal model must share the same training/test origins.
2. Train a simple, regularised **Trends + image features** model (start with Ridge/Elastic Net or comparable model suitable for the sample size). Use the **same test origins** as B. Tune regularisation and any PCA dimensions using **purged, month-grouped expanding-window CV (Section 4)**; fit imputation/scaling/PCA/feature selection independently inside each fold's training data, never on validation or locked test data.
3. Preserve the **main ablation ladder**: matched-history Trends-only vs Trends + full CLIP (train-fold PCA) vs + YOLO vs + OCR, under the identical Jan 2025–Feb 2026 train / May–Jul 2026 holdout protocol. Add **one predeclared, compact and interpretable secondary comparison**: Trends + eight CLIP semantic scores + one within-brand visual-change feature (Section 4), rather than an unlimited model search. Show B's **extended-history Trends-only baseline separately** as an additional benchmark; do not claim it uses the same training information. If a model is infeasible, record why rather than inventing results.
4. Report held-out MAE, rank correlation by forecast month, and error analysis; include plots of predictions vs actuals and a rising/declining watchlist. A complex LSTM or dashboard is **not required** for the first reproducible result.
5. After evaluation is frozen, refit the chosen specification on all available **eligible historical observations** and generate future forecasts. Keep actual observed values separate from predictions.
6. Hand off validated figures, comparison results and interpretation notes to A for commercial analysis.

**Required outputs:**
- outputs/models/model_comparison.csv — tested model names, data coverage, MAE and rank metrics.
- outputs/models/test_predictions.csv — slug, origin_month, y_true, y_pred, model.
- outputs/models/future_forecasts.csv — slug, forecast_origin, predicted_growth, model.
- outputs/models/figures/ and outputs/models/README.md — plots, **internal validation month folds and selected hyperparameters**, evaluation protocol, compact semantic comparison, error analysis, reproducible commands.

**Due:** Complete model comparison and figures by **3 Dec**. D independently reviews E by **5 Dec**.

#### 28 Nov additions — E

- If D delivers `outputs/instagram/monthly_post_activity.csv`, add **one separate** `Trends + post activity` comparison, lagged according to D's point-in-time rules; report it **alongside**, not merged into, the existing image-feature ablation ladder.
- Include B's **growth-continuation** baseline and the **pretrained time-series** model (if delivered) in `model_comparison.csv`.
- **Uncertainty:** Bootstrap brands (resample the **30 brands**, **1000 draws**, fixed seed) to estimate the **test MAE difference versus matched-history Ridge**, with a **95% interval**. Do not claim a model is better if the interval contains zero.
- Save predicted growth for every eligible brand-month origin—**training via out-of-fold predictions, test and future**—in `outputs/models/all_predictions.csv`; A will use it for the Brand Momentum Index.
- Provide `src/models/predict_new_brands.py` to load the **final fitted model** and score new brands from their monthly-feature and Trends files for **test origins 2026-05..07** and the **latest origin 2026-10**. **Do not use new brands for training or tuning.**

## 4. Shared interfaces and dependencies

**Brand key:** Use **slug** from brands.csv for merges. Instagram folders are named by **instagram_handle**, not slug. Join via brands.csv.

**Image key:** The download manifest has a **file** relative path like handle/shortCode_slide.jpg. Set **image_id = file**, preserve that exact value in every per-image output, and use it to join CLIP, YOLO and OCR without mismatches.

**Time key:** Use calendar **month** in YYYY-MM and **origin_month** for the month at which a prediction is made. All forecasts must be made using information available *by* that origin. The target is computed from the following three complete months.

**Handoffs:**
- A → C/D: image ZIP and original image manifest.
- B ↔ E: target formula, shared split, baseline results.
- C → D: frozen image sample by **25 Nov**; completed CLIP/YOLO per-image outputs by **28 Nov**.
- D → E: integrated monthly image features.
- E → A: model evaluation, final watchlist and evidence for business recommendations.

### Fixed forecasting-origin and evaluation protocol (B and E)

**Forecast timing convention:** Each forecast origin month t refers to a prediction made **at the end of month t**, after that month's monthly Google Trends and Instagram data are available. At that point the previous three months (t−2 through t) are known. The target is the change in mean search interest over the **next three complete months**, t+1 through t+3. Do not treat the forecast as having been issued at the start of month t.

Instagram extraction starts in **2024-11**, so the first origin with a nominal three-month visual-history window is **2025-01**. The last fully observed Trends month is **2026-10**, so the last origin with all three *future* monthly target values is **2026-07**.

| Split | Forecast origins | Months | Maximum rows (30 brands) |
| --- | --- | ---: | ---: |
| **Train** | **2025-01 to 2026-02** | **14** | **420** |
| **Purge (unused)** | **2026-03 to 2026-04** | **2** | **60** |
| **Test — locked holdout** | **2026-05 to 2026-07** | **3** | **90** |

There are **19** nominal origin months. The split is **14:3 (82.35% training / 17.65% test of 17 retained months)**, closer to the course's 80/20 requirement than the previous 12:4 split, but **not exactly 80/20**. The two purged months are neither trained nor tested.

**Why purge two origins?** If the first test origin is **T = 2026-05**, a training label must be fully observed by **the end of T**: for any training origin t, require **t+3 ≤ T**. Therefore the latest training origin is **2026-02**, whose future target months are **March–May 2026**. Origins March and April are excluded because their targets would require months after the May forecast date. The first test forecast (end-May) targets **June–August 2026**; its future outcomes never enter training. Freeze the split before any model fitting or inspection of holdout metrics.

The **420/90 row counts are upper bounds** (14 or 3 months × 30 brands). In particular, Bang & Olufsen and Marshall lack early image months, Stanley begins later, and Jo Malone London misses Dec 2024. Once the three-month image-history rule and any other missingness policy are applied, actual complete-case counts can be lower. **B and E must test on the same observed brand–origin rows.** Publish the eligible-row counts and exclusions. Do not retrospectively change the split to improve model scores.

**Two baseline histories:** In the **matched-history comparison**, B's Trends-only model and E's multimodal variants use the same training origins (Jan 2025–Feb 2026) and the same three held-out origin months (May–Jul 2026). B also runs an **extended-history Trends-only baseline** using all earlier eligible Trends records, generally from 2022 onward, but only with training labels observed by the **end of May 2026** and respecting each brand's valid_from. This is a separate benchmark, not a matched-training-data ablation. All versions evaluate on the **identical May–July 2026 test rows**. Hyperparameter fitting/validation must respect chronological availability and must not use test targets.

### Internal hyperparameter validation (B and E; mandatory)

The target uses future Trends months **t+1 through t+3**, so adjacent forecast origins share outcome months. **Do not** use shuffled/random K-fold on this brand-month panel. A plain `TimeSeriesSplit(gap=2)` on the flattened panel is **not sufficient**, because its gap is counted in **rows**, not calendar months.

1. Form folds by **unique calendar `origin_month`**, applying each month's assignment to **all eligible brands**. Use **forward-only expanding-window CV** inside the fixed training-origin period, **2025-01–2026-02**; the outer 2026-03/04 purge and 2026-05–07 holdout must never be used for tuning.
2. For a validation origin **v**, include a training origin **u** only when **u + 3 calendar months ≤ v**. The latest permitted training origin is therefore **v−3**: leave the **two intermediate origin months** out of that fold. All labels in training are then observable by the end of validation month v.
3. **Predefined candidate validation months:** **2025-10**, **2025-12**, **2026-02**, with latest permitted training origin **2025-07**, **2025-09**, **2025-11** respectively. Fit on all eligible earlier origin months and validate across eligible brands in each designated month. B's extended-history baseline may use its longer past training prefix, while preserving these validation dates. If insufficient valid data require an alternative fold calendar, B and E must agree **before inspecting outer test results**, document the change and retain the three-month label-availability rule.
4. Select Ridge/Elastic Net regularisation, PCA components and other hyperparameters using **internal validation results only** (e.g., mean monthly-fold MAE). **Refit imputers, scalers, PCA, feature selection and regression from scratch inside each fold's training rows**; apply only `transform/predict` to validation rows. Report folds, row counts by fold, missingness, candidate grid and chosen settings in B/E workstream README files.
5. After tuning, refit with all eligible **fixed outer training origins through 2026-02**, then evaluate **once** on the **2026-05–07** holdout. Never choose/tune the reported winner from held-out performance; any post-hoc comparison must be labelled exploratory.

The condition addresses **forecast-time data availability**, not simply autocorrelation. Two correctly ordered, purged samples can still be statistically dependent; that does not itself invalidate the evaluation.

### Fixed feature-extraction contract (C, D and E)

**Follow this contract directly rather than letting separate agents design incompatible features.** The three pretrained models are feature extractors, not competing forecasting models. C runs CLIP + YOLO; D runs OCR and integrates their results; E performs prediction and evaluation. Internal testing is not a separate team deliverable.

1. **Shared post-level sample (C; due 25 Nov).** From successfully downloaded files in the original manifest, group by **slug × UTC month × shortCode**. Choose the **first available image** for each post (the smallest numeric slide index), then randomly select **up to 10 distinct posts per brand-month** without replacement using seed **42** and a documented deterministic sort. A post is never counted twice within a brand-month. Freeze outputs/images/sample_manifest.csv with: **image_id, file, handle, slug, shortCode, slide, timestamp, month**. Define **image_id = file** (exact original relative path); verify uniqueness. C and D must run on **exactly these same image_ids**. Do not silently drop missing months or corrupt images.

2. **Shared model settings.** Use pretrained inference (evaluation mode), without fine-tuning. Record the model checkpoint, versions, preprocessing, confidence threshold and number of valid images; apply the same settings across all brands for each model. Recommended defaults unless members agree and document a change before processing: **CLIP ViT-B/32**, **YOLO11n pretrained on COCO**, **EasyOCR English**.

3. **CLIP per-image output (C).** One row per image_id with the full original visual embedding in **clip_000, clip_001, ...** plus **eight predefined business-readable similarity fields** (broad enough for all 30 product categories):
   - `clip_sem_product_closeup` — a close-up product photo on a simple background
   - `clip_sem_styled_interior` — a styled interior or home-lifestyle photo
   - `clip_sem_person_using` — a person wearing, holding or using a product
   - `clip_sem_outdoor_travel` — an outdoor or travel lifestyle photo
   - `clip_sem_gift_packaging` — wrapped gifts or festive product packaging
   - `clip_sem_text_graphic` — typographic or promotional graphic
   - `clip_sem_material_detail` — material or craftsmanship close-up
   - `clip_sem_product_group` — a curated display of several products

   Use one consistent text-photo prompt template across concepts and record **exact English prompt strings** before model evaluation. Encode text with the **same CLIP checkpoint** that produced the image features; cosine similarity equals the dot product of **L2-normalised image and text embeddings**, **not** a probability. If the saved image features are in the matching CLIP joint embedding space, **reuse them without another image inference pass**. Store these fields in the same `clip_features.parquet` / CSV keyed by `image_id`. State embedding dimension, checkpoint, preprocessing, any scoring failure and the fixed prompts in `clip_yolo_notes.md`. Original embeddings remain available for E's full-feature model; **PCA is fitted only inside E's training folds**, never on all images.

4. **YOLO per-image output (C).** One row per image_id, including **yolo_n_detections** and detection counts for every COCO class as **yolo_<class>_count**, with snake_case class names and a consistent model-wide confidence threshold (default **0.25**). Classes with no detections are zero, not omitted columns. Generic COCO classes cannot distinguish every luxury product or brand.

5. **OCR per-image output (D).** One row per image_id, including **ocr_has_text** (0/1), **ocr_n_regions**, **ocr_n_chars**, **ocr_has_brand_mention** (0/1). For brand mentions use case-insensitive matching to brand_name in brands.csv after normalising punctuation/whitespace; document limitations. Store numerical summaries rather than full transcriptions in the feature table.

6. **D's monthly aggregation.** Start from the frozen sample manifest and left-join one-to-one by image_id to CLIP, YOLO and OCR results. Check duplicates and coverage; do **not** turn a failed image/model result into a zero count. Aggregate **one row per slug × month**, retaining **n_images**, availability/missingness indicators and the **mean of each numeric CLIP dimension, eight `clip_sem_*` scores, YOLO count and OCR feature over valid images**. Export outputs/images/monthly_image_features.parquet (or CSV) and a feature dictionary. These values describe the sampled images, not all Instagram content.

7. **E's forecasting input.** At origin month **t**, use image features from **t and earlier only**; never use t+1 or later. Use image summaries over **t−2 to t** as the default three-month history, with explicit handling for missing brand-months. During tuning, fit imputation, scaling, PCA, feature selection and regressions **within each CV training fold only**; for final evaluation, fit on the fixed outer train rows and apply without refitting to locked test. Use B's exact target and evaluation rows.

8. **Within-brand visual change (E; secondary compact model).** At each brand/origin **t**, compute `clip_visual_change = 1 − cosine_similarity` between the **monthly mean CLIP vector at t** and the **mean of available monthly CLIP vectors at t−2 and t−1**. L2-normalise both comparison vectors for this cosine calculation; use raw CLIP feature dimensions (not full-series PCA). Require a valid current month and at least one valid prior month; otherwise set this feature **missing**, not zero, and impute only inside the relevant training fold if necessary. This is a lagged **visual-composition change proxy**, not proof of a new product launch or causal sales/search impact. Avoid silently dropping matched test brand–origin rows. Pair it with the fixed eight `clip_sem_*` feature summaries and the same Trends predictors for the single compact secondary comparison.

**Delivery dependencies:** C publishes the frozen sample by **25 Nov**, both complete per-image CLIP/YOLO tables by **28 Nov**, and documentation by **29 Nov**. D runs OCR as soon as the sample is frozen, then integrates C's completed files and delivers the monthly features to E by **29 Nov**. If an embeddings file is too large for GitHub, share it via the group Drive and document the exact Drive location and schema in the repo. Any changes to this contract must be agreed by affected members before downstream work begins.

**Cross-brand Trends caution:** Each Google Trends series may be scaled to 0–100 independently; 19 brands use Topics and 11 use search queries. Raw values are **not comparable absolute search volumes across brands**. Analyse within-brand changes, document the limitations of cross-brand ranking, and do not equate predicted search attention with sales.

## 5. Timeline

| Date (2026) | Checkpoint |
| --- | --- |
| **25 Nov** | B and E confirm the target and data split; C shares the frozen post-level sample manifest with D |
| **28 Nov** | C delivers both CLIP/YOLO feature files to D for integration |
| **29 Nov** | B, C and D complete and upload their outputs |
| **1 Dec** | Independent reviews due: E→B, B→C and C→D |
| **2 Dec** | A decides whether the optional new-brand data collection is feasible/required and confirms any paid access |
| **3 Dec** | E completes model comparison, evaluation and forecasts; A receives results |
| **5 Dec** | A completes brand analysis; D→E independent review due |
| **6 Dec** | Figures, slides and video ready for final review |
| **7 Dec** | Presentation video submission |
| **11 Dec** | Final presentation (10-minute presentation + 5-minute Q&A) |
| **18 Dec** | Final IEEE report (maximum 4 A4 pages) |

Please commit incremental intermediate outputs **before** the due dates so downstream members are not blocked. Reviews are required in a fresh AI session, preferably with a different model, and recorded in the repository.

## 6. How each member should start with their coding agent

Clone this repository and give your agent the instruction below, replacing [ROLE] with **B, C, D, or E**:

~~~text
Read README.md and AGENTS.md in this repository thoroughly. I am responsible for workstream [ROLE] in Section 3.

First inspect the actual available inputs and identify any dependencies that are missing. Extract Google Trends.zip before using the paths in brands.csv. Implement only my assigned workstream, using the specified output paths and join keys. Test your code internally, then run and verify the full eligible data; intermediate test results do not need to be submitted separately.

Do not fabricate outputs, data-quality claims, evaluation metrics or results. Keep model versions, data coverage, exact run commands, and any limitations in the workstream notes. Commit code and small derived outputs to my own branch; do not commit raw images, large files or credentials. Independently review my assigned peer's work using a fresh session or a different LLM per Section 7 and submit a review file within two days of their final output. Return filenames, actual metrics and blockers.
~~~

Team members can implement in Colab, locally, or another suitable environment. Each owns the code, evidence and results for their workstream; an AI agent may help implement it but **must not substitute imaginary results for execution**.

## 7. Common quality requirements

- Keep reproducible scripts/notebooks, package requirements and exact model checkpoints.
- Preserve raw inputs. Do not manually edit results to make metrics look better.
- Split chronologically **before** fitting preprocessing, feature selection, normalisation, PCA or predictive models. During B/E tuning, enforce the **purged month-grouped expanding-window CV** specified in Section 4; random brand-month K-fold is not allowed.
- Fix a random seed where applicable and report sample counts by brand/month.
- Do not train on target values **unavailable at the validation/test forecast time**; enforce the three-month target-label availability rule and origin-month purges. Train/test fairness matters more than fitting a convenient number of rows.
- If image features fail to improve the baseline, **report that result honestly** and investigate errors.
- Independently verify a sample of image-model outputs and regenerate numerical tables from code. Follow the formal cross-review assignments below.
- Work on a separate branch and open a pull request, so other members can review the changes.
- Do not commit copyrighted raw Instagram images, personal data, tokens, passwords or oversized files. Keep large datasets in the group-shared Drive.
- Keep relevant AI session transcripts and verification notes for the coursework submission.

### Mandatory independent cross-checks

The lecturer requires verification of coding-agent output. **Do not use the original implementation chat as the review.** Start a fresh AI session, ideally with a **different LLM**, and independently check the other member's submitted code, methods, generated files and selected numerical outputs. The reviewer should rerun a small independent check where feasible, inspect source-vs-output consistency, identify data leakage or schema mismatches, and write a short evidence-based review. The author fixes issues and records resolutions before the work is considered verified.

| Reviewer | Workstream reviewed | Main outputs due | Review deadline |
| --- | --- | --- | --- |
| **B** | **C** — sample, CLIP/YOLO and coverage | 29 Nov | **1 Dec** |
| **C** | **D** — OCR and merged monthly features | 29 Nov | **1 Dec** |
| **D** | **E** — model split, metrics, comparisons and forecasts | 3 Dec | **5 Dec** |
| **E** | **B** — Trends/targets, baselines, scaling caveats | 29 Nov | **1 Dec** |

Reviews must be completed within **two days of the relevant final handoff**. Save as `reviews/B_reviews_C.md`, `reviews/C_reviews_D.md`, `reviews/D_reviews_E.md`, `reviews/E_reviews_B.md`. Each review records: independent reviewer and tool/session, files checked, test commands or recalculations performed, factual findings, open issues and author fixes. Report actual observations; never sign off unseen results.

## 8. Final deliverables

A concise, evidence-backed final package: dataset and method summary; matched-history and extended-history Trends baselines; multimodal forecasts on a shared test set; MAE/rank evaluation; visual-feature findings; rising/declining brand watchlist; business recommendations (plus optional new-brand cases where feasible/required); source code and independent-review evidence; presentation video and final report.

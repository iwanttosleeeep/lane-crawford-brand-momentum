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
| **Other collection code** | See src/collection/README.md | Earlier brand-selection and Google Trends retrieval/finalisation scripts remain to be restored |

**Instagram dataset:** 22,850 downloaded images across 30 brands. See the included manifest for image metadata.

Do not upload the full image ZIP, extracted images, large embeddings, raw Apify exports, or pretrained model weights to GitHub. Raw exports may include captions or personal information; only the original **Apify input settings** and privacy-safe collection scripts are versioned. Small tables, reproducible code, figures, and technical notes belong here. Ignore irrelevant Mac archive entries such as `.DS_Store` and `__MACOSX/` when reading the Trends ZIP; re-zipping is optional.

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

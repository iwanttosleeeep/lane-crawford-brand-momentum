# Lane Crawford Brand Discovery — STAT6207 Final Project

CUHK STAT6207 Applied Deep Learning · Group 14 · Topic 2: Lane Crawford Brand Discovery

## 1. Project objective

**Research question:** Can features extracted from brands' Instagram images using pretrained deep learning models improve forecasts of future Google Trends interest, compared with a Trends-only baseline?

We study **30 existing Lane Crawford brands**. The core deliverable is an evaluated forecast and a **rising / declining brands watchlist**, supported by image-feature analysis and commercial interpretation. After validating the approach, investigate a small number of potential new brands not currently sold by Lane Crawford for a discovery case study.

**Pipeline:** Instagram posts → pretrained CLIP / YOLO / OCR → brand-month image features; historical Google Trends → prediction targets and baseline; combine both → multimodal forecasting → quantitative evaluation → brand analysis.

**Primary prediction target (proposed):** For brand b at forecast origin month t,

y(b,t) = log(1 + mean Google Trends during t+1 to t+3) − log(1 + mean Google Trends during t−2 to t).

This predicts the change between the **next three months** and **previous three months** of average search interest. B and E must jointly confirm and freeze this exact definition before modelling; do not independently implement different targets.

**Evaluation:** chronological train/test split targeting the course's 80/20 requirement; MAE on the forecast target and Spearman correlation of predicted vs. observed brand growth rankings. Evaluate both model families on **exactly the same forecast origins and held-out data**.

## 2. Available data and access

| Resource | Location | Notes |
| --- | --- | --- |
| **brands.csv** | This repository root | 30 selected brands, brand slug, category, official Instagram handle, Google Trends query/topic, expected Trends filename and valid-from date |
| **Google Trends.zip** | This repository root | Extract the ZIP; its 30 CSVs are in `Google Trends/`, matching `brands.csv` |
| **images.zip** (~3.7 GB) | **Google Drive link shared privately in the group chat** | Instagram images organised by account, plus a download manifest. Not stored in GitHub |
| **download_images.py** and original Apify JSON exports | Ask A / shared Drive archive | Provenance and reproduction reference; model users normally only need the image ZIP and manifest |

**Instagram dataset:** 22,850 downloaded images across 30 brands. See the included manifest for image metadata.

Do not upload the full image ZIP, extracted images, large embeddings, raw exports, or pretrained model weights to GitHub. Small tables, reproducible code, figures, and technical notes belong here.

## 3. Team responsibilities

The owner labels are **A–E**; members B–E should claim their role in the group chat.

### A — Data collection and business analysis (already assigned)

**Already done:** Select the 30 brands; collect and download Instagram images; provide the brand list and Google Trends archive.

**Remaining work:**
- Share image ZIP and the data manifest with the group and confirm teammates can access them.
- Clarify brand/Instagram handle mappings and missing-file questions.
- After E produces validated forecasts, prepare a concise interpretation of rising/declining brands, visual themes, and Lane Crawford relevance.
- For discovery, identify and verify a small shortlist of potential new brands **not listed as currently sold by Lane Crawford**; use the final model and visual evidence to assess them if sufficient corresponding input data can be collected.

**Deliverable:** Data handoff plus a short, evidence-linked business recommendations section. A is **not** responsible for training the baseline or running image models.

### B — Google Trends, target construction, and baseline forecasting

**Inputs:** brands.csv; Google Trends.zip.

**Tasks:**
1. Extract the Trends ZIP and merge the 30 brand series by **slug and month**. Verify month continuity, validity dates, numeric fields, and query/topic choices. Handle the pre-validity entries for **Nothing** as unavailable, not observed zero.
2. Exclude incomplete November 2026 from measured monthly targets. Document the geographic scope and scaling/query limitations of the extracted series.
3. Agree with E on the three-month log-change target, chronological forecast origins, and **one shared train/validation/test protocol** before fitting any model. Labels require three *future* complete months; disallow label overlap/leakage across the training/testing boundary.
4. Implement two Trends-only baselines: (a) persistence / no-change; (b) regularised Ridge using historical Trends lags, rolling means and recent changes.
5. Fit preprocessing and hyperparameters using training data only. Report held-out MAE and month-by-month brand-rank Spearman where meaningful; preserve exact test predictions.

**Required outputs:**
- outputs/trends/trends_monthly.csv — slug, month, trend_value, valid_from (plus documented source metadata).
- outputs/trends/targets_and_split.csv — slug, origin_month, target_growth, split (and any historical features).
- outputs/trends/baseline_predictions.csv — slug, origin_month, y_true, y_pred, model.
- outputs/trends/baseline_metrics.csv and outputs/trends/README.md — metrics, plots, assumptions, decisions and run instructions.

**Required handoff by 25 Nov:** Confirm the final target and split with E before either model is finalised.

### C — CLIP and YOLO feature extraction

**Inputs:** images.zip; image manifest; brands.csv.

**Tasks:**
1. Check image files against the manifest and exclude failed/missing entries. Create **one deterministic image sample** to be used by C and D, using up to **10 images per brand-month** and a fixed seed. Sample from available images, preserve dates/months, and report coverage. Freeze this file by **25 Nov**; D must not resample independently.
2. Run **pretrained CLIP** on the sampled images for visual embeddings and/or compact semantic features (e.g., CLIP ViT-B/32). Record the exact checkpoint, image preprocessing and output dimensions; do not fit PCA using the full dataset.
3. Run **pretrained YOLO** (e.g., YOLO11n) on the **same sample** to extract interpretable object-class counts/presences. Record checkpoint, confidence threshold and classes; note that a generic object detector may not recognise specialised luxury-product categories.
4. Save **per-image** features (not only monthly summaries), identify missing/broken files, and perform a small visual spot-check of detections/semantic outputs.
5. Provide a simple reproducible run command or notebook. Reuse an available GPU when possible; do not require each member to process all 22,850 files.

**Required outputs:**
- outputs/images/sample_manifest.csv — **image_id, file, handle, slug, shortCode, slide, timestamp, month**; set image_id equal to the manifest-relative **file** path (e.g., handle/shortCode_slide.jpg), and ensure one unique row per image.
- outputs/images/clip_features.parquet (or CSV) — one row per sampled image, keyed by image_id.
- outputs/images/yolo_features.parquet (or CSV) — one row per sampled image, keyed by image_id.
- outputs/images/clip_yolo_notes.md — model versions, sample coverage, feature definitions, QC and reproducible commands.

**Required handoffs:** Send D the frozen **sample_manifest.csv** by **25 Nov** and both complete **per-image CLIP and YOLO feature files** by **28 Nov**, so D can integrate them. Final C documentation/QC is due **29 Nov**.

### D — OCR and monthly feature integration

**Inputs:** C's exact sample_manifest.csv; the corresponding image files; C's CLIP/YOLO outputs.

**Tasks:**
1. Run **pretrained OCR** (e.g., EasyOCR English) on **exactly the images listed in C's frozen sample_manifest.csv**. Derive compact numeric features such as has_text, number of detected text regions, total characters, or presence of the brand name. Record the OCR library/model and preprocessing.
2. Save per-image OCR features keyed by image_id. Avoid publishing unnecessary transcribed text or personal content.
3. Implement the merge/aggregation code independently while C processes CLIP/YOLO, then join the completed per-image files when C uploads them by **28 Nov**. Join using **image_id** (equal to file path), then aggregate into **one row per slug × month**. Preserve **n_images** and missingness and check that no images or months are accidentally duplicated.
4. Keep an explicit feature dictionary and describe how high-dimensional CLIP features are handled. If using PCA or scaling as a fitted step for predictions, **fit only on training data** in E's modelling pipeline, not on the whole dataset.
5. Validate that every image used at forecast origin t was published on or before t. Any rolling image-window features must be formed from past data only.

**Required outputs:**
- outputs/images/ocr_features.parquet (or CSV), keyed by image_id.
- outputs/images/monthly_image_features.parquet (or CSV) — slug, month, n_images plus numeric feature columns.
- outputs/images/feature_dictionary.md and outputs/images/integration_checks.md — schema and verification results.

**Due:** Complete OCR features and integrated monthly image features by **29 Nov**. Do not wait for C's final documentation to start OCR.

### E — Multimodal prediction, evaluation, and results

**Inputs:** B's targets/splits and baseline predictions; D's monthly_image_features; brands.csv.

**Tasks:**
1. **Coordinate with B by 25 Nov** to freeze the target, training/validation/test months and exact evaluation observations. Forecast input at t may use only historical Trends and images available by t.
2. Train a simple, regularised **Trends + image features** model (start with Ridge/Elastic Net or comparable model suitable for the sample size). Use the **same test origins** as B. Fit scaling/PCA/feature selection only on training data.
3. Compare: Trends-only baseline; Trends + CLIP; Trends + CLIP + YOLO; Trends + CLIP + YOLO + OCR. If a model is infeasible, record why rather than inventing results.
4. Report held-out MAE, rank correlation by forecast month, and error analysis; include plots of predictions vs actuals and a rising/declining watchlist. A complex LSTM or dashboard is **not required** for the first reproducible result.
5. After evaluation is frozen, refit the chosen specification on all available **eligible historical observations** and generate future forecasts. Keep actual observed values separate from predictions.
6. Hand off validated figures, comparison results and interpretation notes to A for commercial analysis.

**Required outputs:**
- outputs/models/model_comparison.csv — tested model names, data coverage, MAE and rank metrics.
- outputs/models/test_predictions.csv — slug, origin_month, y_true, y_pred, model.
- outputs/models/future_forecasts.csv — slug, forecast_origin, predicted_growth, model.
- outputs/models/figures/ and outputs/models/README.md — plots, evaluation protocol, error analysis, reproducible commands.

**Due:** Validated model comparison and figures by **3 Dec**.

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

### Fixed feature-extraction contract (C, D and E)

**Follow this contract directly rather than letting separate agents design incompatible features.** The three pretrained models are feature extractors, not competing forecasting models. C runs CLIP + YOLO; D runs OCR and integrates their results; E performs prediction and evaluation. Internal testing is not a separate team deliverable.

1. **Shared image sample (C; due 25 Nov).** Use only successfully downloaded, existing images listed in the download manifest. Select **up to 10 images per slug × calendar month** using a deterministic random seed (**42**), without replacement. Derive month as YYYY-MM from the original UTC timestamp. Freeze one outputs/images/sample_manifest.csv with exactly these columns: **image_id, file, handle, slug, shortCode, slide, timestamp, month**. Define **image_id = file**, where file is the original relative image path; ensure uniqueness. C and D must process **exactly the same image_ids** and must not independently resample or silently exclude brands/months. Log corrupted/missing images.

2. **Shared model settings.** Use pretrained inference (evaluation mode), without fine-tuning. Record the model checkpoint, versions, preprocessing, confidence threshold and number of valid images; apply the same settings across all brands for each model. Recommended defaults unless members agree and document a change before processing: **CLIP ViT-B/32**, **YOLO11n pretrained on COCO**, **EasyOCR English**.

3. **CLIP per-image output (C).** One row per image_id, with a fixed-length visual embedding in columns **clip_000, clip_001, ...** in consistent order. State embedding dimension and checkpoint in clip_yolo_notes.md. No PCA/normalisation fitted across the full dataset; train-only fitting belongs to E.

4. **YOLO per-image output (C).** One row per image_id, including **yolo_n_detections** and detection counts for every COCO class as **yolo_<class>_count**, with snake_case class names and a consistent model-wide confidence threshold (default **0.25**). Classes with no detections are zero, not omitted columns. Generic COCO classes cannot distinguish every luxury product or brand.

5. **OCR per-image output (D).** One row per image_id, including **ocr_has_text** (0/1), **ocr_n_regions**, **ocr_n_chars**, **ocr_has_brand_mention** (0/1). For brand mentions use case-insensitive matching to brand_name in brands.csv after normalising punctuation/whitespace; document limitations. Store numerical summaries rather than full transcriptions in the feature table.

6. **D's monthly aggregation.** Start from the frozen sample manifest and left-join one-to-one by image_id to CLIP, YOLO and OCR results. Check duplicates and coverage; do **not** turn a failed image/model result into a zero count. Aggregate **one row per slug × month**, retaining **n_images**, availability/missingness indicators and the **mean of each numeric CLIP dimension, YOLO count and OCR feature over valid images**. Export outputs/images/monthly_image_features.parquet (or CSV) and a feature dictionary. These values describe the sampled images, not all Instagram content.

7. **E's forecasting input.** At origin month **t**, use image features from **t and earlier only**; never use t+1 or later. Use image summaries over **t−2 to t** as the default three-month history, with explicit handling for missing brand-months. Fit imputation, scaling, PCA, feature selection and regressions **on the training set only**, then apply to validation/test. Use B's exact target and evaluation rows.

**Delivery dependencies:** C publishes the frozen sample by **25 Nov**, both complete per-image CLIP/YOLO tables by **28 Nov**, and documentation by **29 Nov**. D runs OCR as soon as the sample is frozen, then integrates C's completed files and delivers the monthly features to E by **29 Nov**. If an embeddings file is too large for GitHub, share it via the group Drive and document the exact Drive location and schema in the repo. Any changes to this contract must be agreed by affected members before downstream work begins.

**Cross-brand Trends caution:** Each Google Trends series may be scaled to 0–100 independently; 19 brands use Topics and 11 use search queries. Raw values are **not comparable absolute search volumes across brands**. Analyse within-brand changes, document the limitations of cross-brand ranking, and do not equate predicted search attention with sales.

## 5. Timeline

| Date (2026) | Checkpoint |
| --- | --- |
| **25 Nov** | B and E confirm the target and data split; C shares the final sample manifest with D |
| **28 Nov** | C delivers both CLIP/YOLO feature files to D for integration |
| **29 Nov** | B, C and D complete their assigned work and upload final outputs |
| **3 Dec** | E completes model comparison, evaluation and forecasts; A receives the results |
| **5 Dec** | A completes brand analysis and business recommendations |
| **6 Dec** | Figures, slides and video ready for final review |
| **7 Dec** | Presentation video submission |
| **11 Dec** | Final presentation (10-minute presentation + 5-minute Q&A) |
| **18 Dec** | Final IEEE report (maximum 4 A4 pages) |

Please commit incremental intermediate outputs **before** the due dates so downstream members are not blocked.

## 6. How each member should start with their coding agent

Clone this repository and give your agent the instruction below, replacing [ROLE] with **B, C, D, or E**:

~~~text
Read README.md and AGENTS.md in this repository thoroughly. I am responsible for workstream [ROLE] in Section 3.

First inspect the actual available inputs and identify any dependencies that are missing. Extract Google Trends.zip before using the paths in brands.csv. Implement only my assigned workstream, using the specified output paths and join keys. Test your code internally, then run and verify the full eligible data; intermediate test results do not need to be submitted separately.

Do not fabricate outputs, data-quality claims, evaluation metrics or results. Keep model versions, data coverage, exact run commands, and any limitations in the workstream notes. Commit code and small derived outputs to my own branch; do not commit raw images, large files or credentials. Return the filenames created, actual metrics observed and any blockers.
~~~

Team members can implement in Colab, locally, or another suitable environment. Each owns the code, evidence and results for their workstream; an AI agent may help implement it but **must not substitute imaginary results for execution**.

## 7. Common quality requirements

- Keep reproducible scripts/notebooks, package requirements and exact model checkpoints.
- Preserve raw inputs. Do not manually edit results to make metrics look better.
- Split chronologically **before** fitting preprocessing, feature selection, normalisation, PCA or predictive models.
- Fix a random seed where applicable and report sample counts by brand/month.
- Don't train and evaluate on overlapping future target information; train/test fairness matters more than fitting a convenient number of rows.
- If image features fail to improve the baseline, **report that result honestly** and investigate errors.
- Independently verify a sample of image-model outputs and regenerate numerical tables from code.
- Work on a separate branch and open a pull request, so other members can review the changes.
- Do not commit copyrighted raw Instagram images, personal data, tokens, passwords or oversized files. Keep large datasets in the group-shared Drive.
- Keep relevant AI session transcripts and verification notes for the coursework submission.

## 8. Final deliverables

A concise, evidence-backed final package: dataset and method summary; baseline and multimodal forecasts on a shared test set; MAE/rank evaluation; visual-feature findings; rising/declining brand watchlist; business recommendations and selected new-brand cases; code/reproducibility materials; presentation video and final report.

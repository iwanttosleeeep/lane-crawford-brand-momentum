# Independent review — Member C: CLIP and YOLO feature extraction

**Review date:** 2026-11-27  
**Repository:** `https://github.com/iwanttosleeeep/lane-crawford-brand-momentum`  
**Reviewed commit:** `90ed4fe` on `origin/main` (merge of `codex/workstream-c-sample`)  
**Scope:** C's committed deliverables under `outputs/images/` and the README section “C — CLIP and YOLO feature extraction”.

## Method

- Fetched the latest remote refs with `git fetch origin`.
- Extracted the exact committed blobs from `origin/main` with `git archive origin/main outputs/images README.md` into `C:\Users\LINVI\AppData\Local\Temp\opencode\review-c`.
- Wrote and ran an independent Python verifier using `pandas`, `numpy` and `pyarrow`:
  `C:\Users\LINVI\AppData\Local\Temp\opencode\verify_c_independent.py`.
- Did **not** use C's verification scripts or accept C's notes as evidence. Notes were checked against the actual files.
- Did **not** modify any committed repository file. Final `git status --short --branch` remained `## workstream-B...origin/workstream-B` plus the pre-existing untracked `Google Trends/`.
- Did **not** rerun CLIP/YOLO inference. `images.zip`, the original `manifest_trudon.csv`, model weights and local QC contact sheets are not available locally.

A copy of the verifier is saved beside this report as `D:\lane-crawford-review\verify_c_independent.py`.

---

## Check-by-check result

| # | Check | Result | Key evidence |
|---|---|---|---|
| 1 | `sample_manifest.csv` | **PASS** | 5,863 rows; 0 duplicate `image_id`; 0 byte-level `image_id != file` mismatches; 30 slugs; 25 months; max 10 distinct `shortCode` per `(slug, month)`; 0 duplicate `(slug, month, shortCode)` rows |
| 2 | `sample_coverage.csv` | **PASS** | 750 rows; 750 unique `(slug, month)` pairs; 30 brands × 25 months; exactly 15 rows with `eligible_posts=0` and `missing_month=1`; 0 zero/unflagged or flagged/nonzero inconsistencies; `selected_images` sum = 5,863; 0 per-brand-month mismatches vs manifest |
| 3 | SHA-256 integrity | **PASS** | All three recomputed hashes match the values stated in `clip_yolo_notes.md` |
| 4 | `clip_features.parquet` | **PASS** | 5,863 rows; `image_id` + 512 `clip_*` embeddings + 8 `clip_sem_*` columns; no extra columns; 0 duplicate IDs; ID set and row order match manifest; 0 NaN/Inf; semantic range `[0.0867758244, 0.3181831539]`; 0 values outside `[-1,1]`; 0 zero-norm embeddings; min embedding norm `7.090087` |
| 5 | `yolo_features.parquet` | **PASS** | 5,863 rows; `image_id` + `yolo_n_detections` + 80 `yolo_<class>_count` columns; no extra columns; ID set and row order match manifest; 0 non-integral, negative or non-finite values; 0 rows where class counts disagree with `yolo_n_detections`; total detections = 18,452; 1,026 zero-detection images; COCO class list matches `feature_run.json` |
| 6 | C's QC JSON cross-check | **PASS, with caveats** | All independently computable fields matched: `feature_checks.json` 11/11, `sample_checks.json` 11/11, `feature_run.json`/notes all table-verifiable fields. Some recorded QC fields cannot be recomputed without raw images/model weights and are listed below |
| 7 | README section C outputs/schema | **PASS** | All four required files exist; `sample_manifest.csv` has the exact required columns `image_id, file, handle, slug, shortCode, slide, timestamp, month`; CLIP and YOLO have one row per sampled image keyed by identical `image_id`; 8 semantic columns are in the same CLIP file |

---

## Detailed evidence

### 1. Sample manifest

`outputs/images/sample_manifest.csv` was read as strings with NA conversion disabled to preserve exact bytes.

- Rows: **5,863**
- Columns, in exact order: `image_id`, `file`, `handle`, `slug`, `shortCode`, `slide`, `timestamp`, `month`
- Unique `image_id`: **5,863**
- Byte-level mismatches between `image_id` and `file`: **0**
- Distinct slugs: **30**
- Distinct months: **25**
- Maximum distinct `shortCode` values within any `(slug, month)`: **10**
- Duplicate `(slug, month, shortCode)` rows: **0**

### 2. Coverage

`outputs/images/sample_coverage.csv` has **750** rows and **750** unique `(slug, month)` pairs.

- Brands: **30**
- Months: **25**
- Rows with `eligible_posts == 0` and `missing_month == 1`: **15**
- Zero-eligible rows not flagged: **0**
- Flagged rows with nonzero eligible posts: **0**
- Sum of `selected_images`: **5,863**
- Per-brand-month discrepancies against counts recomputed from `sample_manifest.csv`: **0**

The 15 flagged missing brand-months are preserved in the coverage table, not silently dropped.

### 3. SHA-256 integrity

| File | Stated in notes | Recomputed | Match |
|---|---|---|---|
| `sample_manifest.csv` | `34a39dd2b5829aa7b13edd5e9b7f285966757322a769f9124ffd056f6cea939d` | same | **YES** |
| `clip_features.parquet` | `9332165c1d7eea06972f48c802db5858381d7b8733358e2c4046e003daeef61e` | same | **YES** |
| `yolo_features.parquet` | `6609bd86e12f1bd8e2ba00a6ae6e3c70a7b59b054006a7aa8f940220b66c97c0` | same | **YES** |

The notes also state CLIP file size **16,490,093** bytes and YOLO file size **131,069** bytes; actual sizes are **16,490,093** and **131,069** bytes respectively.

### 4. CLIP features

- Rows: **5,863**
- Columns: **521** total = `image_id` + 512 embeddings (`clip_000` … `clip_511`) + 8 `clip_sem_*`
- Extra/unexpected columns: **none**
- Duplicate `image_id`: **0**
- ID set identical to `sample_manifest.csv`: **yes**
- Row order identical to `sample_manifest.csv`: **yes**
- Non-finite numeric values: **0**
- `clip_sem_*` minimum: **0.0867758244**
- `clip_sem_*` maximum: **0.3181831539**
- Semantic values outside `[-1,1]`: **0**
- Zero embedding norms: **0**
- Minimum embedding norm: **7.090087**

The eight semantic column names exactly match the prompt keys in `feature_run.json`.

### 5. YOLO features

- Rows: **5,863**
- Columns: **82** total = `image_id` + `yolo_n_detections` + 80 `yolo_<class>_count`
- Extra/unexpected columns: **none**
- Duplicate `image_id`: **0**
- ID set identical to `sample_manifest.csv`: **yes**
- Row order identical to `sample_manifest.csv`: **yes**
- Non-finite values: **0**
- Non-integral count values: **0**
- Negative count values: **0**
- Rows where the 80 class counts do not sum to `yolo_n_detections`: **0**
- Total `yolo_n_detections`: **18,452**
- Total of all class counts: **18,452**
- Images with zero detections: **1,026**
- The 80 class-count columns correspond exactly to the 80 COCO classes recorded in `feature_run.json`.

### 6. Cross-check of C's recorded QC

#### `feature_checks.json`

11 independently computable fields matched exactly:

- `sample_rows = 5,863`
- `clip_rows = 5,863`
- `yolo_rows = 5,863`
- `clip_embedding_dimensions = 512`
- `clip_semantic_dimensions = 8`
- `yolo_classes = 80`
- `missing_ids = 0`
- `duplicate_ids = 0`
- `nonfinite_values = 0`
- `qc_images = 8` (rows in `feature_qc.csv`)
- `sample_sha256 = 34a39dd2…ea939d`

Fields that could not be independently recomputed from committed tables:

- `max_semantic_recalculation_error = 3.2782554626464844e-07` — requires CLIP text encoder/model weights.
- `repeated_yolo_count_matches = 8` — requires a fresh YOLO run on the raw images.

#### `sample_checks.json`

11 independently computable fields matched exactly:

- `sample_sha256`, `selected_images`, `sampled_brands`
- `coverage_month_start = 2024-11`, `coverage_month_end = 2026-11`
- `brand_months = 750`, `missing_brand_months = 15`
- `selected_by_brand` — all 30 per-brand counts match the manifest exactly
- `excluded_rows = 32` and `exclusion_reasons = {"download_failed": 32}` from `sample_exclusions.csv`
- `brands_sha256 = 1684489c…f7b7f3e`

The last value is the **CRLF Windows working-copy** SHA-256 of the committed `brands.csv`. The raw Git blob hash is `89cb00e794ef8e00f99b304fff728b5c7a21aceb13914c9126c303171b5855fe`; converting line endings to CRLF yields exactly the recorded `1684489c41d5a8aa2b60987a519a94111f49bf0c779e4ab2677d4878fd7b7f3e`. This is a line-ending/provenance caveat, not a content discrepancy.

Fields not verifiable without the original manifest/raw image dataset:

- `seed`, `per_month`, `input_manifest`, `input_manifest_sha256`
- `source_rows = 22,882`, `unique_manifest_files = 22,882`
- `disk_image_files = 22,850`, `unlisted_image_files = 0`, `unlisted_files = []`
- `valid_images = 22,850`, `distinct_posts = 7,002`
- `python = 3.12.14`, `pillow = 13.0.0`

#### `feature_run.json` and notes

All table-verifiable values matched:

- Sample and feature hashes
- Row counts and dimensions
- `yolo.total_detections = 18,452`
- `yolo.images_with_no_detections = 1,026`
- `yolo.top_classes` — independently recomputed top-12 class-count sums match exactly
- CLIP prompt keys match the eight `clip_sem_*` columns
- CLIP and YOLO file sizes match the notes

Not verifiable here: model weight hashes, model/revision strings, preprocessing details, confidence/IoU/threshold settings, elapsed runtimes, `run_fingerprint`, and version strings. These are recorded consistently but require external artifacts to reproduce.

### 7. README required outputs and schema

Required files from README section C:

- `outputs/images/sample_manifest.csv` — exists, exact 8-column schema, one unique row per image
- `outputs/images/clip_features.parquet` — exists, one row per sampled image, keyed by `image_id`, contains 512 original CLIP dimensions plus 8 `clip_sem_*` columns in the same file
- `outputs/images/yolo_features.parquet` — exists, one row per sampled image, keyed by `image_id`
- `outputs/images/clip_yolo_notes.md` — exists and contains model versions, coverage, feature definitions, QC and commands

The join key is consistent: all three per-image tables have the same 5,863 unique `image_id` values in the same order.

---

## Discrepancies and risks

1. **No blocking discrepancy** was found in the committed sample, features, hashes or schemas.
2. `sample_checks.json` uses a CRLF working-copy hash for `brands.csv` rather than the raw Git blob hash. Content is consistent, but the recorded hash is platform-dependent and should be interpreted accordingly.
3. **First-slide rule not independently verified.** Verifying the smallest numeric slide index per post requires the original `manifest_trudon.csv` and raw image files. The committed manifest only shows the selected result.
4. **Source-level claims not independently verified.** Original manifest row counts, unique file counts, disk image counts, unlisted files, valid-image counts, distinct-post counts and exclusion provenance cannot be checked beyond the committed `sample_exclusions.csv`.
5. **Visual spot-checks not reproducible.** The notes report 8 spot-check images and an ignored `.model-cache/qc/spot_check.jpg`; neither the raw images nor that contact sheet are committed.
6. **Inference reproduction not attempted.** CLIP/YOLO weights and `images.zip` are unavailable, and the task explicitly forbids rerunning inference.
7. **Semantic recomputation error and repeated YOLO match not independently verified.** The recorded `3.2783e-7` semantic error and 8/8 YOLO repeat matches require model weights and raw images.
8. **Environment/version claims not independently verified.** Python 3.12.14, Pillow 13.0.0, torch/transformers/Ultralytics versions and model hashes are recorded but not reproducible from the committed tables alone.

---

## Overall verdict

**Accept C's handoff to D for integration.** The committed sample manifest, coverage table and CLIP/YOLO feature tables pass every check that can be performed from the repository contents. The interface is internally consistent: identical 5,863-image ID sets, exact schemas, correct per-image granularity, finite features, valid YOLO counts and correct SHA-256 integrity.

Acceptance is **conditional in the evidential sense**: source-manifest checks, first-slide verification, visual spot-checks and inference reproduction remain unverified because the raw image dataset, original manifest and model artifacts are not available. These are documentation/provenance limitations, not detected data errors. No committed-file discrepancy was found that would block D from proceeding.

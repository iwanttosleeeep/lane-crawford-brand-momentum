# C — frozen sample handoff to D

## Status and scope

The sample handoff and both complete per-image CLIP/YOLO feature files were
completed on 26 November 2026 by SunshineSs920959. This delivery includes the
frozen shared image list and the features D needs to integrate with OCR.
The repository instructions used were main commit
`85a12e1aa4cee07c3d1221ee0af6868d863b4d39`.

## Inputs and reproducibility

The source is A's extracted image dataset, with 30 account folders and
`manifest_trudon.csv` in the same root. Despite its filename, this manifest
contains all 30 brands. The brand mapping is the repository's `brands.csv`.
The original files were read without modification.

Executed environment: Python 3.12.14 and Pillow 13.0.0. Install the sampling
dependency with `python -m pip install -r src/images/requirements-sampling.txt`.
Run from the repository root, adjusting the image and manifest paths for the
local extraction location:

```powershell
python src/images/sample_images.py --images-root "C:\Users\Lenovo\Documents\images\images" --manifest "C:\Users\Lenovo\Documents\images\images\manifest_trudon.csv"
```

Only Pillow and the Python standard library are required for this stage.
`sample_checks.json` records source hashes, versions, and actual counts.

## Frozen sampling method

1. Map the manifest's `handle` to the unique `slug` in `brands.csv`.
2. Parse each timestamp as timezone-aware and derive its UTC calendar month.
   Reject conflicting timestamps, invalid metadata or unknown brand mappings.
3. Accept download statuses `ok` and `exists`. For each successful entry, check
   file existence, source SHA-256, Pillow verification and complete RGB decoding.
   Log failed or unreadable entries in `sample_exclusions.csv`.
4. Group valid images by `slug`, UTC `month` and `shortCode`. Select the smallest
   numeric slide index, breaking a tie by the original file path. Slide indices
   in the provided manifest start at zero and are retained unchanged.
5. Sort the candidate posts by `(shortCode, file)` in each brand-month. If more
   than ten are available, use Python `random.Random(f"42|{slug}|{month}")` to
   sample ten without replacement. Otherwise retain every candidate. This
   group-specific seed makes results independent of source row order and other
   groups. Sort final rows by `(slug, month, shortCode, file)`.
6. Save exactly the agreed eight columns. `image_id` equals `file` byte-for-byte,
   preserving the original relative path, such as `aesop/DB80l0RxBan_0.jpg`.

Post identity determines distinctness. Different slides of one post cannot
occupy multiple sample slots. Identical content in separate posts is not used
as an additional exclusion criterion. Sampling does not use Trends values,
targets, model outputs or held-out metrics.

## Actual coverage

| Check | Result |
| --- | ---: |
| Original manifest rows | 22,882 |
| Unique manifest file paths | 22,882 |
| Successful download entries and actual image files | 22,850 |
| Failed-download entries excluded | 32 |
| Successful files with matching SHA-256 and readable pixels | 22,850 |
| Additional missing, corrupt or hash-mismatched successful files | 0 |
| Image files absent from manifest | 0 |
| Eligible distinct posts after file checks | 7,002 |
| Frozen sampled images / distinct sampled posts | 5,863 |
| Brands represented | 30 |
| Calendar months retained | 25 |
| Full brand-month coverage grid | 750 |
| Brand-months with no eligible image post | 15 |

Coverage spans November 2024 through November 2026. The latest source timestamp
is `2026-11-22T09:01:27.000Z`, so November 2026 is a partial collection snapshot.
It is preserved and flagged here for downstream availability decisions. A
complete month or future label must not be inferred from that snapshot.
All months, including the forecast-origin purge months, remain in the image
coverage table; E applies the locked forecasting split and past-only feature
windows. This sample list does not establish any target's availability.

The full zero-coverage list is:

| slug | Months without eligible posts |
| --- | --- |
| bang-olufsen | 2024-11, 2024-12, 2025-01, 2025-02 |
| marshall | 2024-11, 2024-12, 2025-01, 2025-02, 2025-03 |
| jo-malone-london | 2024-12 |
| stanley | 2024-11, 2024-12 |
| nothing | 2025-11 |
| teenage-engineering | 2025-05 |
| trudon | 2025-03 |

Marshall's first observed eligible image month is April 2025, rather than the
March start reported in README. Nothing, Teenage Engineering and Trudon also
have the additional gaps listed above. These are observations about the
provided dataset, not proof that the accounts published nothing or archived
their posts. `sample_coverage.csv` preserves all 750 brand-months, including
zero sampled-image counts. D should keep the corresponding image features
missing, with explicit availability indicators.

## Verification

- Full-source hash verification and image decoding completed for 22,850 files.
- A second complete run with identical inputs was checked for the same frozen
  sample bytes and the same coverage/exclusion counts.
- Source-to-output checks verified 5,863 unique IDs, one image per post,
  correct first slides, source timestamps, 30 brand mappings, at most ten posts
  per brand-month and consistency with all 750 coverage rows.
- Internal temporary fixtures exercised UTC month-boundary conversion,
  missing/corrupt first-slide fallback, failed-download exclusion, duplicate
  manifest rows, input-order invariance, repeatability and freeze protection.
- CLIP/YOLO verification results are recorded below. B's required independent
  review of C remains due by 1 December in a fresh review session. The checks
  in this implementation chat do not replace that review.

## Handoff and version control

Use `outputs/images/sample_manifest.csv` as the sole image list. D resolves each
`file` against their extraction root, e.g.
`<images-root>/aesop/DB80l0RxBan_0.jpg`. D can begin OCR from this list immediately.
The companion files are `sample_coverage.csv`, `sample_exclusions.csv` and
`sample_checks.json`. Image data stays in the shared dataset location.

Frozen sample SHA-256:
`34a39dd2b5829aa7b13edd5e9b7f285966757322a769f9124ffd056f6cea939d`.

The script refuses to replace an existing sample if its bytes would change.
Coordinate revisions with D before deliberately replacing a frozen manifest.
The completed features use this exact list with pretrained CLIP ViT-B/32 plus
the eight specified semantic scores in the same per-image feature file, and
YOLO11n COCO with confidence threshold 0.25. Details and QC follow.

## Fixed feature configuration

The following configuration and prompts were fixed before the inference run.
Features use the same frozen image list and retain its row order and `image_id`.

- CLIP is `openai/clip-vit-base-patch32`, fixed Hugging Face revision
  `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`. The official weight SHA-256 is
  `a63082132ba4f97a80bea76823f544493bffa8082296d62d71581a4feff1576f`.
- Image processing uses the checkpoint's slow `CLIPProcessor`, RGB conversion,
  bicubic shortest-edge resize to 224, 224-by-224 centre crop, rescaling by
  1/255, and checkpoint-provided channel means and standard deviations.
- `clip_000` through `clip_511` retain the full float32 projected image embedding,
  without PCA or fitted scaling. These projected vectors are saved before L2
  normalisation. Semantic scores use L2-normalised copies of these vectors
  and the matching text encoder's projected vectors. Scores are cosine
  similarities, not probabilities. One image encoder pass produces both outputs.
- YOLO is COCO-pretrained `yolo11n.pt`, from Ultralytics assets release `v8.3.0`.
  Weight SHA-256 is
  `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`.
  Prediction uses confidence 0.25, IoU threshold 0.7, maximum 300 detections,
  image size 640, square letterboxing (`rect=False`), no augmentation, and
  float32 CPU inference. All 80 snake_case COCO class-count columns are retained.
- Both models use pretrained evaluation/inference mode. CPU thread count is
  eight, with CLIP batch size 32 and YOLO batch size 16. Batch checkpoints are
  kept in the ignored `.model-cache` directory and checked against image IDs
  and the input/model/settings fingerprint when resuming.

| Semantic field | Exact English prompt |
| --- | --- |
| `clip_sem_product_closeup` | a photo of a close-up product on a simple background |
| `clip_sem_styled_interior` | a photo of a styled interior or home-lifestyle scene |
| `clip_sem_person_using` | a photo of a person wearing, holding or using a product |
| `clip_sem_outdoor_travel` | a photo of an outdoor or travel lifestyle scene |
| `clip_sem_gift_packaging` | a photo of wrapped gifts or festive product packaging |
| `clip_sem_text_graphic` | a photo of a typographic or promotional graphic |
| `clip_sem_material_detail` | a photo of a material or craftsmanship close-up |
| `clip_sem_product_group` | a photo of a curated display of several products |

Reproduce the feature stage from the repository root using Python 3.12:

```powershell
python -m venv .venv-c
.venv-c/Scripts/python.exe -m pip install -r src/images/requirements-features.txt
.venv-c/Scripts/python.exe src/images/prepare_models.py
.venv-c/Scripts/python.exe src/images/extract_features.py --images-root "C:\Users\Lenovo\Documents\images\images"
.venv-c/Scripts/python.exe src/images/verify_features.py --images-root "C:\Users\Lenovo\Documents\images\images"
```

On other systems, substitute that system's virtual-environment Python path and
the local image extraction root. Models are downloaded from the official OpenAI
Hugging Face repository and Ultralytics release assets. `prepare_models.py`
verifies the weight hashes. The feature command supports `--stage clip` and
`--stage yolo`. A limited smoke test must use a separate output directory,
for example `--limit 32 --output .model-cache/smoke`.

Model or image failures stop the run with the completed batches preserved for
resuming. A failed inference is never silently converted to zero detections or
a missing output row. Zero YOLO class counts denote completed inference with
no detection for that class. Missing brand-months are still described by the
original coverage table and must remain missing in D's aggregate features.

## Completed feature results and QC

Inference ran locally on an Intel Core Ultra 7 155H CPU (eight PyTorch threads),
using PyTorch 2.8.0+cpu, torchvision 0.23.0+cpu, Transformers 4.57.1,
Ultralytics 8.3.230, NumPy 2.3.5, pandas 3.0.1, pyarrow 21.0.0 and Pillow 13.0.0.
No fine-tuning, PCA, fitted feature scaling, target-based filtering or
hyperparameter selection was performed. Both full runs completed successfully.

| Check | Result |
| --- | ---: |
| CLIP rows | 5,863 |
| Original CLIP dimensions per image | 512 |
| CLIP semantic scores per image | 8 |
| YOLO rows | 5,863 |
| COCO class-count columns | 80 |
| Missing or duplicate image IDs in either file | 0 |
| Non-finite numeric values | 0 |
| Total YOLO detections at confidence 0.25 | 18,452 |
| Successfully processed images with no COCO detections | 1,026 |
| Maximum error recomputing all 46,904 semantic scores | 3.2783e-7 |
| Visual spot-check images across different brands | 8 |
| Spot-check YOLO counts matching a fresh inference | 8 of 8 |

The CLIP stage took 422.781 seconds and YOLO took 457.469 seconds, including
stage loading and output writing. Initial dependency/weight downloads, sample
integrity checks, smoke tests and final verification are additional. The
32-image smoke test also confirmed resume behavior and output schema. These
timings describe this machine and run, not a hardware benchmark.

`verify_features.py` checks every image ID against the frozen sample, exact
column names, finite values, nonzero CLIP vector norms, cosine bounds,
nonnegative integral YOLO counts, per-row detection totals and file hashes.
It re-encodes only the eight text prompts and recomputes all semantic scores
from the saved image embeddings; the maximum numerical error is shown above.
It then reruns YOLO on eight deterministic source images and renders a local
annotated contact sheet at `.model-cache/qc/spot_check.jpg`. That image remains
outside Git. `feature_qc.csv` records the checked image IDs, highest semantic
score and detection counts. No detection-accuracy percentage is inferred from
these eight examples.

Visual inspection found these concrete limitations:

- The Aesop bottles, people in the fashion/electronics images, Herman Miller
  chair and Jellycat plush toys produce broadly recognisable COCO detections.
- A decorative vertical detail on the Assouline book cover and dark neck detail
  in the Buccellati portrait were labelled `tie`. These are likely false
  positives. Generic counts are retained consistently instead of manually
  correcting selected brands.
- The Oura example is a text-only graphic and returns zero object detections,
  while its highest semantic score is `clip_sem_text_graphic`.
- Semantic scores reflect broad image composition and can be ambiguous for
  product packaging, book covers or mixed scenes. They are not ground-truth
  scene labels. Generic COCO detection does not recognise every luxury product
  category, such as rings, fragrances, specialised speakers or earbuds.

## Files for D

| File | Contents |
| --- | --- |
| `sample_manifest.csv` | Frozen 5,863-image list and brand/month keys |
| `clip_features.parquet` | `image_id`, 512 float32 `clip_*` dimensions, eight float32 `clip_sem_*` fields |
| `yolo_features.parquet` | `image_id`, integer `yolo_n_detections`, all 80 integer `yolo_<class>_count` fields |
| `feature_run.json` | Model versions, preprocessing, exact prompts, thresholds, runtime, class order and feature hashes |
| `feature_checks.json` | Full-table numerical and key checks |
| `feature_qc.csv` | Eight representative source-image checks |
| `sample_coverage.csv` | Full 750-row brand-month grid with missing months preserved |
| `sample_exclusions.csv`, `sample_checks.json` | Original file exclusions and sampling verification |

The CLIP table is 16,490,093 bytes and the YOLO table is 131,069 bytes. They fit
in the repository as derived tables; raw images, model weights and local batch
caches are excluded from Git. Both Parquet tables use `image_id` as their only
join key; D obtains slug/month through a one-to-one left join to the sample.
The sample SHA-256 above is unchanged. Feature output SHA-256 values are:

- CLIP: `9332165c1d7eea06972f48c802db5858381d7b8733358e2c4046e003daeef61e`
- YOLO: `6609bd86e12f1bd8e2ba00a6ae6e3c70a7b59b054006a7aa8f940220b66c97c0`

D can now combine these tables with OCR on this same sample, then aggregate
the original CLIP dimensions, semantic scores, YOLO counts and OCR features
by slug/month as specified in README. Preserve availability indicators and
the 15 missing brand-months. Fitted imputation/scaling/PCA belongs inside E's
training folds.

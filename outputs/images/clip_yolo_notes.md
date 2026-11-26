# C — frozen sample handoff to D

## Status and scope

The 25 November sample handoff was completed on 26 November 2026 by
SunshineSs920959. This delivery freezes the shared image list for C's CLIP/YOLO
and D's OCR. CLIP/YOLO inference remains pending for the 28 November handoff.
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
- No CLIP/YOLO or OCR numerical results are claimed in this handoff. B's required
  independent review of C remains due by 1 December in a fresh review session.

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
For the next delivery, use this exact list with pretrained CLIP ViT-B/32 plus
the eight specified semantic scores in the same per-image feature file, and
YOLO11n COCO with confidence threshold 0.25. Checkpoints, exact prompts,
preprocessing and actual inference QC will be recorded when those runs occur.

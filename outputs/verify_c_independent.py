#!/usr/bin/env python3
r"""Independent reviewer verification of Member C's committed deliverables.

Reads only files extracted from origin/main into:
  C:\Users\LINVI\AppData\Local\Temp\opencode\review-c
Does not read C's verification scripts and does not modify any repository file.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

BASE = Path(r"C:\Users\LINVI\AppData\Local\Temp\opencode\review-c")
IMG = BASE / "outputs" / "images"
README = BASE / "README.md"
REPO = r"D:\lane-crawford-brand-momentum"

EXPECTED_HASHES = {
    "sample_manifest.csv": "34a39dd2b5829aa7b13edd5e9b7f285966757322a769f9124ffd056f6cea939d",
    "clip_features.parquet": "9332165c1d7eea06972f48c802db5858381d7b8733358e2c4046e003daeef61e",
    "yolo_features.parquet": "6609bd86e12f1bd8e2ba00a6ae6e3c70a7b59b054006a7aa8f940220b66c97c0",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


checks: list[dict] = []


def add(check: str, ok: bool, evidence: str) -> None:
    checks.append({"check": check, "status": "PASS" if ok else "FAIL", "evidence": evidence})


# ---------------------------------------------------------------------------
# load committed tables / C's recorded JSON
# ---------------------------------------------------------------------------
manifest = pd.read_csv(IMG / "sample_manifest.csv", dtype=str, keep_default_na=False)
coverage = pd.read_csv(IMG / "sample_coverage.csv", dtype=str, keep_default_na=False)
exclusions = pd.read_csv(IMG / "sample_exclusions.csv", dtype=str, keep_default_na=False)
qc = pd.read_csv(IMG / "feature_qc.csv", dtype=str, keep_default_na=False)

clip = pq.read_table(IMG / "clip_features.parquet").to_pandas()
yolo = pq.read_table(IMG / "yolo_features.parquet").to_pandas()

feature_checks = json.loads((IMG / "feature_checks.json").read_text(encoding="utf-8"))
sample_checks = json.loads((IMG / "sample_checks.json").read_text(encoding="utf-8"))
feature_run = json.loads((IMG / "feature_run.json").read_text(encoding="utf-8"))
notes = (IMG / "clip_yolo_notes.md").read_text(encoding="utf-8")
readme = README.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# 1. sample_manifest.csv
# ---------------------------------------------------------------------------
manifest_cols_expected = [
    "image_id", "file", "handle", "slug", "shortCode", "slide", "timestamp", "month"
]
byte_mismatch = sum(
    1 for a, b in zip(manifest["image_id"], manifest["file"])
    if a.encode("utf-8") != b.encode("utf-8")
)
slug_n = int(manifest["slug"].nunique())
month_n = int(manifest["month"].nunique())
short_per_group = manifest.groupby(["slug", "month"])["shortCode"].nunique()
max_short_per_group = int(short_per_group.max())
dup_post_rows = int(manifest.duplicated(["slug", "month", "shortCode"]).sum())
dup_id_rows = int(manifest.duplicated("image_id").sum())
manifest_ok = (
    len(manifest) == 5863
    and dup_id_rows == 0
    and byte_mismatch == 0
    and slug_n == 30
    and month_n == 25
    and max_short_per_group <= 10
    and dup_post_rows == 0
    and list(manifest.columns) == manifest_cols_expected
)
add(
    "1 sample_manifest.csv",
    manifest_ok,
    f"rows={len(manifest)}; unique image_id={dup_id_rows == 0}; "
    f"byte mismatches image_id!=file={byte_mismatch}; slugs={slug_n}; months={month_n}; "
    f"max shortCode/(slug,month)={max_short_per_group}; "
    f"duplicate (slug,month,shortCode) rows={dup_post_rows}; columns={list(manifest.columns)}",
)

# ---------------------------------------------------------------------------
# 2. sample_coverage.csv
# ---------------------------------------------------------------------------
eligible = pd.to_numeric(coverage["eligible_posts"], errors="raise")
selected = pd.to_numeric(coverage["selected_images"], errors="raise")
missing_flag = pd.to_numeric(coverage["missing_month"], errors="raise")
zero_flagged = int(((eligible == 0) & (missing_flag == 1)).sum())
zero_unflagged = int(((eligible == 0) & (missing_flag != 1)).sum())
flagged_nonzero = int(((missing_flag == 1) & (eligible != 0)).sum())
cov_pairs_unique = int(coverage.drop_duplicates(["slug", "month"]).shape[0])
sel_sum = int(selected.sum())

manifest_by_bm = manifest.groupby(["slug", "month"]).size()
coverage_by_bm = pd.Series(
    selected.to_numpy(),
    index=pd.MultiIndex.from_frame(coverage[["slug", "month"]]),
    name="selected_images",
)
joined = pd.concat([manifest_by_bm.rename("manifest_n"), coverage_by_bm], axis=1)
joined["manifest_n"] = joined["manifest_n"].fillna(0).astype(int)
coverage_mismatch = int((joined["manifest_n"] != joined["selected_images"]).sum())

coverage_ok = (
    len(coverage) == 750
    and cov_pairs_unique == 750
    and coverage["slug"].nunique() == 30
    and coverage["month"].nunique() == 25
    and zero_flagged == 15
    and zero_unflagged == 0
    and flagged_nonzero == 0
    and sel_sum == 5863
    and coverage_mismatch == 0
)
add(
    "2 sample_coverage.csv",
    coverage_ok,
    f"rows={len(coverage)}; unique (slug,month)={cov_pairs_unique}; "
    f"brands={coverage['slug'].nunique()}; months={coverage['month'].nunique()}; "
    f"eligible=0 & missing_month=1 rows={zero_flagged}; zero-unflagged={zero_unflagged}; "
    f"flagged-nonzero={flagged_nonzero}; selected_images sum={sel_sum}; "
    f"per-brand-month mismatches vs manifest={coverage_mismatch}",
)

# ---------------------------------------------------------------------------
# 3. SHA-256 integrity
# ---------------------------------------------------------------------------
actual_hashes = {name: sha256(IMG / name) for name in EXPECTED_HASHES}
hash_notes_present = {name: expected in notes for name, expected in EXPECTED_HASHES.items()}
hash_matches = {
    name: actual_hashes[name] == expected and hash_notes_present[name]
    for name, expected in EXPECTED_HASHES.items()
}
sha_ok = all(hash_matches.values())
add(
    "3 SHA-256 integrity",
    sha_ok,
    "; ".join(
        f"{name}: notes_claim_present={hash_notes_present[name]}, "
        f"computed={'match' if hash_matches[name] else 'MISMATCH'}, sha256={actual_hashes[name]}"
        for name in EXPECTED_HASHES
    ),
)

# ---------------------------------------------------------------------------
# 4. clip_features.parquet
# ---------------------------------------------------------------------------
clip_cols = list(clip.columns)
emb_cols = [c for c in clip_cols if re.fullmatch(r"clip_\d{3}", c)]
sem_cols = [c for c in clip_cols if c.startswith("clip_sem_")]
allowed_clip_cols = {"image_id", *emb_cols, *sem_cols}
extra_clip_cols = [c for c in clip_cols if c not in allowed_clip_cols]

clip_num = clip[emb_cols + sem_cols].to_numpy(dtype=np.float64)
nonfinite_clip = int((~np.isfinite(clip_num)).sum())
sem = clip[sem_cols].to_numpy(dtype=np.float64)
sem_min, sem_max = float(sem.min()), float(sem.max())
sem_outside = int(((sem < -1) | (sem > 1)).sum())
emb = clip[emb_cols].to_numpy(dtype=np.float64)
norms = np.linalg.norm(emb, axis=1)
zero_norm_count = int((norms == 0).sum())
min_norm = float(norms.min())

manifest_ids = set(manifest["image_id"])
clip_ids = set(clip["image_id"])
clip_dup = int(clip.duplicated("image_id").sum())
clip_set_ok = clip_ids == manifest_ids
clip_order_ok = clip["image_id"].tolist() == manifest["image_id"].tolist()

clip_ok = (
    len(clip) == 5863
    and clip_cols[0] == "image_id"
    and len(emb_cols) == 512
    and len(sem_cols) == 8
    and not extra_clip_cols
    and clip_dup == 0
    and clip_set_ok
    and nonfinite_clip == 0
    and sem_outside == 0
    and zero_norm_count == 0
)
add(
    "4 clip_features.parquet",
    clip_ok,
    f"rows={len(clip)}; embedding cols={len(emb_cols)}; semantic cols={len(sem_cols)}; "
    f"extra cols={extra_clip_cols}; duplicate image_id={clip_dup}; "
    f"ID set matches manifest={clip_set_ok}; row order matches manifest={clip_order_ok}; "
    f"nonfinite={nonfinite_clip}; sem range=[{sem_min:.10f},{sem_max:.10f}]; "
    f"sem outside [-1,1]={sem_outside}; zero-norm embeddings={zero_norm_count}; "
    f"min embedding norm={min_norm:.6f}",
)

# ---------------------------------------------------------------------------
# 5. yolo_features.parquet
# ---------------------------------------------------------------------------
yolo_cols = list(yolo.columns)
count_cols = [c for c in yolo_cols if re.fullmatch(r"yolo_.+_count", c)]
allowed_yolo_cols = {"image_id", "yolo_n_detections", *count_cols}
extra_yolo_cols = [c for c in yolo_cols if c not in allowed_yolo_cols]

det_raw = yolo["yolo_n_detections"].to_numpy(dtype=np.float64)
cnt_raw = yolo[count_cols].to_numpy(dtype=np.float64)
nonfinite_yolo = int((~np.isfinite(det_raw)).sum() + (~np.isfinite(cnt_raw)).sum())
nonintegral_yolo = int(
    (~np.isclose(det_raw, np.round(det_raw))).sum()
    + (~np.isclose(cnt_raw, np.round(cnt_raw))).sum()
)
negative_yolo = int((det_raw < 0).sum() + (cnt_raw < 0).sum())
det_int = det_raw.astype(np.int64)
cnt_int = cnt_raw.astype(np.int64)
row_sum_mismatch = int((cnt_int.sum(axis=1) != det_int).sum())
total_det = int(det_int.sum())
total_cnt = int(cnt_int.sum())
zero_det = int((det_int == 0).sum())

yolo_ids = set(yolo["image_id"])
yolo_dup = int(yolo.duplicated("image_id").sum())
yolo_set_ok = yolo_ids == manifest_ids
yolo_order_ok = yolo["image_id"].tolist() == manifest["image_id"].tolist()

classes_from_cols = [re.sub(r"^yolo_", "", c).replace("_count", "") for c in count_cols]
classes_match_run = classes_from_cols == feature_run["yolo"]["classes"]

yolo_ok = (
    len(yolo) == 5863
    and len(count_cols) == 80
    and not extra_yolo_cols
    and yolo_dup == 0
    and yolo_set_ok
    and nonfinite_yolo == 0
    and nonintegral_yolo == 0
    and negative_yolo == 0
    and row_sum_mismatch == 0
    and total_det == 18452
    and total_cnt == 18452
    and zero_det == 1026
)
add(
    "5 yolo_features.parquet",
    yolo_ok,
    f"rows={len(yolo)}; class-count cols={len(count_cols)}; extra cols={extra_yolo_cols}; "
    f"duplicate image_id={yolo_dup}; ID set matches manifest={yolo_set_ok}; "
    f"row order matches manifest={yolo_order_ok}; nonfinite={nonfinite_yolo}; "
    f"nonintegral={nonintegral_yolo}; negative={negative_yolo}; "
    f"sum(counts)!=n_detections rows={row_sum_mismatch}; total detections={total_det}; "
    f"sum class counts={total_cnt}; zero-detection images={zero_det}; "
    f"COCO class list matches feature_run.json={classes_match_run}",
)

# ---------------------------------------------------------------------------
# 6a. cross-check feature_checks.json
# ---------------------------------------------------------------------------
missing_ids_count = (
    len(manifest_ids - clip_ids)
    + len(manifest_ids - yolo_ids)
    + len(clip_ids - manifest_ids)
    + len(yolo_ids - manifest_ids)
)
computed_feature_checks = {
    "sample_rows": len(manifest),
    "clip_rows": len(clip),
    "yolo_rows": len(yolo),
    "clip_embedding_dimensions": len(emb_cols),
    "clip_semantic_dimensions": len(sem_cols),
    "yolo_classes": len(count_cols),
    "missing_ids": missing_ids_count,
    "duplicate_ids": dup_id_rows + clip_dup + yolo_dup,
    "nonfinite_values": nonfinite_clip + nonfinite_yolo,
    "qc_images": len(qc),
    "sample_sha256": actual_hashes["sample_manifest.csv"],
}
fc_mismatches = {
    k: {"recorded": feature_checks.get(k), "computed": v}
    for k, v in computed_feature_checks.items()
    if feature_checks.get(k) != v
}
fc_unverifiable = ["max_semantic_recalculation_error", "repeated_yolo_count_matches"]
fc_ok = not fc_mismatches
add(
    "6a feature_checks.json",
    fc_ok,
    f"{len(computed_feature_checks)} independently computable fields checked; "
    f"mismatches={fc_mismatches or 'none'}; "
    f"not verifiable from committed tables={fc_unverifiable}",
)

# ---------------------------------------------------------------------------
# 6b. cross-check sample_checks.json
# ---------------------------------------------------------------------------
brands_blob = subprocess.check_output(
    ["git", "cat-file", "blob", "origin/main:brands.csv"], cwd=REPO
)
brands_raw_hash = sha256_bytes(brands_blob)
brands_crlf_hash = sha256_bytes(
    brands_blob.replace(b"\n", b"\r\n").replace(b"\r\r\n", b"\r\n")
)
selected_by_brand = manifest.groupby("slug").size().astype(int).to_dict()
exclusion_reasons = exclusions["reason"].value_counts().to_dict()
computed_sample_checks = {
    "sample_sha256": actual_hashes["sample_manifest.csv"],
    "selected_images": sel_sum,
    "sampled_brands": slug_n,
    "coverage_month_start": manifest["month"].min(),
    "coverage_month_end": manifest["month"].max(),
    "brand_months": len(coverage),
    "missing_brand_months": zero_flagged,
    "selected_by_brand": selected_by_brand,
    "excluded_rows": len(exclusions),
    "exclusion_reasons": exclusion_reasons,
    "brands_sha256": brands_crlf_hash,
}
sc_mismatches = {
    k: {"recorded": sample_checks.get(k), "computed": v}
    for k, v in computed_sample_checks.items()
    if sample_checks.get(k) != v
}
sc_unverifiable = [
    "seed", "per_month", "input_manifest", "input_manifest_sha256",
    "source_rows", "unique_manifest_files", "disk_image_files",
    "unlisted_image_files", "unlisted_files", "valid_images",
    "distinct_posts", "python", "pillow",
]
sc_ok = not sc_mismatches
add(
    "6b sample_checks.json",
    sc_ok,
    f"{len(computed_sample_checks)} independently computable fields checked; "
    f"mismatches={sc_mismatches or 'none'}; "
    f"brands_sha256 is the CRLF working-copy hash (raw Git blob sha256={brands_raw_hash}); "
    f"not verifiable without raw dataset/source manifest={sc_unverifiable}",
)

# ---------------------------------------------------------------------------
# 6c. cross-check feature_run.json and notes claims that are table-verifiable
# ---------------------------------------------------------------------------
class_sums = yolo[count_cols].sum(axis=0)
top12 = class_sums.sort_values(ascending=False).head(12)
top12_dict = {k: int(v) for k, v in top12.items()}
prompts_match = set(feature_run["clip"]["prompts"]) == set(sem_cols)

computed_run_fields = {
    "sample_sha256": actual_hashes["sample_manifest.csv"],
    "sample_rows": len(manifest),
    "clip.rows": len(clip),
    "clip.embedding_dimensions": len(emb_cols),
    "clip.output_sha256": actual_hashes["clip_features.parquet"],
    "yolo.rows": len(yolo),
    "yolo.output_sha256": actual_hashes["yolo_features.parquet"],
    "yolo.total_detections": total_det,
    "yolo.images_with_no_detections": zero_det,
    "yolo.top_classes": top12_dict,
    "yolo.classes_match_columns": classes_match_run,
    "clip.prompt_keys_match_semantic_columns": prompts_match,
}
recorded_run_fields = {
    "sample_sha256": feature_run["sample_sha256"],
    "sample_rows": feature_run["sample_rows"],
    "clip.rows": feature_run["clip"]["rows"],
    "clip.embedding_dimensions": feature_run["clip"]["embedding_dimensions"],
    "clip.output_sha256": feature_run["clip"]["output_sha256"],
    "yolo.rows": feature_run["yolo"]["rows"],
    "yolo.output_sha256": feature_run["yolo"]["output_sha256"],
    "yolo.total_detections": feature_run["yolo"]["total_detections"],
    "yolo.images_with_no_detections": feature_run["yolo"]["images_with_no_detections"],
    "yolo.top_classes": feature_run["yolo"]["top_classes"],
    "yolo.classes_match_columns": True,
    "clip.prompt_keys_match_semantic_columns": True,
}
fr_mismatches = {
    k: {"recorded": recorded_run_fields[k], "computed": v}
    for k, v in computed_run_fields.items()
    if recorded_run_fields[k] != v
}

clip_size = (IMG / "clip_features.parquet").stat().st_size
yolo_size = (IMG / "yolo_features.parquet").stat().st_size
size_claims = {
    "clip_features.parquet": 16_490_093,
    "yolo_features.parquet": 131_069,
}
actual_sizes = {
    "clip_features.parquet": clip_size,
    "yolo_features.parquet": yolo_size,
}
size_mismatches = {
    k: {"notes_claim": v, "actual": actual_sizes[k]}
    for k, v in size_claims.items()
    if f"{v:,}" not in notes and str(v) not in notes
}
size_mismatches.update({
    k: {"notes_claim": v, "actual": actual_sizes[k]}
    for k, v in size_claims.items()
    if actual_sizes[k] != v
})
notes_ok = not fr_mismatches and not size_mismatches
add(
    "6c feature_run.json / notes",
    notes_ok,
    f"feature_run mismatches={fr_mismatches or 'none'}; "
    f"file-size mismatches={size_mismatches or 'none'}; "
    f"actual sizes={actual_sizes}; top-class sums match={not fr_mismatches}",
)

# ---------------------------------------------------------------------------
# 7. README required outputs and schemas
# ---------------------------------------------------------------------------
required_files = [
    "sample_manifest.csv",
    "clip_features.parquet",
    "yolo_features.parquet",
    "clip_yolo_notes.md",
]
all_exist = all((IMG / name).is_file() for name in required_files)
readme_mentions = all(name in readme for name in required_files)
key_ok = (
    clip_cols[0] == "image_id"
    and yolo_cols[0] == "image_id"
    and clip_dup == 0
    and yolo_dup == 0
    and clip_set_ok
    and yolo_set_ok
)
schema_ok = (
    all_exist
    and readme_mentions
    and list(manifest.columns) == manifest_cols_expected
    and len(clip) == len(manifest)
    and len(yolo) == len(manifest)
    and key_ok
    and len(sem_cols) == 8
    and len(emb_cols) == 512
    and len(count_cols) == 80
)
add(
    "7 README section C outputs/schema",
    schema_ok,
    f"required files exist={all_exist} {required_files}; README mentions all={readme_mentions}; "
    f"manifest columns exact={list(manifest.columns) == manifest_cols_expected}; "
    f"one row per image in all three tables={len(manifest)==len(clip)==len(yolo)==5863}; "
    f"image_id key unique and identical across tables={key_ok}",
)

# ---------------------------------------------------------------------------
# checks that cannot be done from committed tables
# ---------------------------------------------------------------------------
cannot_do = [
    "Verify first-slide rule against original manifest_trudon.csv and raw images.zip "
    "(source manifest and images are not available locally).",
    "Verify source-manifest counts/hashes/exclusion reasons beyond sample_exclusions.csv "
    "(manifest_trudon.csv and raw image files are unavailable).",
    "Visual spot-checks of detections/semantic outputs, including the annotated "
    ".model-cache/qc/spot_check.jpg (not committed and raw images unavailable).",
    "Reproduce CLIP/YOLO inference or recompute the 46,904 semantic scores / "
    "max_semantic_recalculation_error (model weights and raw images unavailable; "
    "instruction forbids rerunning inference).",
    "Verify repeated_yolo_count_matches=8 by fresh YOLO rerun (requires raw images and model).",
    "Verify seed 42, per_month 10, input-manifest SHA-256, Python/Pillow versions from "
    "source run environment.",
]

print(json.dumps({
    "repo_commit_reviewed": "90ed4fe (origin/main)",
    "checks": checks,
    "cannot_verify_without_raw_dataset_or_model": cannot_do,
    "computed_values": {
        "manifest_rows": len(manifest),
        "coverage_rows": len(coverage),
        "clip_rows": len(clip),
        "yolo_rows": len(yolo),
        "clip_embedding_cols": len(emb_cols),
        "clip_semantic_cols": len(sem_cols),
        "yolo_class_count_cols": len(count_cols),
        "selected_images_sum": sel_sum,
        "zero_flagged_brand_months": zero_flagged,
        "sha256": actual_hashes,
        "total_yolo_detections": total_det,
        "zero_detection_images": zero_det,
        "brands_csv_raw_blob_sha256_origin_main": brands_raw_hash,
        "brands_csv_crlf_worktree_sha256": brands_crlf_hash,
        "sample_checks_brands_sha256": sample_checks["brands_sha256"],
    },
}, indent=2))

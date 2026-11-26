"""Verify per-image handoff tables and render a local visual spot-check."""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageDraw

from extract_features import PROMPTS, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/images"))
    parser.add_argument("--cache", type=Path, default=Path(".model-cache"))
    parser.add_argument("--images-root", type=Path, required=True)
    args = parser.parse_args()
    (args.cache.resolve() / "ultralytics/Ultralytics").mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(args.cache.resolve() / "ultralytics")
    torch.set_num_threads(8)
    sample = pd.read_csv(args.output / "sample_manifest.csv", dtype=str)
    clip = pd.read_parquet(args.output / "clip_features.parquet")
    yolo = pd.read_parquet(args.output / "yolo_features.parquet")
    run = json.loads((args.output / "feature_run.json").read_text())
    expected = sample["image_id"].tolist()
    for name, table in [("clip", clip), ("yolo", yolo)]:
        assert table["image_id"].tolist() == expected, f"{name} IDs/order differ from sample"
        assert not table["image_id"].duplicated().any()
        assert np.isfinite(table.drop(columns="image_id").to_numpy()).all()
        assert sha256(args.output / f"{name}_features.parquet") == run[name]["output_sha256"]
    embedding_columns = [f"clip_{index:03d}" for index in range(512)]
    assert clip.columns.tolist() == ["image_id", *embedding_columns, *PROMPTS]
    assert yolo.columns.tolist() == ["image_id", "yolo_n_detections", *[
        f"yolo_{name}_count" for name in run["yolo"]["classes"]]]
    embeddings = clip[embedding_columns].to_numpy()
    assert (np.linalg.norm(embeddings, axis=1) > 0).all()
    assert (clip[list(PROMPTS)].abs().to_numpy() <= 1.00001).all()
    counts = yolo.iloc[:, 2:].to_numpy()
    assert (counts >= 0).all() and np.array_equal(counts, counts.astype(np.int32))
    assert np.array_equal(counts.sum(axis=1), yolo["yolo_n_detections"])
    assert sha256(args.output / "sample_manifest.csv") == run["sample_sha256"]

    # Re-encode text only and recompute every saved semantic score from embeddings.
    from transformers import CLIPModel, CLIPProcessor
    model_path = args.cache / "clip-vit-base-patch32"
    model = CLIPModel.from_pretrained(model_path, local_files_only=True).eval()
    processor = CLIPProcessor.from_pretrained(model_path, local_files_only=True, use_fast=False)
    tokens = processor(text=list(PROMPTS.values()), padding=True, return_tensors="pt")
    with torch.inference_mode():
        text = model.get_text_features(**tokens).numpy()
    text /= np.linalg.norm(text, axis=1, keepdims=True)
    expected_scores = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True) @ text.T
    max_error = float(np.max(np.abs(expected_scores - clip[list(PROMPTS)].to_numpy())))
    assert max_error < 1e-5
    del model

    # Representative, deterministic checks span eight brands and product categories.
    from ultralytics import YOLO, settings
    settings.update({"sync": False})
    detector = YOLO(str(args.cache / "yolo11n.pt"))
    slugs = ["aesop", "assouline", "buccellati", "herman-miller",
             "jellycat", "marshall", "nothing", "oura"]
    qc = []
    contact = Image.new("RGB", (1280, 760), "white")
    draw = ImageDraw.Draw(contact)
    for index, slug in enumerate(slugs):
        selected = sample.loc[sample["slug"] == slug].iloc[0]
        image_id = selected["image_id"]
        position = expected.index(image_id)
        source = args.images_root / selected["file"]
        prediction = detector.predict(str(source), imgsz=640, conf=0.25, iou=0.7,
                                      max_det=300, device="cpu", rect=False,
                                      half=False, verbose=False, save=False)[0]
        repeated_counts = np.bincount(prediction.boxes.cls.numpy().astype(int), minlength=80)
        matches = bool(np.array_equal(repeated_counts, counts[position]))
        top_semantic = clip.loc[position, list(PROMPTS)].astype(float).idxmax()
        detected = {name: int(value) for name, value in
                    zip(run["yolo"]["classes"], counts[position]) if value}
        qc.append(dict(image_id=image_id, slug=slug, top_semantic=top_semantic,
                       cosine=float(clip.loc[position, top_semantic]),
                       yolo_detections=json.dumps(detected, sort_keys=True),
                       repeated_counts_match=matches))
        annotated = Image.fromarray(prediction.plot()[:, :, ::-1])
        annotated.thumbnail((310, 300))
        x, y = (index % 4) * 320, (index // 4) * 380
        contact.paste(annotated, (x, y))
        draw.text((x + 4, y + 303), slug, fill="black")
        draw.text((x + 4, y + 322), top_semantic.replace("clip_sem_", ""), fill="black")
        draw.text((x + 4, y + 341), str(detected)[:45], fill="black")
    qc_path = args.cache / "qc"
    qc_path.mkdir(parents=True, exist_ok=True)
    contact.save(qc_path / "spot_check.jpg", quality=90)
    pd.DataFrame(qc).to_csv(args.output / "feature_qc.csv", index=False, lineterminator="\n")
    checks = dict(sample_rows=len(sample), clip_rows=len(clip), yolo_rows=len(yolo),
                  clip_embedding_dimensions=512, clip_semantic_dimensions=8, yolo_classes=80,
                  missing_ids=0, duplicate_ids=0, nonfinite_values=0,
                  max_semantic_recalculation_error=max_error,
                  repeated_yolo_count_matches=sum(row["repeated_counts_match"] for row in qc),
                  qc_images=len(qc), sample_sha256=run["sample_sha256"])
    (args.output / "feature_checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()

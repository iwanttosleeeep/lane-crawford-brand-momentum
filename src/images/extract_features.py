"""Extract frozen-sample CLIP and YOLO per-image features with resumable batches."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image


CLIP_MODEL = "openai/clip-vit-base-patch32"
CLIP_REVISION = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"
PROMPTS = {
    "clip_sem_product_closeup": "a photo of a close-up product on a simple background",
    "clip_sem_styled_interior": "a photo of a styled interior or home-lifestyle scene",
    "clip_sem_person_using": "a photo of a person wearing, holding or using a product",
    "clip_sem_outdoor_travel": "a photo of an outdoor or travel lifestyle scene",
    "clip_sem_gift_packaging": "a photo of wrapped gifts or festive product packaging",
    "clip_sem_text_graphic": "a photo of a typographic or promotional graphic",
    "clip_sem_material_detail": "a photo of a material or craftsmanship close-up",
    "clip_sem_product_group": "a photo of a curated display of several products",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def save_table(path, frame):
    temporary = path.with_suffix(".tmp.parquet")
    frame.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(path)


def image_batch(root, rows):
    images = []
    for relative in rows["file"]:
        with Image.open(root / relative) as image:
            images.append(image.convert("RGB"))
    return images


def batch_outputs(rows, directory, size, infer):
    directory.mkdir(parents=True, exist_ok=True)
    tables = []
    start_time = time.monotonic()
    for start in range(0, len(rows), size):
        batch = rows.iloc[start:start + size]
        part = directory / f"{start:06d}.parquet"
        if part.exists():
            frame = pd.read_parquet(part)
            if frame["image_id"].tolist() != batch["image_id"].tolist():
                raise ValueError(f"Checkpoint IDs differ: {part}")
        else:
            frame = infer(batch)
            save_table(part, frame)
        tables.append(frame)
        print(f"{directory.name}: {min(start + size, len(rows))}/{len(rows)} images; "
              f"{time.monotonic() - start_time:.1f}s", flush=True)
    return pd.concat(tables, ignore_index=True)


def extract_clip(args, rows, checkpoint):
    from transformers import CLIPModel, CLIPProcessor

    local_model = args.cache / "clip-vit-base-patch32"
    processor = CLIPProcessor.from_pretrained(local_model, local_files_only=True, use_fast=False)
    model = CLIPModel.from_pretrained(local_model, local_files_only=True).to(args.device).eval()
    tokens = processor(text=list(PROMPTS.values()), padding=True, return_tensors="pt")
    with torch.inference_mode():
        text = model.get_text_features(**{k: v.to(args.device) for k, v in tokens.items()})
        text = torch.nn.functional.normalize(text.float(), dim=-1)
    columns = [f"clip_{i:03d}" for i in range(model.config.projection_dim)]

    def infer(batch):
        pixels = processor(images=image_batch(args.images_root, batch), return_tensors="pt")
        with torch.inference_mode():
            raw = model.get_image_features(pixel_values=pixels["pixel_values"].to(args.device)).float()
            similarities = torch.nn.functional.normalize(raw, dim=-1) @ text.T
        frame = pd.DataFrame(raw.cpu().numpy(), columns=columns)
        for index, name in enumerate(PROMPTS):
            frame[name] = similarities[:, index].cpu().numpy()
        frame.insert(0, "image_id", batch["image_id"].to_numpy())
        return frame

    result = batch_outputs(rows, checkpoint / "clip", args.clip_batch, infer)
    numeric = result.drop(columns="image_id").to_numpy()
    if not np.isfinite(numeric).all():
        raise ValueError("CLIP produced non-finite features")
    if (result[list(PROMPTS)].abs().to_numpy() > 1.00001).any():
        raise ValueError("CLIP cosine similarities out of range")
    save_table(args.output / "clip_features.parquet", result)
    return dict(rows=len(result), embedding_dimensions=len(columns),
                checkpoint=CLIP_MODEL, revision=CLIP_REVISION, prompts=PROMPTS,
                embedding_representation="float32 unnormalised projected image features",
                semantic_scoring="cosine of L2-normalised matching image/text embeddings",
                weights_sha256=sha256(local_model / "pytorch_model.bin"),
                processor=processor.image_processor.to_dict())


def extract_yolo(args, rows, checkpoint):
    from ultralytics import YOLO, settings

    settings.update({"sync": False})
    model = YOLO(str(args.yolo_weights))
    model.model.eval()
    classes = [re.sub(r"[^a-z0-9]+", "_", model.names[i].lower()).strip("_")
               for i in range(len(model.names))]
    if len(classes) != 80 or len(set(classes)) != 80:
        raise ValueError("Expected 80 unique COCO classes")

    def infer(batch):
        results = model.predict(source=image_batch(args.images_root, batch), imgsz=640,
                                conf=0.25, iou=0.7, max_det=300, device=args.device,
                                rect=False, half=False, augment=False, verbose=False,
                                save=False, stream=False)
        if len(results) != len(batch):
            raise ValueError("YOLO returned an incomplete batch")
        counts = np.stack([np.bincount(result.boxes.cls.cpu().numpy().astype(int), minlength=80)
                           for result in results]).astype(np.int32)
        frame = pd.DataFrame(counts, columns=[f"yolo_{name}_count" for name in classes])
        frame.insert(0, "yolo_n_detections", counts.sum(axis=1).astype(np.int32))
        frame.insert(0, "image_id", batch["image_id"].to_numpy())
        return frame

    result = batch_outputs(rows, checkpoint / "yolo", args.yolo_batch, infer)
    counts = result[[f"yolo_{name}_count" for name in classes]]
    if (counts.to_numpy() < 0).any() or not np.array_equal(counts.sum(axis=1), result["yolo_n_detections"]):
        raise ValueError("YOLO count consistency check failed")
    save_table(args.output / "yolo_features.parquet", result)
    return dict(rows=len(result), weights="yolo11n.pt", weights_sha256=sha256(args.yolo_weights),
                classes=classes, confidence=0.25, iou=0.7, max_det=300,
                imgsz=640, rect=False, half=False, total_detections=int(result["yolo_n_detections"].sum()),
                images_with_no_detections=int((result["yolo_n_detections"] == 0).sum()),
                top_classes=counts.sum().sort_values(ascending=False).head(12).to_dict())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--sample", type=Path, default=Path("outputs/images/sample_manifest.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/images"))
    parser.add_argument("--cache", type=Path, default=Path(".model-cache"))
    parser.add_argument("--yolo-weights", type=Path, default=Path(".model-cache/yolo11n.pt"))
    parser.add_argument("--stage", choices=["clip", "yolo", "all"], default="all")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--clip-batch", type=int, default=32)
    parser.add_argument("--yolo-batch", type=int, default=16)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--limit", type=int, help="Smoke checks only; use a separate output directory")
    args = parser.parse_args()
    (args.cache.resolve() / "ultralytics/Ultralytics").mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(args.cache.resolve() / "ultralytics")
    if min(args.clip_batch, args.yolo_batch, args.threads) < 1 or (args.limit is not None and args.limit < 1):
        parser.error("Batch sizes, threads and limit must be positive")
    if args.limit is not None and args.output.resolve() == args.sample.parent.resolve():
        parser.error("A limited run cannot write official handoff files")
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(2)
    torch.manual_seed(42)
    np.random.seed(42)
    rows = pd.read_csv(args.sample, dtype=str, keep_default_na=False)
    if rows.empty or rows["image_id"].duplicated().any() or not rows["image_id"].equals(rows["file"]):
        raise ValueError("Sample must contain unique image_id=file rows")
    if args.limit:
        rows = rows.head(args.limit)
    for relative in rows["file"]:
        path = (args.images_root / relative).resolve()
        if not path.is_relative_to(args.images_root.resolve()) or not path.is_file():
            raise ValueError(f"Missing or unsafe sample path: {relative}")
    args.output.mkdir(parents=True, exist_ok=True)
    settings = dict(sample_sha256=sha256(args.sample), image_ids=rows["image_id"].tolist(),
                    clip_model=CLIP_MODEL, clip_revision=CLIP_REVISION, prompts=PROMPTS,
                    clip_sha256=sha256(args.cache / "clip-vit-base-patch32/pytorch_model.bin"),
                    yolo_sha256=sha256(args.yolo_weights), device=args.device, threads=args.threads,
                    clip_batch=args.clip_batch, yolo_batch=args.yolo_batch,
                    versions={name: importlib.metadata.version(name) for name in
                              ["torch", "torchvision", "transformers", "ultralytics", "numpy", "pandas", "pyarrow", "Pillow"]})
    fingerprint = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    checkpoint = args.cache / "batches" / fingerprint
    checkpoint.mkdir(parents=True, exist_ok=True)
    save_json(checkpoint / "settings.json", settings)
    metadata_path = args.output / "feature_run.json"
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    if metadata and metadata.get("run_fingerprint") != fingerprint:
        raise ValueError("Existing output settings differ; use a separate output directory")
    metadata.update(run_fingerprint=fingerprint, sample_sha256=settings["sample_sha256"],
                    versions=settings["versions"], device=args.device, threads=args.threads,
                    clip_batch=args.clip_batch, yolo_batch=args.yolo_batch, sample_rows=len(rows))
    save_json(metadata_path, metadata)
    for stage, extract in [("clip", extract_clip), ("yolo", extract_yolo)]:
        if args.stage in {stage, "all"}:
            start = time.monotonic()
            metadata[stage] = extract(args, rows, checkpoint)
            metadata[stage]["elapsed_seconds"] = round(time.monotonic() - start, 3)
            metadata[stage]["output_sha256"] = sha256(args.output / f"{stage}_features.parquet")
            save_json(metadata_path, metadata)
    print(json.dumps({key: value for key, value in metadata.items() if key != "clip"}, indent=2))


if __name__ == "__main__":
    main()

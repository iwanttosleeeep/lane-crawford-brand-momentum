"""Download pinned official model files into the ignored local model cache."""
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

CLIP_MODEL = "openai/clip-vit-base-patch32"
CLIP_REVISION = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"


def download(url, destination, expected_hash=None):
    if destination.exists() and (not expected_hash or digest(destination) == expected_hash):
        return
    temporary = destination.with_suffix(destination.suffix + ".download")
    request = urllib.request.Request(url, headers={"User-Agent": "C-image-features"})
    with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as stream:
        downloaded = 0
        while chunk := response.read(8 * 1024 * 1024):
            stream.write(chunk)
            downloaded += len(chunk)
            if downloaded % (64 * 1024 * 1024) == 0:
                print(f"{destination.name}: {downloaded / 1024**2:.0f} MiB", flush=True)
    if expected_hash and digest(temporary) != expected_hash:
        raise ValueError(f"Official model SHA-256 mismatch: {destination.name}")
    temporary.replace(destination)


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(".model-cache"))
    args = parser.parse_args()
    local_clip = args.cache / "clip-vit-base-patch32"
    local_clip.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/api/models/{CLIP_MODEL}/tree/{CLIP_REVISION}"
    with urllib.request.urlopen(url, timeout=60) as response:
        tree = json.load(response)
    files = {item["path"]: item for item in tree}
    required = ["config.json", "preprocessor_config.json", "tokenizer_config.json",
                "special_tokens_map.json", "vocab.json", "merges.txt", "pytorch_model.bin"]
    for name in required:
        expected = files[name].get("lfs", {}).get("oid")
        download(f"https://huggingface.co/{CLIP_MODEL}/resolve/{CLIP_REVISION}/{name}",
                 local_clip / name, expected)
        print(f"Ready: {name}", flush=True)
    yolo_url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt"
    download(yolo_url, args.cache / "yolo11n.pt",
             "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1")
    metadata = dict(clip_model=CLIP_MODEL, clip_revision=CLIP_REVISION,
                    clip_weights_sha256=digest(local_clip / "pytorch_model.bin"),
                    yolo_url=yolo_url, yolo_weights_sha256=digest(args.cache / "yolo11n.pt"))
    (args.cache / "model_sources.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()

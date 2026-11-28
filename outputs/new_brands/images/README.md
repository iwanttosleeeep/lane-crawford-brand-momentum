# New-brand CLIP/YOLO features

Produced by A with C's unchanged scripts (src/images/sample_images.py, extract_features.py)
and identical pinned versions (torch 2.8.0+cpu, transformers 4.57.1, ultralytics 8.3.230), seed 42,
10 posts per brand-month, first slide per post. Input: new_brands.csv and the new-brand image
download (2026-02 onward; 1,567 valid images, 6 failed downloads excluded). 280 images sampled.

Differences from C's run: Python 3.13 on Colab (C used 3.12). verify_features.py was run with its
hard-coded spot-check brands replaced by the four new brands (local edit, not committed); all
integrity checks passed. Coverage starts at 2024-11 by script design, so 2024-11 to 2026-01 show
as missing for these brands (images were only downloaded from 2026-02).

These brands are never used for training or tuning.

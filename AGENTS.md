# Coding-agent instructions — STAT6207 Lane Crawford Brand Discovery

**Source of truth:** Read [README.md](README.md), especially Sections 2–7, before changing anything. This repository is the **final project**. Do not reuse the old Assignment 4 assumptions or paths.

## Workflow

1. Identify the member workstream (**B**, **C**, **D**, or **E**) specified by the human operator. **A** owns dataset provision and business interpretation. Never take over another member's workstream without an explicit request.
2. Inspect actual inputs before coding. The tracked files initially are **brands.csv** and **Google Trends.zip**; the image ZIP/manifest is available via the team's **privately shared Google Drive link**. Extract **Google Trends.zip** and read the CSVs using the relative `trends_file` paths in brands.csv. Check CSV headers and available images before coding.
3. Test and debug code internally, then complete and verify the full assigned task by its deadline. Intermediate testing is not a separate team deliverable. Provide executable code with a stated environment and actual outputs. Never claim to have run a model, generated a figure or measured a metric unless that happened.
4. Use the schema and handoff paths specified under the chosen role in README. Use **slug** as the brand join key and the manifest's **file** path as the stable image_id.
5. Before building a forecasting model, B and E must share **one target formula**, forecast-origin list, training/validation/test split and evaluation definition. Image workstreams C and D must use **one common sample_manifest.csv** (frozen 25 Nov, with image_id = file from the original manifest). C must provide D with complete CLIP/YOLO per-image feature files by **28 Nov**, before D's 29 Nov integration deadline. Do not independently redefine these interfaces.
6. **Feature contract:** Follow README Section 4, 'Fixed feature-extraction contract (C, D and E)', for shared sample, model defaults, image_id, feature columns, monthly aggregation and delivery dates. Agents must not independently invent incompatible interfaces. Place oversized embedding files in the group Drive and document exact paths.
7. Train/test leakage checks are mandatory: inputs must exist by forecast origin, targets need future three-month observations, and fitted preprocessing must use training data only.
8. Record code version, model/checkpoint, sample sizes, exclusions, metrics and any unresolved errors in workstream notes. If dependencies are missing, report the specific blocker and deliver independently runnable partial work.
9. Keep large files, images, secrets, tokens, raw Instagram exports and personal data out of Git. Commit code, small feature summaries, figures and reproducibility notes to a **workstream branch** and open a pull request for review.

## Start prompt for the operator

"Read README.md and AGENTS.md. I am Member [B/C/D/E]. Inspect real available inputs, follow my assigned scope and output contract, verify the implementation and submit the complete specified files with actual results by the assigned deadline. Do not fabricate data or change other workstreams."

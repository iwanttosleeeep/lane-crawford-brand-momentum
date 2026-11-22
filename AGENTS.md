# Coding-agent instructions — STAT6207 Lane Crawford Brand Discovery

**Source of truth:** Read [README.md](README.md), especially Sections 2–7, before changing anything. This repository is the **final project**. Do not reuse the old Assignment 4 assumptions or paths.

## Workflow

1. Identify the member workstream (**B**, **C**, **D**, or **E**) specified by the human operator. **A** owns dataset provision and business interpretation. Never take over another member's workstream without an explicit request.
2. Inspect actual inputs before coding. The tracked files initially are **brands.csv** and **Google Trends.zip**; the image ZIP/manifest is available via the team's **privately shared Google Drive link**. Extract **Google Trends.zip** and read the CSVs using the relative `trends_file` paths in brands.csv. Check CSV headers and available images before coding.
3. Run a minimal pilot, verify it, then run the intended task. Provide executable code with a stated environment and actual outputs. Never claim to have run a model, generated a figure or measured a metric unless that happened.
4. Use the schema and handoff paths specified under the chosen role in README. Use **slug** as the brand join key and the manifest's **file** path as the stable image_id.
5. Before building a forecasting model, B and E must share **one target formula**, forecast-origin list, training/validation/test split and evaluation definition. Image workstreams C and D must use **one common sample_manifest.csv**. Do not independently redefine either interface.
6. Train/test leakage checks are mandatory: inputs must exist by forecast origin, targets need future three-month observations, and fitted preprocessing must use training data only.
7. Record code version, model/checkpoint, sample sizes, exclusions, metrics and any unresolved errors in workstream notes. If dependencies are missing, report the specific blocker and deliver independently runnable partial work.
8. Keep large files, images, secrets, tokens, raw Instagram exports and personal data out of Git. Commit code, small feature summaries, figures and reproducibility notes to a **workstream branch** and open a pull request for review.

## Start prompt for the operator

"Read README.md and AGENTS.md. I am Member [B/C/D/E]. Inspect real available inputs, follow my assigned scope and output contract, implement and run a small pilot first, then produce the specified files with actual verified results. Do not fabricate data or change other workstreams."

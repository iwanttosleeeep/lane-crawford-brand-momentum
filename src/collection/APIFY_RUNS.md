# Apify collection runs (actor: apify/instagram-scraper)

These are the exact JSON inputs pasted into the Apify Console. All runs were on 2026-11-22.
Item counts are from the exported datasets; costs are Apify's billed amounts.

| # | Input file | Accounts | Settings | Items returned | Purpose / outcome |
|---|---|---|---|---|---|
| 1 | `apify_inputs/01_probe_latest20.json` | 30 (pre-correction list) | latest 20 posts per account | 562 | Handle check and posting-rate estimate (analysed with `analyse_probe.py`). Found: `aesopskincare` and `fretteofficial` do not exist (corrected to `aesop`, `frette`); `riedel_official` returned 14/20 `restricted_page` items (Riedel replaced by Artemide). |
| 2 | `apify_inputs/02_trudon_depth_test.json` | trudon | since 2024-11-01, limit 1200, skip pinned | 286 | Confirmed the scraper reaches back two years (oldest post 2024-11-03). **This export is the final Trudon data.** |
| 3 | `apify_inputs/03_batch1_free.json` | 11 | since 2024-11-01, limit 1500, skip pinned | 2,858 | Final data. No errors. Oldest post: bangolufsen 2025-03-04, stanley1913_brand 2025-01-01; all others reached 2024-11. |
| 4 | `apify_inputs/04_batch2_starter.json` | 18 | since 2024-11-01, limit 3500, skip pinned | 9,023 | Final data. 3 `restricted_page` items (LEGO x F1 collaboration posts; excluded by `download_images.py`). Oldest post: marshall 2025-03-31; jomalonelondon has no posts in 2024-12. No account hit the limit. |

The final dataset = exports of runs 2, 3 and 4 (30 accounts, 12,167 items), passed together to
`download_images.py --since 2024-11-01 --per-month 15 --max-per-post 0` (default `--max-side 1024`).
The dry run selected 7,018 posts / 22,882 images; 22,850 images were downloaded.

Raw exports are not committed (they contain captions and expiring media URLs).

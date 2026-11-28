# Google Trends Hong Kong — manual resumable collection

Status: **STOPPED at baccarat: ValueError: Empty/invalid Trends response for baccarat**

Collected: **25 / 30** official brands

Region: `HK`; exact timeframe: `2021-11-01 2026-10-31`; geo and query terms fixed.
Method: one request per brand; original topic MID payload; weekly→monthly mean.
No automatic 429 retries, proxy rotation or post-hoc term substitution.
Each brand's raw response, monthly means and SHA-256 metadata are saved.
The overall final CSV is written only on full completion.

| slug | source | months | zeros | missing months in fixed window |
|---|---|---:|---:|---:|
| bang-olufsen | topic | 60 | 0 | 0 |
| marshall | query | 60 | 58 | 0 |
| sennheiser | topic | 60 | 0 | 0 |
| teenage-engineering | query | 60 | 59 | 0 |
| assouline | topic | 60 | 59 | 0 |
| kodak | topic | 60 | 0 | 0 |
| polaroid | topic | 60 | 21 | 0 |
| stanley | query | 60 | 54 | 0 |
| anya-hindmarch | query | 60 | 22 | 0 |
| buccellati | topic | 60 | 25 | 0 |
| fortnum-mason | topic | 60 | 24 | 0 |
| aesop | topic | 60 | 6 | 0 |
| astier-de-villatte | topic | 60 | 59 | 0 |
| jo-malone-london | topic | 60 | 29 | 0 |
| trudon | topic | 60 | 56 | 0 |
| herman-miller | query | 60 | 47 | 0 |
| knoll | query | 60 | 59 | 0 |
| vitra | query | 60 | 57 | 0 |
| frette | topic | 60 | 57 | 0 |
| artemide | topic | 60 | 59 | 0 |
| flos | query | 60 | 59 | 0 |
| louis-poulsen | topic | 60 | 58 | 0 |
| tom-dixon | query | 60 | 58 | 0 |
| nothing | query | 60 | 5 | 0 |
| oura | topic | 60 | 14 | 0 |
| baccarat | query | pending | — | — |
| christofle | topic | pending | — | — |
| noritake | topic | pending | — | — |
| jellycat | topic | pending | — | — |
| lego | topic | pending | — | — |

## Interpretation

- These are HK-specific Google Trends indices independently normalised to 0–100.
- Their scale differs from the original Worldwide series. Do not substitute HK data into the frozen main target, splits, or model predictions.
- Recorded zero is an observation, not an absent month; missing months must remain missing.
- The data request uses complete calendar months through October 2026; endpoint sampling or partial weekly points can still create boundary effects.
- Temporal look-ahead from whole-window Google normalisation remains; report it in any sensitivity analysis.

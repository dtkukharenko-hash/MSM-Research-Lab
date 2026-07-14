# Latest Codex Result

- task_id: `EXP-012-R2-ACCEPTED-BOUNDARY-STATE`
- task_status: `AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW`
- implementation_commit_sha: `10437e994b9c1b98cdde281dc7c18bf0882d1477`
- implementation_push_status: `PUSHED origin/main`
- result_commit_status: `PUSHED origin/main`

## Summary

Implemented the mandatory `.codex/TASK_ADDENDUM.md` on top of EXP-012 R2. The primary price-only state machine remains unchanged: price body boundaries define zones, accepted extensions, and accepted exits. EMA27/EMA200 geometry is now a separate causal diagnostic layer that detects EMA27 compact-band departures and annotates price attempts.

The addendum produced 10 confirmed EMA27 band-departure events. November accepted upside exits include `EMA27_EXIT_UP_AWAY_FROM_EMA200`, and the December-January downside process includes `EMA27_EXIT_DOWN_TOWARD_EMA200`. EMA geometry never defines a price boundary and never closes a zone.

## Created files

- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/ema27_band_departures_r2.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/price_ema_geometry_alignment_r2.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/price_only_vs_price_ema_geometry_r2.csv`

## Modified files

- `PROJECT_QUEUE.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REPORT.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REVIEW_INSTRUCTIONS.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/TASK.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012.py`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES_R2.pine`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/r2_acceptance_tests.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/zone_bar_features_r2.csv`

## Tests run

- `git pull --ff-only origin main`
- Read `AGENTS.md`, `PROJECT_INSTRUCTIONS.md`, `.codex/TASK.md`, and mandatory `.codex/TASK_ADDENDUM.md`
- `python3 experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012.py`
- `python3 -m py_compile experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012.py`
- Determinism check: repeated generator run produced identical SHA-256 hashes for generated docs and changed/new R2 artifacts.
- R2 artifact date cutoff scan: no timestamp exceeded `2024-01-09 00:00:00` open-time boundary or `2024-01-08 23:59:59.999000` close-time boundary.
- Pine R2 scan: no `strategy(`, `plot(`, `ta.ema`, or `request.security`; Pine file is 97 lines.
- Manual accepted-boundary review CSV user-field emptiness check: PASS.
- Forbidden-path diff check for `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B: empty.
- `git diff --cached --check`
- Cached forbidden-path diff check for `docs/DEFINITIONS.md`, EXP-011, EXP-011A, EXP-011B, and EXP009A Pine: empty.

## Acceptance results

- `EXPECTED_THREE_PRIMARY_ZONES`: `FAIL` - `6 zones`
- `FIRST_ZONE_COMPACT`: `PASS` - `1 matching zone(s)`
- `NOVEMBER_SINGLE_ZONE`: `FAIL` - `2 matching zone(s)`
- `DECEMBER_JANUARY_SINGLE_ZONE`: `FAIL` - `3 matching zone(s)`
- `DECEMBER_DOWNSIDE_EXIT_ACCEPTED`: `PASS` - `True`
- `DOWNSIDE_EXIT_EARLIER_THAN_R1`: `PASS` - `R2 2023-12-13 16:00:00 vs R1 2024-01-08 20:00:00`
- `NO_POST_FAILURE_DATA_USED`: `PASS`
- `NO_WICK_ONLY_BOUNDARY_EXPANSION`: `PASS`
- `NO_DATE_HARDCODING`: `PASS`
- `NO_PRICE_HARDCODING`: `PASS`
- `NO_ZONE_ID_HARDCODING`: `PASS`
- `NO_FUTURE_PERIOD_USED`: `PASS`
- `NOVEMBER_EMA27_EXIT_UP_AWAY`: `PASS`
- `DECEMBER_EMA27_EXIT_DOWN_TOWARD_EMA200`: `PASS`
- `EMA_GEOMETRY_NEVER_DEFINES_PRICE_BOUNDARY`: `PASS`
- `EMA_DEPARTURE_CAUSAL_NO_CURRENT_BAR_IN_PRIOR_BAND`: `PASS`
- `NO_EMA_ONLY_ZONE_CLOSE`: `PASS`

## Metrics

- R1 zones: `3`
- Primary R2 zones: `6`
- Fixed-bound baseline zones: `7`
- Primary outside candidates: `13`
- Primary accepted upside exits: `4`
- Primary accepted downside exits: `2`
- Primary accepted extensions: `4`
- Primary rejected wick/single excursions: `3`
- EMA27 band departures: `10`
- Accepted price exits with same-direction EMA27 departure before/by confirmation: `4`
- Accepted price exits without same-direction EMA27 departure before/by confirmation: `2`

Primary R2 zones:

- `Z001`: initial body bounds `0.289500`-`0.303100`, final `0.287500`-`0.303100`, exit `UP`, effective `2023-11-02 04:00:00`, confirmation `2023-11-02 16:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`
- `Z002`: initial body bounds `0.356800`-`0.390500`, final `0.356800`-`0.390500`, exit `UP`, effective `2023-11-24 00:00:00`, confirmation `2023-11-24 12:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`
- `Z003`: initial body bounds `0.373900`-`0.394900`, final `0.373900`-`0.397600`, exit `UP`, effective `2023-12-04 00:00:00`, confirmation `2023-12-04 16:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`
- `Z004`: initial body bounds `0.532800`-`0.624300`, final `0.532800`-`0.624300`, exit `UP`, effective `2023-12-13 16:00:00`, confirmation `2023-12-14 04:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`
- `Z005`: initial body bounds `0.600400`-`0.667500`, final `0.600400`-`0.667500`, exit `DOWN`, effective `2023-12-17 04:00:00`, confirmation `2023-12-17 16:00:00`, `ACCEPTED_DOWNSIDE_EXIT_R2`
- `Z006`: initial body bounds `0.559900`-`0.622000`, final `0.559900`-`0.661500`, exit `DOWN`, effective `2024-01-03 16:00:00`, confirmation `2024-01-04 04:00:00`, `ACCEPTED_DOWNSIDE_EXIT_R2`

EMA27 diagnostic highlights:

- November accepted upside attempts `XA002` and `XA006` align with `EMA27_EXIT_UP_AWAY_FROM_EMA200`.
- December-January downside attempt `XA013` aligns with `EMA27_EXIT_DOWN_TOWARD_EMA200`.
- Failed price departures are annotated with same/opposite/no EMA27 departure relation in `price_ema_geometry_alignment_r2.csv`.

R1/R2 mapping:

- R1 `Z001` -> R2 `Z001`
- R1 `Z002` -> R2 `Z002`, `Z003`
- R1 `Z003` -> R2 `Z004`, `Z005`, `Z006`

## Warnings

- Primary R2 still fails the manual-structure diagnostics for three broad zones, November single zone, and December-January single zone. The EMA addendum is diagnostic and does not alter that price-only result.
- Binance spot OHLC was used for automatic outputs; manual review is expected on Bybit ADAUSDT Perpetual Contract 4H, so individual candle boundaries may differ.
- Existing unrelated EXP009A Pine modification remains unstaged and uncommitted.

## Final git status

After implementation push and before this result commit:

```text
 M experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
```

## Unrelated changes preserved

The unrelated local file below was not changed by the task, was not staged, and was not committed:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

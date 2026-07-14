# Latest Codex Result

- task_id: `EXP-012-LONG-CONTEXT-DISPUTED-PRICE-ZONES`
- task_status: `AWAITING_TW_PRICE_ZONE_REVIEW`
- implementation_commit_sha: `5b00b2ee291985dc68a9f58faefa9ea58db08c9f`
- implementation_push_status: `PUSHED origin/main`
- result_commit_status: `PUSHED origin/main`

## Summary

Implemented EXP-012 as a new research-only experiment that detects causal horizontal disputed price zones inside LONG context on ADAUSDT 4H for `2023-10-18` through `2024-01-08`.

The detector uses OHLC-derived EMA27/EMA200 context diagnostics, causal upper/lower price bounds, failed outside-close boundary expansion, and six-bar accepted outside movement. It does not create trading entries, exits, stops, PnL, backtest, forecasts, Technical Ratings, ZigZag, clustering, or BACKBONE_C logic.

EXP-012 produced 3 zones and is ready for TradingView price-zone review.

## Created files

- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/TASK.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REPORT.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REVIEW_INSTRUCTIONS.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012.py`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES.pine`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/acceptance_tests.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/long_context_disputed_zones.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/manual_zone_review.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/r5_zone_mapping.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/zone_bar_features.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/zone_boundary_events.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/zone_exit_attempts.csv`

## Modified files

- `PROJECT_QUEUE.md`

## Tests run

- `git pull --ff-only origin main`
- `python3 experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012.py`
- `python3 -m py_compile experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012.py`
- Determinism check: repeated generator run produced identical SHA-256 hashes for generated docs and artifacts.
- Date cutoff scan: no artifact timestamp exceeded `2024-01-09 00:00:00` open-time boundary or `2024-01-08 23:59:59.999000` close-time boundary.
- Pine scan: no `strategy(`, `plot(`, `ema27`, `ema200`, or `showEMA`; Pine file is 72 lines.
- Manual review CSV user-field emptiness check: PASS.
- Forbidden-path diff check for `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B: empty.
- `git diff --cached --check`
- Cached forbidden-path diff check for `docs/DEFINITIONS.md`, EXP-011, EXP-011A, EXP-011B, and EXP009A Pine: empty.

## Acceptance results

- `EXPECTED_THREE_ZONES`: `PASS` — `3 zones`
- `FIRST_ZONE_PRESERVED`: `PASS` — `1 matching zone(s): Z001`
- `NOVEMBER_SINGLE_ZONE`: `PASS` — `1 matching zone(s): Z002`
- `DECEMBER_JANUARY_SINGLE_ZONE`: `PASS` — `1 matching zone(s): Z003`
- `LC003_EARLIER_DOWNSIDE_EXIT_THAN_R5`: `FAIL` — `zone 2024-01-08 20:00:00 vs R5 2024-01-06 16:00:00`
- `NO_DATE_HARDCODING`: `PASS`
- `NO_PRICE_BOUND_HARDCODING`: `PASS`
- `NO_SECTION_ID_HARDCODING`: `PASS`
- `NO_FUTURE_PERIOD_USED`: `PASS`

## Metrics

- Zones: `3`
- Exit attempts: `6`
- Accepted upside exits: `2`
- Accepted downside exits: `0`
- Failed upside exits: `3`
- Failed downside exits: `1`

Zones:

- `Z001`: R5 `LC001`, start `2023-10-31 12:00:00`, bounds `0.284500` to `0.304600`, effective exit `2023-11-01 20:00:00`, confirmation `2023-11-02 16:00:00`, `ACCEPTED_UPSIDE_EXIT`, boundary updates `0`
- `Z002`: R5 `LC002`, start `2023-11-12 16:00:00`, bounds `0.350000` to `0.415000`, effective exit `2023-12-05 16:00:00`, confirmation `2023-12-06 12:00:00`, `ACCEPTED_UPSIDE_EXIT`, boundary updates `2`
- `Z003`: R5 `LC003`, start `2023-12-11 00:00:00`, bounds `0.464300` to `0.680000`, effective marker `2024-01-08 20:00:00`, confirmation marker `2024-01-08 20:00:00`, `OPEN_AT_TRAIN_END`, boundary updates `2`

## Warnings

- `LC003_EARLIER_DOWNSIDE_EXIT_THAN_R5` failed. The horizontal price-zone detector kept Z003 open at the development-period end instead of producing an earlier accepted downside exit than R5.
- Automatic outputs use Binance spot ADAUSDT 4H; manual review is expected on Bybit ADAUSDT Perpetual Contract 4H, so individual candle boundaries may differ.
- Existing unrelated EXP009A Pine modification remains unstaged and uncommitted.

## Final git status

After implementation push and before this result update:

```text
 M experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
```

## Unrelated changes preserved

The unrelated local file below was not changed by the task, was not staged, and was not committed:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

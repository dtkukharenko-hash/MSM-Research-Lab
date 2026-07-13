# EXP-009 — Causal Move Age

## Goal

Convert the retrospective EXP-008 structure into a causal state mechanism:

- detect the beginning of a new directional movement;
- maintain the age of the active movement;
- allow at most one primary entry;
- block repeated and late entries.

Do not search for a new strategy. Do not change stop or exit. Do not calculate PnL in this first step.

## Period

Use only:

- 2023-07-01 00:00 UTC -> 2024-12-31 23:59 UTC

Do not use 2025-2026 data.

## Inputs

Allowed:

- OHLC;
- EMA27;
- EMA200;
- ATR14;
- closed bars only.

Forbidden:

- ZigZag;
- future extrema;
- retrospective move start as a causal feature;
- PnL;
- stop;
- exit;
- ML;
- 2025-2026 data.

## Reference Labels

Use the 12 major movements from EXP-008 only as reference labels for evaluation. Do not change their boundaries.
Reference labels must not enter causal features.

## Fixed Causal State

`LONG_STATE`:

- EMA27 > EMA200;
- close > EMA200;
- EMA27 slope_5 > 0;
- EMA27 slope_10 >= 0.

`SHORT_STATE`:

- EMA27 < EMA200;
- close < EMA200;
- EMA27 slope_5 < 0;
- EMA27 slope_10 <= 0.

All other bars are `NEUTRAL_STATE`.

## Fixed Start Detectors

Compare exactly:

- `START_A` — EMA context change held for two closed bars.
- `START_B` — new directed expansion.
- `START_C` — breakout after compression.

Do not add other start detectors.

## Active Move State

After a start detector fires, maintain:

- `active_move_id`
- `active_direction`
- `causal_move_start_time`
- `move_age_bars`
- `move_distance_atr`
- `primary_entry_used`
- `secondary_entry_used`

## Fixed End Rules

End active move by:

- `END_A` full EMA context flip;
- `END_B` sustained EMA27 loss;
- `END_C` timeout: age > 120 bars without a new directed extreme in the last 30 bars.

Do not optimize 120/30.

## Entry Windows

`EARLY_WINDOW`:

- age 1..12;
- distance <= 3 ATR.

`SECONDARY_WINDOW`:

- age 4..30;
- distance <= 5 ATR;
- causal pullback to EMA27 observed;
- continuation after pullback observed.

`LATE_BLOCK`:

- age > 30;
- or distance > 5 ATR;
- or both primary and secondary are used.

## Required Artifacts

- `REPORT.md`
- `experiment_009.py`
- `artifacts/causal_active_moves.csv`
- `artifacts/causal_entries.csv`
- `artifacts/start_detector_metrics.csv`
- `artifacts/reference_move_matching.csv`
- `artifacts/reference_entry_matching.csv`
- `artifacts/blocked_example_results.csv`
- `artifacts/repeated_signal_reduction.csv`
- `artifacts/causal_state_timeline.csv`
- `artifacts/EXP009_CAUSAL_MOVE_AGE.pine`
- `artifacts/EXP009_CAUSAL_MOVE_AGE_OVERVIEW.pdf`

## Verdict

One of:

- `CAUSAL_MOVE_AGE_FOUND`
- `PARTIAL_CAUSAL_MOVE_AGE`
- `NO_CAUSAL_MOVE_AGE`
- `REFERENCE_BOUNDARIES_TOO_AMBIGUOUS`
- `DATA_INSUFFICIENT`

## Restrictions

- Do not calculate PnL.
- Do not use stop or exit.
- Do not use 2025-2026.
- Do not use reference labels as predictors.
- Do not optimize parameters.
- Do not change start detectors after seeing results.
- Do not modify Irobot.
- Do not modify `docs/DEFINITIONS.md`.

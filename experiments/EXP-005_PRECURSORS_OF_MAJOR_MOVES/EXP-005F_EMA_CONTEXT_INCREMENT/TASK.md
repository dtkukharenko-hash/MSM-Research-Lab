# EXP-005F - EMA Context Increment

## Status

DONE / REPORT_READY

## Goal

Check whether EMA27 and EMA200 context adds causally available information for separating future major movements from matched non-major events beyond the already tested OHLC feature `pre_net_return_atr`.

This is the last research test in this branch before deciding whether to freeze a simple rule or close the precursor search on the current event set.

## Data

Use the same 60 EXP-005D event points:

- 15 major starts.
- 45 matched non-major events.
- Same `event_time`.
- Same `match_group`.
- Same directions.

Research period:

- `2023-07-01 00:00 UTC` to `2025-07-01 00:00 UTC`

True holdout, not opened:

- `2025-07-01 04:00 UTC` to `2026-07-01 00:00 UTC`

Source:

- Irobot/backtester read-only.

## Allowed Features

Baseline OHLC:

- `pre_net_return_atr`, 30-bar window.

EMA27 at `t-1`:

- `price_minus_ema27_atr`
- `ema27_slope_5`
- `ema27_slope_10`
- `ema27_slope_change`
- `fraction_last10_above_ema27`
- `number_of_ema27_crosses_last20`
- `distance_change_to_ema27_last10`

EMA200 at `t-1`:

- `price_minus_ema200_atr`
- `ema200_slope_10`
- `ema200_slope_30`
- `fraction_last30_above_ema200`
- `number_of_ema200_crosses_last50`
- `distance_change_to_ema200_last20`

EMA27/EMA200 relation:

- `ema27_minus_ema200_atr`
- `ema27_above_ema200`
- `ema27_ema200_distance_change_last20`
- `price_between_ema27_ema200`
- `ema27_turning_against_previous_state`

EMA features are computed only from closed bars before `event_time`. The event bar is not included.

Do not add other features.

## Targets

Primary target:

- `MAJOR = 1`
- `MATCHED_NON_MAJOR = 0`

Secondary target:

- H=30 `severity_score` from EXP-005D, recomputed with the same full-event robust normalization used in EXP-005D.

## Fixed Models

Classification:

- Model 0: `pre_net_return_atr`, logistic regression.
- Model 1: EMA27-only features, L2 logistic regression.
- Model 2: EMA27 + EMA200 + relation features, L2 logistic regression.
- Model 3: `pre_net_return_atr` + full EMA context, L2 logistic regression.

Fixed settings:

- `C = 1.0`
- `class_weight = balanced`
- no hyperparameter tuning

Severity:

- Ridge regression alpha `1.0`.
- Only Model 0 and Model 3.

## Validation

Two required schemes:

1. Group-aware OOF: leave one match group out.
2. Temporal validation: same split as EXP-005E.
   - TRAIN: `M01-M10`
   - TEST: `M11-M15`

Scaler is fit on train only.

## Metrics

Classification:

- ROC-AUC
- PR-AUC
- balanced accuracy
- Brier score
- log loss
- Spearman between predicted probability and H=30 severity
- calibration by probability quartile

Primary comparison:

- Model 3 vs Model 0.

## Verdict Options

- `EMA_INCREMENT_FOUND`
- `WEAK_EMA_INCREMENT`
- `NO_EMA_INCREMENT`
- `SELECTION_BIAS_DOMINATES`
- `DATA_INSUFFICIENT`

## Constraints

- Do not open the true holdout.
- Do not change event points.
- Do not expand features.
- Do not tune hyperparameters.
- Do not change Irobot.
- Do not change `docs/DEFINITIONS.md`.
- Do not build a trading strategy.

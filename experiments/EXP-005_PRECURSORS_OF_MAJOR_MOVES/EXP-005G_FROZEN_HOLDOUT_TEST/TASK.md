# EXP-005G - Frozen Holdout Test

## Status

DONE / BLOCKED

## Goal

Run a one-time confirmatory test of the frozen EXP-005F Model 3 specification on the untouched holdout period.

## Holdout

Holdout period:

- `2025-07-01 04:00 UTC` to `2026-07-01 00:00 UTC`

Research period:

- `2023-07-01 00:00 UTC` to `2025-07-01 00:00 UTC`

Research may be used only to train the already frozen model.

## Frozen Model Specification

Use exactly EXP-005F Model 3:

- target: `MAJOR = 1`, `MATCHED_NON_MAJOR = 0`
- logistic regression
- L2 penalty
- `C = 1.0`
- `class_weight = balanced`
- scaler fit only on research data
- no threshold optimization

Features:

- `pre_net_return_atr`
- `price_minus_ema27_atr`
- `ema27_slope_5`
- `ema27_slope_10`
- `ema27_slope_change`
- `fraction_last10_above_ema27`
- `number_of_ema27_crosses_last20`
- `distance_change_to_ema27_last10`
- `price_minus_ema200_atr`
- `ema200_slope_10`
- `ema200_slope_30`
- `fraction_last30_above_ema200`
- `number_of_ema200_crosses_last50`
- `distance_change_to_ema200_last20`
- `ema27_minus_ema200_atr`
- `ema27_above_ema200`
- `ema27_ema200_distance_change_last20`
- `price_between_ema27_ema200`
- `ema27_turning_against_previous_state`

All features are calculated at `t-1`; the event bar is not included.

## Critical Event-Generation Rule

Holdout may not be tested only on known major movements.

Before scoring or labeling holdout outcomes, EXP-005G must causally generate the full set of holdout candidate event points using the same event-point and matched-control algorithm as EXP-005A/EXP-005B.

If the EXP-005A/EXP-005B event-generation algorithm cannot be reproduced causally and unambiguously, the verdict must be:

`HOLDOUT_BLOCKED_BY_EVENT_DEFINITION`

## Blocker Found

EXP-005A and EXP-005B do not contain a fully formalized causal event-generation algorithm with exact thresholds and constants.

The available text and artifacts specify retrospective boundaries and matched controls, but not enough to generate a complete holdout candidate event set without adding new choices.

Therefore EXP-005G is blocked before opening holdout labels.

## Required Artifacts

Blocked artifacts still record the frozen specification and the reason no holdout test was run:

- `REPORT.md`
- `experiment_005g.py`
- `artifacts/frozen_specification.json`
- `artifacts/research_training_events.csv`
- `artifacts/holdout_candidate_events.csv`
- `artifacts/holdout_labeled_events.csv`
- `artifacts/holdout_features.csv`
- `artifacts/holdout_predictions.csv`
- `artifacts/holdout_metrics.csv`
- `artifacts/model_comparison.csv`
- `artifacts/leave_one_event_out.csv`
- `artifacts/leave_one_major_out.csv`
- `artifacts/direction_results.csv`
- `artifacts/start_shift_results.csv`
- `artifacts/calibration_table.csv`
- `artifacts/holdout_roc.png`
- `artifacts/holdout_pr.png`
- `artifacts/holdout_calibration.png`
- `artifacts/holdout_probability_distribution.png`
- `artifacts/HOLDOUT_REVIEW.pine`
- `artifacts/HOLDOUT_OVERVIEW.pdf`

## Constraints

- Do not change Irobot.
- Do not change `docs/DEFINITIONS.md`.
- Do not change the MSM model.
- Do not build a strategy.
- Do not calculate profit.
- Do not correct event points using future data.
- Preserve UNKNOWN/BLOCKED statuses.

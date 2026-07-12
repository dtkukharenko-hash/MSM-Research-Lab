# EXP-005D — Continuous Outcome Severity

## Status

DONE / REPORT_READY

## Goal

Check whether OHLC state before a matched event can explain or predict the continuous strength of the subsequent movement without forcing outcomes into discrete classes.

## Context

EXP-005A found `OPPOSITE_TREND` before many major starts, but EXP-005B showed that it does not separate major starts from matched non-major turns. EXP-005C found weak taxonomy structure and suggested that major starts may be a right tail of continuous severity rather than a separate class.

EXP-005D therefore studies severity as a continuous target.

## Holdout Rule

The holdout remains untouched:

- `2025-07-01 04:00 UTC` to `2026-07-01 00:00 UTC`

EXP-005D uses only the research period:

- `2023-07-01 00:00 UTC` to `2025-07-01 00:00 UTC`

Holdout is not used for training, feature selection, model choice, metrics, visual review, threshold selection, or sanity checks.

## Events

Use the combined fixed event set:

- 15 major starts from EXP-005A.
- 45 matched non-major events from EXP-005B/EXP-005C.

Expected total:

- 60 event points.

Do not change event times.

## Inputs

Allowed:

- OHLC
- timestamp
- fixed event points

Not allowed:

- EMA
- ZigZag
- volume
- funding
- open interest
- strategy signals
- profit
- post-event features as predictors

## Targets

For horizons H=10, 20, 30, 60 calculate continuous outcome targets:

- signed close return in ATR and percent
- MFE / MAE in ATR
- signed efficiency
- net-to-path ratio
- directional persistence
- longest directional run
- time to MFE / MAE
- path length
- range
- sign changes
- local pivots
- reversal after MFE

Primary horizon:

- H=30

Primary severity score:

`severity_score = (z(signed_close_return_atr) + z(MFE_atr) + z(signed_efficiency)) / 3`

Robust z-score uses median/IQR.

## Pre-Event Features

Use only bars before the event:

- primary: 30 bars before event
- additional: 10, 20, 50 bars

No predictor may include the event bar or future bars.

## Validation

Use match-group-aware cross-validation:

- each major start and its matched non-major controls are one group;
- groups cannot be split between train and validation.

Evaluate:

- mean baseline
- linear regression
- ridge regression
- lasso regression
- huber regression
- simple nonlinear forest baseline
- single-feature pre_net_return model
- volatility-only model
- last5-only model

## Required Artifacts

- `REPORT.md`
- `experiment_005d.py`
- `artifacts/events_input.csv`
- `artifacts/pre_event_features.csv`
- `artifacts/outcome_targets.csv`
- `artifacts/severity_scores.csv`
- `artifacts/feature_correlations.csv`
- `artifacts/model_oof_predictions.csv`
- `artifacts/model_metrics.csv`
- `artifacts/group_cv_folds.csv`
- `artifacts/leave_one_out_stability.csv`
- `artifacts/start_shift_stability.csv`
- `artifacts/permutation_results.csv`
- `artifacts/severity_distribution.png`
- `artifacts/severity_rank_plot.png`
- `artifacts/predicted_vs_actual.png`
- `artifacts/feature_importance.png`
- `artifacts/SEVERITY_REVIEW.pine`
- `artifacts/SEVERITY_OVERVIEW.pdf`

## Verdict Options

- `PRE_EVENT_FEATURES_EXPLAIN_SEVERITY`
- `WEAK_CONTINUOUS_SEVERITY_SIGNAL`
- `SEVERITY_IS_POST_EVENT_ONLY`
- `RESULT_DEPENDS_ON_OUTLIERS`
- `SELECTION_BIAS_DOMINATES`
- `CAUSAL_SEVERITY_DEFINITION_BLOCKED`
- `DATA_INSUFFICIENT`

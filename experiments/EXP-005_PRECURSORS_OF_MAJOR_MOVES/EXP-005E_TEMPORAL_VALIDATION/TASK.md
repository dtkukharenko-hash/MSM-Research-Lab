# EXP-005E - Temporal Validation

## Status

DONE / REPORT_READY

## Goal

Check whether the weak EXP-005D relation between pre-event OHLC state and subsequent continuous severity transfers to a later research-period segment without changing features, event points, target, model rules, or horizons.

This is not a new feature search.

## Data

Use only the 60 fixed EXP-005D events:

- 15 major starts.
- 45 matched non-major events.

Research period:

- `2023-07-01 00:00 UTC` to `2025-07-01 00:00 UTC`

True holdout, not opened:

- `2025-07-01 04:00 UTC` to `2026-07-01 00:00 UTC`

## Temporal Split

Sort match groups by the time of their major event.

Use a fixed temporal split:

- TRAIN: first 70% of match groups.
- TEMPORAL TEST: last 30% of match groups.

Do not shuffle groups.

All events from one match group must stay in only one split.

## Fixed Target

Use H=30 severity score from EXP-005D:

`severity_score = (z(signed_close_return_atr) + z(MFE_atr) + z(signed_efficiency)) / 3`

Robust normalization parameters for each target component:

- median
- IQR

must be computed on TRAIN only and then applied to TEMPORAL TEST.

## Fixed Predictor Models

Model A:

- predictor: `pre_net_return_atr`
- window: 30 bars
- model: simple linear regression

Model B:

- predictor: `pre_signed_efficiency`
- window: 30 bars
- model: simple linear regression

Model C:

- predictors: `pre_net_return_atr`, `pre_signed_efficiency`
- model: ridge regression
- fixed alpha: `1.0`

Baseline:

- TRAIN mean severity

Do not use forest, boosting, lasso, alpha tuning, feature selection, or any new predictor.

## Primary Test

Primary result:

- Model A on TEMPORAL TEST.

Metrics:

- Spearman
- Pearson
- R2
- MAE
- RMSE
- coefficient sign
- predicted severity by quartile
- actual severity by prediction quartile

## Concentration Checks

On TEMPORAL TEST:

- remove top-1 actual severity;
- remove top-1 prediction;
- remove one match group at a time;
- recompute Spearman and R2.

Do not select the best variant.

## Event-Time Shift Check

Only for Model A:

- recompute `pre_net_return_atr` at `t-3`, `t`, and `t+3`.
- train the model separately on TRAIN for each fixed shift.
- do not select the best shift.

## Non-Major Test

Secondary exploratory check:

- train Model A only on TRAIN non-major events;
- test on TEMPORAL TEST non-major events;
- use the same trained coefficient to rank TEMPORAL TEST major events.

## Required Artifacts

- `TASK.md`
- `REPORT.md`
- `experiment_005e.py`
- `artifacts/temporal_split.csv`
- `artifacts/train_parameters.json`
- `artifacts/temporal_test_predictions.csv`
- `artifacts/temporal_metrics.csv`
- `artifacts/leave_one_group_out_test.csv`
- `artifacts/start_shift_temporal.csv`
- `artifacts/temporal_predicted_vs_actual.png`
- `artifacts/temporal_rank_plot.png`

## Verdict Options

- `TEMPORAL_SIGNAL_SURVIVES`
- `WEAK_TEMPORAL_SIGNAL`
- `NO_TEMPORAL_SIGNAL`
- `DATA_INSUFFICIENT`

## Constraints

- Do not open the true holdout.
- Do not add features.
- Do not change event boundaries.
- Do not change target definition.
- Do not make models more complex.
- Do not change Irobot.
- Do not change `docs/DEFINITIONS.md`.
- Do not build a trading strategy.

# EXP-005E - Temporal Validation

## Verdict

`WEAK_TEMPORAL_SIGNAL`

Model A preserved a positive rank relation on the later research-period segment, but the temporal test R2 stayed negative. This is not strong enough to freeze a rule for the true holdout.

## 1. Temporal Split

Match groups were sorted by major event time.

The fixed split used:

- TRAIN: first `floor(15 * 0.70) = 10` match groups.
- TEMPORAL TEST: remaining 5 match groups.

Boundary:

- last TRAIN major event: `2024-12-03 00:00 UTC` (`M10`)
- first TEMPORAL TEST major event: `2024-12-20 08:00 UTC` (`M11`)

Groups:

- TRAIN: `M01` to `M10`
- TEMPORAL TEST: `M11` to `M15`

Events:

- TRAIN: 40 events
- TEMPORAL TEST: 20 events

Composition:

- TRAIN: 10 major, 30 matched non-major
- TEMPORAL TEST: 5 major, 15 matched non-major

## 2. Target Normalization

The H=30 severity target was recomputed with TRAIN-only robust normalization.

TRAIN parameters:

- `signed_close_return_atr`: median `0.8704`, IQR `3.8007`
- `MFE_atr`: median `2.3497`, IQR `2.7046`
- `signed_efficiency`: median `0.0900`, IQR `0.3292`

The same parameters were applied to TEMPORAL TEST.

## 3. Model A Primary Test

Model A:

- feature: `pre_net_return_atr`
- window: 30 bars
- model: simple linear regression

TRAIN:

- Spearman: `0.406`
- Pearson: `0.513`
- R2: `0.264`
- coefficient: `0.0895`
- coefficient sign: positive

TEMPORAL TEST:

- Spearman: `0.376`
- Pearson: `0.177`
- R2: `-0.332`
- MAE: `0.625`
- RMSE: `1.133`
- coefficient sign: positive

The sign matches EXP-005D's positive relation, and test Spearman is above 0.25, but the test R2 is below zero.

## 4. Prediction Quartiles

Model A TEMPORAL TEST by predicted severity quartile:

| Quartile | n | Predicted mean | Actual mean | Actual median |
|---|---:|---:|---:|---:|
| Q1 | 5 | -0.422 | 0.824 | 0.106 |
| Q2 | 5 | -0.280 | -0.145 | -0.162 |
| Q3 | 5 | 0.188 | 0.491 | 0.482 |
| Q4 | 5 | 0.656 | 1.050 | 1.091 |

The top predicted quartile has higher actual severity than the bottom predicted quartile, but the ordering is not monotonic because Q1 contains high-severity cases.

## 5. Other Fixed Models

TEMPORAL TEST:

- Baseline R2: `-0.209`
- Model B (`pre_signed_efficiency`): Spearman `0.044`, R2 `-0.190`
- Model C (`pre_net_return_atr` + `pre_signed_efficiency`, ridge alpha 1.0): Spearman `0.373`, R2 `-0.333`

Model C did not improve over Model A.

## 6. Concentration Checks

Model A TEMPORAL TEST:

- all test events: Spearman `0.376`, R2 `-0.332`
- remove top-1 actual severity: Spearman `0.586`, R2 `0.113`
- remove top-1 prediction: Spearman `0.314`, R2 `-0.347`

Leave-one-match-group-out:

- remove `M11`: Spearman `0.303`, R2 `-0.447`
- remove `M12`: Spearman `0.203`, R2 `-0.444`
- remove `M13`: Spearman `0.529`, R2 `-0.024`
- remove `M14`: Spearman `0.318`, R2 `-0.339`
- remove `M15`: Spearman `0.441`, R2 `-0.299`

The positive Spearman is not created by one obvious event or group, but R2 remains mostly negative.

## 7. Event-Time Shift Stability

Model A shift check:

| Shift | Coefficient sign | Spearman | R2 |
|---:|---|---:|---:|
| t-3 | positive | 0.531 | -0.245 |
| t | positive | 0.376 | -0.332 |
| t+3 | positive | 0.592 | -0.238 |

The coefficient sign and rank relation stay positive across `t-3/t/t+3`, but R2 remains negative for every shift. This supports weak temporal rank stability, not a strong predictive rule.

## 8. Non-Major Secondary Test

Model A trained only on TRAIN non-major events:

- TEMPORAL TEST non-major Spearman: `0.714`
- TEMPORAL TEST non-major R2: `0.110`
- coefficient: `0.1163`

The same fitted coefficient ranked TEMPORAL TEST major events poorly:

- major-only Spearman: `-0.300`

This suggests that the relation may be stronger inside matched non-major outcomes than for ranking later major starts.

## 9. Answers

1. The temporal split used `M01-M10` for TRAIN and `M11-M15` for TEMPORAL TEST.
2. TRAIN has 40 events; TEMPORAL TEST has 20 events.
3. Model A kept a positive Spearman of `0.376` on the later research segment.
4. The coefficient sign stayed positive.
5. Test R2 is not positive; it is `-0.332`.
6. Rank order partially survived, but quartiles are not monotonic.
7. The result does not depend on a single obvious event or group, but it remains weak.
8. The `t-3/t/t+3` shift check keeps positive Spearman and positive coefficient signs, with negative R2 throughout.
9. The relation works better inside non-major events, but does not rank test major events well.
10. Do not freeze a rule for the true holdout yet.

## 10. Artifacts

- `artifacts/temporal_split.csv`
- `artifacts/train_parameters.json`
- `artifacts/temporal_test_predictions.csv`
- `artifacts/temporal_metrics.csv`
- `artifacts/leave_one_group_out_test.csv`
- `artifacts/start_shift_temporal.csv`
- `artifacts/temporal_predicted_vs_actual.png`
- `artifacts/temporal_rank_plot.png`

## Constraints Check

- The true holdout was not opened.
- No new features were added.
- Event points were not changed.
- The target definition was not changed.
- Models were not optimized or made more complex.
- Irobot was used read-only.
- `docs/DEFINITIONS.md` was not changed.
- No trading strategy was built.

# EXP-005F - EMA Context Increment

## Verdict

`EMA_INCREMENT_FOUND`

EMA context adds diagnostic information over the fixed OHLC baseline `pre_net_return_atr` on the current 60-event research set.

This does not open the true holdout and does not create a trading rule. It freezes a candidate Model 3 specification for a separate future holdout test.

## 1. Data And Split

Events:

- 60 fixed EXP-005D events
- 15 major starts
- 45 matched non-major events

Research period:

- `2023-07-01 00:00 UTC` to `2025-07-01 00:00 UTC`

True holdout not opened:

- `2025-07-01 04:00 UTC` to `2026-07-01 00:00 UTC`

Temporal split:

- TRAIN: `M01-M10`, 40 events, 10 major and 30 matched non-major
- TEST: `M11-M15`, 20 events, 5 major and 15 matched non-major

## 2. Fixed Model Specification

Model 0:

- `pre_net_return_atr`
- 30-bar window
- logistic regression, balanced class weights

Model 3:

- `pre_net_return_atr`
- EMA27 context
- EMA200 context
- EMA27/EMA200 relation features
- logistic regression, L2
- `C = 1.0`
- balanced class weights

All EMA features use closed bars before `event_time`; the event bar is not included.

## 3. Main Classification Results

Group-aware OOF:

| Model | ROC-AUC | PR-AUC | Balanced accuracy | Brier | Log loss |
|---|---:|---:|---:|---:|---:|
| Model 0 | 0.530 | 0.279 | 0.500 | 0.250 | 0.694 |
| Model 1 | 0.449 | 0.233 | 0.444 | 0.261 | 0.712 |
| Model 2 | 0.787 | 0.588 | 0.689 | 0.181 | 0.547 |
| Model 3 | 0.782 | 0.580 | 0.689 | 0.184 | 0.554 |

Temporal TEST:

| Model | ROC-AUC | PR-AUC | Balanced accuracy | Brier | Log loss |
|---|---:|---:|---:|---:|---:|
| Model 0 | 0.533 | 0.395 | 0.500 | 0.251 | 0.695 |
| Model 1 | 0.720 | 0.535 | 0.567 | 0.214 | 0.609 |
| Model 2 | 0.773 | 0.630 | 0.700 | 0.164 | 0.484 |
| Model 3 | 0.773 | 0.614 | 0.700 | 0.164 | 0.483 |

Primary comparison:

- temporal ROC-AUC improvement Model 3 over Model 0: `+0.240`
- group-aware OOF ROC-AUC Model 3: `0.782`
- temporal PR-AUC Model 3: `0.614`, above test prevalence `0.250`

## 4. EMA27 Context

EMA27-only Model 1 improved temporal ROC-AUC over Model 0:

- Model 1 temporal ROC-AUC: `0.720`
- Model 0 temporal ROC-AUC: `0.533`

But Model 1 did not hold up in group-aware OOF:

- Model 1 group OOF ROC-AUC: `0.449`

Conclusion:

EMA27 context alone is not stable enough as the main explanation.

## 5. EMA200 And Relation Context

Adding EMA200 and EMA27/EMA200 relation features changed the result materially:

- Model 2 group OOF ROC-AUC: `0.787`
- Model 2 temporal ROC-AUC: `0.773`

Model 3 was almost identical to Model 2, which means most of the increment came from EMA context, not from the OHLC baseline.

## 6. Calibration And Concentration

Temporal Model 3 predicted-probability quartiles:

| Quartile | n | Mean probability | Major rate | Major count |
|---|---:|---:|---:|---:|
| Q1 | 5 | 0.059 | 0.000 | 0 |
| Q2 | 5 | 0.175 | 0.200 | 1 |
| Q3 | 5 | 0.332 | 0.400 | 2 |
| Q4 | 5 | 0.777 | 0.400 | 2 |

The top quartile contains more major events than the bottom quartile.

However, Q3 and Q4 have the same major count. This is useful evidence of separation, not a clean calibrated probability model.

## 7. Leave-One-Group And Major Removal

Temporal TEST, Model 3 after removing one match group:

| Removed group | ROC-AUC | PR-AUC |
|---|---:|---:|
| M11 | 0.917 | 0.817 |
| M12 | 0.750 | 0.625 |
| M13 | 0.729 | 0.566 |
| M14 | 0.667 | 0.427 |
| M15 | 0.812 | 0.695 |

After removing one major event:

| Removed major | ROC-AUC | PR-AUC |
|---|---:|---:|
| M11 | 0.883 | 0.685 |
| M12 | 0.767 | 0.613 |
| M13 | 0.733 | 0.546 |
| M14 | 0.717 | 0.421 |
| M15 | 0.767 | 0.613 |

The result is weaker when `M14` is removed, but the Model 3 ROC-AUC remains above 0.65 in every leave-one-group and leave-one-major check.

## 8. LONG / SHORT Check

Temporal TEST by direction:

- LONG Model 3 ROC-AUC: `0.852`, PR-AUC `0.810`
- SHORT Model 3 ROC-AUC: `0.917`, PR-AUC `0.833`

Both directions show separation in this diagnostic split. No separate directional rule was created.

## 9. Event-Time Shift Check

Temporal TEST:

| Shift | Model | ROC-AUC | PR-AUC | Balanced accuracy |
|---:|---|---:|---:|---:|
| t-3 | Model 0 | 0.533 | 0.284 | 0.533 |
| t-3 | Model 3 | 0.893 | 0.811 | 0.767 |
| t | Model 0 | 0.533 | 0.395 | 0.500 |
| t | Model 3 | 0.773 | 0.614 | 0.700 |
| t+3 | Model 0 | 0.373 | 0.235 | 0.500 |
| t+3 | Model 3 | 0.800 | 0.750 | 0.767 |

The shift check does not reverse the conclusion. Model 3 remains above Model 0 at all three fixed shifts.

## 10. Main EMA Coefficients

Largest temporal Model 3 coefficients by absolute value:

- `number_of_ema200_crosses_last50`: `-1.308`
- `price_between_ema27_ema200`: `-1.100`
- `distance_change_to_ema27_last10`: `0.881`
- `fraction_last10_above_ema27`: `0.772`
- `distance_change_to_ema200_last20`: `-0.549`
- `fraction_last30_above_ema200`: `-0.492`
- `ema27_above_ema200`: `-0.454`
- `ema27_turning_against_previous_state`: `0.347`
- `price_minus_ema27_atr`: `0.325`
- `ema27_slope_change`: `-0.287`

Across group OOF folds, the largest EMA coefficients had stable signs:

- `number_of_ema200_crosses_last50`: negative in all folds
- `fraction_last10_above_ema27`: positive in all folds
- `price_between_ema27_ema200`: negative in all folds
- `distance_change_to_ema27_last10`: positive in all folds
- `fraction_last30_above_ema200`: negative in all folds

## 11. Severity Secondary Result

Temporal severity ridge:

| Model | R2 | Spearman | MAE | RMSE |
|---|---:|---:|---:|---:|
| Model 0 | -0.325 | 0.376 | 0.664 | 1.198 |
| Model 3 | -0.199 | 0.400 | 0.711 | 1.139 |

EMA context slightly improves R2 and Spearman for severity, but R2 remains negative. Severity prediction is not strong enough by itself.

## 12. Selection Bias Risk

The result could still reflect event-point selection because all events are retrospective. The checks reduce, but do not eliminate, that risk:

- matched groups were kept together;
- temporal TEST used later match groups only;
- leave-one-group checks stayed positive;
- t-3/t/t+3 did not reverse the conclusion.

Therefore this is a candidate increment for a future holdout test, not a confirmed causal rule.

## 13. Answers

1. EMA27 context differs on temporal validation, but EMA27 alone is not stable in group OOF.
2. EMA200 and EMA relation context add the strongest stable increment.
3. EMA context improves over `pre_net_return_atr`.
4. Group-aware and temporal results both favor Model 3 over Model 0.
5. The increment survives `t-3/t/t+3`.
6. The result does not depend on a single match group by ROC-AUC, though `M14` removal weakens PR-AUC.
7. Main contributing EMA features are EMA200 crossing count, price between EMA27/EMA200, EMA27 distance change, EMA27-above fraction, and EMA200 distance/fraction features.
8. Retrospective event-time selection remains a possible artifact; the current checks do not prove causality.
9. EMA context weakly improves severity prediction, but severity R2 is still negative.
10. Do not open the true holdout in this step. Freeze Model 3 specification for a separate future holdout task.
11. Do not close the precursor branch as negative; the branch has a fixed candidate for future validation.

## 14. Frozen Candidate For Future Holdout

Candidate:

- Model 3.
- Event target: `MAJOR = 1`, `MATCHED_NON_MAJOR = 0`.
- Features: exactly the allowed EXP-005F `pre_net_return_atr` + EMA27 + EMA200 + EMA27/EMA200 relation feature set.
- EMA timing: all EMA features computed at `t-1`, using only closed bars before event time.
- Model: L2 logistic regression.
- `C = 1.0`.
- `class_weight = balanced`.
- Scaler fit on training data only.
- No threshold optimization.

## 15. Artifacts

- `artifacts/events_with_ema_features.csv`
- `artifacts/group_oof_predictions.csv`
- `artifacts/group_oof_metrics.csv`
- `artifacts/temporal_predictions.csv`
- `artifacts/temporal_metrics.csv`
- `artifacts/model_coefficients.csv`
- `artifacts/leave_one_group_out.csv`
- `artifacts/start_shift_results.csv`
- `artifacts/calibration_table.csv`
- `artifacts/ema_feature_distributions.png`
- `artifacts/temporal_roc.png`
- `artifacts/temporal_calibration.png`
- `artifacts/EMA_CONTEXT_REVIEW.pine`

## Constraints Check

- True holdout was not opened.
- Event points were not changed.
- Features were not expanded beyond the task list.
- Hyperparameters were not tuned.
- Irobot was used read-only.
- `docs/DEFINITIONS.md` was not changed.
- No trading strategy was built.

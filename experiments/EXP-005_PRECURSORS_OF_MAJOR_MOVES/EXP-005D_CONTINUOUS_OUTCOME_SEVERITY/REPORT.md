# EXP-005D — Continuous Outcome Severity

## Verdict

`WEAK_CONTINUOUS_SEVERITY_SIGNAL`

Some pre-event OHLC features have moderate descriptive correlation with H=30 outcome severity, but group-aware out-of-fold prediction is weak. The best OOF Spearman is 0.205, and the best OOF R2 remains negative.

This does not support a strong causal or predictive severity model.

## 1. Events Used

Total events:

- 60

By source:

- major starts: 15
- matched non-major events: 45

No events were excluded for inconvenient behavior.

## 2. Exclusions

No event was excluded from the primary H=30 calculation.

All events had enough pre-event history for the 30-bar feature window.

## 3. Severity Score

Primary target:

`severity_score = (z(signed_close_return_atr) + z(MFE_atr) + z(signed_efficiency)) / 3`

The z-score is robust:

`z = (value - median) / IQR`

Components are saved in:

- `artifacts/severity_scores.csv`

## 4. Major Starts: Class Or Right Tail?

Major starts have higher median severity than matched non-major events:

- major mean H=30 severity: 0.781
- matched non-major mean H=30 severity: -0.128
- major median H=30 severity: 0.472
- matched non-major median H=30 severity: -0.330

However, non-major events also appear in the right tail. The top 10 severity events include several matched non-major events.

Conclusion:

Major starts look more like a right tail of continuous severity than a clean separate class.

## 5. Pre-Event Features Linked To Severity

Top descriptive Spearman correlations with H=30 severity:

- `new_low_count`: -0.408
- `pre_net_return_atr`: 0.367
- `distance_from_30bar_high`: -0.354
- `range_expansion_ratio`: -0.325
- `new_high_count`: 0.317
- `distance_from_30bar_low`: 0.316

These are pre-event OHLC features, available before the event point.

## 6. Group-Aware Validation

Validation uses match groups:

- each major start and its matched controls stay together;
- no group is split between train and validation.

Best OOF Spearman:

- `pre_net_return_only`: 0.205

Best OOF R2:

- `forest`: -0.006

All R2 values are below zero, so no model explains severity better than a constant baseline in squared-error terms.

## 7. Best OOF Result

Best Spearman model:

- model: `pre_net_return_only`
- OOF Spearman: 0.205
- OOF R2: -0.070

Best R2 model:

- model: `forest`
- OOF Spearman: 0.176
- OOF R2: -0.006

## 8. Baseline And Permutation

Permutation baseline for the best Spearman model:

- mean Spearman: -0.238
- max Spearman: 0.143

The best real OOF Spearman of 0.205 is above this permutation sample, but it remains below the strong-result threshold of 0.30 and has negative R2.

## 9. Top-Event Removal

Using the best Spearman model:

- no removal: Spearman 0.205, R2 -0.070
- remove top-1 severity: Spearman 0.268, R2 0.019
- remove top-3 severity: Spearman 0.225, R2 0.025

The rank signal does not disappear after removing top-1/top-3, but it remains weak.

## 10. Non-Major Only

After removing all 15 major starts:

- Spearman: 0.359
- R2: 0.037

This suggests the weak continuous signal is not only a major-vs-non-major artifact. It may exist inside matched non-major events, but the sample is still small.

## 11. Ranking Major Starts From Non-Major Training

The implemented validation does not train exclusively on non-major and then score major starts as a separate model. The non-major-only stability check shows the relation is not destroyed when major starts are removed, but a proper non-major-to-major ranking test should be a follow-up if this line continues.

## 12. LONG / SHORT

EXP-005D uses direction-normalized features and targets. Separate LONG/SHORT checks were not strong enough to justify different rules. The report keeps a unified mirrored formulation.

## 13. Event-Time Shift Stability

The top pre-event correlations were recalculated for shifts from t-3 to t+3. Signs are not perfectly stable across all shifts, especially around local turning points. This limits causal confidence.

## 14. Possible Selection Artifacts

Several top features may be affected by retrospective event selection:

- `pre_net_return_atr`
- `new_high_count`
- `new_low_count`
- distances from 30-bar high/low

They describe where the event sits inside a recent local move, which is partly entangled with how matched event points were selected.

## 15. Causal Pre-Event Severity Signal

There is a weak causal candidate signal because the features are pre-event and group-aware Spearman is positive.

There is not enough evidence for a strong causal severity model:

- OOF Spearman < 0.30
- OOF R2 < 0
- shift sensitivity remains a concern
- feature selection may still reflect event-point selection bias

## 16. Holdout Readiness

Rules are not ready for holdout.

The current result is useful for narrowing hypotheses, not for opening the untouched 12-month holdout.

## 17. Recommended Next Experiment

Recommended next step:

`EXP-005E_PRE_EVENT_SEVERITY_SIGNAL_AUDIT`

Goal:

Audit the small set of top pre-event severity features for causal availability and shift stability before any holdout test.

## Artifacts

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

## Constraints Check

- Holdout was not opened.
- Irobot was used read-only.
- `docs/DEFINITIONS.md` was not changed.
- The MSM model was not changed.
- No EMA, ZigZag, volume, funding, OI, strategy signal, or profit was used.
- Outcome features were not used as predictors.

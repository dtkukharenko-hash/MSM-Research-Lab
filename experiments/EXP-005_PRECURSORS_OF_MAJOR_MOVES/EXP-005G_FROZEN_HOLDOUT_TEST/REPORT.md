# EXP-005G - Frozen Holdout Test

## Verdict

`HOLDOUT_BLOCKED_BY_EVENT_DEFINITION`

The frozen EXP-005F Model 3 was not run on holdout outcomes.

The holdout period remains unopened for outcome labeling because EXP-005A/EXP-005B do not define a causal, exact event-generation algorithm that can enumerate a complete holdout candidate event set without adding new choices.

## 1. Event Generation

The causal event-generation step could not be reproduced unambiguously.

EXP-005A describes major movement boundaries as:

- retrospective OHLC close turning regions;
- 120-bar local context;
- not imported from prior EXP-005.

EXP-005B describes matched failed turns as:

- local turns after movement in the opposite direction;
- similar prior volatility;
- similar prior 30-bar net return;
- similar efficiency ratio;
- similar local range;
- similar previous directional duration;
- no comparable major movement after the candidate point.

These are research descriptions, not an executable event-generation specification.

Missing exact rules:

- numeric major movement thresholds;
- causal candidate turn rule;
- complete holdout candidate event-point generation rule;
- exact matched-control selection formula and admissible universe;
- formal `CENSORED` / `UNKNOWN` outcome rules;
- exact outcome horizon and completion rules for `MAJOR` / `MATCHED_NON_MAJOR` labeling.

Because of that, any generated holdout event set would require new decisions after the holdout was opened. EXP-005G therefore stops before scoring.

## 2. Holdout Candidate Events

Holdout candidate events found:

- 0

Reason:

- no causal candidate event-generation algorithm was available.

This is not a data result; it is a methodological block.

## 3. Labels

Holdout labels assigned:

- `MAJOR`: 0
- `MATCHED_NON_MAJOR`: 0
- `UNKNOWN`: 1 blocked placeholder
- `CENSORED`: 0

No actual holdout event was labeled.

## 4. Model Metrics

Model 0, Model 2, and Model 3 were not evaluated on holdout.

No ROC-AUC, PR-AUC, balanced accuracy, Brier score, log loss, or calibration metric was calculated from holdout outcomes.

## 5. EMA Increment

EMA increment was not tested on holdout.

EXP-005F remains a research-period result only.

## 6. Top-vs-Bottom Quartile

Not calculated.

Reason:

- no causally generated holdout events;
- no holdout predictions;
- no holdout labels.

## 7. Single-Event Dependence

Not calculated.

Reason:

- no holdout event set.

## 8. LONG / SHORT

Not calculated.

Reason:

- no holdout event set.

## 9. Event-Time Shift

Not calculated.

Reason:

- no fixed holdout event points exist to shift.

## 10. Coefficient Signs

The frozen EXP-005F Model 3 specification was recorded in `artifacts/frozen_specification.json`, but no holdout model application was performed.

Coefficient sign comparison on holdout is therefore not meaningful.

## 11. Independent Confirmation

The candidate was not confirmed.

This is not a rejection of the EMA hypothesis. It is a block on the independent test procedure.

## 12. Hypothesis Status

The hypothesis should not be accepted or rejected from EXP-005G.

Required next step:

Formalize event generation on the research period only, without using holdout labels or holdout outcomes.

## 13. Live Detector

No.

A live detector cannot be formulated until the event-generation rule is causal and exact.

## 14. Remaining Limitations

- EXP-005A boundaries are retrospective.
- EXP-005B matched failed turns are selected by descriptive similarity, not a fully frozen algorithm.
- A complete candidate-event universe is not defined.
- Major/non-major/censored labeling rules are not formal enough for a confirmatory holdout.
- The holdout must not be reused for tuning after this block.

## Artifacts

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

## Constraints Check

- Irobot was not changed.
- `docs/DEFINITIONS.md` was not changed.
- The MSM model was not changed.
- No strategy was built.
- No profit was calculated.
- Holdout candidate event points were not corrected by future outcomes.
- Holdout outcomes were not labeled.

# EXP-005H - Causal Event Generator

## Verdict

`EVENT_DEFINITION_BLOCKED`

EXP-005H successfully freezes a simple causal candidate event generator and runs it left-to-right on DEVELOPMENT and PSEUDO-HOLDOUT using only closed research-period bars.

The experiment cannot complete the confirmatory model test because the EXP-005A major/non-major/censored outcome definition is not formalized with exact numeric rules. Therefore pseudo-holdout labels remain `UNKNOWN / BLOCKED`, and no ROC-AUC / PR-AUC is calculated on the full causal candidate stream.

The true holdout was not opened.

## 1. Causal Reproduction Of Original Events

Original retrospective event points can only be partially reproduced causally.

Using a +/-3 bar matching tolerance:

- DEVELOPMENT known events matched: 15/38
- DEVELOPMENT retrospective-only: 23/38
- PSEUDO-HOLDOUT known events matched: 15/22
- PSEUDO-HOLDOUT retrospective-only: 7/22

Pseudo-holdout known major starts:

- matched: 4/5
- retrospective-only: 1/5 (`M14`)

This means the causal generator captures part of the retrospective event structure, but not enough to claim that the old event set was fully causal.

## 2. RETROSPECTIVE_ONLY Share

Pseudo-holdout retrospective-only share:

- 7/22 = 31.8%

Development retrospective-only share:

- 23/38 = 60.5%

The development share is high because many EXP-005A/005B points were selected retrospectively around turning regions rather than by a frozen left-to-right rule.

## 3. Frozen Generator Specification

The frozen specification is saved in:

- `artifacts/causal_event_specification.json`

LONG candidate at closed bar `t`:

1. `pre_net_return_atr_30 <= -2.0`
2. `close[t] > close[t-1]`
3. `close[t] - EMA27[t] > close[t-3] - EMA27[t-3]`
4. `(close[t] - EMA27[t]) / ATR14[t] >= -1.5`
5. `number_of_ema200_crosses_last50 <= 12`

SHORT is the mirror:

1. `pre_net_return_atr_30 >= 2.0`
2. `close[t] < close[t-1]`
3. `close[t] - EMA27[t] < close[t-3] - EMA27[t-3]`
4. `(close[t] - EMA27[t]) / ATR14[t] <= 1.5`
5. `number_of_ema200_crosses_last50 <= 12`

Cooldown:

- at least 6 bars between any two generated candidates;
- at least 12 bars between same-direction candidates.

## 4. DEVELOPMENT Candidates

DEVELOPMENT period:

- `2023-07-01 00:00 UTC` to `2024-12-19 23:59 UTC`

Generated candidates:

- total: 130
- LONG: 65
- SHORT: 65

The generator is symmetric by count on DEVELOPMENT.

## 5. PSEUDO-HOLDOUT Candidates

PSEUDO-HOLDOUT period:

- `2024-12-20 00:00 UTC` to `2025-07-01 00:00 UTC`

Generated candidates:

- total: 41
- LONG: 26
- SHORT: 15

Candidate rate:

- 6.47 events/month

This satisfies the count requirement of at least 20 pseudo-holdout candidates, but labels are blocked.

## 6. Outcome Labels

Pseudo-holdout generated candidates:

- `MAJOR`: 0 confirmed
- `NON_MAJOR`: 0 confirmed
- `UNKNOWN`: 41
- `CENSORED`: 0

Reason:

EXP-005A does not provide a numeric major outcome definition with exact thresholds, horizon, completion rule, and censored rule. Assigning labels now would require a new conceptual decision after pseudo-holdout generation.

## 7. Event Frequency

Pseudo-holdout event frequency:

- 41 events across about 6.34 months
- 6.47 events/month

This is not an excessive event stream, but it is much denser than the old retrospective major-start list.

## 8. EMA Increment On Candidate Stream

Not calculated.

Reason:

- pseudo-holdout labels are blocked;
- all generated candidates remain `UNKNOWN`;
- ROC-AUC and PR-AUC require `MAJOR` / `NON_MAJOR` labels.

EXP-005F's EMA increment therefore remains a research-event-set result, not a causal candidate-stream result.

## 9. Model 3 Versus Model 0

Not calculated on the full candidate stream.

The script does generate frozen Model 3 probabilities for pseudo-holdout candidates in:

- `artifacts/pseudo_holdout_predictions.csv`

These are descriptive only. They do not support a verdict without outcome labels.

## 10. LONG / SHORT Symmetry

The generator is explicitly mirrored.

Observed counts:

- DEVELOPMENT: LONG 65, SHORT 65
- PSEUDO-HOLDOUT: LONG 26, SHORT 15

The pseudo-holdout imbalance reflects market path in that period, not separate directional rules.

## 11. Dependence On One Event

Not calculated.

Reason:

- no major labels are assigned;
- leave-one-major-out is blocked.

## 12. Holdout Readiness

Not ready.

The causal event generator itself is now explicit and reproducible, but the outcome definition is still blocked. A true holdout test must wait until the major/non-major/censored label rule is formalized on research only.

## 13. Remaining Limitations

- The generator was designed as a minimal approximation of the old event structure, not as a proof of market causality.
- Only 15/38 development known events were matched within +/-3 bars.
- 31.8% of pseudo-holdout known retrospective events remain `RETROSPECTIVE_ONLY`.
- Outcome labels are blocked by nonformalized EXP-005A major definition.
- Model metrics are therefore unavailable on the causal candidate stream.
- True holdout remains closed.

## Artifacts

- `artifacts/causal_event_specification.json`
- `artifacts/development_events.csv`
- `artifacts/pseudo_holdout_candidates.csv`
- `artifacts/pseudo_holdout_labels.csv`
- `artifacts/pseudo_holdout_predictions.csv`
- `artifacts/event_matching.csv`
- `artifacts/generator_metrics.csv`
- `artifacts/model_metrics.csv`
- `artifacts/leave_one_major_out.csv`
- `artifacts/candidate_timeline.png`
- `artifacts/probability_distribution.png`
- `artifacts/CAUSAL_EVENT_REVIEW.pine`
- `artifacts/CAUSAL_EVENT_OVERVIEW.pdf`

## Constraints Check

- True holdout was not opened.
- Irobot was used read-only.
- `docs/DEFINITIONS.md` was not changed.
- The MSM model was not changed.
- No strategy was built.
- No profit was calculated.

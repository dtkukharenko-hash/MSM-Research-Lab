# EXP-005H - Causal Event Generator

## Status

DONE / BLOCKED

## Goal

Formalize a causal candidate event generator for the EXP-005F model.

The generator must process closed ADAUSDT 4H bars from left to right and must not know whether a future major movement will occur.

## Periods

Research only:

- `2023-07-01 00:00 UTC` to `2025-07-01 00:00 UTC`

DEVELOPMENT:

- `2023-07-01 00:00 UTC` to `2024-12-19 23:59 UTC`

PSEUDO-HOLDOUT:

- `2024-12-20 00:00 UTC` to `2025-07-01 00:00 UTC`

True holdout remains closed and unused:

- `2025-07-01 04:00 UTC` to `2026-07-01 00:00 UTC`

## Allowed Inputs

- OHLC
- EMA27
- EMA200
- closed bars up to and including candidate close `t`
- EXP-005F Model 3 features

Not allowed:

- future bars for event generation
- ZigZag
- future-confirmed local extrema
- outcome severity
- major/non-major labels
- profit
- holdout optimization

## Frozen Causal Generator

The EXP-005H generator was frozen before pseudo-holdout matching.

LONG candidate at closed bar `t` if:

1. Prior 30-bar `pre_net_return_atr <= -2.0`.
2. The event bar closes up: `close[t] > close[t-1]`.
3. Distance to EMA27 improves in the LONG direction over 3 bars:
   `close[t] - EMA27[t] > close[t-3] - EMA27[t-3]`.
4. Price is not far below EMA27:
   `(close[t] - EMA27[t]) / ATR14[t] >= -1.5`.
5. EMA200 context is not too choppy:
   `number_of_ema200_crosses_last50 <= 12`.

SHORT candidate is the mirror:

1. Prior 30-bar `pre_net_return_atr >= 2.0`.
2. The event bar closes down: `close[t] < close[t-1]`.
3. Distance to EMA27 improves in the SHORT direction over 3 bars:
   `close[t] - EMA27[t] < close[t-3] - EMA27[t-3]`.
4. Price is not far above EMA27:
   `(close[t] - EMA27[t]) / ATR14[t] <= 1.5`.
5. EMA200 context is not too choppy:
   `number_of_ema200_crosses_last50 <= 12`.

Cooldown / de-duplication:

- minimum 6 bars between any two generated events;
- minimum 12 bars between generated events of the same direction.

## Outcome Definition Block

EXP-005A/EXP-005B do not contain a fully formalized major/non-major/censored outcome definition with numeric thresholds and completion rules.

Therefore EXP-005H can freeze a causal generator and create pseudo-holdout candidates, but cannot assign confirmatory outcome labels without a new conceptual decision.

Verdict:

`EVENT_DEFINITION_BLOCKED`

## Required Artifacts

- `REPORT.md`
- `experiment_005h.py`
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

## Constraints

- Do not open true holdout.
- Do not change Irobot.
- Do not change `docs/DEFINITIONS.md`.
- Do not build a strategy.
- Do not calculate profit.

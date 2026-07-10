# EXP-005B — Selection Bias Test

## Goal

Check whether `OPPOSITE_TREND` is a real precursor candidate for major ADAUSDT 4H movements or a mechanical artifact of selecting `start_time` near retrospective local extremes.

## Holdout Rule

The last 12 months remain untouched:

- `2025-07-01 04:00 UTC` to `2026-07-01 00:00 UTC`

The holdout must not be used for calculation, visual review, controls, threshold changes, or intermediate decisions.

## Data

- Asset: ADAUSDT
- Timeframe: 4H
- Source: Irobot/backtester, read-only
- Period used: research period only, `2023-07-01 00:00 UTC` to `2025-07-01 00:00 UTC`
- Inputs: OHLC and time only

## Not Used

- EMA
- ZigZag
- volume
- funding
- open interest
- strategy logic
- profit
- holdout

## Hypotheses

H1:

`OPPOSITE_TREND` occurs before future major movements more often than before similar local turns that do not produce a major movement.

H0:

`OPPOSITE_TREND` is a result of selecting a point near a local extreme and occurs just as often before ordinary failed turns.

## Stage 1 — Positive Cases

Use the 15 completed EXP-005A major movements as positive cases.

Do not change their boundaries.

For each positive case save:

- move_id
- direction
- start_time
- 20/30/50-bar precursor state
- start_shift_stability
- confidence

## Stage 2 — Failed Turns

For each positive case, find matched failed turns in the research period:

- local turn after movement in the opposite direction;
- similar prior volatility;
- similar prior 30-bar net return;
- similar efficiency ratio;
- similar local range;
- similar previous directional duration;
- no comparable major movement after the candidate point.

Minimum target:

- 3 failed turns per positive case, if available.

The candidate point must be identifiable by a causal rule on the bar close. Future data may be used only to assign the final label:

- `MAJOR_MOVE`
- `FAILED_TURN`

## Stage 3 — Matched Control

Use matched turning points, not random windows, as the main control.

For each failed turn save match diagnostics against the corresponding positive case.

## Stage 4 — Compare OPPOSITE_TREND

Compare positive cases and failed turns:

- `OPPOSITE_TREND` frequency on 20/30/50 bars;
- opposite net return strength;
- efficiency ratio;
- prior range;
- previous directional duration;
- last 5 bars;
- failed attempt to continue old direction.

## Stage 5 — Shift Stability

For every major start and failed turn, test the candidate point shifted by:

- t-3
- t-2
- t-1
- t
- t+1
- t+2
- t+3

Do not choose the best shift post-factum.

## Stage 6 — Causal Framing

For each point, distinguish:

- what was known on the candidate bar close;
- what required future bars;
- how many outcomes remain unknowable at the candidate close.

Do not build a trading signal.

## Required Artifacts

- `REPORT.md`
- `artifacts/major_starts.csv`
- `artifacts/failed_turns.csv`
- `artifacts/matched_turn_controls.csv`
- `artifacts/selection_bias_comparison.csv`
- `artifacts/SELECTION_BIAS_REVIEW.pine`
- `artifacts/SELECTION_BIAS_OVERVIEW.pdf`

## Verdict Options

- `PRECURSOR_SURVIVES_MATCHED_TURNS`
- `OPPOSITE_STATE_IS_SELECTION_ARTIFACT`
- `ADDITIONAL_PRECURSOR_NEEDED`
- `CAUSAL_DEFINITION_BLOCKED`
- `DATA_INSUFFICIENT`

# EXP-005A — Price State Before Major Moves

## Verdict

`OPPOSITE_STATE_CANDIDATE_FOUND`

In the research period, 12 of 15 completed major movements started after a 30-bar `OPPOSITE_TREND` price state. The same state appeared in 11 of 75 matched control windows.

This is a candidate result only. Boundaries are retrospective, and only 7 of 15 cases kept the same 30-bar state when `start_time` was shifted by ±1-3 bars.

## 1. Actual Period Used

- `data_start`: `2023-07-01 00:00 UTC`
- `research_end`: `2025-07-01 00:00 UTC`
- `holdout_start`: `2025-07-01 04:00 UTC`
- `data_end`: `2026-07-01 00:00 UTC`
- research bars: 4387
- holdout bars: 2190

The holdout period was not used for movement search, boundaries, feature calculation, controls, visual review, or intermediate decisions.

## 2. Excluded Last 12 Months

Excluded holdout:

`2025-07-01 04:00 UTC` through `2026-07-01 00:00 UTC`.

This period is reserved for future independent verification.

## 3. Major Movements In Research

Completed movements used in precursor statistics: 15.

- LONG: 9
- SHORT: 6

One right-edge candidate was marked `CENSORED` and excluded:

- `C01` SHORT, `2025-05-10 20:00` to `2025-07-01 00:00`

It reached the research boundary without independent right-side confirmation inside research.

## 4. State Counts By Direction

30-bar state before LONG starts:

- `OPPOSITE_TREND`: 7
- `CHOP`: 1
- `TRANSITION`: 1
- `RANGE`: 0
- `SAME_TREND`: 0
- `UNKNOWN`: 0

30-bar state before SHORT starts:

- `OPPOSITE_TREND`: 5
- `CHOP`: 1
- `TRANSITION`: 0
- `RANGE`: 0
- `SAME_TREND`: 0
- `UNKNOWN`: 0

Combined:

- `OPPOSITE_TREND`: 12/15 = 80.0%
- `CHOP`: 2/15 = 13.3%
- `TRANSITION`: 1/15 = 6.7%
- continuations (`SAME_TREND`): 0/15

## 5. Control Comparison

Control design:

- 5 control windows per completed movement;
- 75 control 30-bar windows total;
- research period only;
- not within 50 bars of any major start;
- not intersecting a completed major movement;
- volatility-nearest where possible.

Control 30-bar states:

- `CHOP`: 29/75
- `TRANSITION`: 17/75
- `OPPOSITE_TREND`: 11/75
- `RANGE`: 9/75
- `SAME_TREND`: 9/75

The `OPPOSITE_TREND` state was much more frequent before completed major movements than in controls:

- real starts: 12/15 = 80.0%
- controls: 11/75 = 14.7%

## 6. LONG / SHORT Mirror

The result is directionally mirrored:

- LONG often started after a downward 30-bar state.
- SHORT often started after an upward 30-bar state.

Both sides show `OPPOSITE_TREND` as the dominant precursor label.

## 7. Window Stability: 20 / 30 / 50 Bars

Real windows:

- 20-bar: `OPPOSITE_TREND` in 13/15 cases.
- 30-bar: `OPPOSITE_TREND` in 12/15 cases.
- 50-bar: `OPPOSITE_TREND` in 10/15 cases.

Control windows:

- 20-bar: `OPPOSITE_TREND` in 20/75 controls.
- 30-bar: `OPPOSITE_TREND` in 11/75 controls.
- 50-bar: `OPPOSITE_TREND` in 12/75 controls.

The candidate survives the 20/30/50 comparison, but it weakens on 50-bar windows.

## 8. Start-Time Shift Stability

For each completed move, the 30-bar class was recalculated with `start_time` shifted by ±1-3 bars.

- stable class: 7/15
- changed class: 8/15

This is the main weakness of the result. The broad opposite-state pattern is frequent, but exact classification is sensitive around several retrospective starts.

## 9. Counterexamples

30-bar counterexamples:

- `M05` LONG: `TRANSITION`
- `M08` LONG: `CHOP`
- `M12` SHORT: `CHOP`

Shift-sensitive examples:

- `M01`, `M02`, `M04`, `M05`, `M10`, `M12`, `M14` changed state under at least some ±1-3 bar shifts.

## 10. Retrospective Selection Risks

The following may be partly produced by hindsight:

- The start is selected at a retrospective turning region, so the preceding 30 bars naturally tend to contain opposite movement.
- `OPPOSITE_TREND` may partly reflect the method of selecting local close extrema.
- Exact class assignment can change when the start is shifted a few bars.

The control comparison reduces, but does not remove, this risk.

## 11. Can We State The Claim?

A cautious claim is justified for the research period:

Major ADAUSDT 4H movements in the research period often began after an OHLC-only opposite price state.

This is not a trading rule, not a live detector, and not a model change.

## 12. Holdout Questions For Later

Future holdout test should check:

- whether the same fixed movement-selection and state-classification rules produce `OPPOSITE_TREND` before major moves in the holdout;
- whether the real-vs-control gap remains large;
- whether start-shift stability improves or remains weak;
- whether `CHOP` counterexamples form a second state or are boundary artifacts.

## Artifacts

- `artifacts/major_moves_research_period.csv`
- `artifacts/price_state_windows.csv`
- `artifacts/control_windows.csv`
- `artifacts/start_shift_stability.csv`
- `artifacts/PRICE_STATE_PRECURSORS.pine`
- `artifacts/PRICE_STATE_PRECURSORS_OVERVIEW.pdf`

## Constraints Check

- Holdout was not used.
- Irobot was used read-only.
- `docs/DEFINITIONS.md` was not changed.
- The MSM model was not changed.
- EMA and all other indicators were not used.
- ZigZag was not used.
- No strategy, profit search, or entries were created.

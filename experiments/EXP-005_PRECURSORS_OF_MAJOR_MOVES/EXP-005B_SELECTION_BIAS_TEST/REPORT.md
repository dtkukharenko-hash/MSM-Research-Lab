# EXP-005B — Selection Bias Test

## Verdict

`OPPOSITE_STATE_IS_SELECTION_ARTIFACT`

`OPPOSITE_TREND` did not survive the matched-turn control. It appeared before failed turns at least as often as before major starts.

The result means EXP-005A found a real descriptive property of retrospective turning points, but not yet a sufficient precursor of major movement.

## 1. Failed Turns Found

Positive cases:

- 15 completed major starts from EXP-005A.

Matched failed turns:

- 45 total.
- 3 failed turns per positive case.

Failed turns were selected only from the research period:

`2023-07-01 00:00 UTC` to `2025-07-01 00:00 UTC`.

The holdout period was not used:

`2025-07-01 04:00 UTC` to `2026-07-01 00:00 UTC`.

## 2. Match Quality

Failed turns were matched to positive cases by:

- direction of the hypothetical turn;
- previous 30-bar net return;
- previous 30-bar absolute path;
- efficiency ratio;
- previous 30-bar range;
- previous directional duration.

The matched control is stricter than the random-window control in EXP-005A because every control is itself a local turn candidate, not an arbitrary market window.

## 3. OPPOSITE_TREND Frequency

| window | major starts | failed turns |
|---:|---:|---:|
| 20 bars | 13/15 = 86.7% | 30/45 = 66.7% |
| 30 bars | 12/15 = 80.0% | 38/45 = 84.4% |
| 50 bars | 10/15 = 66.7% | 21/45 = 46.7% |

The main 30-bar result does not support H1. `OPPOSITE_TREND` is slightly more frequent before failed turns than before major starts.

## 4. Does The Advantage Survive?

No.

Against matched failed turns, the 30-bar `OPPOSITE_TREND` frequency is:

- major starts: 80.0%
- failed turns: 84.4%

This supports H0: `OPPOSITE_TREND` is largely produced by selecting candidate points near local turns after an opposite move.

## 5. What Distinguishes Major Starts From Failed Turns?

The simple state label does not distinguish them.

Observed differences in matched samples:

- absolute 30-bar net return was larger before major starts on average: 0.1595 vs 0.1260;
- 30-bar range was larger before major starts on average: 0.2445 vs 0.1849;
- efficiency ratio was similar: 0.3352 for major starts vs 0.3581 for failed turns;
- prior directional duration was longer before major starts: 2.53 vs 1.29 close-steps by the current working measure.

These differences suggest that an additional magnitude or structure feature may be needed. `OPPOSITE_TREND` alone is not enough.

## 6. Shift Stability

EXP-005A major starts:

- stable under ±1-3 bar shift: 7/15.

Matched failed turns:

- stable under ±1-3 bar shift: 24/45.

The class is not uniquely stable for major starts. Failed turns often preserve the same state under small shifts as well.

## 7. Causal Framing

At the candidate bar close, the following are known:

- prior 20/30/50-bar OHLC state;
- prior net return, range, efficiency ratio, and direction changes;
- whether the bar itself is a causal turn candidate by the fixed rule.

The following require future bars:

- whether the candidate becomes `MAJOR_MOVE`;
- whether it becomes `FAILED_TURN`;
- future favorable return used only for outcome labeling.

Outcome status is therefore unknown at the candidate close for all reviewed points:

- UNKNOWN outcome at close: 60/60.

This blocks a causal precursor claim based on `OPPOSITE_TREND` alone.

## 8. Selection Artifact Assessment

EXP-005A's `OPPOSITE_TREND` finding is best interpreted as a selection artifact unless paired with additional evidence.

Reason:

- both major starts and failed turns are selected near local turn candidates;
- both naturally have opposite movement before the candidate point;
- failed turns show the same 30-bar state at comparable or higher frequency.

## 9. Can Rules Be Frozen For Holdout?

Not yet.

The movement-selection and state-classification rules can be frozen, but `OPPOSITE_TREND` alone should not be frozen as the expected precursor. Before using holdout, the next research step should define one additional OHLC-only discriminator between major starts and matched failed turns.

Candidate discriminator directions from this run:

- larger pre-turn range;
- larger absolute prior net return;
- longer prior directional duration;
- stronger evidence of old-regime exhaustion.

These are observations for the next task, not new accepted rules.

## Artifacts

- `artifacts/major_starts.csv`
- `artifacts/failed_turns.csv`
- `artifacts/matched_turn_controls.csv`
- `artifacts/selection_bias_comparison.csv`
- `artifacts/SELECTION_BIAS_REVIEW.pine`
- `artifacts/SELECTION_BIAS_OVERVIEW.pdf`

## Constraints Check

- Holdout was not used.
- Irobot was used read-only.
- `docs/DEFINITIONS.md` was not changed.
- The MSM model was not changed.
- EMA, ZigZag, volume, funding, and open interest were not used.
- No strategy, profit search, or entries were created.
